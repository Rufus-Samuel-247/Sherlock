"""
SHERLOCK Backend - Autoencoder Anomaly Detector
Neural network autoencoder trained exclusively on benign/normal transactions.
Higher reconstruction error indicates anomalous/unseen behavior.
"""

import torch
import torch.nn as nn
import numpy as np
from typing import List, Dict, Any, Tuple

class TransactionAutoencoder(nn.Module):
    """
    Symmetric autoencoder for tabular transaction feature reconstruction.
    Encoder: in_dim -> 32 -> 16 -> 8 (bottleneck)
    Decoder: 8 -> 16 -> 32 -> in_dim
    """
    def __init__(self, in_dim: int = 10, bottleneck_dim: int = 8):
        super(TransactionAutoencoder, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(in_dim, 32),
            nn.BatchNorm1d(32),
            nn.LeakyReLU(0.2),
            nn.Linear(32, 16),
            nn.BatchNorm1d(16),
            nn.LeakyReLU(0.2),
            nn.Linear(16, bottleneck_dim),
        )
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck_dim, 16),
            nn.BatchNorm1d(16),
            nn.LeakyReLU(0.2),
            nn.Linear(16, 32),
            nn.BatchNorm1d(32),
            nn.LeakyReLU(0.2),
            nn.Linear(32, in_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded


class AutoencoderTrainer:
    def __init__(self, in_dim: int = 10):
        self.in_dim = in_dim
        self.model = TransactionAutoencoder(in_dim=in_dim)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.005, weight_decay=1e-5)
        self.criterion = nn.MSELoss(reduction='none')
        self.mean: np.ndarray = np.zeros(in_dim)
        self.std: np.ndarray = np.ones(in_dim)
        self.max_error: float = 1.0

    def fit(self, X_normal: np.ndarray, epochs: int = 25, batch_size: int = 128):
        """
        Fit autoencoder on normal transaction features only.
        """
        if len(X_normal) == 0:
            return
            
        self.in_dim = X_normal.shape[1]
        self.model = TransactionAutoencoder(in_dim=self.in_dim)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.005, weight_decay=1e-5)
        
        self.mean = np.mean(X_normal, axis=0, keepdims=True)
        self.std = np.std(X_normal, axis=0, keepdims=True) + 1e-6
        X_norm = (X_normal - self.mean) / self.std

        tensor_x = torch.tensor(X_norm, dtype=torch.float32)
        dataset = torch.utils.data.TensorDataset(tensor_x)
        loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

        self.model.train()
        for epoch in range(epochs):
            for batch in loader:
                x_b = batch[0]
                self.optimizer.zero_grad()
                recon = self.model(x_b)
                loss = nn.MSELoss()(recon, x_b)
                loss.backward()
                self.optimizer.step()

        # Compute max error on training data for calibration
        self.model.eval()
        with torch.no_grad():
            train_recon = self.model(tensor_x)
            train_errors = torch.mean((train_recon - tensor_x) ** 2, dim=1).cpu().numpy()
            self.max_error = float(np.percentile(train_errors, 99) * 2.5 + 1e-5)

    def score(self, X: np.ndarray) -> np.ndarray:
        """
        Compute anomaly score normalized to [0, 1].
        """
        if len(X) == 0:
            return np.array([])
            
        self.model.eval()
        X_norm = (X - self.mean) / self.std
        tensor_x = torch.tensor(X_norm, dtype=torch.float32)
        
        with torch.no_grad():
            recon = self.model(tensor_x)
            errors = torch.mean((recon - tensor_x) ** 2, dim=1).cpu().numpy()
            
        # Sigmoidal squash of normalized reconstruction error
        normalized_scores = 1.0 / (1.0 + np.exp(-3.0 * (errors / (self.max_error + 1e-6) - 0.8)))
        return np.clip(normalized_scores, 0.0, 1.0)
