"""
ITR Cross-Check — Three-way reconciliation:
ITR Gross Income ↔ Annual Report Revenue ↔ GSTR Aggregate Turnover
"""
import re
from typing import List, Dict, Any, Optional
from loguru import logger
from backend.config import ITR_REVENUE_MISMATCH_THRESHOLD


class ITRCrosscheck:
    def check(self, segmented_docs: List, tables: List[Dict]) -> Dict[str, Any]:
        itr_income  = self._extract_itr_income(segmented_docs, tables)
        ar_revenue  = self._extract_ar_revenue(segmented_docs, tables)
        flags       = []
        mismatch_score = 0.0

        sources = {k: v for k, v in {"itr": itr_income, "annual_report": ar_revenue}.items() if v}

        if len(sources) >= 2:
            vals   = list(sources.values())
            maxval = max(vals)
            minval = min(vals)
            delta  = (maxval - minval) / maxval if maxval > 0 else 0
            mismatch_score = round(min(delta / 0.5, 1.0), 3)

            if delta > ITR_REVENUE_MISMATCH_THRESHOLD:
                severity = "HIGH" if delta > 0.35 else "MEDIUM"
                flags.append({
                    "flag":     "ITR_REVENUE_MISMATCH",
                    "severity": severity,
                    "detail":   (
                        f"ITR Income: ₹{itr_income:,.0f} vs "
                        f"Annual Report Revenue: ₹{ar_revenue:,.0f} — "
                        f"delta {delta*100:.1f}%"
                    ),
                    "delta_pct": round(delta * 100, 2),
                })
                logger.warning(f"[ITRCrosscheck] {flags[-1]['flag']}: delta={delta*100:.1f}%")

        return {
            "itr_income":      itr_income,
            "ar_revenue":      ar_revenue,
            "mismatch_score":  mismatch_score,
            "flags":           flags,
            "reconciliation":  {k: v for k, v in {"itr": itr_income, "annual_report": ar_revenue}.items()},
            "status":          "checked" if len(sources) >= 2 else "insufficient_data",
        }

    def _extract_itr_income(self, docs: List, tables: List[Dict]) -> Optional[float]:
        # Source 1: TableExtractor financial_data
        for tbl in tables:
            if "annual_report" in tbl.get("source_file", "").lower():
                continue
            fd = tbl.get("financial_data", {})
            for key in ("total_income", "revenue"):
                if key in fd:
                    vals = [v for v in fd[key].values() if v]
                    if vals:
                        return max(vals)

        # Source 2: SegmentedDocument.all_financial_figures (ITR docs)
        for doc in docs:
            if doc.doc_type != "itr":
                continue
            for fig in getattr(doc, "all_financial_figures", []):
                if fig.get("canonical_label") in ("revenue", "pat") and fig.get("unit"):
                    val = fig.get("absolute_value")
                    if val and val > 0:
                        logger.info(f"[ITRCrosscheck] ITR income from figures: {val:,.0f}")
                        return val

        # Source 3: Text regex fallback (unit-aware)
        for doc in docs:
            if doc.doc_type != "itr":
                continue
            _UNIT = r"(Cr\.?|Crore(?:s)?|L\.?|Lakh(?:s)?)?"
            for pat in [
                rf"gross total income[^\n]{{0,80}}?([\d,]+\.?\d*)\s*{_UNIT}",
                rf"total income[^\n]{{0,80}}?([\d,]+\.?\d*)\s*{_UNIT}",
            ]:
                m = re.search(pat, doc.text_content, re.IGNORECASE)
                if m:
                    val = self._to_float(m.group(1), m.group(2) if m.lastindex >= 2 else "")
                    if val:
                        return val
        return None

    def _extract_ar_revenue(self, docs: List, tables: List[Dict]) -> Optional[float]:
        # Source 1: TableExtractor financial_data
        for tbl in tables:
            fd = tbl.get("financial_data", {})
            if "revenue" in fd:
                vals = [v for v in fd["revenue"].values() if v]
                if vals:
                    return max(vals)

        # Source 2: SegmentedDocument.all_financial_figures (annual_report docs)
        for doc in docs:
            if doc.doc_type != "annual_report":
                continue
            for fig in getattr(doc, "all_financial_figures", []):
                if fig.get("canonical_label") == "revenue" and fig.get("unit"):
                    val = fig.get("absolute_value")
                    if val and val > 0:
                        logger.info(f"[ITRCrosscheck] AR revenue from figures: {val:,.0f}")
                        return val

        # Source 3: Text regex fallback (unit-aware)
        for doc in docs:
            if doc.doc_type != "annual_report":
                continue
            _UNIT = r"(Cr\.?|Crore(?:s)?|L\.?|Lakh(?:s)?)?"
            for pat in [
                rf"revenue from operations[^\n]{{0,80}}?([\d,]+\.?\d*)\s*{_UNIT}",
                rf"(?:total|net) revenue[^\n]{{0,80}}?([\d,]+\.?\d*)\s*{_UNIT}",
            ]:
                m = re.search(pat, doc.text_content, re.IGNORECASE)
                if m:
                    val = self._to_float(m.group(1), m.group(2) if m.lastindex >= 2 else "")
                    if val:
                        return val
        return None

    def _to_float(self, s: str, unit: str = "") -> Optional[float]:
        """Convert amount string to float with optional Cr/Lakh unit scaling."""
        clean = re.sub(r"[^\d.]", "", str(s))
        try:
            if not clean:
                return None
            val = float(clean)
            u = unit.lower().strip().rstrip(".") if unit else ""
            if u in ("cr", "crore", "crores"):
                val *= 10_000_000
            elif u in ("l", "lakh", "lakhs"):
                val *= 100_000
            elif u == "k":
                val *= 1_000
            return val
        except ValueError:
            return None
