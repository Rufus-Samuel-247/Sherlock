"""
SHERLOCK Backend - XGBoost Fraud Classifier
Combines traditional features, topological graph features, and 32-dim GNN embeddings.
Configured with scale_pos_weight and optimized for PR-AUC.
"""

import xgboost as xgb
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from sklearn.metrics import precision_recall_curve, auc

class XGBoostFraudModel:
    def __init__(self):
        self.model: Optional[xgb.XGBClassifier] = None
        self.feature_names: List[str] = []

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        scale_pos_weight: Optional[float] = None
    ):
        """
        Train XGBoost with scale_pos_weight and PR-AUC metric.
        """
        if feature_names:
            self.feature_names = feature_names
        else:
            self.feature_names = [f"f_{i}" for i in range(X.shape[1])]

        pos_count = np.sum(y == 1)
        neg_count = np.sum(y == 0)
        
        if scale_pos_weight is None:
            scale_pos_weight = float(neg_count) / float(max(1, pos_count))

        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.85,
            colsample_bytree=0.85,
            scale_pos_weight=scale_pos_weight,
            eval_metric="aucpr",
            random_state=42,
            n_jobs=2
        )

        self.model.fit(X, y)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Returns probability of fraud P(y=1) for each sample.
        """
        if self.model is None:
            return np.zeros(len(X))
        probs = self.model.predict_proba(X)
        return probs[:, 1]

    def get_feature_importances(self) -> Dict[str, float]:
        """Return mapping of feature names to importance scores."""
        if self.model is None:
            return {}
        importances = self.model.feature_importances_
        return {
            name: float(imp)
            for name, imp in zip(self.feature_names, importances)
        }
