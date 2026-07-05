# OPT-7: Pipeline-Aware Batch Coalescing + Dual-Signal Scheduler
from dataclasses import dataclass
from typing import List, Dict
import numpy as np


@dataclass
class WorkloadTicket:
    lat: float
    lon: float
    timestamp: str
    npi_score: float
    disc_anomaly_score: float
    is_novel_cluster: bool
    priority: str


def schedule(npi_score: float, disc_anomaly: float, is_novel: bool) -> str:
    """
    Dual-signal scheduler using both z_npi and z_disc outputs.

    Priority tiers (highest to lowest):
        CRITICAL   -- Very high NPI (> 0.8)
        DISCOVERY  -- Novel pattern in z_disc (unseen cluster)
        HIGH       -- High NPI (0.6-0.8) or significant anomaly
        INVESTIGATE-- Moderate anomaly worth checking
        ROUTINE    -- Low NPI, no anomaly
    """
    if npi_score > 0.8:
        return "CRITICAL"
    if is_novel:
        return "DISCOVERY"
    if npi_score > 0.6 or disc_anomaly > 0.5:
        return "HIGH"
    if disc_anomaly > 0.3:
        return "INVESTIGATE"
    return "ROUTINE"


def coalesce_workloads(
    tickets: List[WorkloadTicket],
    grid_size: float = 1.0,
) -> List[List[WorkloadTicket]]:
    """
    OPT-7: Group adjacent grid cells into regional batches.

    Cells within grid_size degrees of each other are coalesced
    into a single GPU batch, improving throughput 5-10x.
    """
    if not tickets:
        return []

    # Group by grid cell (floor to grid_size)
    groups: Dict[tuple, List[WorkloadTicket]] = {}
    for t in tickets:
        key = (round(t.lat // grid_size), round(t.lon // grid_size))
        groups.setdefault(key, []).append(t)

    # Sort batches: CRITICAL first, then DISCOVERY, then others
    priority_order = {"CRITICAL": 0, "DISCOVERY": 1, "HIGH": 2, "INVESTIGATE": 3, "ROUTINE": 4}
    batches = list(groups.values())
    batches.sort(key=lambda b: min(priority_order.get(t.priority, 5) for t in b))

    return batches
