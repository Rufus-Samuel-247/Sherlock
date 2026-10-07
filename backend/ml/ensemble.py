"""
SHERLOCK Backend - Model Ensemble & Precision Calibration
Combines predictions: 0.55 * xgb + 0.25 * gnn + 0.20 * anomaly.
Calibrates the classification threshold for 95% target precision.
"""

import numpy as np
from typing import Dict, Any, Tuple
from sklearn.metrics import precision_recall_curve

class FraudEnsemble:
    def __init__(
        self,
        weight_xgb: float = 0.55,
        weight_gnn: float = 0.25,
        weight_ae: float = 0.20,
        default_threshold: float = 0.65
    ):
        self.w_xgb = weight_xgb
        self.w_gnn = weight_gnn
        self.w_ae = weight_ae
        self.threshold = default_threshold
        self.calibrated_precision = 0.95
        self.calibrated_fpr = 0.001

    def combine_scores(
        self,
        xgb_score: float | np.ndarray,
        gnn_score: float | np.ndarray,
        ae_score: float | np.ndarray
    ) -> float | np.ndarray:
        """
        Ensemble formula: 0.55*xgb + 0.25*gnn + 0.20*anomaly
        """
        score = (
            self.w_xgb * np.array(xgb_score) +
            self.w_gnn * np.array(gnn_score) +
            self.w_ae * np.array(ae_score)
        )
        return np.clip(score, 0.0, 1.0)

    def calibrate(
        self,
        y_true: np.ndarray,
        ensemble_scores: np.ndarray,
        target_precision: float = 0.95
    ) -> Dict[str, float]:
        """
        Find decision threshold achieving target precision (95%).
        """
        precisions, recalls, thresholds = precision_recall_curve(y_true, ensemble_scores)
        
        chosen_thresh = self.threshold
        best_precision = 0.95
        best_recall = 0.0

        # Scan thresholds where precision >= target_precision
        valid_indices = np.where(precisions >= target_precision)[0]
        if len(valid_indices) > 0:
            # Pick the lowest threshold (highest recall) that meets precision >= target_precision
            idx = valid_indices[0]
            if idx < len(thresholds):
                chosen_thresh = float(thresholds[idx])
                best_precision = float(precisions[idx])
                best_recall = float(recalls[idx])
        else:
            # Fallback to threshold giving highest precision
            best_idx = np.argmax(precisions)
            if best_idx < len(thresholds):
                chosen_thresh = float(thresholds[best_idx])
                best_precision = float(precisions[best_idx])
                best_recall = float(recalls[best_idx])

        self.threshold = max(0.40, min(float(chosen_thresh), 0.85))
        
        # Calculate false positive rate on negatives
        y_pred = (ensemble_scores >= self.threshold).astype(int)
        negatives = (y_true == 0)
        fp_count = np.sum((y_pred == 1) & negatives)
        total_neg = np.sum(negatives)
        self.calibrated_fpr = float(fp_count / max(1, total_neg))
        self.calibrated_precision = float(best_precision)

        return {
            "threshold": self.threshold,
            "precision": self.calibrated_precision,
            "recall": best_recall,
            "fpr": self.calibrated_fpr
        }

    def predict(self, ensemble_score: float) -> Tuple[bool, float]:
        """
        Returns (is_fraud, risk_score)
        """
        score = float(np.clip(ensemble_score, 0.0, 1.0))
        is_fraud = bool(score >= self.threshold)
        return is_fraud, round(score, 4)
