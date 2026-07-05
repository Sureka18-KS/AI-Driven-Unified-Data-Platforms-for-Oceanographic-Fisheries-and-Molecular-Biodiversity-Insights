# Disentangled Dual-Channel Autoencoder
# Channels: z_npi (RM-NPI correlated) + z_disc (discovery / NPI-orthogonal)
# Embedded optimizations: OPT-1 (cache), OPT-2 (selective gate),
#                         OPT-4 (quantization), OPT-6 (feature pruning)

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, Tuple


class LatentCache:
    """OPT-1: Skip re-encoding unchanged grid cells."""

    def __init__(self, capacity: int = 10000, epsilon: float = 0.01):
        self.capacity = capacity
        self.epsilon = epsilon
        self._cache: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}

    def get(self, cell_id: int, x: np.ndarray):
        if cell_id in self._cache:
            cached_x, cached_z = self._cache[cell_id]
            if np.mean(np.abs(x - cached_x)) < self.epsilon:
                return cached_z
        return None

    def put(self, cell_id: int, x: np.ndarray, z: np.ndarray):
        if len(self._cache) >= self.capacity:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[cell_id] = (x.copy(), z.copy())


class SubEncoder(nn.Module):
    """One sub-encoder for a single feature group."""

    def __init__(self, in_dim: int, out_dim: int):
        super().__init__()
        hidden = max(in_dim * 2, 32)
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.LayerNorm(hidden),
            nn.GELU(),
            nn.Linear(hidden, out_dim),
            nn.GELU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class ScalableOceanAutoencoder(nn.Module):
    """
    Disentangled Dual-Channel Autoencoder with embedded optimizations.

    Architecture:
      Input -> AttentionGate -> SubEncoders -> Fusion -> [z_npi | z_disc]
            -> Quantization -> Decoder -> x_hat
            -> HybridNPIHead -> RM-NPI prediction
            -> ReconError -> needs_analysis flag
    """

    RECON_ERROR_PERCENTILE = 80  # OPT-2: flag top 20% error cells

    def __init__(
        self,
        feature_groups: Dict[str, int],
        latent_npi: int = 16,
        latent_disc: int = 16,
    ):
        super().__init__()
        self.feature_groups = feature_groups
        self.latent_npi = latent_npi
        self.latent_disc = latent_disc
        total_in = sum(feature_groups.values())

        # OPT-6: Attention gate — learns to prune low-value features
        self.attention_gate = nn.Sequential(
            nn.Linear(total_in, total_in),
            nn.Sigmoid(),
        )

        # Sub-encoders per feature group
        sub_out = 32
        self.sub_encoders = nn.ModuleDict({
            name: SubEncoder(dim, sub_out)
            for name, dim in feature_groups.items()
        })

        fused_dim = sub_out * len(feature_groups)

        # Fusion -> latent split
        self.fusion = nn.Sequential(
            nn.Linear(fused_dim, 128),
            nn.GELU(),
        )
        self.npi_proj = nn.Linear(128, latent_npi)
        self.disc_proj = nn.Linear(128, latent_disc)

        # OPT-4: Quantization bottleneck (straight-through estimator)
        self.quant_scale = nn.Parameter(torch.ones(latent_npi + latent_disc))

        # Decoder: full latent -> reconstruct all features
        latent_dim = latent_npi + latent_disc
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 128),
            nn.GELU(),
            nn.Linear(128, total_in),
        )

    def quantize(self, z: torch.Tensor) -> torch.Tensor:
        """OPT-4: Quantize to 8-bit with straight-through gradient."""
        z_scaled = z * self.quant_scale[:z.shape[-1]]
        z_int = z_scaled.detach().round()
        return z + (z_int - z).detach()

    def forward(self, x: torch.Tensor, group_splits: Dict[str, Tuple[int, int]]) -> dict:
        """
        Forward pass through the full autoencoder.

        Args:
            x: Input tensor (batch, total_features)
            group_splits: {group_name: (start_idx, end_idx)}

        Returns dict with z_npi, z_disc, x_hat, recon_error, gates, needs_analysis
        """
        # OPT-6: Feature attention gate
        gates = self.attention_gate(x)
        x_gated = x * gates

        # Sub-encoders per group
        sub_outputs = []
        for name, encoder in self.sub_encoders.items():
            s, e = group_splits[name]
            sub_outputs.append(encoder(x_gated[:, s:e]))

        # Fuse all sub-encoder outputs
        fused = torch.cat(sub_outputs, dim=-1)
        h = self.fusion(fused)

        # Split into dual channels
        z_npi = self.npi_proj(h)
        z_disc = self.disc_proj(h)

        # OPT-4: Quantization
        z_full = torch.cat([z_npi, z_disc], dim=-1)
        z_q = self.quantize(z_full)

        # Decode
        x_hat = self.decoder(z_q)

        # OPT-2: Reconstruction error -> selective reprocessing flag
        recon_error = torch.mean((x - x_hat) ** 2, dim=-1)
        with torch.no_grad():
            threshold = torch.quantile(recon_error, self.RECON_ERROR_PERCENTILE / 100.0)
        needs_analysis = (recon_error > threshold)

        return {
            "z_npi": z_npi,
            "z_disc": z_disc,
            "z_q": z_q,
            "x_hat": x_hat,
            "recon_error": recon_error,
            "gates": gates,
            "needs_analysis": needs_analysis,
        }
