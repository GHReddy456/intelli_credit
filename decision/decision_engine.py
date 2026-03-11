"""
Decision Engine — combines rule_engine + ML output into final credit decision.
Computes recommended loan amount, interest rate, and conditions.
"""
from __future__ import annotations
import math
from typing import Dict, Any, List
from loguru import logger
from backend.config import (
    APPROVE_THRESHOLD, CONDITIONAL_THRESHOLD,
    BASE_INTEREST_RATE, LOAN_TO_TURNOVER_RATIO,
)
from backend.llm import llm_call, gemini_available as ollama_available


class DecisionEngine:

    # Grade → standard PD midpoints (aligned with credit_model._GRADE_TABLE)
    _GRADE_PD = {
        "AAA": 0.005, "AA":  0.015, "A":   0.030,
        "BBB": 0.060, "BB":  0.110, "B":   0.180,
        "C":   0.300, "D":   0.500,
    }

    @staticmethod
    def _score_to_grade(score: float) -> str:
        """Convert blended credit score to risk grade."""
        if score >= 90: return "AAA"
        if score >= 80: return "AA"
        if score >= 75: return "A"
        if score >= 70: return "BBB"
        if score >= 65: return "BB"
        if score >= 60: return "B"
        if score >= 50: return "C"
        return "D"

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
            raw_score = ml_result.get("credit_score", 0)
            reject_grade = self._score_to_grade(raw_score)
            return self._build_decision(
                verdict="REJECT",
                reason="Hard reject: " + "; ".join(
                    f.get("message", "") for f in _hard_reject_flags
                ),
                credit_score=round(raw_score, 1),
                risk_grade=reject_grade,
                features=features,
                policy_score=rule_result.get("policy_score", 0),
                conditions=[],
                hard_reject_flags=_hard_reject_flags,
                policy_flags=_policy_flags,
                ml_result=ml_result,
            )

        credit_score = ml_result.get("credit_score", 0)

        # Blend ML score with policy score (80/20)
        blended = round(0.80 * credit_score + 0.20 * rule_result.get("policy_score", 50), 1)
        # Grade and PD are derived from the blended score (not raw ML score)
        risk_grade   = self._score_to_grade(blended)

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
            credit_score=blended,
            risk_grade=risk_grade,
            features=features,
            policy_score=rule_result.get("policy_score", 50),
            conditions=conditions,
            hard_reject_flags=[],
            policy_flags=_policy_flags,
            loan_details=loan_details,
            ml_result=ml_result,
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
                        loan_details=None, ml_result=None) -> Dict[str, Any]:
        logger.info(f"[Decision] {verdict} — score={credit_score}, grade={risk_grade}")
        # Logistic PD: z = 0.5 - 0.055 × score
        # Score <20 → PD≈42%, 40 → PD≈20%, 60 → PD≈8%, 80 → PD≈3%
        z   = 0.5 - 0.055 * credit_score
        pod = round(1.0 / (1.0 + math.exp(-z)), 4)
        ml  = ml_result or {}
        # Build rule path: feature → rule → decision chain for traceability
        rule_path = []
        for f in hard_reject_flags:
            rule_path.append({
                "feature": f.get("rule", ""),
                "trigger": "HARD_REJECT",
                "message": f.get("message", ""),
                "impact":  "Blocks approval",
            })
        for f in policy_flags:
            rule_path.append({
                "feature": f.get("rule", ""),
                "trigger": "POLICY_DEDUCTION",
                "message": f.get("message", ""),
                "impact":  f"-{f.get('deduction', 0)} pts",
            })
        return {
            "verdict":             verdict,
            "reason":              reason,
            "credit_score":        credit_score,
            "risk_grade":          risk_grade,
            "probability_of_default": pod,
            "score_ci_low":        ml.get("score_ci_low", round(max(credit_score - 3, 0), 1)),
            "score_ci_high":       ml.get("score_ci_high", round(min(credit_score + 3, 100), 1)),
            "ml_pd":               ml.get("probability_of_default", pod),
            "policy_score":        policy_score,
            "conditions":          conditions,
            "hard_reject_flags":   hard_reject_flags,
            "policy_flags":        policy_flags,
            "loan_details":        loan_details or {},
            "rule_path":           rule_path,
            "five_cs_scores":      self._five_cs(features),
            "weighted_scorecard":  self._weighted_scorecard(features),
        }

    def _weighted_scorecard(self, features: Dict) -> Dict[str, Any]:
        """
        Transparent weighted credit score breakdown:
          Credit_Score = 0.25×Financial_Health + 0.20×Cashflow + 0.15×Governance
                       + 0.15×Fraud_Risk + 0.15×Sector_Risk + 0.10×Collateral
        """
        f = features

        def clamp(v: float) -> float:
            return round(max(0.0, min(100.0, v)), 1)

        # Financial Health (profitability + leverage)
        fin_health = clamp(
            min(f.get("ebitda_margin", 0) / 0.20, 1.0) * 35 +
            min(f.get("pat_margin", 0) / 0.12, 1.0) * 25 +
            (1 - min(f.get("debt_to_equity", 2.0) / 4.0, 1.0)) * 40
        )

        # Cashflow (DSCR + ICR + revenue growth)
        cashflow = clamp(
            min(f.get("dscr", 1.0) / 2.0, 1.0) * 40 +
            min(f.get("interest_coverage_ratio", 1.0) / 3.0, 1.0) * 35 +
            min(max(f.get("revenue_growth_3yr", 0), 0) / 0.15 + 0.5, 1.0) * 25
        )

        # Governance (lower fraud / litigation → higher score)
        governance = clamp(
            100
            - f.get("promoter_network_risk", 0.3) * 40
            - f.get("litigation_severity_score", 0) * 30
            - f.get("regulatory_violation_count", 0) * 3
        )

        # Fraud risk (lower fraud scores → higher score)
        gst_mm   = f.get("gst_bank_mismatch_score", 0)
        ct_score = f.get("circular_trading_score", 0)
        benford  = f.get("benford_deviation_score", 0)
        fraud_risk = clamp(
            100
            - gst_mm * 40
            - ct_score * 35
            - benford * 25
        )

        # Sector risk
        sector_risk = clamp((1 - f.get("sector_risk_score", 0.5)) * 100)

        # Collateral
        collateral = clamp(min(f.get("collateral_coverage_ratio", 1.0) / 2.0, 1.0) * 100)

        # Weighted total
        score = round(
            0.25 * fin_health +
            0.20 * cashflow   +
            0.15 * governance +
            0.15 * fraud_risk +
            0.15 * sector_risk +
            0.10 * collateral,
            1,
        )

        return {
            "financial_health": fin_health,
            "cashflow":         cashflow,
            "governance":       governance,
            "fraud_risk":       fraud_risk,
            "sector_risk":      sector_risk,
            "collateral":       collateral,
            "weighted_total":   score,
            "weights": {"financial_health": 0.25, "cashflow": 0.20, "governance": 0.15,
                        "fraud_risk": 0.15, "sector_risk": 0.15, "collateral": 0.10},
        }

    def _five_cs(self, features: Dict) -> Dict[str, float]:
        """Compute Five Cs sub-scores (0-100) for radar chart."""
        f = features

        def clamp(v: float) -> float:
            return round(max(0.0, min(100.0, v)), 1)

        character = clamp(100 - f.get("promoter_network_risk", 0.5) * 30
                          - f.get("litigation_severity_score", 0) * 30
                          - f.get("regulatory_violation_count", 0) * 5
                          - f.get("news_sentiment_score", 0.5) * 10)

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
