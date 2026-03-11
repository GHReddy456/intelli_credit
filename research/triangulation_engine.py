"""
Triangulation Engine — cross-references secondary research findings with
data extracted from uploaded documents.

Signal types:
  CORROBORATED  — multiple independent sources confirm the same risk (high confidence).
  DISCREPANCY   — sources disagree; manual / HITL verification strongly recommended.
  UNVERIFIED    — only one source flagging; insufficient evidence to conclude.

Runs AFTER feature engineering so it can compare external intelligence
against computed financial features and document-level extractions.
"""
from __future__ import annotations

from typing import Dict, Any, List

from loguru import logger


class TriangulationEngine:
    """Cross-reference secondary research vs document-derived features."""

    def triangulate(
        self,
        research:      Dict[str, Any],
        features:      Dict[str, Any],
        doc_summaries: List[Dict],
    ) -> Dict[str, Any]:
        logger.info("[Triangulation] Cross-referencing research vs document data")

        signals: List[Dict] = []

        news_data = research.get("news", {})
        lit_data  = research.get("litigation", {})
        promoters = research.get("promoter_names", [])

        # ── 1. Fraud corroboration / discrepancy ──────────────────────────────
        news_neg_ratio   = news_data.get("news_sentiment_score", 0.5)   # 0-1 risk
        news_has_fraud   = news_neg_ratio > 0.65
        benford_flag     = features.get("benford_deviation_score", 0) > 0.25
        circular_flag    = features.get("circular_trading_score",  0) > 0.25
        gst_flag         = features.get("gst_bank_mismatch_score", 0) > 0.25
        doc_fraud_signal = benford_flag or circular_flag or gst_flag

        if news_has_fraud and doc_fraud_signal:
            signals.append({
                "type":     "CORROBORATED",
                "severity": "HIGH",
                "signal":   "Fraud risk: external news + document analysis both flag manipulation",
                "detail":   (
                    "Both web/news sources (adverse sentiment) AND document-level analysis "
                    "(Benford deviation / circular trading / GST-bank mismatch) independently "
                    "signal fraud or financial manipulation. Multi-source corroboration."
                ),
                "sources": ["News sentiment", "Document fraud analysis"],
            })
        elif news_has_fraud and not doc_fraud_signal:
            signals.append({
                "type":     "DISCREPANCY",
                "severity": "MEDIUM",
                "signal":   "Adverse news not reflected in submitted financial documents",
                "detail":   (
                    "External sources carry high adverse sentiment but document-level fraud "
                    "indicators are low. Possible incomplete document submission or news relates "
                    "to a different entity period. Verify document completeness."
                ),
                "sources": ["News sentiment", "Document analysis"],
            })

        # ── 2. Litigation corroboration / discrepancy ─────────────────────────
        lit_count    = research.get("litigation_count", 0)
        doc_red_flags = " ".join(
            str(s.get("red_flags", "")) for s in doc_summaries
        ).lower()
        doc_has_litigation = "litigation" in doc_red_flags or "court" in doc_red_flags

        if lit_count > 2 and doc_has_litigation:
            signals.append({
                "type":     "CORROBORATED",
                "severity": "HIGH",
                "signal":   f"Litigation ({lit_count} cases) confirmed in external research AND documents",
                "detail":   (
                    f"{lit_count} litigation cases detected via web research AND reflected in "
                    "uploaded legal documents. Independent corroboration confirms legal exposure."
                ),
                "sources": ["Web research", "Uploaded legal documents"],
            })
        elif lit_count > 2 and not doc_has_litigation:
            signals.append({
                "type":     "DISCREPANCY",
                "severity": "HIGH",
                "signal":   f"Litigation found externally ({lit_count} cases) but absent from submitted documents",
                "detail":   (
                    f"{lit_count} litigation cases found via external research but NOT disclosed "
                    "in submitted documents. Selective disclosure is a material integrity risk."
                ),
                "sources": ["Web research", "Uploaded documents"],
            })

        # ── 3. Financial stress multi-source corroboration ────────────────────
        dscr     = features.get("dscr", 1.5)
        de       = features.get("debt_to_equity", 1.0)
        neg_news = news_data.get("negative_count", 0)

        if dscr < 1.0 and de > 2.5 and neg_news >= 2:
            signals.append({
                "type":     "CORROBORATED",
                "severity": "HIGH",
                "signal":   "Severe financial distress corroborated by external news coverage",
                "detail":   (
                    f"Weak financials (DSCR {dscr:.2f}x, D/E {de:.2f}x) are consistent with "
                    f"external negative news ({neg_news} adverse articles). "
                    "Multiple independent sources confirm credit distress."
                ),
                "sources": ["Financial statements", "News sentiment"],
            })

        # ── 4. Revenue underreporting — multi-tax-source corroboration ────────
        gst_mismatch = features.get("gst_bank_mismatch_score", 0)
        itr_mismatch = features.get("itr_revenue_mismatch_score", 0)

        if gst_mismatch > 0.30 and itr_mismatch > 0.30:
            signals.append({
                "type":     "CORROBORATED",
                "severity": "HIGH",
                "signal":   "Revenue underreporting: GST-bank AND ITR-revenue both diverge",
                "detail":   (
                    f"GST vs bank mismatch ({gst_mismatch:.2f}) AND ITR vs declared revenue "
                    f"mismatch ({itr_mismatch:.2f}) both indicate systematic underreporting. "
                    "Two independent tax/banking data sources agree."
                ),
                "sources": ["GST Returns", "Bank Statements", "Income Tax Returns"],
            })
        elif gst_mismatch > 0.30 and itr_mismatch <= 0.15:
            signals.append({
                "type":     "UNVERIFIED",
                "severity": "MEDIUM",
                "signal":   "GST-bank mismatch without ITR corroboration — single-source signal",
                "detail":   (
                    f"GST vs bank turnover diverges ({gst_mismatch:.2f}) but ITR figures are "
                    "consistent. Single-source signal; request full 3-year ITR to verify."
                ),
                "sources": ["GST Returns", "Bank Statements"],
            })

        # ── 5. Promoter integrity — news vs document corroboration ────────────
        promoter_risk = features.get("promoter_network_risk", 0)
        promoter_neg_news = sum(
            1 for a in news_data.get("articles", [])
            if a.get("sentiment") == "NEGATIVE" and
               any(p.split()[0].lower() in a.get("title", "").lower()
                   for p in promoters if p)
        )
        if promoter_risk > 0.5 and promoter_neg_news > 0:
            signals.append({
                "type":     "CORROBORATED",
                "severity": "HIGH",
                "signal":   "Promoter integrity questioned in both network analysis and media",
                "detail":   (
                    f"Promoter network risk score {promoter_risk:.2f} corroborated by "
                    f"{promoter_neg_news} adverse news article(s) mentioning promoter names directly."
                ),
                "sources": ["Promoter network graph", "News sentiment"],
            })

        # ── 6. Sector alignment — company performance vs sector data ──────────
        sector_risk  = research.get("sector_risk_score", 0.5)
        ebitda_m     = features.get("ebitda_margin", 0.10)
        sector_name  = research.get("sector", {}).get("sector", "targeted") \
                       if isinstance(research.get("sector"), dict) else "targeted"

        if sector_risk > 0.60 and ebitda_m < 0.08:
            signals.append({
                "type":     "CORROBORATED",
                "severity": "MEDIUM",
                "signal":   "Company underperformance consistent with sector-level stress",
                "detail":   (
                    f"Company EBITDA margin ({ebitda_m:.1%}) is below healthy levels in a sector "
                    f"already under stress (sector risk {sector_risk:.0%}). "
                    "Sector headwinds explain and amplify company-level weakness."
                ),
                "sources": ["Financial statements", "Sector research"],
            })
        elif sector_risk < 0.40 and ebitda_m < 0.05:
            signals.append({
                "type":     "DISCREPANCY",
                "severity": "HIGH",
                "signal":   f"Company underperforms despite healthy {sector_name} sector",
                "detail":   (
                    f"The {sector_name} sector appears relatively healthy (risk {sector_risk:.0%}) "
                    f"but company EBITDA is very thin ({ebitda_m:.1%}). "
                    "Company-specific issues (management, operations, one-off charges) suspected."
                ),
                "sources": ["Financial statements", "Sector research"],
            })

        # ── Aggregate ─────────────────────────────────────────────────────────
        corroborated  = [s for s in signals if s["type"] == "CORROBORATED"]
        discrepancies = [s for s in signals if s["type"] == "DISCREPANCY"]
        unverified    = [s for s in signals if s["type"] == "UNVERIFIED"]

        triang_risk = round(
            min(len(corroborated) * 0.15 + len(discrepancies) * 0.10, 0.90), 4
        )

        logger.info(
            f"[Triangulation] {len(signals)} signals — "
            f"{len(corroborated)} CORROBORATED, {len(discrepancies)} DISCREPANCY, "
            f"{len(unverified)} UNVERIFIED — risk={triang_risk:.3f}"
        )

        return {
            "signals":            signals,
            "corroborated_count": len(corroborated),
            "discrepancy_count":  len(discrepancies),
            "unverified_count":   len(unverified),
            "total_signals":      len(signals),
            "triangulation_risk": triang_risk,
            "top_corroborations": corroborated[:3],
            "top_discrepancies":  discrepancies[:3],
        }
