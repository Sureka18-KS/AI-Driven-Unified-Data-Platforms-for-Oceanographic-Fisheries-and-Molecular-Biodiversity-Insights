# OPT-5: Adaptive Spatial Tiling — variable resolution grid
import numpy as np


RESOLUTIONS = {
    "critical": 0.05,
    "high": 0.10,
    "moderate": 0.25,
    "low": 0.50,
    "minimal": 1.00,
}


def assign_tile_resolution(npi_score: float, is_coastal: bool) -> float:
    """OPT-5: Finer resolution near coasts and high-NPI zones."""
    if npi_score > 0.7 or is_coastal:
        return RESOLUTIONS["critical"]
    if npi_score > 0.5:
        return RESOLUTIONS["high"]
    if npi_score > 0.3:
        return RESOLUTIONS["moderate"]
    if npi_score > 0.1:
        return RESOLUTIONS["low"]
    return RESOLUTIONS["minimal"]
