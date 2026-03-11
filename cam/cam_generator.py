"""
CAM Generator -- assembles the full Credit Appraisal Memo content dict.

Section order (mirrors Indian bank CAM format):
  1. Executive Summary
  2. SWOT Analysis
  3. Borrower Profile
  4. Facility Structure
  5. Five Cs Analysis
  6. Financial Ratios
  7. Fraud & Integrity Assessment
  8. Promoter & Governance
  9. Sector Outlook
  10. AI Risk Attribution (SHAP)
  11. Evidence Traceability
  12. Sanction Recommendation

The content dict is then rendered to PDF by cam/pdf_exporter.py.
"""
from __future__ import annotations
import datetime
from typing import Dict, Any, List, Optional
from loguru import logger


# == Helpers ==================================================================

def _fmt(val, unit="", pct=False, times=False, days=False, dp=2):
    """Format a possibly-None value for display. Returns a dash when unavailable."""
    if val is None:
        return "N/A"
    if pct:
        return f"{val * 100:.{dp}f}%"
    if times:
        return f"{val:.{dp}f}x"
    if days:
        return f"{val:.0f} days"
    return f"{val:.{dp}f}{unit}"


class CAMGenerator:

    # Feature -> (source doc type, source section) for evidence traceability
    _FEATURE_SOURCES = {
        "revenue_growth_3yr":        ("Annual Report",          "Profit & Loss Statement"),
        "ebitda_margin":             ("Annual Report",          "Profit & Loss Statement"),
        "pat_margin":                ("Annual Report",          "Profit & Loss Statement"),
        "debt_to_equity":            ("Annual Report",          "Balance Sheet"),
        "current_ratio":             ("Annual Report",          "Balance Sheet"),
        "interest_coverage_ratio":   ("Annual Report",          "P&L / Finance Costs"),
        "dscr":                      ("Bank Statement / AR",    "Cash Flow Statement"),
        "working_capital_days":      ("Annual Report",          "Balance Sheet"),
        "debtor_days":               ("Annual Report",          "Balance Sheet / Debtors Schedule"),
        "inventory_days":            ("Annual Report",          "Balance Sheet / Inventory Schedule"),
        "cashflow_volatility":       ("Bank Statement",         "Monthly Credit Transactions"),
        "gst_bank_mismatch_score":   ("GST Return + Bank Stmt", "Revenue Reconciliation"),
        "gstr2a_3b_mismatch_score":  ("GST Return (2A vs 3B)",  "ITC Reconciliation"),
        "itr_revenue_mismatch_score":("ITR + Annual Report",    "Revenue Cross-check"),
        "circular_trading_score":    ("Bank Statement",         "Transaction Network Analysis"),
        "benford_deviation_score":   ("Bank Stmt / Annual Report","Benford Statistical Test"),
        "litigation_count":          ("Legal Documents",        "Court Orders / DRT / NCLT"),
        "litigation_severity_score": ("Legal Documents",        "Litigation Impact Assessment"),
        "news_sentiment_score":      ("External News Feed",     "Sentiment Analysis"),
        "promoter_network_risk":     ("Annual Report / MCA",    "Director & Group Entity Analysis"),
        "sector_risk_score":         ("Sector Database",        "Industry Risk Assessment"),
        "collateral_coverage_ratio": ("DD Notes / Valuation",   "Collateral Valuation"),
        "capacity_utilization":      ("DD Notes / Annual Report","Operations Commentary"),
        "customer_concentration":    ("Annual Report",          "Revenue by Customer Segment"),
        "regulatory_violation_count":("Annual Report / Legal",  "Auditor Report / CARO"),
    }

    def generate(
        self,
        company_name:  str,
        loan_request:  Dict,
        decision:      Dict[str, Any],
        features:      Dict[str, Any],
        shap_result:   Dict[str, Any],
        verification:  Dict[str, Any],
        fraud:         Dict[str, Any],
        doc_agent:     Dict[str, Any],
        promoter:      Dict[str, Any],
        sector:        Dict[str, Any],
        research:      Dict[str, Any],
        doc_summaries: List[Dict],
        entity:        Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        logger.info(f"[CAM] Generating appraisal memo for {company_name}")

        five_cs = decision.get("five_cs_scores", {})
        loan    = decision.get("loan_details", {})
        dr      = features.get("_display_ratios", {})
        snap    = features.get("_financial_snapshot", {})

        cam = {
            "meta": {
                "company_name":  company_name,
                "date":          datetime.datetime.now().strftime("%d %B %Y"),
                "prepared_by":   "Intelli-Credit AI Engine v1.0",
                "version":       "1.0",
                "loan_purpose":  loan_request.get("purpose", "Working Capital / Term Loan"),
                "amount_crore":  loan.get("max_loan_crore", "As per computation"),
            },
            # Section 1
            "executive_summary": self._exec_summary(
                decision, features, company_name, doc_summaries, five_cs),
            # Section 2
            "borrower_profile": self._borrower_profile(
                company_name, features, sector, doc_summaries, snap),
            # Section 3
            "facility_structure": self._facility_structure(decision, features, loan),
            # Section 4 (decision block + five Cs)
            "decision_block": {
                "verdict":             decision["verdict"],
                "credit_score":        decision["credit_score"],
                "risk_grade":          decision["risk_grade"],
                "probability_default": decision["probability_of_default"],
                "score_ci_low":        decision.get("score_ci_low", "N/A"),
                "score_ci_high":       decision.get("score_ci_high", "N/A"),
                "reason":              decision["reason"],
                "conditions":         decision.get("conditions", []),
                "loan_details":        loan,
            },
            "five_cs": {
                "character":  {"score": five_cs.get("character",  0),
                               "details": self._character_section(features, promoter, research)},
                "capacity":   {"score": five_cs.get("capacity",   0),
                               "details": self._capacity_section(features, dr)},
                "capital":    {"score": five_cs.get("capital",    0),
                               "details": self._capital_section(features, dr)},
                "collateral": {"score": five_cs.get("collateral", 0),
                               "details": self._collateral_section(features)},
                "conditions": {"score": five_cs.get("conditions", 0),
                               "details": self._conditions_section(features, sector)},
            },
            # Section 5
            "financial_ratios": self._ratio_table(features, dr),
            # Section 6
            "fraud_integrity": self._fraud_integrity_section(features, fraud, verification),
            # Section 7
            "promoter_governance": {
                "risk_score":         features.get("promoter_network_risk", 0),
                "character_score":    features.get("_character_score", 0),
                "governance_risk":    features.get("_governance_risk_score", 0),
                "directors":          promoter.get("directors", []),
                "litigation_summary": self._litigation_summary(features, promoter, research),
                "network_summary":    promoter.get("network_summary", ""),
                "audit_issues":       doc_agent.get("audit_issues", []),
                "red_flags":          doc_agent.get("red_flags", []),
                "graph_data":         promoter.get("graph_data", {}),
            },
            # Section 8
            "sector_outlook": {
                "sector_name":     sector.get("sector_name", sector.get("sector", "General")),
                "risk_score":      features.get("sector_risk_score", 0),
                "outlook":         sector.get("conditions_summary", ""),
                "regulatory_note": sector.get("regulatory_note", ""),
                "benchmarks":      features.get("_sector_benchmarks", {}),
            },
            # Section 9
            "ai_risk_attribution": {
                "top_drivers":    shap_result.get("top_drivers", [])[:10],
                "human_readable": shap_result.get("human_readable", []),
                "method":         shap_result.get("method", ""),
                "expected_value": shap_result.get("expected_value"),
            },
            # Section 10
            "evidence_traceability": self._evidence_traceability(
                features, doc_summaries, shap_result),
            # Section 11
            "sanction_recommendation": self._sanction_recommendation(
                decision, features, loan, company_name),
            # Supporting
            "documents_reviewed": [
                {"name":       d.get("file_name", ""),
                 "type":       d.get("doc_type", ""),
                 "pages":      d.get("page_count", 0),
                 "confidence": d.get("confidence", 0),
                 "status":     "Processed" if d.get("page_count", 0) > 0 else "Extraction Failed"}
                for d in doc_summaries
            ],
            "rule_flags": {
                "hard_reject":  decision.get("hard_reject_flags", []),
                "policy":       decision.get("policy_flags", []),
                "policy_score": decision.get("policy_score", 0),
            },
            "risk_radar": self._risk_radar(decision, features),
        }
        # Attach structured SWOT (built inside _exec_summary)
        cam["swot"] = getattr(self, "_last_swot", {
            "strengths": [], "weaknesses": [], "opportunities": [], "threats": [],
        })
        return cam

    # =========================================================================
    # Section 1 -- Executive Summary (deterministic, no LLM leakage)
    # =========================================================================
    def _exec_summary(self, decision, features, company, doc_summaries, five_cs):
        verdict  = decision["verdict"]
        score    = decision["credit_score"]
        grade    = decision["risk_grade"]
        pd       = decision["probability_of_default"]
        loan     = decision.get("loan_details", {})
        ci_low   = decision.get("score_ci_low", "N/A")
        ci_high  = decision.get("score_ci_high", "N/A")
        dscr     = features.get("dscr", 0)
        de       = features.get("debt_to_equity", 0)
        ebitda_m = features.get("ebitda_margin", 0)
        char_sc  = five_cs.get("character", 0)
        cap_sc   = five_cs.get("capacity", 0)
        capt_sc  = five_cs.get("capital", 0)
        coll_sc  = five_cs.get("collateral", 0)
        cond_sc  = five_cs.get("conditions", 0)

        hard_flags = decision.get("hard_reject_flags", [])

        verdict_map = {
            "APPROVE":             "RECOMMENDED FOR APPROVAL",
            "CONDITIONAL_APPROVE": "RECOMMENDED FOR CONDITIONAL APPROVAL",
            "REJECT":              "RECOMMENDED FOR REJECTION",
        }
        # Distinguish policy-triggered rejection from score-based rejection
        if verdict == "REJECT" and hard_flags:
            verdict_text = "RECOMMENDED FOR REJECTION (Policy Override)"
        else:
            verdict_text = verdict_map.get(verdict, verdict)

        strengths, risks = [], []
        if dscr >= 1.25:
            strengths.append(f"Adequate debt service coverage (DSCR: {dscr:.2f}x)")
        else:
            risks.append(f"Weak debt service coverage (DSCR: {dscr:.2f}x below 1.25x threshold)")
        if de < 1.5:
            strengths.append(f"Conservative leverage (D/E: {de:.2f}x)")
        elif de > 2.5:
            risks.append(f"High leverage (D/E: {de:.2f}x)")
        if ebitda_m >= 0.12:
            strengths.append(f"Healthy EBITDA margin ({ebitda_m * 100:.1f}%)")
        elif ebitda_m < 0.07:
            risks.append(f"Thin EBITDA margin ({ebitda_m * 100:.1f}%)")
        fraud_total = (
            features.get("circular_trading_score", 0) +
            features.get("benford_deviation_score", 0) +
            features.get("gst_bank_mismatch_score", 0) * 0.5 +
            features.get("gstr2a_3b_mismatch_score", 0) * 0.5 +
            features.get("_audit_remark_score", 0) * 0.5 +
            features.get("_shell_entity_score", 0) * 0.5 +
            features.get("_shell_network_score", 0) * 0.3
        )
        any_high_policy_fraud = any(
            "ITC" in f.get("rule", "") or "GSTR" in f.get("rule", "")
            or "fraud" in f.get("message", "").lower()
            for f in decision.get("policy_flags", [])
            if isinstance(f, dict)
        )
        fraud_flags_exist = len(decision.get("hard_reject_flags", [])) > 0 or any_high_policy_fraud
        if fraud_total < 0.20 and not fraud_flags_exist:
            strengths.append("No material fraud indicators detected")
        elif fraud_total < 0.40 and not fraud_flags_exist:
            risks.append("Minor fraud-risk indicators noted — routine monitoring recommended")
        else:
            risks.append("Elevated fraud-risk indicators require monitoring")
        lit_count = int(features.get("litigation_count", 0))
        if lit_count == 0:
            strengths.append("Clean litigation record")
        elif lit_count <= 2:
            risks.append(f"{lit_count} active litigation case(s) under review")
        else:
            risks.append(f"Multiple litigation cases ({lit_count}) -- elevated legal risk")

        max_loan = loan.get("max_loan_crore", "N/A")
        rate     = loan.get("interest_rate_pct", "N/A")
        tenure   = loan.get("tenure_years", "N/A")

        ci_str = f" [95% CI: {ci_low}-{ci_high}]" if ci_low != "N/A" else ""
        loan_line = (
            f"Recommended Facility: Rs.{max_loan} Cr at {rate}% p.a. for {tenure} years.\n"
            if verdict != "REJECT" else ""
        )
        no_reject  = "No hard-reject triggers identified. " if not hard_flags and verdict != "REJECT" else ""

        conds    = decision.get("conditions", [])
        strength_bullets = "\n".join(f"  * {s}" for s in strengths) or "  * (none identified)"
        risk_bullets     = "\n".join(f"  * {r}" for r in risks)     or "  * (none identified)"

        # ── Opportunities & Threats (complete SWOT) ──────────────────────────
        opportunities, threats = [], []
        sector_data = decision.get("sector", {}) or {}
        sector_risk = features.get("sector_risk_score", 50)
        news_sent = features.get("news_sentiment_score", 0.5)

        if sector_risk < 40:
            opportunities.append("Favourable sector outlook with below-average industry risk")
        if news_sent > 0.6:
            opportunities.append(f"Positive media sentiment (score: {news_sent:.2f})")
        if ebitda_m >= 0.15:
            opportunities.append("Strong margins provide room for business expansion")
        if dscr >= 1.75:
            opportunities.append("Robust cash flows enable capacity growth / capex investment")
        rev_growth = features.get("_display_ratios", {}).get("revenue_growth_3yr")
        if rev_growth and rev_growth > 0.10:
            opportunities.append(f"Consistent revenue growth trajectory ({rev_growth*100:.1f}% 3-yr CAGR)")
        if not opportunities:
            opportunities.append("Stable operating environment supports existing capacity utilisation")

        if sector_risk > 65:
            threats.append("Elevated sector headwinds may impact future performance")
        if news_sent < 0.35:
            threats.append(f"Adverse media sentiment (score: {news_sent:.2f}) warrants monitoring")
        if fraud_flags_exist:
            threats.append("Fraud-risk indicators detected — enhanced monitoring required")
        if lit_count > 2:
            threats.append(f"Multiple active litigations ({lit_count}) pose legal/financial risk")
        reg_violations = int(features.get("regulatory_violation_count", 0))
        if reg_violations > 0:
            threats.append(f"Regulatory violation(s) noted ({reg_violations}) — compliance risk")
        if de > 2.0:
            threats.append(f"High leverage (D/E: {de:.2f}x) limits financial flexibility")
        if not threats:
            threats.append("No material external threats identified at the time of assessment")

        opportunity_bullets = "\n".join(f"  * {o}" for o in opportunities)
        threat_bullets      = "\n".join(f"  * {t}" for t in threats)

        lines = [
            f"{company} -- CREDIT APPRAISAL SUMMARY",
            "",
            f"Based on AI-assisted analysis of {len(doc_summaries)} document(s), {company} is",
            f"{verdict_text}.",
            "",
            f"Credit Score: {score:.1f}/100{ci_str}  |  Risk Grade: {grade}  |  Probability of Default: {pd:.1%}",
            loan_line,
            f"{no_reject}Five Cs: Character {char_sc:.0f}  Capacity {cap_sc:.0f}  Capital {capt_sc:.0f}  Collateral {coll_sc:.0f}  Conditions {cond_sc:.0f} (out of 100)",
            "",
            "── SWOT ANALYSIS ──",
            "",
            "Strengths:",
            strength_bullets,
            "",
            "Weaknesses / Risk Factors:",
            risk_bullets,
            "",
            "Opportunities:",
            opportunity_bullets,
            "",
            "Threats:",
            threat_bullets,
        ]
        if conds:
            lines += ["", "Conditions Precedent / Subsequent:"]
            lines += [f"  * {c}" for c in conds[:6]]

        if hard_flags:
            lines += ["", "Hard Reject Triggers:"]
            for hf in hard_flags[:5]:
                msg = hf.get("message", str(hf)) if isinstance(hf, dict) else str(hf)
                lines.append(f"  * {msg}")

        # Store structured SWOT for frontend consumption
        self._last_swot = {
            "strengths": strengths,
            "weaknesses": risks,
            "opportunities": opportunities,
            "threats": threats,
        }

        return "\n".join(lines).strip()

    # =========================================================================
    # Section 2 -- Borrower Profile
    # =========================================================================
    def _borrower_profile(self, company_name, features, sector, doc_summaries, snap):
        gstin = pan = cin = reg_address = ""
        for d in doc_summaries:
            meta = d.get("metadata", {})
            gstin       = gstin       or meta.get("gstin", "")
            pan         = pan         or meta.get("pan", "")
            cin         = cin         or meta.get("cin", "")
            reg_address = reg_address or meta.get("registered_address", "")

        turnover_cr = features.get("_turnover_crore", 0)
        sector_name = sector.get("sector_name", sector.get("sector", "N/A"))
        fy = datetime.datetime.now()
        fy_str = f"FY {fy.year - 1}-{str(fy.year)[-2:]}"

        return {
            "company_name":            company_name,
            "gstin":                   gstin or "N/A",
            "pan":                     pan   or "N/A",
            "cin":                     cin   or "N/A",
            "sector":                  sector_name,
            "registered_address":      reg_address or "N/A",
            "estimated_turnover_cr":   turnover_cr,
            "doc_types_submitted":     sorted({d.get("doc_type", "N/A") for d in doc_summaries}),
            "financial_year_assessed": fy_str,
        }

    # =========================================================================
    # Section 3 -- Facility Structure
    # =========================================================================
    def _facility_structure(self, decision, features, loan):
        verdict = decision.get("verdict", "")

        # For REJECT verdicts, show "Not Recommended" instead of zero facility
        if verdict == "REJECT":
            return {
                "total_facility_cr":       "Not Recommended",
                "working_capital_cr":      "N/A",
                "term_loan_cr":            "N/A",
                "interest_rate_pct":       "N/A",
                "base_rate_pct":           "N/A",
                "risk_premium_pct":        "N/A",
                "tenure_years":            "N/A",
                "approx_monthly_emi_cr":   "N/A",
                "facility_status":         "DECLINED — credit application does not meet sanction criteria",
                "security":                {},
                "repayment_terms":         "Not applicable — facility not recommended.",
                "drawdown_condition":      "Not applicable.",
            }

        max_loan = float(loan.get("max_loan_crore") or 0)
        rate     = float(loan.get("interest_rate_pct") or 0)
        tenure   = int(loan.get("tenure_years") or 5)
        premium  = float(loan.get("risk_premium_pct") or 0)
        base     = float(loan.get("base_rate_pct") or 0)

        monthly_rate = rate / 100 / 12
        months = tenure * 12
        try:
            emi = round(
                max_loan * 1e7 * monthly_rate / (1 - (1 + monthly_rate) ** -months) / 1e7, 2
            ) if monthly_rate > 0 and max_loan > 0 else 0
        except Exception:
            emi = 0

        wc_limit   = round(max_loan * 0.60, 2)
        term_limit = round(max_loan * 0.40, 2)
        ccr        = features.get("collateral_coverage_ratio", 0)

        return {
            "total_facility_cr":       max_loan,
            "working_capital_cr":      wc_limit,
            "term_loan_cr":            term_limit,
            "interest_rate_pct":       rate,
            "base_rate_pct":           base,
            "risk_premium_pct":        premium,
            "tenure_years":            tenure,
            "approx_monthly_emi_cr":   emi,
            "security": {
                "primary":    "Hypothecation of stock, receivables and book debts",
                "collateral": (f"Equitable/registered mortgage of immovable property "
                               f"(coverage {ccr:.2f}x)"),
                "guarantee":  "Personal guarantee of all promoters/directors",
            },
            "repayment_terms": (
                f"Working capital: revolving, annual review. "
                f"Term loan: {tenure}-yr tenor with approx. monthly EMI of Rs.{emi:.2f} Cr."
            ),
            "drawdown_condition": (
                "First drawdown subject to execution of loan documents and "
                "satisfaction of all conditions precedent."
            ),
        }

    # =========================================================================
    # Section 5 -- Financial Ratios (N/A-aware)
    # =========================================================================
    def _ratio_table(self, features, dr):
        rows = [
            ("Revenue Growth (3-yr CAGR)",   _fmt(dr.get("revenue_growth_3yr"),        pct=True),  True,  "P&L (3 years)"),
            ("EBITDA Margin",                 _fmt(dr.get("ebitda_margin"),              pct=True),  True,  "P&L Statement"),
            ("PAT Margin",                    _fmt(dr.get("pat_margin"),                 pct=True),  True,  "P&L Statement"),
            ("Debt / Equity Ratio",           _fmt(dr.get("debt_to_equity"),             times=True),False, "Balance Sheet"),
            ("Current Ratio",                 _fmt(dr.get("current_ratio"),              times=True),True,  "Balance Sheet"),
            ("Interest Coverage Ratio (ICR)", _fmt(dr.get("interest_coverage_ratio"),   times=True),True,  "P&L / Finance Costs"),
            ("Debt Service Coverage (DSCR)",  _fmt(dr.get("dscr"),                      times=True),True,  "Cash Flow / AR"),
            ("Debtor Days",                   _fmt(dr.get("debtor_days"),                days=True), False, "Balance Sheet"),
            ("Inventory Days",                _fmt(dr.get("inventory_days"),             days=True), False, "Balance Sheet"),
            ("Working Capital Days",          _fmt(dr.get("working_capital_days"),       days=True), False, "Balance Sheet"),
        ]
        return [
            {"metric": name, "value": val, "higher_is_better": hib, "source": src}
            for name, val, hib, src in rows
        ]

    # =========================================================================
    # Section 6 -- Fraud & Integrity Assessment
    # =========================================================================
    def _fraud_integrity_section(self, features, fraud, verification):
        circ   = features.get("circular_trading_score", 0)
        benf   = features.get("benford_deviation_score", 0)
        gst_mm = features.get("gst_bank_mismatch_score", 0)
        gstr_mm= features.get("gstr2a_3b_mismatch_score", 0)
        itr_mm = features.get("itr_revenue_mismatch_score", 0)

        def _band(score_100):
            """Fraud risk band on 0-100 scale: 0-20 Low, 20-40 Moderate, 40-70 High, 70+ Severe."""
            if score_100 < 20: return "LOW"
            if score_100 < 40: return "MODERATE"
            if score_100 < 70: return "HIGH"
            return "SEVERE"

        def _sub_band(score_01):
            """Sub-score band on 0-1 scale."""
            return _band(score_01 * 100)

        # Use fraud detection agent's actual composite score (0-100)
        fraud_score_100 = fraud.get("fraud_risk_score", 0)
        integrity_score = round(100 - fraud_score_100, 1)

        vf = verification
        all_flags = (
            vf.get("gst_bank", {}).get("flags", [])
            + vf.get("itr", {}).get("flags", [])
            + vf.get("gstr2a_3b", {}).get("flags", [])
        )
        return {
            "integrity_score":    integrity_score,
            "fraud_risk_score":   fraud_score_100,
            "overall_risk_band":  _band(fraud_score_100),
            "circular_trading":   {"score": round(circ, 4),   "band": _sub_band(circ),
                                   "detail": fraud.get("circular_trading", {}).get("summary", "")},
            "benford_deviation":  {"score": round(benf, 4),   "band": _sub_band(benf),
                                   "detail": "0=natural distribution, 1=highly suspicious"},
            "gst_bank_reconciliation": {
                "mismatch_pct": round(gst_mm * 100, 2), "band": _sub_band(gst_mm),
                "flags": vf.get("gst_bank", {}).get("flags", [])},
            "gstr_reconciliation": {
                "mismatch_pct": round(gstr_mm * 100, 2), "band": _sub_band(gstr_mm),
                "flags": vf.get("gstr2a_3b", {}).get("flags", [])},
            "itr_reconciliation": {
                "mismatch_pct": round(itr_mm * 100, 2), "band": _sub_band(itr_mm),
                "flags": vf.get("itr", {}).get("flags", [])},
            "all_flags":          all_flags,
            "fraud_flags":        fraud.get("all_flags", []),
            "overall_severity":   vf.get("overall_severity", "LOW"),
        }

    # =========================================================================
    # Section 10 -- Evidence Traceability
    # =========================================================================
    def _evidence_traceability(self, features, doc_summaries, shap_result):
        doc_map = {}
        for d in doc_summaries:
            dt = d.get("doc_type", "")
            fn = d.get("file_name", "")
            pg = d.get("page_count", 0)
            doc_map[dt] = f"{fn} ({pg}pp)"

        top_features = [d["feature"] for d in shap_result.get("top_drivers", [])[:10]]
        all_feats = top_features + [f for f in self._FEATURE_SOURCES if f not in top_features]

        rows = []
        for feat in all_feats[:20]:
            src_doc, src_section = self._FEATURE_SOURCES.get(feat, ("Internal Computation", "Derived"))

            file_ref = "N/A"
            for dt_key in ["annual_report", "bank_statement", "gst", "itr", "legal", "sanction_letter"]:
                if dt_key.replace("_", " ") in src_doc.lower() or src_doc.lower().startswith(dt_key[:3]):
                    candidate = doc_map.get(dt_key, "")
                    if candidate:
                        file_ref = candidate
                        break

            raw_val = features.get(feat)
            if raw_val is None:
                disp_val = "N/A"
            elif isinstance(raw_val, (int, float)):
                disp_val = f"{raw_val:.4f}"
            else:
                disp_val = "N/A"

            rows.append({
                "metric":        feat.replace("_", " ").title(),
                "value":         disp_val,
                "source_doc":    src_doc,
                "source_file":   file_ref,
                "section":       src_section,
                "is_top_driver": feat in top_features,
            })
        return rows

    # =========================================================================
    # Section 11 -- Sanction Recommendation
    # =========================================================================
    def _sanction_recommendation(self, decision, features, loan, company_name="the applicant"):
        verdict  = decision["verdict"]
        score    = decision["credit_score"]
        grade    = decision["risk_grade"]
        pd       = decision["probability_of_default"]
        max_loan = loan.get("max_loan_crore", 0) or 0
        rate     = loan.get("interest_rate_pct", 0) or 0
        tenure   = loan.get("tenure_years", 5)
        premium  = loan.get("risk_premium_pct", 0)
        conds    = decision.get("conditions", [])

        if verdict == "APPROVE":
            wc  = round(max_loan * 0.6, 2)
            tl  = round(max_loan * 0.4, 2)
            narrative = (
                f"The Sanctioning Committee is recommended to APPROVE a total credit facility of "
                f"Rs.{max_loan} Cr to {company_name}, comprising Working Capital of Rs.{wc} Cr "
                f"and a Term Loan of Rs.{tl} Cr, at an interest rate of {rate}% p.a. "
                f"(Base Rate {loan.get('base_rate_pct', 0)}% + Risk Premium {premium}%) "
                f"for a tenor of {tenure} years. "
                f"AI Credit Score: {score:.1f}/100 (Grade {grade}), PD: {pd:.1%} -- "
                f"within acceptable risk appetite."
            )
        elif verdict == "CONDITIONAL_APPROVE":
            cond_str = "; ".join(conds[:3]) or "conditions detailed above"
            narrative = (
                f"The Sanctioning Committee is recommended to CONDITIONALLY APPROVE "
                f"the credit facility of Rs.{max_loan} Cr at {rate}% p.a., subject to "
                f"satisfactory resolution of: {cond_str}. "
                f"AI Score: {score:.1f}/100 (Grade {grade}), PD: {pd:.1%}."
            )
        else:
            flags_str = "; ".join(
                f.get("message", str(f)) for f in decision.get("hard_reject_flags", [])[:3]
            ) or "Credit score below minimum acceptable threshold"
            # Distinguish policy override from score-based rejection
            reject_label = "DECLINE (Policy Override)" if decision.get("hard_reject_flags") else "DECLINE"
            narrative = (
                f"The Sanctioning Committee is recommended to {reject_label} the credit request. "
                f"Grounds: {flags_str}. AI Score: {score:.1f}/100 (Grade {grade}), "
                f"PD: {pd:.1%} -- exceeds acceptable risk tolerance."
            )

        return {
            "verdict":          verdict,
            "narrative":        narrative,
            "conditions":       conds,
            "credit_score":     score,
            "risk_grade":       grade,
            "pd":               pd,
            "max_loan_cr":      max_loan,
            "rate_pct":         rate,
            "tenure_years":     tenure,
            "review_frequency": "Annual review / upon renewal",
            "disclaimer": (
                "This recommendation is generated by an AI Credit Decisioning Engine. "
                "All credit decisions must be reviewed and authorised by a qualified "
                "credit officer and sanctioning authority as per the institution's credit policy."
            ),
        }

    # =========================================================================
    # Risk Radar data (for frontend spider chart)
    # =========================================================================
    def _risk_radar(self, decision, features):
        five_cs = decision.get("five_cs_scores", {})
        return {
            "axes": [
                {"name": "Character",  "score": five_cs.get("character",  0)},
                {"name": "Capacity",   "score": five_cs.get("capacity",   0)},
                {"name": "Capital",    "score": five_cs.get("capital",    0)},
                {"name": "Collateral", "score": five_cs.get("collateral", 0)},
                {"name": "Conditions", "score": five_cs.get("conditions", 0)},
            ],
            "fraud_risk":   round((features.get("circular_trading_score", 0) +
                                   features.get("benford_deviation_score", 0)) * 50, 1),
            "credit_score": decision["credit_score"],
            "pd_pct":       round(decision["probability_of_default"] * 100, 2),
            "risk_grade":   decision["risk_grade"],
        }

    # =========================================================================
    # Five Cs detail section builders
    # =========================================================================
    def _character_section(self, f, promoter, research):
        return [
            {"metric": "Promoter Network Risk",  "value": f"{f.get('promoter_network_risk', 0):.3f}",     "unit": "0-1 (lower=better)"},
            {"metric": "Governance Risk Score",  "value": f"{f.get('_governance_risk_score', 0):.3f}",    "unit": "0-1 (lower=better)"},
            {"metric": "Character Score",        "value": f"{f.get('_character_score', 0):.1f}",           "unit": "/100 (higher=better)"},
            {"metric": "Litigation Count",       "value": str(int(f.get("litigation_count", 0))),          "unit": "cases"},
            {"metric": "Litigation Severity",    "value": f"{f.get('litigation_severity_score', 0):.3f}", "unit": "0-1"},
            {"metric": "Regulatory Violations",  "value": str(int(f.get("regulatory_violation_count", 0))),"unit": "count"},
            {"metric": "News Sentiment Risk",    "value": f"{f.get('news_sentiment_score', 0):.3f}",       "unit": "0-1 (lower=better)"},
        ]

    def _capacity_section(self, f, dr):
        return [
            {"metric": "DSCR",                   "value": _fmt(dr.get("dscr"),                     times=True), "unit": "(>=1.25 required)"},
            {"metric": "Interest Coverage Ratio", "value": _fmt(dr.get("interest_coverage_ratio"),  times=True), "unit": "(>=1.5 preferred)"},
            {"metric": "EBITDA Margin",           "value": _fmt(dr.get("ebitda_margin"),             pct=True),   "unit": "(>=12% preferred)"},
            {"metric": "PAT Margin",              "value": _fmt(dr.get("pat_margin"),                pct=True),   "unit": ""},
            {"metric": "Cashflow Volatility",     "value": f"{f.get('cashflow_volatility', 0):.3f}", "unit": "CV (lower=stable)"},
        ]

    def _capital_section(self, f, dr):
        return [
            {"metric": "Debt / Equity Ratio",      "value": _fmt(dr.get("debt_to_equity"),     times=True), "unit": "(<=2.0 preferred)"},
            {"metric": "Current Ratio",            "value": _fmt(dr.get("current_ratio"),       times=True), "unit": "(>=1.0 required)"},
            {"metric": "Revenue Growth (3yr CAGR)","value": _fmt(dr.get("revenue_growth_3yr"),  pct=True),   "unit": ""},
            {"metric": "Working Capital Days",     "value": _fmt(dr.get("working_capital_days"),days=True),  "unit": ""},
        ]

    def _collateral_section(self, f):
        ccr  = f.get("collateral_coverage_ratio", 0)
        band = ("Adequate (>=1.5x)" if ccr >= 1.5
                else "Marginal (1.0-1.5x)" if ccr >= 1.0
                else "Insufficient (<1.0x)")
        return [
            {"metric": "Collateral Coverage Ratio", "value": f"{ccr:.2f}x", "unit": "(>=1.25x required)"},
            {"metric": "Assessment",                "value": band,           "unit": ""},
        ]

    def _conditions_section(self, f, sector):
        return [
            {"metric": "Sector Risk Score",      "value": f"{f.get('sector_risk_score', 0):.3f}",            "unit": "0-1 (lower=better)"},
            {"metric": "Capacity Utilisation",   "value": f"{f.get('capacity_utilization', 0) * 100:.1f}%",  "unit": "(>=60% preferred)"},
            {"metric": "Customer Concentration", "value": f"{f.get('customer_concentration', 0) * 100:.1f}%","unit": "(<=40% preferred)"},
            {"metric": "Sector",                 "value": sector.get("sector_name", "N/A"),                   "unit": ""},
        ]

    def _litigation_summary(self, features, promoter, research):
        """Build litigation summary from actual data; avoid false 'no material litigation' when cases exist."""
        lit_count = int(features.get("litigation_count", 0))
        lit_sev   = features.get("litigation_severity_score", 0)
        cases     = promoter.get("litigation_cases", [])
        # Also check research for litigation
        research_lit = research.get("litigation", {}).get("cases", []) if isinstance(research.get("litigation"), dict) else []
        total_cases  = cases or research_lit

        if lit_count == 0 and not total_cases:
            return "No material litigation identified."

        sev_label = "HIGH" if lit_sev >= 0.6 else "MODERATE" if lit_sev >= 0.3 else "LOW"
        summary = f"{lit_count} active litigation case(s) identified (severity: {sev_label}, score: {lit_sev:.2f})."
        if total_cases:
            case_strs = []
            for c in total_cases[:3]:
                case_name = c.get("case_name", c.get("title", "Unnamed"))
                case_type = c.get("type", c.get("court", "N/A"))
                case_strs.append(f"{case_name} ({case_type})")
            summary += " Key cases: " + "; ".join(case_strs) + "."
        return summary
