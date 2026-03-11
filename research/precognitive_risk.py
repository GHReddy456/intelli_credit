"""
Pre-Cognitive Risk Engine — generates EARLY WARNING signals that predict
FUTURE financial distress BEFORE it crystallizes into defaults.

Pre-cognitive signals synthesize:
  • Trajectory analysis  (trend direction, not just current snapshot value)
  • Multi-source convergence (independent sources agreeing = high confidence)
  • Macro-sector-company compounding (stresses at multiple levels amplify each other)
  • Behavioral anomalies (Benford deviation, circular trading = financial manipulation)
  • Credit rating intelligence (agency leading indicators)
  • Liquidity early-warning (working capital cycle, current ratio, CF volatility)
  • Disclosure risk (external evidence not reflected in submitted documents)

Each signal is tagged with: category, severity (CRITICAL / HIGH / MEDIUM),
title, description, and recommended action.
"""
from __future__ import annotations

from typing import Dict, Any, List

from loguru import logger


# ── Severity → CAM color mapping (used by pdf_exporter) ─────────────────────
SEVERITY_COLORS = {
    "CRITICAL": "#DC2626",   # red
    "HIGH":     "#D97706",   # amber
    "MEDIUM":   "#2563EB",   # blue
}


class PreCognitiveRiskEngine:
    """Synthesizes early-warning pre-cognitive risk signals."""

    def generate_signals(
        self,
        research:      Dict[str, Any],
        features:      Dict[str, Any],
        macro:         Dict[str, Any],
        triangulation: Dict[str, Any],
        credit_ratings: Dict[str, Any],
    ) -> Dict[str, Any]:
        logger.info("[PreCognitive] Generating pre-cognitive risk signals")

        signals: List[Dict] = []

        # ── Signal 1: Triple leverage stress ─────────────────────────────────
        de         = features.get("debt_to_equity",            1.0)
        dscr       = features.get("dscr",                      1.5)
        icr        = features.get("interest_coverage_ratio",   3.0)
        rev_growth = features.get("revenue_growth_3yr",        0.05)
        ebitda_m   = features.get("ebitda_margin",             0.10)

        if de > 2.0 and dscr < 1.25 and icr < 1.5:
            signals.append({
                "category":    "LEVERAGE_STRESS",
                "severity":    "CRITICAL",
                "title":       "Triple Leverage Warning — D/E + DSCR + ICR all breached",
                "description": (
                    f"D/E ({de:.2f}x), DSCR ({dscr:.2f}x), and ICR ({icr:.2f}x) simultaneously "
                    f"breach safe thresholds. This 'triple stress' pattern is a high-confidence "
                    f"90-day precursor to debt-service failure observed in Indian NPA cases."
                ),
                "action": "Immediate debt-repayment schedule review and restructuring capacity assessment.",
            })
        elif de > 1.5 and rev_growth < 0:
            signals.append({
                "category":    "LEVERAGE_STRESS",
                "severity":    "HIGH",
                "title":       "Rising Debt + Falling Revenue — Leverage Squeeze Trajectory",
                "description": (
                    f"D/E {de:.2f}x with negative 3yr revenue CAGR ({rev_growth:.1%}). "
                    f"Debt fixed costs growing relative to shrinking revenue — "
                    f"classic early-stage distress trajectory."
                ),
                "action": "Request revenue-debt bridge model; monitor next two quarters closely.",
            })

        # ── Signal 2: Multi-source fraud convergence ──────────────────────────
        benford  = features.get("benford_deviation_score",   0)
        circular = features.get("circular_trading_score",    0)
        gst_mm   = features.get("gst_bank_mismatch_score",   0)
        itr_mm   = features.get("itr_revenue_mismatch_score",0)
        neg_news = research.get("news", {}).get("negative_count", 0)
        corroborated = triangulation.get("corroborated_count", 0)

        fraud_streams = sum([
            benford  > 0.25,
            circular > 0.25,
            gst_mm   > 0.25,
            itr_mm   > 0.25,
            neg_news >= 3,
            corroborated >= 2,
        ])

        if fraud_streams >= 4:
            signals.append({
                "category":    "FRAUD_CONVERGENCE",
                "severity":    "CRITICAL",
                "title":       f"Multi-Stream Fraud Convergence ({fraud_streams}/6 independent sources)",
                "description": (
                    f"Fraud/manipulation risk flagged across {fraud_streams} independent data streams: "
                    f"Benford ({benford:.2f}), Circular Trading ({circular:.2f}), "
                    f"GST-Bank ({gst_mm:.2f}), ITR ({itr_mm:.2f}), "
                    f"Media ({neg_news} neg. articles), Triangulation ({corroborated} corroborated). "
                    f"Independent convergence dramatically elevates signal confidence."
                ),
                "action": "Mandatory forensic audit before any credit sanction.",
            })
        elif fraud_streams >= 2:
            signals.append({
                "category":    "FRAUD_CONVERGENCE",
                "severity":    "HIGH",
                "title":       f"Partial Fraud Signal Convergence ({fraud_streams}/6 sources)",
                "description": (
                    f"Fraud indicators appearing in {fraud_streams} independent data streams. "
                    f"Not conclusive, but warrants enhanced due diligence and field verification."
                ),
                "action": "Request additional bank statements, GST reconciliation, and independent field visit.",
            })

        # ── Signal 3: Macro-Sector-Company compounding ────────────────────────
        macro_risk  = macro.get("macro_risk_score",       0.5)
        sector_risk = research.get("sector_risk_score",   0.5)
        rate_env    = macro.get("rate_environment",        "NEUTRAL")

        if macro_risk > 0.55 and sector_risk > 0.55 and ebitda_m < 0.10:
            signals.append({
                "category":    "MACRO_COMPOUNDING",
                "severity":    "HIGH",
                "title":       "Macro × Sector × Company Stress Compounding",
                "description": (
                    f"Three independent stress layers compounding: "
                    f"(1) Macro environment risk {macro_risk:.0%} (RBI: {rate_env}), "
                    f"(2) Sector headwinds {sector_risk:.0%}, "
                    f"(3) Company EBITDA margin {ebitda_m:.1%}. "
                    f"Compounding stresses amplify default risk non-linearly."
                ),
                "action": "Apply heightened macro stress-testing; scenario model 200bp rate hike.",
            })

        # ── Signal 4: Credit rating deterioration ─────────────────────────────
        co_trend      = credit_ratings.get("company_rating_trend",   "STABLE")
        sec_quality   = credit_ratings.get("sector_credit_quality",  "STABLE")
        ratings_found = credit_ratings.get("company_rating_mentions", [])

        if co_trend == "DETERIORATING":
            signals.append({
                "category":    "RATING_DETERIORATION",
                "severity":    "HIGH",
                "title":       "Credit Rating Downgrade Signal Detected (CRISIL/ICRA/CARE)",
                "description": (
                    f"External credit rating intelligence suggests deteriorating credit quality. "
                    f"Detected ratings: {', '.join(ratings_found[:3]) or '— see agency reports'}. "
                    f"Sector credit quality trend: {sec_quality}. "
                    f"Rating downgrades often activate covenant triggers on existing debt."
                ),
                "action": "Verify latest CRISIL/ICRA/CARE rating directly; check covenant clauses.",
            })
        elif sec_quality == "DETERIORATING" and co_trend == "STABLE":
            signals.append({
                "category":    "RATING_DETERIORATION",
                "severity":    "MEDIUM",
                "title":       "Sector-Level Rating Deterioration Even as Company Appears Stable",
                "description": (
                    f"Sector credit quality is deteriorating per rating agency signals, "
                    f"while company-specific alerts are currently muted. "
                    f"Sector peer pressure may flow through within 2-3 quarters."
                ),
                "action": "Monitor sector peer group ratings and covenant headroom quarterly.",
            })

        # ── Signal 5: Cash conversion cycle breakdown ─────────────────────────
        wc_days  = features.get("working_capital_days", 90)
        cf_vol   = features.get("cashflow_volatility",   0.2)
        curr_rat = features.get("current_ratio",          1.5)

        if wc_days > 180 and curr_rat < 1.2 and cf_vol > 0.3:
            signals.append({
                "category":    "LIQUIDITY_RISK",
                "severity":    "HIGH",
                "title":       "Cash Conversion Cycle Breakdown with Liquidity Vulnerability",
                "description": (
                    f"Working capital cycle stretched at {wc_days:.0f} days, "
                    f"current ratio {curr_rat:.2f}x, and high cashflow volatility ({cf_vol:.2f}). "
                    f"Business relies on rollover of short-term debt to fund operations. "
                    f"Any credit tightening could trigger a liquidity event."
                ),
                "action": "Map month-by-month cash flow for next 12 months; assess credit line headroom.",
            })
        elif wc_days > 120 and curr_rat < 1.5:
            signals.append({
                "category":    "LIQUIDITY_RISK",
                "severity":    "MEDIUM",
                "title":       "Stretched Working Capital → Latent Liquidity Risk",
                "description": (
                    f"Working capital at {wc_days:.0f} days with current ratio {curr_rat:.2f}x. "
                    f"Reliance on short-term borrowings to fund operations may compress margins."
                ),
                "action": "Review debtor/creditor aging; check bank utilization utilisation levels.",
            })

        # ── Signal 6: Selective disclosure risk ───────────────────────────────
        discrepancy_count = triangulation.get("discrepancy_count", 0)
        if discrepancy_count >= 2:
            top_disc = triangulation.get("top_discrepancies", [])
            disc_titles = "; ".join(d["signal"] for d in top_disc[:2])
            signals.append({
                "category":    "DISCLOSURE_RISK",
                "severity":    "HIGH",
                "title":       f"Selective Disclosure Risk — {discrepancy_count} Information Gaps",
                "description": (
                    f"External research reveals {discrepancy_count} material piece(s) of information "
                    f"NOT reflected in submitted documents — a pattern consistent with selective disclosure. "
                    f"Issues identified: {disc_titles}."
                ),
                "action": "Request complete document set; engage independent verification agency.",
            })

        # ── Signal 7: Customer concentration + revenue decline ────────────────
        cust_conc = features.get("customer_concentration", 0.5)
        if cust_conc > 0.60 and rev_growth < 0:
            signals.append({
                "category":    "CONCENTRATION_RISK",
                "severity":    "MEDIUM",
                "title":       "High Customer Concentration + Declining Revenue = Binary Risk",
                "description": (
                    f"Customer concentration {cust_conc:.0%} — loss of a key customer combined with "
                    f"already declining revenue ({rev_growth:.1%}) creates binary credit risk. "
                    f"No revenue diversification to absorb customer loss."
                ),
                "action": "Assess top-3 customer health; verify order book next 12 months.",
            })

        # ── Aggregate ─────────────────────────────────────────────────────────
        critical = [s for s in signals if s["severity"] == "CRITICAL"]
        high     = [s for s in signals if s["severity"] == "HIGH"]
        medium   = [s for s in signals if s["severity"] == "MEDIUM"]

        precog_score = round(
            min(len(critical) * 0.25 + len(high) * 0.12 + len(medium) * 0.05, 1.0), 4
        )

        logger.info(
            f"[PreCognitive] {len(signals)} signals — "
            f"{len(critical)} CRITICAL, {len(high)} HIGH, {len(medium)} MEDIUM — "
            f"score={precog_score:.3f}"
        )

        return {
            "signals":                 signals,
            "critical_count":          len(critical),
            "high_count":              len(high),
            "medium_count":            len(medium),
            "total_signals":           len(signals),
            "precognitive_risk_score": precog_score,
            "top_signals":             signals[:5],
        }
