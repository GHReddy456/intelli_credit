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

        # Extract core financial figures from tables + segmented doc text figures
        fin = self._aggregate_financials(tables, segmented_docs)

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
            # ICR = EBIT / Interest_Expense (EBITDA fallback)
            "interest_coverage_ratio": self._icr(fin),

            # ── 7. DSCR (Debt Service Coverage Ratio) ────────────────────────
            "dscr": self._compute_dscr(fin),

            # ── 8. Working Capital Days ───────────────────────────────────────
            "working_capital_days": self._wc_days(fin),

            # ── 9. Debtor Days ────────────────────────────────────────────────
            "debtor_days": self._days(fin.get("receivables"), fin.get("revenue")),

            # ── 10. Inventory Days ────────────────────────────────────────────
            # Inventory_Days = (Inventory / COGS) × 365; fallback: revenue
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
            # Also expose count-based risk: min(1, count/20)
            "litigation_severity_score": max(
                research.get("litigation_severity_score", 0.0),
                research.get("litigation_risk", 0.0),
            ),

            # ── 19. News Sentiment Score ──────────────────────────────────────
            "news_sentiment_score": research.get("news_sentiment_score", 0.5),

            # ── 20. Promoter Network Risk ─────────────────────────────────────
            "promoter_network_risk": round(min(
                promoter.get("promoter_network_risk", 0.3) +
                promoter.get("shell_network_score", 0.0) * 0.20,
                1.0,
            ), 4),

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

        # ── Governance / Character score (0–100, higher = riskier) ──────────
        gov_score = self._governance_risk_score(features, promoter, fraud)
        features["_governance_risk_score"] = gov_score
        # Character score for Five Cs: invert so higher = better governance
        features["_character_score"] = round(max(0, 100 - gov_score * 100), 1)

        # ── Auxiliary fraud sub-scores (not ML features; used by CAM) ──────
        features["_layered_transaction_score"] = fraud.get("layered_transaction_score", 0.0)
        features["_shell_entity_score"]        = fraud.get("shell_entity_score", 0.0)
        features["_shell_network_score"]       = promoter.get("shell_network_score", 0.0)
        features["_audit_remark_score"]        = fraud.get("audit_remark_score", 0.0)

        # ── Financial trend series (for sparklines) ──────────────────────────
        features["_revenue_series"] = fin.get("revenue_series", [])
        features["_ebitda_series"]  = fin.get("ebitda_series",  [])
        features["_pat_series"]     = fin.get("pat_series",     [])
        features["_cfo_series"]     = fin.get("cfo_series",     [])

        # ── Sector peer benchmarks ───────────────────────────────────────────
        features["_sector_benchmarks"] = self._get_sector_benchmarks(sector)

        # ── Display-quality ratios (None = data not extracted from docs) ─────
        # Used by CAM to show "N/A" instead of defaulted 0.0
        def _has_data(*keys):
            return all(fin.get(k) for k in keys)

        features["_display_ratios"] = {
            "debt_to_equity":           features["debt_to_equity"]           if _has_data("total_debt", "equity") else None,
            "current_ratio":            features["current_ratio"]            if _has_data("current_assets", "current_liabilities") else None,
            "interest_coverage_ratio":  features["interest_coverage_ratio"]  if fin.get("interest") and (fin.get("ebit") or fin.get("ebitda")) else None,
            "dscr":                     features["dscr"]                     if fin.get("cfo") or fin.get("ebitda") else None,
            "ebitda_margin":            features["ebitda_margin"]            if _has_data("ebitda", "revenue") else None,
            "pat_margin":               features["pat_margin"]               if _has_data("pat", "revenue") else None,
            "revenue_growth_3yr":       features["revenue_growth_3yr"]       if len(fin.get("revenue_series", [])) >= 2 else None,
            "debtor_days":              features["debtor_days"]              if _has_data("receivables", "revenue") else None,
            "inventory_days":           features["inventory_days"]           if fin.get("inventories") and (fin.get("cogs") or fin.get("revenue")) else None,
            "working_capital_days":     features["working_capital_days"]     if fin.get("revenue") else None,
        }

        # ── Raw financial snapshot (in ₹ Cr) for borrower profile in CAM ────
        cr = 1_00_00_000  # 1 crore
        features["_financial_snapshot"] = {
            "revenue_cr":       round(fin.get("revenue", 0) / cr, 2) if fin.get("revenue", 0) > cr else fin.get("revenue", 0),
            "ebitda_cr":        round(fin.get("ebitda", 0) / cr, 2) if fin.get("ebitda") else None,
            "pat_cr":           round(fin.get("pat", 0) / cr, 2) if fin.get("pat") else None,
            "total_debt_cr":    round(fin.get("total_debt", 0) / cr, 2) if fin.get("total_debt") else None,
            "equity_cr":        round(fin.get("equity", 0) / cr, 2) if fin.get("equity") else None,
            "revenue_series":   fin.get("revenue_series", []),
        }

        logger.info(f"[FeatureEngine] Computed {len(features)} features")
        return features

    # ── Mapping from SegmentedDocument canonical labels → FeatureEngine metrics ─
    _SEG_TO_FIN: Dict[str, str] = {
        "revenue":        "revenue",
        "ebitda":         "ebitda",
        "pat":            "pat",
        "gross_profit":   "gross_profit",
        "total_debt":     "total_debt",
        "net_worth":      "equity",          # net_worth → equity
        "current_assets": "current_assets",
        "current_liab":   "current_liabilities",
        "cash":           "cash",
        "gst_turnover":   "gst_turnover",
        "itc":            "itc_claimed",
        "capex":          "cfi",
    }

    # ── Financial aggregation ─────────────────────────────────────────────
    def _aggregate_financials(self, tables: List[Dict], segmented_docs: List = None) -> Dict[str, Optional[float]]:
        """
        Aggregate financial metrics from two sources:
        1. TableExtractor output (structured tables from pdfplumber) — primary
        2. SegmentedDocument.all_financial_figures (text currency patterns) — fallback

        Source 2 is only used for metrics that Source 1 did not produce, avoiding
        scale-mixing between raw table numbers and Cr/Lakh-converted absolute values.
        """
        # ── Source 1: TableExtractor ─────────────────────────────────────────
        table_agg: Dict[str, list] = {}
        for tbl in tables:
            fd = tbl.get("financial_data", {})
            for metric, year_vals in fd.items():
                vals = [v for v in year_vals.values() if v is not None]
                if vals:
                    table_agg.setdefault(metric, []).extend(vals)

        # ── Source 2: SegmentedDocument text-currency figures (fallback) ─────
        # Only use figures with an explicit unit (Cr / Lakh / K) so that the
        # already-computed absolute_value is reliably scaled.
        seg_agg: Dict[str, list] = {}
        if segmented_docs:
            for doc in segmented_docs:
                for fig in getattr(doc, "all_financial_figures", []):
                    if fig.get("type") != "currency" or not fig.get("unit"):
                        continue           # skip unitless / tabular / ratio figures
                    mapped = self._SEG_TO_FIN.get(fig.get("canonical_label", "other"))
                    if not mapped:
                        continue
                    val = fig.get("absolute_value")
                    if val and val > 0:
                        seg_agg.setdefault(mapped, []).append(val)
            if seg_agg:
                logger.info(f"[FeatureEngine] Segment-extracted metrics: {list(seg_agg.keys())}")

        # ── Merge: table_agg wins; seg_agg fills gaps ─────────────────────────
        agg: Dict[str, list] = {}
        for metric in set(list(table_agg.keys()) + list(seg_agg.keys())):
            agg[metric] = table_agg[metric] if metric in table_agg else seg_agg[metric]

        # ── Best estimate = max (most recent year typically largest for trends) ─
        result = {}
        MULTI_YEAR = ["revenue", "pat", "ebitda", "cfo"]
        for metric, vals in agg.items():
            if metric in MULTI_YEAR:
                result[metric] = max(vals)
                result[f"{metric}_series"] = sorted(vals)
            else:
                result[metric] = max(vals)

        # ── Computed fallbacks for balance sheet totals ───────────────────────
        # total_debt = long_term_debt + short_term_debt (if total not extracted)
        if "total_debt" not in result:
            ltd = result.get("long_term_debt")
            std = result.get("short_term_debt")
            if ltd is not None or std is not None:
                result["total_debt"] = (ltd or 0.0) + (std or 0.0)
                logger.info("[FeatureEngine] total_debt computed from LTD + STD")

        # current_assets = inventories + receivables + cash (if total not extracted)
        if "current_assets" not in result:
            components = [result.get(k) for k in ("inventories", "receivables", "cash") if result.get(k)]
            if len(components) >= 2:
                result["current_assets"] = sum(components)
                logger.info("[FeatureEngine] current_assets computed from components")

        if result:
            logger.info(f"[FeatureEngine] Aggregated metrics: {list(result.keys())}")
        else:
            logger.warning("[FeatureEngine] No financial metrics extracted from tables or documents")
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

    def _icr(self, fin: Dict) -> float:
        """
        ICR = EBIT / Interest_Expense
        Fallback: use EBITDA if EBIT not extracted.
        If interest_expense = 0 / None, returns 0.0 (data missing).
        """
        ebit     = fin.get("ebit") or fin.get("ebitda")
        interest = fin.get("interest")
        if not ebit or not interest or interest == 0:
            return 0.0
        return round(ebit / interest, 4)

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

    def _governance_risk_score(self, features: Dict, promoter: Dict = None, fraud: Dict = None) -> float:
        """
        Composite governance / character risk score (0–1, higher = worse).
        Weights key integrity signals for the Five Cs CHARACTER dimension.
        """
        promoter = promoter or {}
        fraud    = fraud or {}
        score = 0.0
        # Litigation signals (max 0.35)
        lit_sev = min(features.get("litigation_severity_score", 0.0), 1.0)
        lit_cnt = min(features.get("litigation_count", 0.0) / 10.0, 1.0)
        score += 0.25 * lit_sev + 0.10 * lit_cnt
        # Fraud signals (max 0.25)
        benford  = min(features.get("benford_deviation_score", 0.0), 1.0)
        circular = min(features.get("circular_trading_score", 0.0), 1.0)
        layered  = min(fraud.get("layered_transaction_score", 0.0), 1.0)
        shell_t  = min(fraud.get("shell_entity_score", 0.0), 1.0)
        shell_p  = min(promoter.get("shell_network_score", 0.0), 1.0)
        score += 0.12 * benford + 0.08 * circular + 0.03 * layered + 0.02 * shell_t + 0.03 * shell_p
        # Audit qualifications (max 0.10)
        audit_score = min(fraud.get("audit_remark_score", 0.0), 1.0)
        score += 0.10 * audit_score
        # Cross-verification / tax compliance (max 0.20)
        gst_mm  = min(features.get("gst_bank_mismatch_score", 0.0), 1.0)
        gstr_mm = min(features.get("gstr2a_3b_mismatch_score", 0.0), 1.0)
        itr_mm  = min(features.get("itr_revenue_mismatch_score", 0.0), 1.0)
        score += 0.08 * gst_mm + 0.07 * gstr_mm + 0.05 * itr_mm
        # Regulatory violations (max 0.15)
        reg_v = min(features.get("regulatory_violation_count", 0.0) / 10.0, 1.0)
        score += 0.15 * reg_v
        return round(min(score, 1.0), 4)

    # Sector medians for peer benchmarking
    _SECTOR_MEDIANS: Dict[str, Dict[str, float]] = {
        "steel":          {"dscr": 1.30, "debt_to_equity": 2.20, "ebitda_margin": 0.14, "current_ratio": 1.25},
        "textile":        {"dscr": 1.25, "debt_to_equity": 1.80, "ebitda_margin": 0.12, "current_ratio": 1.30},
        "real_estate":    {"dscr": 1.10, "debt_to_equity": 2.50, "ebitda_margin": 0.22, "current_ratio": 1.10},
        "it":             {"dscr": 3.00, "debt_to_equity": 0.30, "ebitda_margin": 0.24, "current_ratio": 2.50},
        "pharma":         {"dscr": 2.50, "debt_to_equity": 0.60, "ebitda_margin": 0.22, "current_ratio": 1.80},
        "nbfc":           {"dscr": 1.50, "debt_to_equity": 3.50, "ebitda_margin": 0.30, "current_ratio": 1.20},
        "infrastructure": {"dscr": 1.20, "debt_to_equity": 2.00, "ebitda_margin": 0.20, "current_ratio": 1.15},
        "agri":           {"dscr": 1.40, "debt_to_equity": 1.20, "ebitda_margin": 0.10, "current_ratio": 1.40},
        "auto":           {"dscr": 1.60, "debt_to_equity": 1.00, "ebitda_margin": 0.14, "current_ratio": 1.30},
        "cement":         {"dscr": 1.80, "debt_to_equity": 1.00, "ebitda_margin": 0.20, "current_ratio": 1.20},
        "fmcg":           {"dscr": 3.50, "debt_to_equity": 0.40, "ebitda_margin": 0.18, "current_ratio": 1.50},
        "energy":         {"dscr": 1.40, "debt_to_equity": 2.00, "ebitda_margin": 0.22, "current_ratio": 1.20},
        "logistics":      {"dscr": 1.70, "debt_to_equity": 1.10, "ebitda_margin": 0.12, "current_ratio": 1.25},
        "chemicals":      {"dscr": 1.80, "debt_to_equity": 1.20, "ebitda_margin": 0.16, "current_ratio": 1.35},
        "default":        {"dscr": 1.40, "debt_to_equity": 1.50, "ebitda_margin": 0.15, "current_ratio": 1.30},
    }

    def _get_sector_benchmarks(self, sector_result: Dict) -> Dict:
        """
        Return sector median ratios and vs-company comparisons for three key metrics.
        """
        sector_name = sector_result.get("sector", "default")
        medians = self._SECTOR_MEDIANS.get(sector_name, self._SECTOR_MEDIANS["default"])
        return {
            "sector": sector_name,
            "medians": medians,
        }
