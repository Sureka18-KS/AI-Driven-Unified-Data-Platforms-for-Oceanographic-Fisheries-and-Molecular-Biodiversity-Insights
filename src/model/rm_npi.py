# Hybrid RM-NPI Computation
# Formula: RM-NPI = exp(w1*log(Q) + w2*log(N) + w3*log(S) + w4*log(D))
# Equivalent to: Q^w1 * N^w2 * S^w3 * D^w4  (weighted product in log-space)

import numpy as np


def compute_hybrid_rm_npi(
    Q: np.ndarray,
    N: np.ndarray,
    S: np.ndarray,
    D: np.ndarray,
    w1: float = 0.25,
    w2: float = 0.25,
    w3: float = 0.25,
    w4: float = 0.25,
) -> np.ndarray:
    """
    Compute the Hybrid Log-Space RM-NPI score.

    Components:
        Q: River Discharge proxy (0-1)  -- from rainfall near river mouths
        N: Nutrient Load proxy  (0-1)  -- from chlorophyll-a
        S: Seasonal Factor      (0-1)  -- from monthly rainfall
        D: Distance Decay       (0-1)  -- from proximity to river mouths

    Formula in log-space:
        log(RM-NPI) = w1*log(Q) + w2*log(N) + w3*log(S) + w4*log(D)
        RM-NPI = exp(log(RM-NPI))

    Returns: np.ndarray of RM-NPI scores (0-1 range)
    """
    # Safety-clamp to prevent log(0)
    Q = np.clip(Q, 1e-6, 1.0).astype(np.float32)
    N = np.clip(N, 1e-6, 1.0).astype(np.float32)
    S = np.clip(S, 1e-6, 1.0).astype(np.float32)
    D = np.clip(D, 1e-6, 1.0).astype(np.float32)

    log_npi = w1 * np.log(Q) + w2 * np.log(N) + w3 * np.log(S) + w4 * np.log(D)
    npi = np.exp(log_npi)
    return np.clip(npi, 0.0, 1.0)


def compute_distance_decay(
    lats: np.ndarray,
    lons: np.ndarray,
    river_mouths: list,
    alpha: float = 0.05,
) -> np.ndarray:
    """
    Compute Distance Decay factor D for each grid cell.

    D = exp(-alpha * min_dist_km)
    Where min_dist_km is the distance to the nearest major river mouth.

    Args:
        lats, lons: Arrays of grid cell coordinates
        river_mouths: List of (lat, lon) tuples for major river mouths
        alpha: Decay rate per km (default 0.05 = ~20 km half-life)

    Returns: D array in (0, 1]
    """
    if len(lats) == 0:
        return np.array([], dtype=np.float32)

    min_dists = np.full(len(lats), np.inf, dtype=np.float32)

    for rlat, rlon in river_mouths:
        # Haversine-approximated distance in km
        dlat = np.radians(lats - rlat)
        dlon = np.radians(lons - rlon)
        a = (np.sin(dlat / 2) ** 2
             + np.cos(np.radians(rlat)) * np.cos(np.radians(lats))
             * np.sin(dlon / 2) ** 2)
        dist_km = 6371.0 * 2 * np.arcsin(np.sqrt(a))
        min_dists = np.minimum(min_dists, dist_km)

    D = np.exp(-alpha * min_dists)
    return np.clip(D, 1e-6, 1.0).astype(np.float32)


def extend_rm_npi(components: dict, weights: dict) -> np.ndarray:
    """
    Dynamically extend RM-NPI with user-supplied components.

    Used when new features (e.g. carbon content C) are added
    via the dynamic feature registry.

    Args:
        components: dict of {name: np.ndarray} normalized 0-1 values
        weights: dict of {name: float} learnable weights

    Returns: np.ndarray of extended RM-NPI scores
    """
    log_npi = np.zeros(len(next(iter(components.values()))), dtype=np.float32)
    total_weight = sum(weights.values())

    for name, values in components.items():
        w = weights.get(name, 0.0)
        values = np.clip(values, 1e-6, 1.0).astype(np.float32)
        log_npi += (w / total_weight) * np.log(values)

    return np.clip(np.exp(log_npi), 0.0, 1.0)
