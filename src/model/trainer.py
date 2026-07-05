# Autoencoder Trainer — 5-term hybrid loss function
import torch
import torch.nn as nn
import numpy as np


def compute_training_loss(
    output: dict,
    npi_output: dict,
    x_orig: torch.Tensor,
    npi_target: torch.Tensor,
    Q_target: torch.Tensor,
    N_target: torch.Tensor,
    S_target: torch.Tensor,
    D_target: torch.Tensor,
    lambda_npi: float = 1.0,
    lambda_comp: float = 0.5,
    lambda_ortho: float = 0.1,
    lambda_weight: float = 0.01,
) -> dict:
    """
    5-term hybrid loss for the dual-channel autoencoder.

    L_total = L_recon + L_npi + L_comp + L_ortho + L_weight

    Terms:
        L_recon  -- reconstruction quality (MSE)
        L_npi    -- RM-NPI prediction accuracy (log-space MSE)
        L_comp   -- component prediction (Q, N, S, D individually)
        L_ortho  -- force z_npi and z_disc to be uncorrelated
        L_weight -- regularize learnable NPI weights toward uniform
    """
    eps = 1e-6

    # L_recon: reconstruction quality
    L_recon = nn.functional.mse_loss(output["x_hat"], x_orig)

    # L_npi: RM-NPI prediction in log-space
    npi_pred = npi_output["npi_pred"].clamp(min=eps)
    npi_target_c = npi_target.clamp(min=eps)
    L_npi = nn.functional.mse_loss(torch.log(npi_pred), torch.log(npi_target_c))

    # L_comp: per-component prediction in log-space
    def comp_loss(pred, target):
        pred = pred.clamp(min=eps)
        target = target.clamp(min=eps)
        return nn.functional.mse_loss(torch.log(pred), torch.log(target))

    L_comp = (comp_loss(npi_output["Q"], Q_target)
              + comp_loss(npi_output["N"], N_target)
              + comp_loss(npi_output["S"], S_target)
              + comp_loss(npi_output["D"], D_target)) / 4.0

    # L_ortho: decorrelate z_npi from z_disc
    z_npi = output["z_npi"] - output["z_npi"].mean(dim=0)
    z_disc = output["z_disc"] - output["z_disc"].mean(dim=0)
    B = z_npi.shape[0]
    cov = torch.mm(z_npi.T, z_disc) / (B - 1 + eps)
    L_ortho = (cov ** 2).mean()

    # L_weight: regularize toward uniform weights
    weights = npi_output["weights"]
    L_weight = ((weights - 0.25) ** 2).sum()

    L_total = (L_recon
               + lambda_npi * L_npi
               + lambda_comp * L_comp
               + lambda_ortho * L_ortho
               + lambda_weight * L_weight)

    return {
        "total": L_total,
        "recon": L_recon.item(),
        "npi": L_npi.item(),
        "comp": L_comp.item(),
        "ortho": L_ortho.item(),
        "weight": L_weight.item(),
    }
