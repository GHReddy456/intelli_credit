"""
Credit Model — XGBoost classifier for corporate credit risk.
Train on synthetic Indian corporate dataset (500 samples).
Saves model to disk and loads on subsequent runs.
"""
import os
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, Any
from loguru import logger
from backend.config import FEATURE_NAMES, MODEL_DIR
from models.feature_pipeline import build_pipeline, features_to_array, features_to_matrix


MODEL_PATH    = MODEL_DIR / "credit_model.pkl"
PIPELINE_PATH = MODEL_DIR / "feature_pipeline.pkl"


class CreditModel:
    def __init__(self):
        self.model    = None
        self.pipeline = None
        self._load_or_train()

    # ── Public API ─────────────────────────────────────────────────────────
    def predict(self, features: Dict[str, float]) -> Dict[str, Any]:
        X_raw  = features_to_array(features)
        X_proc = self.pipeline.transform(X_raw)

        prob_default = float(self.model.predict_proba(X_proc)[0][1])
        credit_score = round((1 - prob_default) * 100, 1)

        logger.info(f"[CreditModel] score={credit_score}, PD={prob_default:.4f}")
        return {
            "credit_score":           credit_score,
            "probability_of_default": round(prob_default, 4),
            "risk_grade":             self._grade(credit_score),
        }

    # ── Model training ─────────────────────────────────────────────────────
    def _load_or_train(self):
        if MODEL_PATH.exists() and PIPELINE_PATH.exists():
            logger.info("[CreditModel] Loading saved model")
            with open(MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)
            with open(PIPELINE_PATH, "rb") as f:
                self.pipeline = pickle.load(f)
        else:
            logger.info("[CreditModel] Training new model on synthetic dataset")
            self._train()

    def _train(self):
        from xgboost import XGBClassifier

        X, y = self._generate_synthetic_dataset(n=600)

        self.pipeline = build_pipeline()
        X_proc = self.pipeline.fit_transform(X)

        self.model = XGBClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.8,
            colsample_bytree=0.8,
            use_label_encoder=False,
            eval_metric="logloss",
            random_state=42,
        )
        self.model.fit(X_proc, y)

        with open(MODEL_PATH, "wb") as f:
            pickle.dump(self.model, f)
        with open(PIPELINE_PATH, "wb") as f:
            pickle.dump(self.pipeline, f)

        logger.info("[CreditModel] Model trained and saved")

    def _generate_synthetic_dataset(self, n: int = 600):
        """
        Generate synthetic Indian corporate credit dataset.
        Feature values follow realistic distributions for the 25 features.
        Label = 1 (default) determined by rule-based logic reflecting real credit logic.
        """
        np.random.seed(42)
        N = n

        data = {
            "revenue_growth_3yr":            np.random.normal(0.07,  0.12, N),
            "ebitda_margin":                  np.random.normal(0.12,  0.07, N),
            "pat_margin":                     np.random.normal(0.06,  0.05, N),
            "debt_to_equity":                 np.abs(np.random.normal(1.5,  1.2, N)),
            "current_ratio":                  np.abs(np.random.normal(1.4,  0.5, N)),
            "interest_coverage_ratio":        np.abs(np.random.normal(2.5,  1.5, N)),
            "dscr":                           np.abs(np.random.normal(1.4,  0.5, N)),
            "working_capital_days":           np.random.normal(75,    40,   N),
            "debtor_days":                    np.abs(np.random.normal(65,   30,   N)),
            "inventory_days":                 np.abs(np.random.normal(55,   25,   N)),
            "cashflow_volatility":            np.abs(np.random.normal(0.25, 0.20, N)),
            "gst_bank_mismatch_score":        np.abs(np.random.normal(0.10, 0.12, N)),
            "gstr2a_3b_mismatch_score":       np.abs(np.random.normal(0.08, 0.10, N)),
            "itr_revenue_mismatch_score":     np.abs(np.random.normal(0.08, 0.10, N)),
            "circular_trading_score":         np.abs(np.random.exponential(0.10, N)),
            "benford_deviation_score":        np.abs(np.random.normal(0.20, 0.15, N)),
            "litigation_count":               np.abs(np.random.poisson(1.5, N)).astype(float),
            "litigation_severity_score":      np.abs(np.random.normal(0.20, 0.20, N)),
            "news_sentiment_score":           np.random.uniform(0.2, 0.8, N),
            "promoter_network_risk":          np.abs(np.random.normal(0.30, 0.20, N)),
            "sector_risk_score":              np.random.uniform(0.25, 0.75, N),
            "collateral_coverage_ratio":      np.abs(np.random.normal(1.4, 0.4, N)),
            "capacity_utilization":           np.random.uniform(0.40, 0.95, N),
            "customer_concentration":         np.random.uniform(0.15, 0.75, N),
            "regulatory_violation_count":     np.abs(np.random.poisson(0.8, N)).astype(float),
        }

        X = np.column_stack([data[f] for f in FEATURE_NAMES])

        # Label: default=1 if several bad signals present
        y = (
            (data["dscr"]                     < 1.1)  |
            (data["circular_trading_score"]   > 0.6)  |
            (data["debt_to_equity"]           > 3.5)  |
            (data["litigation_severity_score"]> 0.65) |
            (data["gst_bank_mismatch_score"]  > 0.40) |
            (data["promoter_network_risk"]    > 0.70) |
            (
                (data["interest_coverage_ratio"] < 1.2) &
                (data["pat_margin"]              < 0.02)
            )
        ).astype(int)

        logger.info(f"[CreditModel] Synthetic data: {N} samples, {y.sum()} defaults ({y.mean()*100:.1f}%)")
        return X, y

    def _grade(self, score: float) -> str:
        if score >= 85: return "AAA"
        if score >= 80: return "AA"
        if score >= 75: return "A"
        if score >= 70: return "BBB"
        if score >= 65: return "BB"
        if score >= 60: return "B"
        if score >= 50: return "C"
        return "D"
