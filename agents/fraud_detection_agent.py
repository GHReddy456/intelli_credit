"""
Fraud Detection Agent
Aggregates all fraud signals: circular trading + Benford + GST mismatches + bank anomalies
+ auditor remarks + layered transactions + shell entity detection.
Produces a unified fraud_risk_score (0-100).
"""
from typing import List, Dict, Any
from loguru import logger
from fraud.circular_trading_detector import CircularTradingDetector
from fraud.benford_analyzer import BenfordAnalyzer


class FraudDetectionAgent:
    def run(self, segmented_docs: List, tables: List[Dict], verification: Dict) -> Dict[str, Any]:
        logger.info("[FraudAgent] Running fraud detection")

        ct   = CircularTradingDetector()
        ba   = BenfordAnalyzer()

        ct_result  = ct.detect(segmented_docs, tables)
        ba_result  = ba.analyze(segmented_docs, tables)

        # Pull mismatch scores from verification
        ms    = verification.get("mismatch_scores", {})
        gst_m = ms.get("gst_bank_mismatch_score", 0.0)
        gstr  = ms.get("gstr2a_3b_mismatch_score", 0.0)
        itr_m = ms.get("itr_revenue_mismatch_score", 0.0)

        # Bank anomaly score from document agent flags
        bank_anomaly = self._detect_bank_anomalies(segmented_docs, tables)

        # Audit remark score — structured remarks from document segmenter
        audit_remark_score = self._compute_audit_remark_score(segmented_docs)

        # Sub-scores already computed inside ct_result
        layered_score = ct_result.get("layered_score", 0.0)
        shell_score   = ct_result.get("shell_score", 0.0)

        # Weighted composite fraud score
        fraud_score = (
            ct_result.get("circular_trading_score", 0.0) * 0.30 +
            ba_result.get("benford_deviation_score", 0.0) * 0.18 +
            gst_m                                          * 0.17 +
            gstr                                           * 0.12 +
            bank_anomaly                                   * 0.08 +
            audit_remark_score                             * 0.10 +
            layered_score                                  * 0.03 +
            shell_score                                    * 0.02
        )
        fraud_score = round(min(fraud_score, 1.0), 4)

        # ── ITC-to-turnover anomaly boost ─────────────────────────────────
        itc_flags = [f for f in verification.get("gst_bank", {}).get("flags", [])
                     if (f.get("flag") or f.get("type") or "") == "HIGH_ITC_TO_TURNOVER"]
        itc_ratio = verification.get("mismatch_scores", {}).get("itc_to_turnover_ratio", 0.0)
        if itc_ratio > 0.25 or itc_flags:
            fraud_score = round(min(fraud_score + 0.30, 1.0), 4)
            if not itc_flags:
                all_flags_extra = [{
                    "flag": "HIGH_ITC_TO_TURNOVER", "severity": "HIGH",
                    "detail": f"ITC-to-turnover ratio {itc_ratio:.2f} exceeds 0.25 threshold — possible inflated input credits",
                }]
            else:
                all_flags_extra = []
        else:
            all_flags_extra = []

        fraud_score_100 = round(fraud_score * 100, 1)

        all_flags = (
            ct_result.get("flags", []) +
            ba_result.get("flags", []) +
            verification.get("gst_bank", {}).get("flags", []) +
            verification.get("gstr2a_3b", {}).get("flags", []) +
            all_flags_extra
        )
        if audit_remark_score > 0.3:
            all_flags.append({
                "flag": "AUDIT_QUALIFICATIONS_HIGH", "severity": "HIGH",
                "detail": f"Audit remark score {audit_remark_score:.2f} — significant auditor qualifications found",
            })

        is_hard_reject = (
            ct_result.get("is_hard_reject", False) or
            fraud_score > 0.85
        )

        logger.info(
            f"[FraudAgent] fraud_score={fraud_score:.3f}, audit={audit_remark_score:.3f}, "
            f"layered={layered_score:.3f}, shell={shell_score:.3f}, hard_reject={is_hard_reject}"
        )

        return {
            "fraud_risk_score":        fraud_score_100,
            "fraud_risk_normalized":   fraud_score,
            "circular_trading":        ct_result,
            "benford":                 ba_result,
            "bank_anomaly_score":      bank_anomaly,
            "audit_remark_score":      audit_remark_score,
            "layered_transaction_score": layered_score,
            "shell_entity_score":      shell_score,
            "all_flags":               all_flags,
            "is_hard_reject":          is_hard_reject,
            # Flat fields for FeatureEngine
            "circular_trading_score":  ct_result.get("circular_trading_score", 0.0),
            "benford_deviation_score": ba_result.get("benford_deviation_score", 0.0),
        }

    def _detect_bank_anomalies(self, docs: List, tables: List[Dict]) -> float:
        """Score bank statement anomalies: cheque returns, cash spikes, EOD zeroing."""
        score = 0.0

        for doc in docs:
            if doc.doc_type != "bank_statement":
                continue
            tl = doc.text_content.lower()

            if "cheque return" in tl or "dishonor" in tl or "insufficient funds" in tl:
                score += 0.3
            if "ecs return" in tl or "nach return" in tl:
                score += 0.2
            if tl.count("cash withdrawal") > 20:   # Excessive cash withdrawals
                score += 0.2
            if "end of day balance" in tl and "0.00" in tl:   # EOD zeroing
                score += 0.15

        return round(min(score, 1.0), 4)

    # Weights for each audit remark type (sum used to derive 0-1 score)
    _AUDIT_REMARK_WEIGHTS = {
        "ADVERSE_OPINION":              1.0,
        "GOING_CONCERN":                0.9,
        "QUALIFIED_OPINION":            0.7,
        "MATERIAL_WEAKNESS":            0.6,
        "SCOPE_LIMITATION":             0.5,
        "CARO_QUALIFICATION":           0.4,
        "NON_COMPLIANCE":               0.5,
        "INTERNAL_CONTROL_DEFICIENCY":  0.4,
        "EMPHASIS_OF_MATTER":           0.2,
        "RECONCILIATION_DIFFERENCE":    0.3,
        "UNDER_PROVISIONING":           0.2,
    }

    def _compute_audit_remark_score(self, docs: List) -> float:
        """
        Use structured audit_remarks from each SegmentedDocument's segment_summary
        to compute a weighted audit remark score (0-1).
        """
        total = 0.0
        for doc in docs:
            remarks = (
                getattr(doc, "segment_summary", {}) or {}
            ).get("audit_remarks", [])
            for remark in remarks:
                weight = self._AUDIT_REMARK_WEIGHTS.get(remark.get("type", ""), 0.1)
                total += weight
                logger.info(f"[FraudAgent] Audit remark: {remark.get('type')} (+{weight})")
        return round(min(total, 1.0), 4)
