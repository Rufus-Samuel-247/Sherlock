"""
SHERLOCK Backend - Graph Neural Network (GraphSAGE)
2-layer GraphSAGE with Mean Aggregation implemented in PyTorch.
Outputs 32-dimensional node embeddings and node-level fraud probability scores.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Any

class SAGEConv(nn.Module):
    """
    GraphSAGE convolution layer with Mean Aggregation:
    h_v = ReLU(W * [h_v || Mean_{u in N(v)}(h_u)] + b)
    """
    def __init__(self, in_feats: int, out_feats: int, activation=F.relu):
        super(SAGEConv, self).__init__()
        self.in_feats = in_feats
        self.out_feats = out_feats
        self.linear = nn.Linear(in_feats * 2, out_feats)
        self.activation = activation
        
    def forward(self, x: torch.Tensor, adj_norm: torch.Tensor) -> torch.Tensor:
        """
        x: (N, in_feats) node features
        adj_norm: (N, N) row-normalized adjacency matrix (for mean aggregation)
        """
        # Neighbor aggregation via normalized adjacency multiplication
        neigh_mean = torch.matmul(adj_norm, x)  # (N, in_feats)
        combined = torch.cat([x, neigh_mean], dim=1)  # (N, 2 * in_feats)
        out = self.linear(combined)
        if self.activation:
            out = self.activation(out)
        return out


class GraphSAGE(nn.Module):
    """
    2-Layer GraphSAGE model:
    Input: Node Features (N, in_feats)
    Layer 1: (N, in_feats) -> (N, hidden_feats)
    Layer 2: (N, hidden_feats) -> (N, 32) (Embeddings)
    Classifier Head: (N, 32) -> (N, 1) (Fraud probability)
    """
    def __init__(self, in_feats: int = 16, hidden_feats: int = 64, out_embed_dim: int = 32):
        super(GraphSAGE, self).__init__()
        self.conv1 = SAGEConv(in_feats, hidden_feats, activation=F.relu)
        self.dropout = nn.Dropout(0.2)
        self.conv2 = SAGEConv(hidden_feats, out_embed_dim, activation=F.relu)
        self.classifier = nn.Sequential(
            nn.Linear(out_embed_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x: torch.Tensor, adj_norm: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        h = self.conv1(x, adj_norm)
        h = self.dropout(h)
        embeddings = self.conv2(x=h, adj_norm=adj_norm)  # (N, 32)
        fraud_probs = self.classifier(embeddings).squeeze(-1)  # (N,)
        return embeddings, fraud_probs


class GNNTrainer:
    """Wrapper to train GraphSAGE and produce node embeddings."""
    def __init__(self, in_feats: int = 16, embed_dim: int = 32, lr: float = 0.01):
        self.model = GraphSAGE(in_feats=in_feats, hidden_feats=64, out_embed_dim=embed_dim)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr, weight_decay=1e-4)
        self.embed_dim = embed_dim
        self.account_id_to_idx: Dict[str, int] = {}
        self.idx_to_account_id: Dict[int, str] = {}
        self.embeddings: Dict[str, np.ndarray] = {}
        
    def prepare_graph_data(
        self,
        account_features: Dict[str, Dict[str, float]],
        G,
        labels: Dict[str, int]
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, List[str]]:
        """Convert account graph and features into PyTorch tensors."""
        account_ids = sorted(list(account_features.keys()))
        self.account_id_to_idx = {acc: i for i, acc in enumerate(account_ids)}
        self.idx_to_account_id = {i: acc for i, acc in enumerate(account_ids)}
        N = len(account_ids)
        
        # Build feature matrix
        feat_keys = sorted(list(next(iter(account_features.values())).keys()))
        X_mat = np.zeros((N, len(feat_keys)), dtype=np.float32)
        for i, acc in enumerate(account_ids):
            for j, k in enumerate(feat_keys):
                X_mat[i, j] = account_features[acc].get(k, 0.0)
                
        # Normalize features
        mean = np.mean(X_mat, axis=0, keepdims=True)
        std = np.std(X_mat, axis=0, keepdims=True) + 1e-6
        X_mat = (X_mat - mean) / std
        
        # Build adjacency matrix (Account <-> Account co-occurrence / transfer)
        A = np.eye(N, dtype=np.float32)  # self-loops
        for u in account_ids:
            u_idx = self.account_id_to_idx[u]
            if G.has_node(u):
                for nbr in G.neighbors(u):
                    if nbr in self.account_id_to_idx:
                        v_idx = self.account_id_to_idx[nbr]
                        A[u_idx, v_idx] += 1.0
                        A[v_idx, u_idx] += 1.0
                    else:
                        # 2-hop connection through shared entity (device/ip)
                        for two_hop in G.neighbors(nbr):
                            if two_hop in self.account_id_to_idx and two_hop != u:
                                v_idx = self.account_id_to_idx[two_hop]
                                A[u_idx, v_idx] += 0.5
                                A[v_idx, u_idx] += 0.5

        # Row-normalize adjacency for mean aggregation
        deg = np.sum(A, axis=1, keepdims=True)
        deg[deg == 0] = 1.0
        A_norm = A / deg
        
        y_vec = np.zeros(N, dtype=np.float32)
        for acc, lbl in labels.items():
            if acc in self.account_id_to_idx:
                y_vec[self.account_id_to_idx[acc]] = float(lbl)
                
        return (
            torch.tensor(X_mat, dtype=torch.float32),
            torch.tensor(A_norm, dtype=torch.float32),
            torch.tensor(y_vec, dtype=torch.float32),
            account_ids
        )

    def train(
        self,
        account_features: Dict[str, Dict[str, float]],
        G,
        labels: Dict[str, int],
        epochs: int = 50
    ):
        """Train GraphSAGE model and compute 32-dim node embeddings."""
        X, A_norm, y, account_ids = self.prepare_graph_data(account_features, G, labels)
        
        # Re-initialize input dim if needed
        in_feats = X.shape[1]
        self.model = GraphSAGE(in_feats=in_feats, hidden_feats=64, out_embed_dim=self.embed_dim)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.01, weight_decay=1e-4)
        
        # Pos weight for class imbalance
        pos_count = (y == 1.0).sum().item()
        neg_count = (y == 0.0).sum().item()
        pos_weight = torch.tensor([neg_count / max(1.0, pos_count)])
        criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
        
        self.model.train()
        for epoch in range(epochs):
            self.optimizer.zero_grad()
            h = self.model.conv1(X, A_norm)
            h = self.model.dropout(h)
            embeds = self.model.conv2(h, A_norm)
            logits = self.model.classifier[2](F.relu(self.model.classifier[0](embeds))).squeeze(-1)
            loss = criterion(logits, y)
            loss.backward()
            self.optimizer.step()
            
        # Extract embeddings and store
        self.model.eval()
        with torch.no_grad():
            final_embeds, final_probs = self.model(X, A_norm)
            embeds_np = final_embeds.cpu().numpy()
            probs_np = final_probs.cpu().numpy()
            
        self.embeddings = {}
        self.node_gnn_scores = {}
        for i, acc_id in enumerate(account_ids):
            self.embeddings[acc_id] = embeds_np[i]
            self.node_gnn_scores[acc_id] = float(probs_np[i])
            
        return self.embeddings, self.node_gnn_scores

    def get_embedding(self, account_id: str) -> np.ndarray:
        return self.embeddings.get(account_id, np.zeros(self.embed_dim, dtype=np.float32))

    def get_score(self, account_id: str) -> float:
        return self.node_gnn_scores.get(account_id, 0.05)
