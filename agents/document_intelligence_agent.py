"""
Document Intelligence Agent
Performs LLM-level (or fallback rule-based) analysis over segmented document sections.
Extracts qualitative flags: audit issues, board disputes, going concern, related party anomalies.
"""
import re
from typing import List, Dict, Any
from loguru import logger
from backend.config import USE_LLM, OLLAMA_BASE_URL, OLLAMA_MODEL
from backend.llm import llm_call, gemini_available as ollama_available


AUDIT_RED_FLAGS = [
    ("going_concern",         ["going concern", "material uncertainty", "doubt about ability"]),
    ("qualified_opinion",     ["qualified opinion", "except for", "qualification"]),
    ("emphasis_of_matter",    ["emphasis of matter"]),
    ("scope_limitation",      ["unable to obtain", "scope limitation", "we were unable"]),
    ("adverse_opinion",       ["adverse opinion"]),
    ("fraud_suspicion",       ["suspected fraud", "forensic", "management override"]),
    ("related_party_excess",  ["related party transactions", "arm's length", "rpt"]),
    ("contingent_large",      ["contingent liabilities", "contingent assets"]),
]

GOVERNANCE_FLAGS = [
    ("promoter_pledge",       ["pledge", "pledged shares", "promoter holding pledged"]),
    ("board_dispute",         ["resignation of director", "reconstitution", "removed from board"]),
    ("auditor_change",        ["change of auditor", "resigned as auditor", "new auditor appointed"]),
    ("regulatory_show_cause", ["show cause notice", "demand notice", "regulatory action"]),
]


class DocumentIntelligenceAgent:
    def run(self, segmented_docs: List) -> Dict[str, Any]:
        logger.info(f"[DocAgent] Analyzing {len(segmented_docs)} documents")

        audit_flags      = []
        governance_flags = []
        key_findings     = []
        section_summaries = {}

        for doc in segmented_docs:
            # ── Per-section analysis ─────────────────────────────────────
            for section in doc.sections:
                text = section.raw_text
                tl   = text.lower()

                # Audit flags
                for flag_name, keywords in AUDIT_RED_FLAGS:
                    if any(kw in tl for kw in keywords):
                        context = self._extract_context(text, keywords)
                        audit_flags.append({
                            "flag":     flag_name,
                            "severity": "HIGH" if flag_name in ("qualified_opinion", "going_concern", "adverse_opinion") else "MEDIUM",
                            "section":  section.label,
                            "source":   doc.file_name,
                            "context":  context,
                        })

                # Governance flags
                for flag_name, keywords in GOVERNANCE_FLAGS:
                    if any(kw in tl for kw in keywords):
                        context = self._extract_context(text, keywords)
                        governance_flags.append({
                            "flag":    flag_name,
                            "section": section.label,
                            "source":  doc.file_name,
                            "context": context,
                        })

            # ── Key financial findings from segment summary ───────────────
            summary = doc.segment_summary
            kf      = summary.get("key_financial_figures", {})
            if kf:
                key_findings.append({
                    "source":   doc.file_name,
                    "doc_type": doc.doc_type,
                    "figures":  kf,
                })

            section_summaries[doc.file_name] = {
                "sections_found": summary.get("sections_found", []),
                "flag_severity":  summary.get("flag_severity", "LOW"),
                "page_count":     summary.get("page_count", 0),
            }

        # ── LLM enrichment (optional) ────────────────────────────────────
        llm_summary = None
        if USE_LLM:
            llm_summary = self._llm_summarize(segmented_docs)

        # Deduplicate flags
        audit_flags      = self._dedup(audit_flags, "flag")
        governance_flags = self._dedup(governance_flags, "flag")

        high_severity = [f for f in audit_flags if f["severity"] == "HIGH"]

        logger.info(f"[DocAgent] {len(audit_flags)} audit flags, {len(governance_flags)} governance flags")

        return {
            "audit_flags":        audit_flags,
            "governance_flags":   governance_flags,
            "key_findings":       key_findings,
            "section_summaries":  section_summaries,
            "llm_summary":        llm_summary,
            "high_severity_count": len(high_severity),
            "overall_doc_risk":   "HIGH" if high_severity else ("MEDIUM" if audit_flags else "LOW"),
        }

    def _extract_context(self, text: str, keywords: List[str]) -> str:
        for kw in keywords:
            idx = text.lower().find(kw)
            if idx >= 0:
                start = max(0, idx - 80)
                end   = min(len(text), idx + 200)
                return text[start:end].strip()
        return ""

    def _dedup(self, items: List[Dict], key: str) -> List[Dict]:
        seen = set()
        result = []
        for item in items:
            k = item.get(key, "")
            if k not in seen:
                seen.add(k)
                result.append(item)
        return result

    def _llm_summarize(self, docs: List) -> str:
        """LLM audit risk summary via Ollama (phi3:mini, CPU-only friendly)."""
        if not ollama_available():
            return None
        # Build a compact context — keep under 1500 chars to stay fast on CPU
        snippets = []
        for doc in docs:
            chunk = doc.text_content[:600] if hasattr(doc, 'text_content') else ""
            if chunk:
                snippets.append(f"[{doc.doc_type}] {chunk}")
        text = " ".join(snippets)[:1500]
        prompt = (
            f"Analyse these Indian corporate document excerpts and list the top 3 credit risks "
            f"in 2-3 sentences. Focus on audit qualifications, going concern, related parties, "
            f"and fraud indicators:\n\n{text}"
        )
        return llm_call(prompt, max_tokens=180)
