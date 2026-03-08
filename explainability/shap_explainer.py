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
        """Convert SHAP values to plain English sentences."""
        lines = []
        templates = {
            "circular_trading_score":    "Circular trading score of {val:.2f} significantly increases default risk",
            "dscr":                      "DSCR of {val:.2f} {'reduces' if v < 0 else 'increases'} default probability",
            "debt_to_equity":            "High leverage (D/E {val:.2f}) increases credit risk",
            "litigation_severity_score": "Litigation severity {val:.2f} contributes to elevated risk",
            "gst_bank_mismatch_score":   "GST-bank revenue mismatch ({val:.0%}) signals possible inflation",
            "interest_coverage_ratio":   "Interest coverage {val:.2f}x {'comforts' if v < 0 else 'concerns'} the assessment",
            "news_sentiment_score":      "{'Negative' if val > 0.5 else 'Positive'} news sentiment affects risk score",
            "promoter_network_risk":     "Promoter network risk {val:.2f} {'adds' if v > 0 else 'reduces'} concern",
            "ebitda_margin":             "EBITDA margin {val:.1%} {'supports' if v < 0 else 'reduces'} repayment confidence",
            "revenue_growth_3yr":        "Revenue CAGR {val:.1%} {'strengthens' if v < 0 else 'weakens'} business outlook",
        }
        for d in top:
            fname = d["feature"]
            val   = features.get(fname, 0)
            v     = d["shap_value"]
            direction = "↑ Risk" if v > 0 else "↓ Risk"
            if fname in templates:
                try:
                    msg = templates[fname].format(val=val, v=v)
                except Exception:
                    msg = f"{fname}: {val:.3f}"
            else:
                msg = f"{fname.replace('_',' ').title()}: {val:.3f}"
            lines.append(f"{direction}  {msg}  (SHAP: {v:+.4f})")

        return lines

    def _fallback_explain(self, features: Dict, ml_result: Dict) -> Dict:
        """Rule-based explanation when SHAP is unavailable."""
        ranked = sorted(features.items(), key=lambda x: abs(x[1]), reverse=True)[:10]
        return {
            "top_drivers":    [{"feature": k, "feature_value": v, "shap_value": 0.0, "direction": "unknown"} for k, v in ranked],
            "all_shap":       [],
            "human_readable": [f"{k.replace('_',' ').title()}: {v:.3f}" for k, v in ranked],
            "method":         "fallback_ranked_features",
        }
