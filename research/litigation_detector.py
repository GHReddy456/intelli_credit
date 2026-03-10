"""
Litigation Detector
Searches eCourts, DuckDuckGo, and uploaded legal docs for litigation.
Returns count, severity, and case summaries.
"""
import re
from typing import List, Dict, Any
from loguru import logger
from backend.config import LITIGATION_KEYWORDS


SEVERITY_KEYWORDS = {
    "CRITICAL": ["wilful defaulter", "fraud classification", "pmla", "enforcement directorate", "cbi", "insolvency", "ibc"],
    "HIGH":     ["nclt", "drt", "drat", "winding up", "recovery suit", "criminal complaint", "fir"],
    "MEDIUM":   ["cheque bounce", "section 138", "civil suit", "arbitration", "claim"],
    "LOW":      ["consumer forum", "labour dispute", "minor claim"],
}


class LitigationDetector:
    def detect(self, company_name: str, segmented_docs: List, research_data: Dict = None) -> Dict[str, Any]:
        logger.info(f"[Litigation] Detecting for: {company_name}")

        cases = []

        # 1. From uploaded legal documents
        cases.extend(self._extract_from_docs(segmented_docs))

        # 2. From web research
        candidates = self._search_web(company_name)
        for c in candidates:
            severity = self._classify_severity(c.get("text", ""))
            cases.append({
                "source":   "web_search",
                "summary":  c["summary"],
                "url":      c.get("url", ""),
                "severity": severity,
            })

        # 3. From news articles already scraped
        if research_data:
            for article in research_data.get("articles", []):
                if article.get("has_litigation_signal"):
                    sev = self._classify_severity(article.get("snippet", ""))
                    cases.append({
                        "source":   "news",
                        "summary":  article.get("title", ""),
                        "url":      article.get("url", ""),
                        "severity": sev,
                    })

        # Deduplicate
        seen = set()
        unique_cases = []
        for c in cases:
            key = c.get("summary", "")[:60]
            if key not in seen:
                seen.add(key)
                unique_cases.append(c)

        # Severity-weighted score (qualitative)
        severity_weights = {"CRITICAL": 1.0, "HIGH": 0.75, "MEDIUM": 0.4, "LOW": 0.15}
        raw_score = sum(severity_weights.get(c["severity"], 0.1) for c in unique_cases)
        litigation_score = round(min(raw_score / 5.0, 1.0), 4)   # normalise

        # Count-based litigation risk: Litigation_Risk = min(1, count / 20)
        # HIGH band when count > 15 cases
        count = len(unique_cases)
        litigation_risk = round(min(1.0, count / 20.0), 4)

        high_cases = [c for c in unique_cases if c["severity"] in ("CRITICAL", "HIGH")]

        flags = []
        if high_cases:
            flags.append({
                "flag":     "SIGNIFICANT_LITIGATION",
                "severity": "HIGH",
                "detail":   f"{len(high_cases)} high/critical severity cases found",
            })
        if count > 15:
            flags.append({
                "flag":     "LITIGATION_COUNT_HIGH",
                "severity": "HIGH",
                "detail":   f"{count} total litigation cases — high-risk band (threshold: 15)",
            })

        logger.info(f"[Litigation] Found {count} cases, score={litigation_score:.3f}, risk={litigation_risk:.3f}")

        return {
            "litigation_count":          count,
            "high_severity_count":       len(high_cases),
            "litigation_severity_score": litigation_score,
            "litigation_risk":           litigation_risk,   # min(1, count/20) formula
            "cases":                     unique_cases[:20],
            "flags":                     flags,
        }

    def _extract_from_docs(self, docs: List) -> List[Dict]:
        cases = []
        for doc in docs:
            if doc.doc_type != "legal":
                continue
            text = doc.text_content
            # Extract case number and type
            case_nos = re.findall(r"[A-Z]+\s*No\.?\s*\d+[/\\\-]\d{4}", text)
            severity = self._classify_severity(text)
            summary  = f"Legal document ({doc.file_name}): {', '.join(case_nos[:3]) or 'case reference found'}"
            cases.append({"source": "uploaded_doc", "summary": summary, "severity": severity, "url": ""})
        return cases

    def _search_web(self, company_name: str) -> List[Dict]:
        import concurrent.futures
        queries = [
            f'"{company_name}" NCLT insolvency IBC winding up',
            f'"{company_name}" DRT recovery suit debt default',
            f'"{company_name}" fraud PMLA enforcement directorate CBI',
            f'"{company_name}" wilful defaulter NPA bank',
            f'"{company_name}" court case FIR criminal complaint',
        ]

        all_results = []

        def _run_query(q: str):
            out = []
            try:
                from ddgs import DDGS
                with DDGS() as ddgs:
                    for r in ddgs.text(q, max_results=6):
                        out.append({
                            "summary": r.get("title", ""),
                            "url":     r.get("href", ""),
                            "text":    r.get("body", ""),
                        })
            except Exception as e:
                logger.warning(f"[Litigation] Query failed '{q[:40]}': {e}")
            return out

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            futures = {ex.submit(_run_query, q): q for q in queries}
            for future in concurrent.futures.as_completed(futures, timeout=25):
                try:
                    all_results.extend(future.result())
                except Exception:
                    pass

        logger.info(f"[Litigation] Web search returned {len(all_results)} raw results")
        return all_results

    def _classify_severity(self, text: str) -> str:
        tl = text.lower()
        for sev, keywords in SEVERITY_KEYWORDS.items():
            if any(kw in tl for kw in keywords):
                return sev
        return "LOW"
