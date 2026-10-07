"""
SHERLOCK Backend - ML Training & Inference Pipeline Orchestrator
Coordinates GraphSAGE, Autoencoder, XGBoost, and the FraudEnsemble.
Provides score_transaction() and score_account() methods.
"""

import numpy as np
import datetime
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict

from .gnn_model import GNNTrainer
from .autoencoder import AutoencoderTrainer
from .xgb_model import XGBoostFraudModel
from .ensemble import FraudEnsemble

class MLPipeline:
    def __init__(self):
        self.gnn_trainer = GNNTrainer(in_feats=7, embed_dim=32)
        self.autoencoder_trainer = AutoencoderTrainer(in_dim=7)
        self.xgb_model = XGBoostFraudModel()
        self.ensemble = FraudEnsemble()
        
        self.accounts_meta: Dict[str, Dict[str, Any]] = {}
        self.graph_features: Dict[str, Dict[str, float]] = {}
        self.is_trained: bool = False

    def _extract_traditional_features(
        self,
        txn: Dict[str, Any],
        acc_meta: Dict[str, Any]
    ) -> List[float]:
        """Extract traditional tabular features from transaction and account meta."""
        amount = float(txn.get("amount", 0.0))
        log_amt = float(np.log1p(max(0.0, amount)))
        
        try:
            ts = datetime.datetime.fromisoformat(txn["timestamp"])
            hour = float(ts.hour)
            dow = float(ts.weekday())
        except Exception:
            hour = 12.0
            dow = 2.0
            
        history_days = float(acc_meta.get("history_days", 30))
        log_history = float(np.log1p(history_days))
        
        # Device match flag
        dev = txn.get("device_id")
        primary_dev = acc_meta.get("primary_device")
        is_same_device = 1.0 if (dev and primary_dev and dev == primary_dev) else 0.0
        
        # IP match flag
        ip = txn.get("ip_address")
        primary_ip = acc_meta.get("primary_ip")
        is_same_ip = 1.0 if (ip and primary_ip and ip == primary_ip) else 0.0
        
        return [amount, log_amt, hour, dow, log_history, is_same_device, is_same_ip]

    def train_pipeline(
        self,
        accounts: Dict[str, Dict[str, Any]],
        transactions: List[Dict[str, Any]],
        G,
        graph_features: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Train all components:
        1. GraphSAGE embeddings & node scores
        2. Autoencoder on normal transactions
        3. XGBoost on full tabular + graph + embeddings
        4. Ensemble threshold calibration
        """
        self.accounts_meta = accounts
        self.graph_features = graph_features
        
        # 1. Train GraphSAGE
        account_labels = {
            acc_id: 1 if meta.get("is_fraud") else 0
            for acc_id, meta in accounts.items()
        }
        gnn_embeddings, gnn_node_scores = self.gnn_trainer.train(
            account_features=graph_features,
            G=G,
            labels=account_labels,
            epochs=40
        )

        # 2. Extract transaction tabular features
        X_traditional = []
        y_labels = []
        normal_traditional = []
        
        for txn in transactions:
            acc_id = txn["account_id"]
            acc_meta = accounts.get(acc_id, {})
            feats = self._extract_traditional_features(txn, acc_meta)
            X_traditional.append(feats)
            lbl = 1 if txn.get("is_fraud") else 0
            y_labels.append(lbl)
            if lbl == 0:
                normal_traditional.append(feats)

        X_traditional = np.array(X_traditional, dtype=np.float32)
        y_labels = np.array(y_labels, dtype=np.int32)
        normal_traditional = np.array(normal_traditional, dtype=np.float32)

        # 3. Train Autoencoder exclusively on normal transactions
        self.autoencoder_trainer.fit(normal_traditional, epochs=20)
        ae_scores = self.autoencoder_trainer.score(X_traditional)

        # 4. Construct full feature matrix for XGBoost
        # Features = [traditional (7)] + [graph_features (7)] + [gnn_embedding (32)]
        graph_keys = ["pagerank", "clustering_coeff", "shared_device_count", "community_id", "temporal_burst_score", "in_degree", "out_degree"]
        
        X_full = []
        for i, txn in enumerate(transactions):
            acc_id = txn["account_id"]
            g_feats = [graph_features.get(acc_id, {}).get(k, 0.0) for k in graph_keys]
            embed = self.gnn_trainer.get_embedding(acc_id)
            row = np.concatenate([X_traditional[i], g_feats, embed])
            X_full.append(row)
            
        X_full = np.array(X_full, dtype=np.float32)

        feature_names = (
            ["amt", "log_amt", "hour", "dow", "history", "same_dev", "same_ip"] +
            [f"graph_{k}" for k in graph_keys] +
            [f"gnn_dim_{j}" for j in range(32)]
        )

        # Train XGBoost
        self.xgb_model.fit(X_full, y_labels, feature_names=feature_names)
        xgb_probs = self.xgb_model.predict_proba(X_full)

        # GNN scores per transaction based on account
        gnn_probs = np.array([
            self.gnn_trainer.get_score(txn["account_id"])
            for txn in transactions
        ], dtype=np.float32)

        # 5. Ensemble & Calibration
        raw_ensemble_scores = self.ensemble.combine_scores(
            xgb_score=xgb_probs,
            gnn_score=gnn_probs,
            ae_score=ae_scores
        )
        
        calibration_stats = self.ensemble.calibrate(
            y_true=y_labels,
            ensemble_scores=raw_ensemble_scores,
            target_precision=0.95
        )
        
        self.is_trained = True
        return {
            "status": "trained",
            "calibration": calibration_stats,
            "feature_importance": self.xgb_model.get_feature_importances()
        }

    def score_transaction(
        self,
        txn: Dict[str, Any],
        acc_meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Score an individual transaction through the full ensemble.
        """
        acc_id = txn["account_id"]
        if acc_meta is None:
            acc_meta = self.accounts_meta.get(acc_id, {})
            
        trad_feats = np.array([self._extract_traditional_features(txn, acc_meta)], dtype=np.float32)
        ae_score = float(self.autoencoder_trainer.score(trad_feats)[0])
        
        graph_keys = ["pagerank", "clustering_coeff", "shared_device_count", "community_id", "temporal_burst_score", "in_degree", "out_degree"]
        g_feats = [self.graph_features.get(acc_id, {}).get(k, 0.0) for k in graph_keys]
        embed = self.gnn_trainer.get_embedding(acc_id)
        
        x_full = np.concatenate([trad_feats[0], g_feats, embed]).reshape(1, -1)
        xgb_score = float(self.xgb_model.predict_proba(x_full)[0])
        gnn_score = float(self.gnn_trainer.get_score(acc_id))
        
        ensemble_score = float(self.ensemble.combine_scores(xgb_score, gnn_score, ae_score))
        is_fraud, risk_score = self.ensemble.predict(ensemble_score)
        
        return {
            "risk_score": risk_score,
            "is_fraud": is_fraud,
            "components": {
                "xgb_score": round(xgb_score, 4),
                "gnn_score": round(gnn_score, 4),
                "anomaly_score": round(ae_score, 4),
            }
        }

    def score_account(self, account_id: str) -> float:
        """Return aggregate risk score for an account."""
        gnn_score = self.gnn_trainer.get_score(account_id)
        return float(gnn_score)
