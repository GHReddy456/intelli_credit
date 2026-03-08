"""
Decision Engine — combines rule_engine + ML output into final credit decision.
Computes recommended loan amount, interest rate, and conditions.
"""
from __future__ import annotations
from typing import Dict, Any, List
from loguru import logger
from backend.config import (
    APPROVE_THRESHOLD, CONDITIONAL_THRESHOLD,
    BASE_INTEREST_RATE, LOAN_TO_TURNOVER_RATIO,
)
from backend.llm import llm_call, ollama_available


class DecisionEngine:

    # Risk premium by score band
    RATE_PREMIUM = {
        "AAA": 0.0,
        "AA":  0.25,
        "A":   0.50,
        "BBB": 1.00,
        "BB":  1.75,
        "B":   2.50,
        "C":   3.50,
        "D":   5.00,
    }

    # Conditions map for conditional approvals
    CONDITIONS_MAP = {
        "dscr_low":               "DSCR < 1.25 — require additional security / step-down EMI structure",
        "gst_mismatch":           "GST-bank mismatch > 10% — post audited financials for last 3 years",
        "itr_mismatch":           "ITR-revenue mismatch — obtain CA certificate reconciling income",
        "high_leverage":          "D/E > 2.5 — promoter infusion of ₹ equity required before first drawdown",
        "litigation_medium":      "Active MEDIUM litigation — obtain No-Objection Certificate from legal counsel",
        "negative_news":          "Negative press mentions — management explanation letter required",
        "collateral_below_125":   "Collateral coverage < 1.25× — enhance collateral or reduce loan amount",
        "capacity_low":           "Capacity utilisation < 50% — obtain business plan for capacity ramp-up",
        "customer_concentration": "Revenue concentration > 40% — diversification plan to be submitted",
    }

    def decide(
        self,
        rule_result:  Dict[str, Any],
        ml_result:    Dict[str, Any],
        features:     Dict[str, float],
        shap_result:  Dict[str, Any],
    ) -> Dict[str, Any]:

        # ── 1. Extract typed flags from risk_flags ────────────────────────────
        all_risk_flags = rule_result.get("risk_flags", [])
        _hard_reject_flags = [f for f in all_risk_flags if f.get("type") == "HARD_REJECT"]
        _policy_flags = [f for f in all_risk_flags if f.get("type") == "POLICY_FLAG"]

        # ── 2. Hard reject check ─────────────────────────────────────────────
        if rule_result.get("hard_reject"):
            return self._build_decision(
                verdict="REJECT",
                reason="Hard reject: " + "; ".join(
                    f.get("message", "") for f in _hard_reject_flags
                ),
                credit_score=ml_result.get("credit_score", 0),
                risk_grade=ml_result.get("risk_grade", "D"),
                features=features,
                policy_score=rule_result.get("policy_score", 0),
                conditions=[],
                hard_reject_flags=_hard_reject_flags,
                policy_flags=_policy_flags,
            )

        credit_score = ml_result.get("credit_score", 0)
        risk_grade   = ml_result.get("risk_grade", "D")

        # Blend ML score with policy score (80/20)
        blended = 0.80 * credit_score + 0.20 * rule_result.get("policy_score", 50)

        # ── 2. Verdict ───────────────────────────────────────────────────────
        if blended >= APPROVE_THRESHOLD:
            verdict = "APPROVE"
            reason  = f"Blended score {blended:.1f} exceeds approval threshold {APPROVE_THRESHOLD}"
        elif blended >= CONDITIONAL_THRESHOLD:
            verdict = "CONDITIONAL_APPROVE"
            reason  = f"Blended score {blended:.1f} in conditional band ({CONDITIONAL_THRESHOLD}–{APPROVE_THRESHOLD})"
        else:
            verdict = "REJECT"
            reason  = f"Blended score {blended:.1f} below minimum threshold {CONDITIONAL_THRESHOLD}"
        # Enrich reason with a 1-sentence LLM rationale if Ollama is available
        if ollama_available():
            flags_txt = "; ".join(
                f.get("message", "") for f in rule_result.get("risk_flags", [])[:4]
            )
            prompt = (
                f"In one sentence, explain why a company with credit score {blended:.0f}/100 "
                f"and these risk flags should be {verdict.lower().replace('_',' ')}: {flags_txt or 'no major flags'}. "
                f"Be direct and use Indian banking terminology."
            )
            llm_reason = llm_call(prompt, max_tokens=80)
            if llm_reason:
                reason = f"{reason}. {llm_reason}"
        # ── 3. Conditions list ───────────────────────────────────────────────
        conditions: List[str] = []
        if verdict in ("APPROVE", "CONDITIONAL_APPROVE"):
            conditions = self._derive_conditions(features, rule_result)

        # ── 4. Loan & rate computation ───────────────────────────────────────
        loan_details = self._compute_loan(features, risk_grade) if verdict != "REJECT" else {}

        return self._build_decision(
            verdict=verdict,
            reason=reason,
            credit_score=round(blended, 1),
            risk_grade=risk_grade,
            features=features,
            policy_score=rule_result.get("policy_score", 50),
            conditions=conditions,
            hard_reject_flags=[],
            policy_flags=_policy_flags,
            loan_details=loan_details,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _derive_conditions(self, features: Dict, rule_result: Dict) -> List[str]:
        conds: List[str] = []
        f = features
        if f.get("dscr", 2) < 1.25:
            conds.append(self.CONDITIONS_MAP["dscr_low"])
        if f.get("gst_bank_mismatch_score", 0) > 0.10:
            conds.append(self.CONDITIONS_MAP["gst_mismatch"])
        if f.get("itr_revenue_mismatch_score", 0) > 0.10:
            conds.append(self.CONDITIONS_MAP["itr_mismatch"])
        if f.get("debt_to_equity", 0) > 2.5:
            conds.append(self.CONDITIONS_MAP["high_leverage"])
        if f.get("litigation_severity_score", 0) >= 0.25:
            conds.append(self.CONDITIONS_MAP["litigation_medium"])
        if f.get("news_sentiment_score", 0) > 0.60:
            conds.append(self.CONDITIONS_MAP["negative_news"])
        if f.get("collateral_coverage_ratio", 2) < 1.25:
            conds.append(self.CONDITIONS_MAP["collateral_below_125"])
        if f.get("capacity_utilization", 0.80) < 0.50:
            conds.append(self.CONDITIONS_MAP["capacity_low"])
        if f.get("customer_concentration", 0) > 0.40:
            conds.append(self.CONDITIONS_MAP["customer_concentration"])
        return conds

    def _compute_loan(self, features: Dict, risk_grade: str) -> Dict:
        revenue = features.get("revenue_growth_3yr", 0)  # Not turnover — use fallback
        # Try to infer turnover from features; we store a proxy as annual_revenue_crore
        # Features doesn't directly expose revenue; use collateral as a proxy if needed
        # Placeholder: ₹10 Cr default; main.py should patch this from actual financials
        estimated_turnover_cr = features.get("_turnover_crore", 10.0)
        max_loan_cr = estimated_turnover_cr * LOAN_TO_TURNOVER_RATIO

        premium = self.RATE_PREMIUM.get(risk_grade, 3.50)
        interest_rate = BASE_INTEREST_RATE + premium

        return {
            "max_loan_crore":     round(max_loan_cr, 2),
            "interest_rate_pct":  round(interest_rate, 2),
            "risk_premium_pct":   round(premium, 2),
            "base_rate_pct":      BASE_INTEREST_RATE,
            "tenure_years":       5,
            "note":               "Loan limit = 40% of estimated annual turnover; rate = base + risk premium",
        }

    def _build_decision(self, verdict, reason, credit_score, risk_grade, features,
                        policy_score, conditions, hard_reject_flags, policy_flags,
                        loan_details=None) -> Dict[str, Any]:
        logger.info(f"[Decision] {verdict} — score={credit_score}, grade={risk_grade}")
        pod = round(max(0, 1 - credit_score / 100), 4)
        return {
            "verdict":             verdict,
            "reason":              reason,
            "credit_score":        credit_score,
            "risk_grade":          risk_grade,
            "probability_of_default": pod,
            "policy_score":        policy_score,
            "conditions":          conditions,
            "hard_reject_flags":   hard_reject_flags,
            "policy_flags":        policy_flags,
            "loan_details":        loan_details or {},
            "five_cs_scores":      self._five_cs(features),
        }

    def _five_cs(self, features: Dict) -> Dict[str, float]:
        """Compute Five Cs sub-scores (0-100) for radar chart."""
        f = features

        def clamp(v: float) -> float:
            return round(max(0.0, min(100.0, v)), 1)

        character = clamp(100 - f.get("promoter_network_risk", 0.5) * 100
                          - f.get("litigation_severity_score", 0) * 40
                          - f.get("news_sentiment_score", 0.5) * 20)

        capacity = clamp(
            min(f.get("dscr", 1.0) / 2.0, 1.0) * 40
            + min(f.get("interest_coverage_ratio", 1.0) / 3.0, 1.0) * 30
            + min(f.get("ebitda_margin", 0) / 0.20, 1.0) * 30
        )

        capital = clamp(
            (1 - min(f.get("debt_to_equity", 2.0) / 4.0, 1.0)) * 50
            + min(f.get("pat_margin", 0) / 0.12, 1.0) * 30
            + min(f.get("revenue_growth_3yr", 0) / 0.15 + 0.5, 1.0) * 20
        )

        collateral = clamp(min(f.get("collateral_coverage_ratio", 1.0) / 2.0, 1.0) * 100)

        conditions = clamp(
            (1 - f.get("sector_risk_score", 0.5)) * 60
            + f.get("capacity_utilization", 0.7) * 40
        )

        return {
            "character":  character,
            "capacity":   capacity,
            "capital":    capital,
            "collateral": collateral,
            "conditions": conditions,
        }
