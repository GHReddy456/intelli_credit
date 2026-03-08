"""
Feature Pipeline — sklearn scaler + imputer.
Converts raw feature dict → normalized numpy array for XGBoost.
"""
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from typing import Dict, List
from backend.config import FEATURE_NAMES


def build_pipeline() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
    ])


def features_to_array(features: Dict[str, float]) -> np.ndarray:
    """Convert feature dict → 1×25 numpy array in canonical order."""
    row = [features.get(name, np.nan) for name in FEATURE_NAMES]
    return np.array(row, dtype=float).reshape(1, -1)


def features_to_matrix(feature_list: List[Dict]) -> np.ndarray:
    """Convert list of feature dicts → N×25 matrix."""
    return np.array(
        [[fd.get(name, np.nan) for name in FEATURE_NAMES] for fd in feature_list],
        dtype=float,
    )
