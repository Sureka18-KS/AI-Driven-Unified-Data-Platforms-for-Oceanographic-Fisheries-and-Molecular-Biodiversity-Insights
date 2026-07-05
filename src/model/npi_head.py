# Hybrid NPI Head — Learnable RM-NPI weights as nn.Parameter
import torch
import torch.nn as nn
import numpy as np


class HybridNPIHead(nn.Module):
    """
    Predicts RM-NPI and its components from the z_npi latent vector.

    Uses the hybrid log-space formula with LEARNABLE weights:
        log(RM-NPI) = w1*log(Q) + w2*log(N) + w3*log(S) + w4*log(D)

    The weights are stored as nn.Parameter and optimized during training.
    """

    def __init__(self, latent_npi: int = 16, initial_weights: list = None):
        super().__init__()
        self.latent_npi = latent_npi

        # 4 component predictors: Q, N, S, D
        self.Q_head = nn.Sequential(nn.Linear(latent_npi, 32), nn.ReLU(), nn.Linear(32, 1), nn.Sigmoid())
        self.N_head = nn.Sequential(nn.Linear(latent_npi, 32), nn.ReLU(), nn.Linear(32, 1), nn.Sigmoid())
        self.S_head = nn.Sequential(nn.Linear(latent_npi, 32), nn.ReLU(), nn.Linear(32, 1), nn.Sigmoid())
        self.D_head = nn.Sequential(nn.Linear(latent_npi, 32), nn.ReLU(), nn.Linear(32, 1), nn.Sigmoid())

        # Learnable log-space weights (softmax-normalized to sum to 1)
        if initial_weights is None:
            initial_weights = [0.25, 0.25, 0.25, 0.25]
        raw = torch.tensor(initial_weights, dtype=torch.float32)
        self.log_weights = nn.Parameter(torch.log(raw))

    def forward(self, z_npi: torch.Tensor) -> dict:
        """
        Predict RM-NPI and all components from z_npi.

        Returns dict with keys: Q, N, S, D, npi_pred, weights
        """
        Q = self.Q_head(z_npi).squeeze(-1)
        N = self.N_head(z_npi).squeeze(-1)
        S = self.S_head(z_npi).squeeze(-1)
        D = self.D_head(z_npi).squeeze(-1)

        # Normalized weights via softmax
        weights = torch.softmax(self.log_weights, dim=0)
        w1, w2, w3, w4 = weights[0], weights[1], weights[2], weights[3]

        # Hybrid log-space RM-NPI
        eps = 1e-6
        log_npi = (w1 * torch.log(Q.clamp(min=eps))
                   + w2 * torch.log(N.clamp(min=eps))
                   + w3 * torch.log(S.clamp(min=eps))
                   + w4 * torch.log(D.clamp(min=eps)))
        npi_pred = torch.exp(log_npi).clamp(0, 1)

        return {"Q": Q, "N": N, "S": S, "D": D, "npi_pred": npi_pred, "weights": weights}

    def get_learned_weights(self) -> dict:
        """Return current learned weights as a plain dict."""
        with torch.no_grad():
            w = torch.softmax(self.log_weights, dim=0).cpu().numpy()
        return {"w_Q": float(w[0]), "w_N": float(w[1]),
                "w_S": float(w[2]), "w_D": float(w[3])}
