"""
Financial Consistency Engine — master cross-document verifier.
Runs all sub-checkers and returns a unified verification report.
"""
from typing import List, Dict, Any
from loguru import logger

from verification.gst_bank_validator import GSTBankValidator
from verification.itr_crosscheck import ITRCrosscheck
from verification.gstr2a_vs_3b_checker import GSTR2Avs3BChecker


class FinancialConsistencyEngine:
    def run(self, segmented_docs: List, tables: List[Dict]) -> Dict[str, Any]:
        logger.info("[Consistency] Running all financial cross-checks")

        gst_val    = GSTBankValidator()
        itr_check  = ITRCrosscheck()
        gstr_check = GSTR2Avs3BChecker()

        gst_result  = gst_val.check(segmented_docs, tables)
        itr_result  = itr_check.check(segmented_docs, tables)
        gstr_result = gstr_check.check(segmented_docs, tables)

        all_flags = (
            gst_result.get("flags", []) +
            itr_result.get("flags", []) +
            gstr_result.get("flags", [])
        )

        # Severity: count HIGH flags
        high  = sum(1 for f in all_flags if f.get("severity") == "HIGH")
        med   = sum(1 for f in all_flags if f.get("severity") == "MEDIUM")
        overall = "CRITICAL" if high >= 2 else ("HIGH" if high == 1 else ("MEDIUM" if med >= 2 else "LOW"))

        return {
            "overall_severity": overall,
            "total_flags": len(all_flags),
            "all_flags": all_flags,
            "gst_bank":  gst_result,
            "itr":       itr_result,
            "gstr2a_3b": gstr_result,
            "mismatch_scores": {
                "gst_bank_mismatch_score":   gst_result.get("mismatch_score", 0.0),
                "itr_revenue_mismatch_score": itr_result.get("mismatch_score", 0.0),
                "gstr2a_3b_mismatch_score":  gstr_result.get("mismatch_score", 0.0),
            },
        }
