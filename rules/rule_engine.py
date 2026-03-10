"""
Rule Engine — Deterministic credit policy rules.
Runs before the ML model. Hard rejects bypass ML entirely.
"""
from typing import Dict, Any, List
from loguru import logger
from backend.config import (
    DSCR_MIN, ICR_MIN, CURRENT_RATIO_MIN, DEBT_EQUITY_MAX,
    PROMOTER_RISK_HARD_REJECT, LITIGATION_SEVERITY_REJECT,
    CIRCULAR_TRADING_THRESHOLD, COLLATERAL_COVERAGE_MIN,
)


# ── Rule definitions ──────────────────────────────────────────────────────────
# Each rule: (feature_key, operator, threshold, severity, reject_type, message)
HARD_REJECT_RULES = [
    ("circular_trading_score",   ">",  CIRCULAR_TRADING_THRESHOLD,      "CRITICAL", "Circular trading score exceeds hard-reject threshold ({val:.2f} > {thr})"),
    ("promoter_network_risk",    ">",  PROMOTER_RISK_HARD_REJECT,        "CRITICAL", "Promoter network risk too high ({val:.2f} > {thr})"),
    ("litigation_severity_score",">",  LITIGATION_SEVERITY_REJECT,       "CRITICAL", "Litigation severity score exceeds threshold ({val:.2f} > {thr})"),
    ("dscr",                     "<",  DSCR_MIN,                         "HIGH",     "DSCR {val:.2f} below minimum {thr} — insufficient cash flow to service debt"),
]

POLICY_RULES = [
    ("current_ratio",            "<",  CURRENT_RATIO_MIN,  10, "Current ratio {val:.2f} below minimum {thr}"),
    ("interest_coverage_ratio",  "<",  ICR_MIN,            12, "Interest coverage {val:.2f} below minimum {thr}"),
    ("debt_to_equity",           ">",  DEBT_EQUITY_MAX,    15, "Debt-to-equity {val:.2f} above maximum {thr}"),
    ("gst_bank_mismatch_score",  ">",  0.30,               10, "GST-bank mismatch score {val:.2f} — possible revenue inflation"),
    ("gstr2a_3b_mismatch_score", ">",  0.20,                8, "GSTR-2A/3B mismatch {val:.2f} — ITC irregularity"),
    ("benford_deviation_score",  ">",  0.50,                8, "Benford deviation {val:.2f} — possible fabricated figures"),
    ("collateral_coverage_ratio","<",  COLLATERAL_COVERAGE_MIN, 10, "Collateral coverage {val:.2f}x below minimum {thr}x"),
    ("capacity_utilization",     "<",  0.40,                5, "Capacity utilization {val:.0%} very low — operational concerns"),
    ("news_sentiment_score",     ">",  0.70,                7, "Negative news sentiment score {val:.2f}"),
    ("regulatory_violation_count",">", 3,                   6, "High regulatory violations: {val:.0f}"),
    ("itr_revenue_mismatch_score",">", 0.20,               10, "ITR-revenue mismatch {val:.2f} — income concealment risk"),
    ("debtor_days",              ">",  90,                   8, "Debtor days {val:.0f} — elevated receivable cycle risk"),
    ("pat_margin",               "<",  0,                   10, "Net loss: PAT margin {val:.1%} — company is loss-making"),
]


class RuleEngine:
    def evaluate(self, features: Dict[str, float]) -> Dict[str, Any]:
        logger.info("[RuleEngine] Evaluating credit policy rules")

        hard_reject  = False
        reject_reason = None
        risk_flags   = []
        policy_deductions = 0

        # ── Hard reject rules ─────────────────────────────────────────────
        for feat, op, thr, severity, msg_template in HARD_REJECT_RULES:
            val = features.get(feat, 0.0)
            if self._evaluate(val, op, thr):
                msg = msg_template.format(val=val, thr=thr)
                risk_flags.append({"rule": feat, "severity": severity, "message": msg, "type": "HARD_REJECT"})
                if not hard_reject:   # First hard reject wins
                    hard_reject   = True
                    reject_reason = msg
                logger.warning(f"[RuleEngine] HARD REJECT: {msg}")

        # ── Policy rules (score deductions) ──────────────────────────────
        for feat, op, thr, deduction, msg_template in POLICY_RULES:
            val = features.get(feat, 0.0)
            if self._evaluate(val, op, thr):
                msg = msg_template.format(val=val, thr=thr)
                risk_flags.append({"rule": feat, "severity": "MEDIUM", "message": msg, "type": "POLICY_FLAG", "deduction": deduction})
                policy_deductions += deduction

        policy_score = max(100 - policy_deductions, 0)

        logger.info(
            f"[RuleEngine] hard_reject={hard_reject}, "
            f"policy_score={policy_score}, "
            f"flags={len(risk_flags)}"
        )

        return {
            "hard_reject":    hard_reject,
            "reject_reason":  reject_reason,
            "policy_score":   policy_score,
            "risk_flags":     risk_flags,
            "flag_count":     len(risk_flags),
            "hard_reject_count": sum(1 for f in risk_flags if f["type"] == "HARD_REJECT"),
            "policy_flag_count": sum(1 for f in risk_flags if f["type"] == "POLICY_FLAG"),
        }

    def _evaluate(self, val: float, op: str, threshold: float) -> bool:
        if op == ">":
            return val > threshold
        if op == "<":
            return val < threshold
        if op == ">=":
            return val >= threshold
        if op == "<=":
            return val <= threshold
        return False
