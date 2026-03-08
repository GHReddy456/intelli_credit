"""
Feature Engine — Computes exactly 25 credit risk features from all upstream outputs.
Returns a flat dict {feature_name: float} ready for the ML model.
"""
import re
from typing import List, Dict, Any, Optional
from loguru import logger
from backend.config import FEATURE_NAMES


class FeatureEngine:
    """
    All 25 features with fallback defaults so the ML model always gets a full vector.
    Missing data is imputed to the population median (handled in feature_pipeline.py).
    """

    def compute(
        self,
        segmented_docs: List,
        tables:         List[Dict],
        verification:   Dict,
        fraud:          Dict,
        research:       Dict,
        promoter:       Dict,
        sector:         Dict,
        dd_notes:       str = "",
    ) -> Dict[str, Any]:
        logger.info("[FeatureEngine] Computing 25 risk features")

        # Extract core financial figures from tables
        fin = self._aggregate_financials(tables)

        features = {
            # ── 1. Revenue growth (3-year CAGR) ─────────────────────────────
            "revenue_growth_3yr": self._revenue_cagr(fin),

            # ── 2. EBITDA margin ─────────────────────────────────────────────
            "ebitda_margin": self._ratio(fin.get("ebitda"), fin.get("revenue")),

            # ── 3. PAT margin ─────────────────────────────────────────────────
            "pat_margin": self._ratio(fin.get("pat"), fin.get("revenue")),

            # ── 4. Debt-to-Equity ─────────────────────────────────────────────
            "debt_to_equity": self._ratio(fin.get("total_debt"), fin.get("equity")),

            # ── 5. Current Ratio ──────────────────────────────────────────────
            "current_ratio": self._ratio(fin.get("current_assets"), fin.get("current_liabilities")),

            # ── 6. Interest Coverage Ratio ────────────────────────────────────
            "interest_coverage_ratio": self._ratio(fin.get("ebit") or fin.get("ebitda"), fin.get("interest")),

            # ── 7. DSCR (Debt Service Coverage Ratio) ────────────────────────
            "dscr": self._compute_dscr(fin),

            # ── 8. Working Capital Days ───────────────────────────────────────
            "working_capital_days": self._wc_days(fin),

            # ── 9. Debtor Days ────────────────────────────────────────────────
            "debtor_days": self._days(fin.get("receivables"), fin.get("revenue")),

            # ── 10. Inventory Days ────────────────────────────────────────────
            "inventory_days": self._days(fin.get("inventories"), fin.get("cogs") or fin.get("revenue")),

            # ── 11. Cash Flow Volatility ──────────────────────────────────────
            "cashflow_volatility": self._cfo_volatility(fin),

            # ── 12. GST-Bank Mismatch Score ───────────────────────────────────
            "gst_bank_mismatch_score": verification.get("mismatch_scores", {}).get("gst_bank_mismatch_score", 0.0),

            # ── 13. GSTR-2A vs 3B Mismatch ────────────────────────────────────
            "gstr2a_3b_mismatch_score": verification.get("mismatch_scores", {}).get("gstr2a_3b_mismatch_score", 0.0),

            # ── 14. ITR Revenue Mismatch ──────────────────────────────────────
            "itr_revenue_mismatch_score": verification.get("mismatch_scores", {}).get("itr_revenue_mismatch_score", 0.0),

            # ── 15. Circular Trading Score ────────────────────────────────────
            "circular_trading_score": fraud.get("circular_trading_score", 0.0),

            # ── 16. Benford Deviation Score ───────────────────────────────────
            "benford_deviation_score": fraud.get("benford_deviation_score", 0.0),

            # ── 17. Litigation Count ──────────────────────────────────────────
            "litigation_count": float(research.get("litigation_count", 0)),

            # ── 18. Litigation Severity Score ─────────────────────────────────
            "litigation_severity_score": research.get("litigation_severity_score", 0.0),

            # ── 19. News Sentiment Score ──────────────────────────────────────
            "news_sentiment_score": research.get("news_sentiment_score", 0.5),

            # ── 20. Promoter Network Risk ─────────────────────────────────────
            "promoter_network_risk": promoter.get("promoter_network_risk", 0.3),

            # ── 21. Sector Risk Score ─────────────────────────────────────────
            "sector_risk_score": sector.get("sector_risk_score", 0.5),

            # ── 22. Collateral Coverage Ratio ─────────────────────────────────
            "collateral_coverage_ratio": self._collateral_coverage(dd_notes, fin),

            # ── 23. Capacity Utilization ──────────────────────────────────────
            "capacity_utilization": self._capacity_from_notes(dd_notes),

            # ── 24. Customer Concentration ────────────────────────────────────
            "customer_concentration": self._customer_concentration(segmented_docs),

            # ── 25. Regulatory Violation Count ────────────────────────────────
            "regulatory_violation_count": (
                float(research.get("regulatory_violation_count", 0))
                + self._count_audit_violations(segmented_docs)
            ),
        }

        # ── Prefer text-extracted key ratios (more reliable than multi-year table max) ──
        text_fin = self._extract_text_financials(segmented_docs)
        _ratio_overrides = {
            "debt_to_equity":          "debt_equity_ratio",
            "current_ratio":           "current_ratio",
            "interest_coverage_ratio": "interest_coverage",
            "dscr":                    "dscr",
        }
        for feat, text_key in _ratio_overrides.items():
            if text_key in text_fin:          # override regardless of table value
                features[feat] = text_fin[text_key]
        if "debtor_days" in text_fin:
            features["debtor_days"] = text_fin["debtor_days"]

        # Clip all to [0, inf] and round
        for k, v in features.items():
            if v is None:
                features[k] = 0.0
            else:
                features[k] = round(float(v), 6)

        # Compute _turnover_crore for decision engine loan computation
        revenue_raw = fin.get("revenue", 0) or 0
        if revenue_raw >= 1_00_00_000:  # ≥ 1 Cr in absolute
            features["_turnover_crore"] = round(revenue_raw / 1_00_00_000, 2)
        elif revenue_raw > 0:           # might already be in Cr
            features["_turnover_crore"] = round(revenue_raw, 2)
        else:
            features["_turnover_crore"] = 0.0

        logger.info(f"[FeatureEngine] Computed {len(features)} features")
        return features

    # ── Financial aggregation ─────────────────────────────────────────────
    def _aggregate_financials(self, tables: List[Dict]) -> Dict[str, Optional[float]]:
        """Aggregate financial metrics from all table extracts."""
        agg: Dict[str, list] = {}

        for tbl in tables:
            fd = tbl.get("financial_data", {})
            for metric, year_vals in fd.items():
                vals = [v for v in year_vals.values() if v is not None]
                if vals:
                    agg.setdefault(metric, []).extend(vals)

        # Best estimate = max (most recent year is typically largest)
        result = {}
        MULTI_YEAR = ["revenue", "pat", "ebitda", "cfo"]  # take all for trend
        for metric, vals in agg.items():
            if metric in MULTI_YEAR:
                result[metric] = max(vals)
                result[f"{metric}_series"] = sorted(vals)
            else:
                result[metric] = max(vals)

        return result

    # ── Individual feature computations ──────────────────────────────────
    def _revenue_cagr(self, fin: Dict) -> float:
        series = fin.get("revenue_series", [])
        if len(series) >= 2:
            start, end = series[0], series[-1]
            n = len(series) - 1
            if start > 0 and n > 0:
                cagr = (end / start) ** (1 / n) - 1
                return round(cagr, 4)
        return 0.05   # default 5% growth assumption

    def _ratio(self, numerator, denominator) -> float:
        if numerator is None or denominator is None or denominator == 0:
            return 0.0
        return round(numerator / denominator, 4)

    def _compute_dscr(self, fin: Dict) -> float:
        """DSCR = CFO / (Interest + CPLTD)"""
        cfo       = fin.get("cfo", fin.get("ebitda"))
        interest  = fin.get("interest", 0) or 0
        # Approximate CPLTD as 10% of total debt if not available
        cpltd     = (fin.get("total_debt", 0) or 0) * 0.10
        denominator = interest + cpltd
        return self._ratio(cfo, denominator) if denominator > 0 else 1.5

    def _wc_days(self, fin: Dict) -> float:
        """Working Capital Days = (CA - CL) / (Revenue / 365)"""
        ca  = fin.get("current_assets", 0) or 0
        cl  = fin.get("current_liabilities", 0) or 0
        rev = fin.get("revenue", 0)
        if not rev:
            return 90.0  # default
        return round(((ca - cl) / rev) * 365, 1)

    def _days(self, balance, turnover) -> float:
        if not balance or not turnover or turnover == 0:
            return 0.0   # 0 = data missing (not optimistic 60)
        return round((balance / turnover) * 365, 1)

    def _cfo_volatility(self, fin: Dict) -> float:
        series = fin.get("cfo_series", [])
        if len(series) < 2:
            return 0.2   # moderate default
        import statistics
        try:
            mean = statistics.mean(series)
            if mean == 0:
                return 0.5
            std  = statistics.stdev(series)
            return round(std / abs(mean), 4)   # coefficient of variation
        except Exception:
            return 0.2

    def _collateral_coverage(self, dd_notes: str, fin: Dict) -> float:
        # Try to extract from DD notes: "collateral value X cr"
        m = re.search(r"collateral[^\n]*?(?:₹|Rs\.?|INR)?\s*([\d.]+)\s*(?:cr|crore|lakh)?", dd_notes, re.IGNORECASE)
        if m:
            collateral_val = float(m.group(1))
            total_debt     = (fin.get("total_debt") or 0) / 10_000_000   # convert to Cr
            if total_debt > 0:
                return round(collateral_val / total_debt, 3)
        return 1.30   # default 1.30x coverage assumption

    def _capacity_from_notes(self, dd_notes: str) -> float:
        """Extract capacity utilization % from DD notes."""
        m = re.search(r"(?:capacity|utilization|util)[^\n]*?(\d{1,3})\s*%", dd_notes, re.IGNORECASE)
        if m:
            pct = float(m.group(1))
            return round(pct / 100, 4)
        # Check for qualitative hints
        dl = dd_notes.lower()
        if "low capacity" in dl or "idle" in dl:
            return 0.35
        if "full capacity" in dl or "running well" in dl:
            return 0.90
        return 0.70   # default 70%

    def _customer_concentration(self, docs: List) -> float:
        """Estimate customer concentration from annual report text."""
        for doc in docs:
            if doc.doc_type != "annual_report":
                continue
            text = doc.text_content
            # Look for top customer % pattern
            m = re.search(
                r"(?:top \d+ customers?|major customers?)[^.]*?(\d{1,3})\s*%",
                text, re.IGNORECASE,
            )
            if m:
                pct = float(m.group(1))
                return round(pct / 100, 4)
        return 0.40   # default: 40% concentration

    def _extract_text_financials(self, docs: List) -> Dict[str, float]:
        """
        Fallback: extract key financial ratios directly from document text
        (Key Ratios section in annual report). Used to override 0.0 values
        that arise when table extraction fails.
        """
        result: Dict[str, float] = {}
        patterns = {
            "debt_equity_ratio": [
                r"debt[/\s-]*equity[^\n]*?(\d+\.?\d*)",
                r"d/e[^\n]*?(\d+\.?\d*)",
            ],
            "current_ratio": [
                r"current ratio[^\n]*?(\d+\.?\d*)",
            ],
            "interest_coverage": [
                r"interest coverage[^\n]*?(\d+\.?\d*)",
            ],
            "dscr": [
                r"\bdscr[^\n]*?(\d+\.?\d*)",
                r"debt service coverage[^\n]*?(\d+\.?\d*)",
            ],
            "debtor_days": [
                r"debtor days?[^\n]*?(\d+)",
                r"receivable days?[^\n]*?(\d+)",
            ],
            "cfo": [
                r"cash flow from operations[^\n]*?(\d+\.?\d*)",
                r"operating cash flow[^\n]*?(\d+\.?\d*)",
            ],
        }
        for doc in docs:
            try:
                text = doc.text_content or ""
            except Exception:
                continue
            for feat, pats in patterns.items():
                if feat in result:
                    continue          # already found from earlier doc
                for pat in pats:
                    m = re.search(pat, text, re.IGNORECASE)
                    if m:
                        try:
                            result[feat] = float(m.group(1))
                            break
                        except ValueError:
                            pass
        if result:
            logger.info(f"[FeatureEngine] Text-extracted ratios: {result}")
        return result

    def _count_audit_violations(self, docs: List) -> float:
        """
        Scan document text for high-risk audit language.
        Returns a count added to regulatory_violation_count.
        """
        AUDIT_FLAGS = [
            (["qualified opinion", "basis for qualified"], 2.0),
            (["going concern", "material uncertainty relating to going concern"], 3.0),
            (["adverse opinion"], 4.0),
            (["emphasis of matter", "emphasis-of-matter"], 1.0),
            (["scope limitation", "unable to obtain sufficient audit evidence"], 1.5),
        ]
        total = 0.0
        for doc in docs:
            try:
                text = (doc.text_content or "").lower()
            except Exception:
                continue
            for keywords, weight in AUDIT_FLAGS:
                if any(kw in text for kw in keywords):
                    total += weight
                    logger.warning(f"[FeatureEngine] Audit flag detected (+{weight}): {keywords[0]}")
        return min(total, 10.0)   # cap so it can't dominate
