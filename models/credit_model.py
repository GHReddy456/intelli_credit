"""
Credit Model — XGBoost classifier for corporate credit risk.
Train on synthetic Indian corporate dataset (2000 samples).
Saves model + evaluation metrics to disk and loads on subsequent runs.
"""
import os
import json
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, Any
from loguru import logger
from backend.config import FEATURE_NAMES, MODEL_DIR
from models.feature_pipeline import build_pipeline, features_to_array, features_to_matrix


MODEL_PATH    = MODEL_DIR / "credit_model.pkl"
PIPELINE_PATH = MODEL_DIR / "feature_pipeline.pkl"
METRICS_PATH  = MODEL_DIR / "model_metrics.json"


class CreditModel:
    def __init__(self):
        self.model    = None
        self.pipeline = None
        self.metrics  = {}
        self._load_or_train()

    # ── Public API ─────────────────────────────────────────────────────────
    def predict(self, features: Dict[str, float]) -> Dict[str, Any]:
        X_raw  = features_to_array(features)
        X_proc = self.pipeline.transform(X_raw)

        prob_default = float(self.model.predict_proba(X_proc)[0][1])
        credit_score = round((1 - prob_default) * 100, 1)

        # ── Confidence band via 10-bootstrap re-samples ────────────────────
        rng = np.random.default_rng(42)
        scores = []
        for _ in range(10):
            noise = rng.normal(0, 0.005, X_proc.shape)
            p = float(self.model.predict_proba(X_proc + noise)[0][1])
            scores.append((1 - p) * 100)
        score_std = float(np.std(scores))
        ci_low  = round(max(credit_score - 1.96 * score_std, 0), 1)
        ci_high = round(min(credit_score + 1.96 * score_std, 100), 1)

        logger.info(f"[CreditModel] score={credit_score} ±{score_std:.1f}, PD={prob_default:.4f}")
        return {
            "credit_score":           credit_score,
            "probability_of_default": round(prob_default, 4),
            "risk_grade":             self._grade(credit_score),
            "score_ci_low":           ci_low,
            "score_ci_high":          ci_high,
            "score_std":              round(score_std, 2),
        }

    def get_metrics(self) -> Dict:
        """Return saved training evaluation metrics."""
        return self.metrics

    # ── Model training ─────────────────────────────────────────────────────
    def _load_or_train(self):
        if MODEL_PATH.exists() and PIPELINE_PATH.exists():
            logger.info("[CreditModel] Loading saved model")
            with open(MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)
            with open(PIPELINE_PATH, "rb") as f:
                self.pipeline = pickle.load(f)
            if METRICS_PATH.exists():
                with open(METRICS_PATH) as f:
                    self.metrics = json.load(f)
        else:
            logger.info("[CreditModel] Training new model on synthetic dataset")
            self._train()

    def _train(self):
        from xgboost import XGBClassifier
        from sklearn.model_selection import train_test_split, cross_val_score
        from sklearn.metrics import (
            roc_auc_score, f1_score, precision_score,
            recall_score, accuracy_score,
        )

        X, y = self._generate_synthetic_dataset(n=2000)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, stratify=y, random_state=42
        )

        self.pipeline = build_pipeline()
        X_train_p = self.pipeline.fit_transform(X_train)
        X_test_p  = self.pipeline.transform(X_test)

        self.model = XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.06,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            use_label_encoder=False,
            eval_metric="logloss",
            random_state=42,
        )
        self.model.fit(
            X_train_p, y_train,
            eval_set=[(X_test_p, y_test)],
            verbose=False,
        )

        # ── Evaluate on hold-out test set ─────────────────────────────────
        y_pred_proba = self.model.predict_proba(X_test_p)[:, 1]
        y_pred       = (y_pred_proba >= 0.5).astype(int)

        self.metrics = {
            "roc_auc":   round(float(roc_auc_score(y_test, y_pred_proba)), 4),
            "f1_score":  round(float(f1_score(y_test, y_pred)), 4),
            "precision": round(float(precision_score(y_test, y_pred)), 4),
            "recall":    round(float(recall_score(y_test, y_pred)), 4),
            "accuracy":  round(float(accuracy_score(y_test, y_pred)), 4),
            "train_size": int((X.shape[0] * 0.8)),
            "test_size":  int((X.shape[0] * 0.2)),
            "default_rate_pct": round(float(y.mean() * 100), 1),
            "model":     "XGBoost (n_est=300, depth=5)",
        }

        with open(MODEL_PATH, "wb") as f:
            pickle.dump(self.model, f)
        with open(PIPELINE_PATH, "wb") as f:
            pickle.dump(self.pipeline, f)
        with open(METRICS_PATH, "w") as f:
            json.dump(self.metrics, f, indent=2)

        logger.info(
            f"[CreditModel] Trained — AUC={self.metrics['roc_auc']}, "
            f"F1={self.metrics['f1_score']}, Accuracy={self.metrics['accuracy']}"
        )

    def _generate_synthetic_dataset(self, n: int = 2000):
        """
        Synthetic Indian corporate credit dataset — 2000 samples, ~25% default rate.
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

    # Standard Indian bank internal credit rating bands with typical PD midpoints
    _GRADE_TABLE = [
        (90, "AAA", 0.005),   # 90–100: AAA, PD ≈ 0.5%
        (80, "AA",  0.015),   # 80–90:  AA,  PD ≈ 1.5%
        (75, "A",   0.030),   # 75–80:  A,   PD ≈ 3%
        (70, "BBB", 0.060),   # 70–75:  BBB, PD ≈ 6%
        (65, "BB",  0.110),   # 65–70:  BB,  PD ≈ 11%
        (60, "B",   0.180),   # 60–65:  B,   PD ≈ 18%
        (50, "C",   0.300),   # 50–60:  C,   PD ≈ 30%
        (0,  "D",   0.500),   # < 50:   D,   PD ≈ 50%
    ]

    def _grade(self, score: float) -> str:
        for threshold, grade, _ in self._GRADE_TABLE:
            if score >= threshold:
                return grade
        return "D"

    def _grade_pd(self, grade: str) -> float:
        """Return standard PD midpoint for a given risk grade."""
        for _, g, pd in self._GRADE_TABLE:
            if g == grade:
                return pd
        return 0.50
