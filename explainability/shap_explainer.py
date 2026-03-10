"""
SHAP Explainer — TreeExplainer on the XGBoost credit model.
Returns top feature contributions with signs and human-readable messages.
"""
import numpy as np
from typing import Dict, Any, List
from loguru import logger
from backend.config import FEATURE_NAMES
from models.feature_pipeline import features_to_array


class SHAPExplainer:
    def explain(self, features: Dict[str, float], ml_result: Dict) -> Dict[str, Any]:
        logger.info("[SHAP] Computing feature explanations")

        try:
            import shap
            from models.credit_model import CreditModel
            cm = CreditModel()

            X_raw  = features_to_array(features)
            X_proc = cm.pipeline.transform(X_raw)

            explainer   = shap.TreeExplainer(cm.model)
            shap_values = explainer.shap_values(X_proc)

            # For binary classification, shap_values shape is (1, n_features) or (2, 1, n_features)
            if isinstance(shap_values, list):
                sv = shap_values[1][0]   # Default class
            else:
                sv = shap_values[0]

            # Build explanations
            contributions = []
            for i, (name, shap_val) in enumerate(zip(FEATURE_NAMES, sv)):
                contributions.append({
                    "feature":      name,
                    "shap_value":   round(float(shap_val), 6),
                    "feature_value": round(float(X_raw[0][i]), 4),
                    "direction":    "increases_risk" if shap_val > 0 else "decreases_risk",
                    "abs_impact":   abs(float(shap_val)),
                })

            # Sort by absolute impact
            contributions.sort(key=lambda x: -x["abs_impact"])
            top_10 = contributions[:10]

            # Human-readable lines
            human_readable = self._to_human(top_10, features)

            return {
                "top_drivers":     top_10,
                "all_shap":        contributions,
                "expected_value":  float(explainer.expected_value[1] if isinstance(explainer.expected_value, list) else explainer.expected_value),
                "human_readable":  human_readable,
                "method":          "SHAP TreeExplainer",
            }

        except Exception as e:
            logger.error(f"[SHAP] Failed: {e} — using fallback rule-based explanation")
            return self._fallback_explain(features, ml_result)

    def _to_human(self, top: List[Dict], features: Dict) -> List[str]:
        """Convert SHAP values to plain-English sentences with correct financial logic."""
        PCT_FEATURES  = {"ebitda_margin", "pat_margin", "revenue_growth_3yr",
                         "gst_bank_mismatch_score", "capacity_utilization",
                         "customer_concentration", "itr_revenue_mismatch_score",
                         "gstr2a_3b_mismatch_score"}
        RATIO_FEATURES = {"dscr", "debt_to_equity", "current_ratio",
                          "interest_coverage_ratio", "collateral_coverage_ratio"}
        DAY_FEATURES   = {"debtor_days", "inventory_days", "working_capital_days"}

        lines = []
        for d in top:
            fname = d["feature"]
            val   = features.get(fname, 0.0)
            v     = d["shap_value"]
            direction = "↑ Risk" if v > 0 else "↓ Risk"
            risk_word = "increases" if v > 0 else "reduces"
            strength  = "significantly " if abs(v) > 0.01 else ""

            if fname in PCT_FEATURES:
                val_str = f"{val * 100:.1f}%"
            elif fname in RATIO_FEATURES:
                val_str = f"{val:.2f}×"
            elif fname in DAY_FEATURES:
                val_str = f"{val:.0f} days"
            elif fname == "litigation_count":
                val_str = f"{int(val)} case(s)"
            else:
                val_str = f"{val:.3f}"

            label = fname.replace("_", " ").title()
            lines.append(
                f"{direction}  {label} ({val_str}) {strength}{risk_word} default risk"
                f"  (SHAP: {v:+.4f})"
            )
        return lines

    def _fallback_explain(self, features: Dict, ml_result: Dict) -> Dict:
        """Uses model feature_importances_ when SHAP is unavailable."""
        try:
            from models.credit_model import CreditModel
            cm = CreditModel()
            importances = cm.model.feature_importances_          # shape (n_features,)
            max_imp = float(importances.max()) if importances.max() > 0 else 1.0

            # Features where LOW value = bad (high value reduces risk)
            GOOD_AT_HIGH = {
                "dscr", "interest_coverage_ratio", "current_ratio",
                "collateral_coverage_ratio", "ebitda_margin", "pat_margin",
                "revenue_growth_3yr", "capacity_utilization",
            }
            _GOOD_THRESH = {
                "dscr": 1.25, "interest_coverage_ratio": 1.5, "current_ratio": 1.0,
                "collateral_coverage_ratio": 1.0, "ebitda_margin": 0.10,
                "pat_margin": 0.04, "revenue_growth_3yr": 0.03, "capacity_utilization": 0.60,
            }
            # Features where HIGH value = bad (increases risk)
            HIGH_RISK_FEATURES = {
                "debt_to_equity", "circular_trading_score", "benford_deviation_score",
                "litigation_severity_score", "gst_bank_mismatch_score",
                "itr_revenue_mismatch_score", "gstr2a_3b_mismatch_score",
                "regulatory_violation_count", "news_sentiment_score",
                "promoter_network_risk",
            }

            contributions = []
            for name, imp in zip(FEATURE_NAMES, importances):
                feat_val = features.get(name, 0.0)
                if name in GOOD_AT_HIGH:
                    thresh = _GOOD_THRESH.get(name, 0.5)
                    sign = 1 if feat_val < thresh else -1   # low good-feature → increases risk
                elif name in HIGH_RISK_FEATURES:
                    sign = 1 if feat_val > 0.25 else -1     # high risk-feature → increases risk
                else:
                    sign = 1 if feat_val > 90 else -1        # working-capital days etc.
                pseudo_shap = sign * float(imp)
                contributions.append({
                    "feature":       name,
                    "shap_value":    round(pseudo_shap, 6),
                    "feature_value": round(float(feat_val), 4),
                    "direction":     "increases_risk" if pseudo_shap > 0 else "decreases_risk",
                    "abs_impact":    float(imp),
                    "importance":    round(float(imp) / max_imp, 4),
                })

            contributions.sort(key=lambda x: -x["abs_impact"])
            top_10 = contributions[:10]
            human_readable = self._to_human(top_10, features)
            return {
                "top_drivers":    top_10,
                "all_shap":       contributions,
                "human_readable": human_readable,
                "method":         "feature_importances_fallback",
            }
        except Exception as e2:
            logger.error(f"[SHAP] Fallback also failed: {e2}")
            ranked = sorted(features.items(), key=lambda x: abs(x[1]), reverse=True)[:10]
            return {
                "top_drivers":    [{"feature": k, "feature_value": v, "shap_value": 0.0, "direction": "unknown"} for k, v in ranked],
                "all_shap":       [],
                "human_readable": [f"{k.replace('_',' ').title()}: {v:.3f}" for k, v in ranked],
                "method":         "fallback_ranked_features",
            }
