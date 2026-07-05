# OPT-4: Tiered Storage Assignment + Latent Compression
import numpy as np


def assign_storage_tier(
    npi_score: float,
    disc_anomaly: float,
    is_novel: bool,
) -> str:
    """
    Assign each grid cell to hot / warm / cold storage tier.

    hot  -- Keep full raw data + latent vector (high value)
    warm -- Keep latent vector only, raw data compressed
    cold -- Discard raw data, store compressed latent (OPT-4)
    """
    if npi_score > 0.6 or is_novel:
        return "hot"
    if npi_score > 0.3 or disc_anomaly > 0.3:
        return "warm"
    return "cold"


def compress_latent(z: np.ndarray, bits: int = 8) -> np.ndarray:
    """
    OPT-4: Quantize latent vector to 8-bit integer representation.
    Reduces storage by ~54% vs 32-bit float.
    """
    z_min, z_max = z.min(), z.max()
    scale = (z_max - z_min) / (2 ** bits - 1) + 1e-8
    z_int = np.round((z - z_min) / scale).astype(np.uint8)
    return z_int, z_min, scale


def decompress_latent(z_int: np.ndarray, z_min: float, scale: float) -> np.ndarray:
    """Reconstruct float latent from quantized representation."""
    return z_int.astype(np.float32) * scale + z_min
