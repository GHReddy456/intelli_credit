"""
Fraud Detection Agent
Aggregates all fraud signals: circular trading + Benford + GST mismatches + bank anomalies.
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

        # Weighted composite fraud score
        fraud_score = (
            ct_result.get("circular_trading_score", 0.0) * 0.35 +
            ba_result.get("benford_deviation_score", 0.0) * 0.20 +
            gst_m                                          * 0.20 +
            gstr                                           * 0.15 +
            bank_anomaly                                   * 0.10
        )
        fraud_score = round(min(fraud_score, 1.0), 4)
        fraud_score_100 = round(fraud_score * 100, 1)

        all_flags = (
            ct_result.get("flags", []) +
            ba_result.get("flags", []) +
            verification.get("gst_bank", {}).get("flags", []) +
            verification.get("gstr2a_3b", {}).get("flags", [])
        )

        is_hard_reject = (
            ct_result.get("is_hard_reject", False) or
            fraud_score > 0.85
        )

        logger.info(f"[FraudAgent] fraud_score={fraud_score:.3f}, hard_reject={is_hard_reject}")

        return {
            "fraud_risk_score":       fraud_score_100,
            "fraud_risk_normalized":  fraud_score,
            "circular_trading":       ct_result,
            "benford":                ba_result,
            "bank_anomaly_score":     bank_anomaly,
            "all_flags":              all_flags,
            "is_hard_reject":         is_hard_reject,
            # Flat fields for FeatureEngine
            "circular_trading_score": ct_result.get("circular_trading_score", 0.0),
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
