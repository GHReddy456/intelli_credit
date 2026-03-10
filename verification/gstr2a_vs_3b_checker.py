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

            # Rule: if ITC_claimed > ITC_available → FAKE_ITC
            if itc_claimed > itc_available:
                flags.append({
                    "flag":          "FAKE_ITC",
                    "severity":      "CRITICAL" if ratio > 0.25 else "HIGH",
                    "detail":        (
                        f"ITC claimed ₹{itc_claimed:,.0f} exceeds "
                        f"ITC available in GSTR-2A ₹{itc_available:,.0f} — "
                        f"bogus ITC {ratio*100:.1f}% above eligible"
                    ),
                    "itc_available": itc_available,
                    "itc_claimed":   itc_claimed,
                    "excess_pct":    round(ratio * 100, 2),
                })
                logger.warning(f"[GSTR2A3B] FAKE_ITC detected: excess {ratio*100:.1f}%")
                mismatch_score = round(min(ratio / 0.5, 1.0), 3)
            elif ratio > GSTR2A_3B_MISMATCH_THRESHOLD:
                mismatch_score = round(min(ratio / 0.5, 1.0), 3)
                flags.append({
                    "flag":          "GSTR2A_3B_ITC_MISMATCH",
                    "severity":      "HIGH" if ratio > 0.25 else "MEDIUM",
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

            # Rule: ITC_Ratio = ITC_claimed / GST_turnover; flag if > 25%
            gst_turnover = self._extract_gst_turnover(segmented_docs)
            if gst_turnover and gst_turnover > 0:
                itc_ratio = itc_claimed / gst_turnover
                if itc_ratio > 0.25:
                    flags.append({
                        "flag":      "HIGH_ITC_TO_TURNOVER",
                        "severity":  "HIGH" if itc_ratio > 0.40 else "MEDIUM",
                        "detail":    f"ITC ratio {itc_ratio*100:.1f}% of GST turnover — unusually high (>25%)",
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
        # Source 1: TableExtractor
        for tbl in tables:
            fd = tbl.get("financial_data", {})
            if "itc_claimed" in fd:
                vals = [v for v in fd["itc_claimed"].values() if v]
                if vals:
                    return max(vals)

        # Source 2: all_financial_figures
        for doc in docs:
            if doc.doc_type != "gst":
                continue
            for fig in getattr(doc, "all_financial_figures", []):
                if fig.get("canonical_label") == "itc" and fig.get("unit"):
                    val = fig.get("absolute_value")
                    if val and val > 0:
                        return val

        # Source 3: text regex (unit-aware)
        for doc in docs:
            if doc.doc_type != "gst":
                continue
            _UNIT = r"(Cr\.?|Crore(?:s)?|L\.?|Lakh(?:s)?)?"
            for p in [
                rf"(?:itc available|eligible itc|2a)[^\n]{{0,80}}?([\d,]+\.?\d*)\s*{_UNIT}",
                rf"input tax credit available[^\n]{{0,80}}?([\d,]+\.?\d*)\s*{_UNIT}",
            ]:
                m = re.search(p, doc.text_content, re.IGNORECASE)
                if m:
                    val = self._to_float(m.group(1), m.group(2) if m.lastindex >= 2 else "")
                    if val:
                        return val
        return None

    def _extract_itc_claimed(self, docs: List, tables: List[Dict]) -> Optional[float]:
        # Source 1: all_financial_figures
        for doc in docs:
            if doc.doc_type != "gst":
                continue
            for fig in getattr(doc, "all_financial_figures", []):
                if fig.get("canonical_label") == "itc" and fig.get("unit"):
                    val = fig.get("absolute_value")
                    if val and val > 0:
                        return val

        # Source 2: text regex (unit-aware)
        for doc in docs:
            if doc.doc_type != "gst":
                continue
            _UNIT = r"(Cr\.?|Crore(?:s)?|L\.?|Lakh(?:s)?)?"
            for p in [
                rf"(?:itc claimed|itc availed|3b)[^\n]{{0,80}}?([\d,]+\.?\d*)\s*{_UNIT}",
                rf"input tax credit claimed[^\n]{{0,80}}?([\d,]+\.?\d*)\s*{_UNIT}",
            ]:
                m = re.search(p, doc.text_content, re.IGNORECASE)
                if m:
                    val = self._to_float(m.group(1), m.group(2) if m.lastindex >= 2 else "")
                    if val:
                        return val
        return None

    def _extract_gst_turnover(self, docs: List) -> Optional[float]:
        for doc in docs:
            if doc.doc_type != "gst":
                continue
            # Check all_financial_figures first
            for fig in getattr(doc, "all_financial_figures", []):
                if fig.get("canonical_label") == "gst_turnover" and fig.get("unit"):
                    val = fig.get("absolute_value")
                    if val and val > 0:
                        return val
            # Text fallback
            _UNIT = r"(Cr\.?|Crore(?:s)?|L\.?|Lakh(?:s)?)?"
            m = re.search(
                rf"aggregate turnover[^\n]{{0,80}}?([\d,]+\.?\d*)\s*{_UNIT}",
                doc.text_content, re.IGNORECASE
            )
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
