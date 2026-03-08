"""
GSTR-2A vs GSTR-3B Checker
Detects excess ITC claims: if ITC_claimed > ITC_available → GST irregularity.
Also flags suspiciously large ITC ratios.
"""
import re
from typing import List, Dict, Any, Optional
from loguru import logger
from backend.config import GSTR2A_3B_MISMATCH_THRESHOLD


class GSTR2Avs3BChecker:
    def check(self, segmented_docs: List, tables: List[Dict]) -> Dict[str, Any]:
        itc_available = self._extract_itc_available(segmented_docs, tables)  # from 2A
        itc_claimed   = self._extract_itc_claimed(segmented_docs, tables)    # from 3B
        flags         = []
        mismatch_score = 0.0

        if itc_available and itc_claimed and itc_available > 0:
            excess = itc_claimed - itc_available
            ratio  = excess / itc_available if itc_available > 0 else 0

            if ratio > GSTR2A_3B_MISMATCH_THRESHOLD:
                mismatch_score = round(min(ratio / 0.5, 1.0), 3)
                severity       = "HIGH" if ratio > 0.25 else "MEDIUM"
                flags.append({
                    "flag":          "GSTR2A_3B_ITC_MISMATCH",
                    "severity":      severity,
                    "detail":        (
                        f"ITC claimed ₹{itc_claimed:,.0f} exceeds "
                        f"ITC available in 2A ₹{itc_available:,.0f} — "
                        f"excess {ratio*100:.1f}%"
                    ),
                    "itc_available": itc_available,
                    "itc_claimed":   itc_claimed,
                    "excess_pct":    round(ratio * 100, 2),
                })
                logger.warning(f"[GSTR2A3B] Excess ITC: {ratio*100:.1f}%")

            # Also check ITC-to-turnover ratio (healthy: 5-18%)
            gst_turnover = self._extract_gst_turnover(segmented_docs)
            if gst_turnover and gst_turnover > 0:
                itc_ratio = itc_claimed / gst_turnover
                if itc_ratio > 0.25:
                    flags.append({
                        "flag":      "HIGH_ITC_TO_TURNOVER",
                        "severity":  "MEDIUM",
                        "detail":    f"ITC ratio {itc_ratio*100:.1f}% of turnover — unusually high (>25%)",
                        "itc_ratio": round(itc_ratio, 4),
                    })

        return {
            "itc_available":   itc_available,
            "itc_claimed":     itc_claimed,
            "mismatch_score":  mismatch_score,
            "flags":           flags,
            "status":          "checked" if (itc_available and itc_claimed) else "insufficient_data",
        }

    def _extract_itc_available(self, docs: List, tables: List[Dict]) -> Optional[float]:
        for tbl in tables:
            fd = tbl.get("financial_data", {})
            if "itc_claimed" in fd:
                vals = [v for v in fd["itc_claimed"].values() if v]
                if vals:
                    return max(vals)
        for doc in docs:
            if doc.doc_type != "gst":
                continue
            for p in [
                r"(?:itc available|eligible itc|2a)[^\n]*?([\d,]+)",
                r"input tax credit available[^\n]*?([\d,]+)",
            ]:
                m = re.search(p, doc.text_content, re.IGNORECASE)
                if m:
                    return self._to_float(m.group(1))
        return None

    def _extract_itc_claimed(self, docs: List, tables: List[Dict]) -> Optional[float]:
        for doc in docs:
            if doc.doc_type != "gst":
                continue
            for p in [
                r"(?:itc claimed|itc availed|3b)[^\n]*?([\d,]+)",
                r"input tax credit claimed[^\n]*?([\d,]+)",
            ]:
                m = re.search(p, doc.text_content, re.IGNORECASE)
                if m:
                    return self._to_float(m.group(1))
        return None

    def _extract_gst_turnover(self, docs: List) -> Optional[float]:
        for doc in docs:
            if doc.doc_type != "gst":
                continue
            m = re.search(r"aggregate turnover[^\n]*?([\d,]+)", doc.text_content, re.IGNORECASE)
            if m:
                return self._to_float(m.group(1))
        return None

    def _to_float(self, s: str) -> Optional[float]:
        clean = re.sub(r"[^\d.]", "", str(s))
        try:
            return float(clean) if clean else None
        except ValueError:
            return None
