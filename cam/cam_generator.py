"""
CAM Generator — assembles the full Credit Appraisal Memo content dict.
The content dict is then rendered to PDF by cam/pdf_exporter.py.
"""
from __future__ import annotations
import datetime
from typing import Dict, Any, List
from loguru import logger
from backend.llm import llm_call, ollama_available


class CAMGenerator:

    def generate(
        self,
        company_name:  str,
        loan_request:  Dict,
        decision:      Dict[str, Any],
        features:      Dict[str, float],
        shap_result:   Dict[str, Any],
        verification:  Dict[str, Any],
        fraud:         Dict[str, Any],
        doc_agent:     Dict[str, Any],
        promoter:      Dict[str, Any],
        sector:        Dict[str, Any],
        research:      Dict[str, Any],
        doc_summaries: List[Dict],
    ) -> Dict[str, Any]:
        logger.info(f"[CAM] Generating appraisal memo for {company_name}")

        five_cs = decision.get("five_cs_scores", {})

        cam = {
            "meta": {
                "company_name":   company_name,
                "date":           datetime.datetime.now().strftime("%d %B %Y"),
                "prepared_by":    "Intelli-Credit AI Engine v1.0",
                "version":        "1.0",
                "loan_purpose":   loan_request.get("purpose", "Working Capital / Term Loan"),
                "amount_crore":   loan_request.get("amount_crore", "As per computation"),
            },
            "executive_summary": self._exec_summary(decision, features, company_name),
            "decision_block": {
                "verdict":              decision["verdict"],
                "credit_score":         decision["credit_score"],
                "risk_grade":           decision["risk_grade"],
                "probability_default":  decision["probability_of_default"],
                "reason":               decision["reason"],
                "conditions":           decision.get("conditions", []),
                "loan_details":         decision.get("loan_details", {}),
            },
            "five_cs": {
                "character": {
                    "score":   five_cs.get("character", 0),
                    "details": self._character_section(features, promoter, research),
                },
                "capacity": {
                    "score":   five_cs.get("capacity", 0),
                    "details": self._capacity_section(features),
                },
                "capital": {
                    "score":   five_cs.get("capital", 0),
                    "details": self._capital_section(features),
                },
                "collateral": {
                    "score":   five_cs.get("collateral", 0),
                    "details": self._collateral_section(features),
                },
                "conditions": {
                    "score":   five_cs.get("conditions", 0),
                    "details": self._conditions_section(features, sector),
                },
            },
            "financial_ratios": self._ratio_table(features),
            "verification_findings": self._verification_summary(verification),
            "fraud_assessment": {
                "fraud_risk_score":       fraud.get("fraud_risk_score", 0),
                "circular_trading_score": features.get("circular_trading_score", 0),
                "benford_deviation":      features.get("benford_deviation_score", 0),
                "flags":                  fraud.get("flags", []),
                "summary":                fraud.get("summary", "No major fraud indicators detected."),
            },
            "document_intelligence": {
                "red_flags":    doc_agent.get("red_flags", []),
                "audit_issues": doc_agent.get("audit_issues", []),
                "summary":      doc_agent.get("summary", ""),
            },
            "promoter_profile": {
                "risk_score":         features.get("promoter_network_risk", 0),
                "directors":          promoter.get("directors", []),
                "litigation_summary": promoter.get("litigation_summary", ""),
                "network_summary":    promoter.get("network_summary", ""),
                "graph_data":         promoter.get("graph_data", {}),
            },
            "sector_outlook": {
                "sector_name":     sector.get("sector_name", ""),
                "risk_score":      features.get("sector_risk_score", 0),
                "outlook":         sector.get("conditions_summary", ""),
                "regulatory_note": sector.get("regulatory_note", ""),
            },
            "ml_explanation": {
                "top_drivers":    shap_result.get("top_drivers", [])[:10],
                "human_readable": shap_result.get("human_readable", []),
                "method":         shap_result.get("method", ""),
            },
            "documents_reviewed": [
                {"name": d.get("file_name", ""), "type": d.get("doc_type", ""),
                 "pages": d.get("page_count", 0), "confidence": d.get("extraction_confidence", 0)}
                for d in doc_summaries
            ],
            "rule_flags": {
                "hard_reject": decision.get("hard_reject_flags", []),
                "policy":      decision.get("policy_flags", []),
                "policy_score": decision.get("policy_score", 0),
            },
            "risk_narrative":       self._risk_narrative(features, decision, fraud),
            "recommendation_note":  self._recommendation_note(decision, features),
        }

        return cam

    # ── Section builders ──────────────────────────────────────────────────────

    def _exec_summary(self, decision: Dict, features: Dict, company: str) -> str:
        verdict  = decision["verdict"]
        score    = decision["credit_score"]
        grade    = decision["risk_grade"]
        dscr     = features.get("dscr", 0)
        de       = features.get("debt_to_equity", 0)
        verdict_text = {
            "APPROVE":             "recommended for APPROVAL",
            "CONDITIONAL_APPROVE": "recommended for CONDITIONAL APPROVAL",
            "REJECT":              "REJECTED",
        }.get(verdict, verdict)

        base = (
            f"{company} has been {verdict_text} with a credit score of {score:.1f}/100 "
            f"(Risk Grade: {grade}). DSCR of {dscr:.2f}× and D/E of {de:.2f}× "
            f"reflect the company's debt servicing capacity and leverage position. "
            f"{'All hard-reject triggers are absent. ' if verdict != 'REJECT' else ''}"
            f"Key risk drivers are identified below through SHAP-based ML attribution."
        )

        # LLM enrichment — 2-sentence analyst narrative appended to the boilerplate
        if ollama_available():
            conditions = decision.get("conditions", [])
            flags      = decision.get("hard_reject_flags", []) + decision.get("policy_flags", [])
            flags_txt  = "; ".join(f.get("message", "") for f in flags[:3]) or "none"
            cond_txt   = "; ".join(conditions[:2]) or "none"
            prompt = (
                f"Write 2 sentences as an Indian bank credit analyst summarising this case: "
                f"Company={company}, verdict={verdict}, credit_score={score:.0f}/100, "
                f"DSCR={dscr:.2f}, D/E={de:.2f}, key risk flags={flags_txt}, conditions={cond_txt}. "
                f"Be factual and use RBI/Basel risk language."
            )
            llm_text = llm_call(prompt, max_tokens=150)
            if llm_text:
                return f"{base} {llm_text}"
        return base

    def _character_section(self, f: Dict, promoter: Dict, research: Dict) -> List[Dict]:
        return [
            {"metric": "Promoter Network Risk",   "value": f.get("promoter_network_risk", 0),   "unit": "score 0-1"},
            {"metric": "Litigation Count",         "value": f.get("litigation_count", 0),         "unit": "cases"},
            {"metric": "Litigation Severity",      "value": f.get("litigation_severity_score", 0), "unit": "score 0-1"},
            {"metric": "News Sentiment Risk",       "value": f.get("news_sentiment_score", 0),      "unit": "score 0-1"},
            {"metric": "Regulatory Violations",    "value": f.get("regulatory_violation_count", 0), "unit": "count"},
        ]

    def _capacity_section(self, f: Dict) -> List[Dict]:
        return [
            {"metric": "DSCR",                    "value": round(f.get("dscr", 0), 2),                    "unit": "×"},
            {"metric": "Interest Coverage Ratio", "value": round(f.get("interest_coverage_ratio", 0), 2), "unit": "×"},
            {"metric": "EBITDA Margin",            "value": round(f.get("ebitda_margin", 0) * 100, 1),     "unit": "%"},
            {"metric": "PAT Margin",               "value": round(f.get("pat_margin", 0) * 100, 1),        "unit": "%"},
            {"metric": "Cashflow Volatility",      "value": round(f.get("cashflow_volatility", 0), 3),     "unit": "CV"},
        ]

    def _capital_section(self, f: Dict) -> List[Dict]:
        return [
            {"metric": "Debt / Equity",        "value": round(f.get("debt_to_equity", 0), 2),     "unit": "×"},
            {"metric": "Current Ratio",        "value": round(f.get("current_ratio", 0), 2),      "unit": "×"},
            {"metric": "Revenue Growth 3yr",   "value": round(f.get("revenue_growth_3yr", 0)*100, 1), "unit": "% CAGR"},
            {"metric": "Working Capital Days", "value": round(f.get("working_capital_days", 0), 0), "unit": "days"},
        ]

    def _collateral_section(self, f: Dict) -> List[Dict]:
        ccr = f.get("collateral_coverage_ratio", 0)
        return [
            {"metric": "Collateral Coverage Ratio", "value": round(ccr, 2), "unit": "×"},
            {"metric": "Assessment",
             "value": "Adequate" if ccr >= 1.5 else "Marginal" if ccr >= 1.0 else "Insufficient",
             "unit": ""},
        ]

    def _conditions_section(self, f: Dict, sector: Dict) -> List[Dict]:
        return [
            {"metric": "Sector Risk Score",       "value": round(f.get("sector_risk_score", 0), 2), "unit": "score 0-1"},
            {"metric": "Capacity Utilisation",    "value": round(f.get("capacity_utilization", 0)*100, 1), "unit": "%"},
            {"metric": "Customer Concentration",  "value": round(f.get("customer_concentration", 0)*100, 1), "unit": "%"},
            {"metric": "Sector",                  "value": sector.get("sector_name", "Unknown"), "unit": ""},
        ]

    def _ratio_table(self, f: Dict) -> List[Dict]:
        """Standard financial ratio summary for CAM table."""
        rows = [
            ("Revenue Growth (3yr CAGR)", f.get("revenue_growth_3yr", 0), "%", True),
            ("EBITDA Margin",              f.get("ebitda_margin", 0),       "%", True),
            ("PAT Margin",                 f.get("pat_margin", 0),          "%", True),
            ("Debt / Equity",              f.get("debt_to_equity", 0),     "×", False),
            ("Current Ratio",              f.get("current_ratio", 0),      "×", True),
            ("Interest Coverage Ratio",    f.get("interest_coverage_ratio", 0), "×", True),
            ("DSCR",                       f.get("dscr", 0),               "×", True),
            ("Debtor Days",                f.get("debtor_days", 0),        "days", False),
            ("Inventory Days",             f.get("inventory_days", 0),     "days", False),
            ("Working Capital Days",       f.get("working_capital_days", 0), "days", False),
        ]
        result = []
        for name, val, unit, higher_is_better in rows:
            display = f"{val*100:.1f}{unit}" if unit == "%" else f"{val:.2f}{unit}"
            result.append({"metric": name, "value": display, "higher_is_better": higher_is_better})
        return result

    def _verification_summary(self, v: Dict) -> Dict:
        return {
            "overall_severity":   v.get("overall_severity", "LOW"),
            "gst_bank_flags":     v.get("gst_bank", {}).get("flags", []),
            "itr_flags":          v.get("itr", {}).get("flags", []),
            "gstr_flags":         v.get("gstr2a_3b", {}).get("flags", []),
            "mismatch_scores":    v.get("mismatch_scores", {}),
        }

    # ── LLM narrative sections ────────────────────────────────────────────────

    def _risk_narrative(self, features: Dict, decision: Dict, fraud: Dict) -> str:
        """2-3 sentences of factual risk commentary written by the LLM.
        Strictly fact-anchored — only numbers provided in the prompt are used."""
        fraud_score  = fraud.get("fraud_risk_score", 0)
        lit_count    = int(features.get("litigation_count", 0))
        lit_sev      = features.get("litigation_severity_score", 0)
        benford_dev  = features.get("benford_deviation_score", 0)
        circ_score   = features.get("circular_trading_score", 0)
        dscr         = features.get("dscr", 0)
        de           = features.get("debt_to_equity", 0)

        # Deterministic fallback (no LLM)
        fallback = (
            f"Fraud risk score stands at {fraud_score:.0f}/100 with a Benford deviation of "
            f"{benford_dev:.2f} (0=normal, 1=highly suspicious) and circular trading score of "
            f"{circ_score:.2f}. "
            f"The promoter network shows {lit_count} litigation case(s) with a severity score "
            f"of {lit_sev:.2f}. "
            f"Debt-service coverage of {dscr:.2f}× and D/E of {de:.2f}× frame the overall credit risk."
        )

        if not ollama_available():
            return fallback

        prompt = (
            "INSTRUCTION: Use ONLY the numerical facts provided below. "
            "Do not invent any company name, person name, date, amount, or event. "
            "If uncertain, omit rather than assume. "
            "Write 2-3 sentences as an Indian bank credit analyst assessing risk:\n"
            f"fraud_risk_score={fraud_score:.0f}/100, "
            f"benford_deviation={benford_dev:.2f} (0=normal,1=suspicious), "
            f"circular_trading_score={circ_score:.2f} (0=none,1=severe), "
            f"litigation_count={lit_count} case(s), "
            f"litigation_severity={lit_sev:.2f}, "
            f"DSCR={dscr:.2f}x, "
            f"debt_to_equity={de:.2f}x. "
            "Use RBI Basel-III risk language. Be objective and concise."
        )
        result = llm_call(prompt, max_tokens=180)
        return result if result else fallback

    def _recommendation_note(self, decision: Dict, features: Dict) -> str:
        """1-2 sentences of specific lending conditions written by the LLM.
        Provides actionable guidance to the sanctioning committee."""
        verdict  = decision.get("verdict", "CONDITIONAL_APPROVE")
        score    = decision.get("credit_score", 50)
        dscr     = features.get("dscr", 0)
        de       = features.get("debt_to_equity", 0)
        icr      = features.get("interest_coverage_ratio", 0)
        cond_list = decision.get("conditions", [])

        # Deterministic fallback
        cond_str = "; ".join(cond_list[:3]) if cond_list else "standard covenants apply"
        fallback = (
            f"For a {verdict} case with credit score {score:.0f}/100, the sanctioning committee "
            f"should mandate quarterly DSCR monitoring (current: {dscr:.2f}×, threshold ≥1.25×), "
            f"D/E ceiling of {de:.2f}× (or lower), and ICR ≥ 2.0× (current: {icr:.2f}×). "
            f"Conditions: {cond_str}."
        )

        if not ollama_available():
            return fallback

        prompt = (
            "INSTRUCTION: Use ONLY the numerical facts listed. "
            "Do not mention any company name or invent figures. "
            "Write 2 sentences as a senior Indian banker recommending specific, "
            "RBI-compliant loan conditions for the sanctioning committee:\n"
            f"verdict={verdict}, credit_score={score:.0f}/100, "
            f"DSCR={dscr:.2f}x (minimum RBI guideline 1.25x), "
            f"debt_to_equity={de:.2f}x, "
            f"interest_coverage_ratio={icr:.2f}x. "
            "Name specific financial covenants or RBI/Basel-III ratios to monitor. "
            "Do not add facts not provided."
        )
        result = llm_call(prompt, max_tokens=160)
        return result if result else fallback
