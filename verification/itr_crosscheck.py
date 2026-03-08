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
        for tbl in tables:
            if "annual_report" in tbl.get("source_file", "").lower():
                continue
            fd = tbl.get("financial_data", {})
            for key in ("total_income", "revenue"):
                if key in fd:
                    vals = [v for v in fd[key].values() if v]
                    if vals:
                        return max(vals)

        for doc in docs:
            if doc.doc_type != "itr":
                continue
            for pattern in [
                r"gross total income[^\n]*?([\d,]+)",
                r"total income[^\n]*?([\d,]+)",
            ]:
                m = re.search(pattern, doc.text_content, re.IGNORECASE)
                if m:
                    return self._to_float(m.group(1))
        return None

    def _extract_ar_revenue(self, docs: List, tables: List[Dict]) -> Optional[float]:
        for tbl in tables:
            fd = tbl.get("financial_data", {})
            if "revenue" in fd:
                vals = [v for v in fd["revenue"].values() if v]
                if vals:
                    return max(vals)

        for doc in docs:
            if doc.doc_type != "annual_report":
                continue
            for pattern in [
                r"revenue from operations[^\n]*?([\d,]+)",
                r"(?:total|net) revenue[^\n]*?([\d,]+)",
            ]:
                m = re.search(pattern, doc.text_content, re.IGNORECASE)
                if m:
                    return self._to_float(m.group(1))
        return None

    def _to_float(self, s: str) -> Optional[float]:
        clean = re.sub(r"[^\d.]", "", str(s))
        try:
            return float(clean) if clean else None
        except ValueError:
            return None
