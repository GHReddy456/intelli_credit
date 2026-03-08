"""
GST vs Bank Statement Validator
Compares GSTR-1 declared turnover against total bank credits.
Flags significant revenue mismatch (> 15% threshold).
"""
import re
from typing import List, Dict, Any, Optional
from loguru import logger
from backend.config import GST_BANK_MISMATCH_THRESHOLD


class GSTBankValidator:
    def check(self, segmented_docs: List, tables: List[Dict]) -> Dict[str, Any]:
        gst_turnover   = self._extract_gst_turnover(segmented_docs, tables)
        bank_credits   = self._extract_bank_credits(segmented_docs, tables)
        flags          = []
        mismatch_score = 0.0

        if gst_turnover and bank_credits and bank_credits > 0:
            delta = abs(gst_turnover - bank_credits) / bank_credits
            mismatch_score = round(min(delta / 0.5, 1.0), 3)   # normalise to 0-1

            if delta > GST_BANK_MISMATCH_THRESHOLD:
                severity = "HIGH" if delta > 0.30 else "MEDIUM"
                flags.append({
                    "flag": "GST_BANK_MISMATCH",
                    "severity": severity,
                    "detail": (
                        f"GST turnover ₹{gst_turnover:,.0f} vs "
                        f"Bank credits ₹{bank_credits:,.0f} — "
                        f"delta {delta*100:.1f}% exceeds {GST_BANK_MISMATCH_THRESHOLD*100:.0f}% threshold"
                    ),
                    "gst_turnover":  gst_turnover,
                    "bank_credits":  bank_credits,
                    "delta_pct":     round(delta * 100, 2),
                })
                logger.warning(f"[GSTBankValidator] {flags[-1]['flag']}: {flags[-1]['detail']}")
        else:
            logger.info("[GSTBankValidator] Insufficient data for GST-Bank comparison")

        return {
            "gst_turnover":   gst_turnover,
            "bank_credits":   bank_credits,
            "mismatch_score": mismatch_score,
            "flags":          flags,
            "status":         "checked" if (gst_turnover and bank_credits) else "insufficient_data",
        }

    # ── Extraction helpers ─────────────────────────────────────────────────
    def _extract_gst_turnover(self, docs: List, tables: List[Dict]) -> Optional[float]:
        # Try tables first
        for tbl in tables:
            fd = tbl.get("financial_data", {})
            if "gst_turnover" in fd:
                vals = list(fd["gst_turnover"].values())
                nums = [v for v in vals if v is not None]
                if nums:
                    return max(nums)

        # Fall back to text search
        for doc in docs:
            if doc.doc_type not in ("gst", "annual_report"):
                continue
            text = doc.text_content
            patterns = [
                r"(?:aggregate turnover|outward supplies)[^\n₹Rs.]*[₹Rs.]\s*([\d,]+)",
                r"(?:total taxable value)[^\n]*?([\d,]+)",
            ]
            for p in patterns:
                m = re.search(p, text, re.IGNORECASE)
                if m:
                    return self._to_float(m.group(1))
        return None

    def _extract_bank_credits(self, docs: List, tables: List[Dict]) -> Optional[float]:
        # Sum all credit entries from bank statement tables
        total = 0.0
        found = False
        for tbl in tables:
            src = tbl.get("source_file", "").lower()
            if "bank" not in src and "statement" not in src:
                continue
            for row in tbl.get("rows", []):
                for key, val in row.items():
                    if "credit" in key.lower():
                        v = self._to_float(str(val))
                        if v:
                            total += v
                            found = True

        if found:
            return total

        # Fallback: parse text
        for doc in docs:
            if doc.doc_type != "bank_statement":
                continue
            m = re.search(r"total credits?[^\n]*?([\d,]+)", doc.text_content, re.IGNORECASE)
            if m:
                return self._to_float(m.group(1))
        return None

    def _to_float(self, s: str) -> Optional[float]:
        clean = re.sub(r"[^\d.]", "", str(s))
        try:
            return float(clean) if clean else None
        except ValueError:
            return None
