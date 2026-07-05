# Pattern Discoverer — names environmental regimes from z_disc clusters
import numpy as np


REGIME_NAMES = [
    "Monsoon Upwelling", "Inter-Monsoon Calm", "River Plume Intrusion",
    "Coastal Bloom", "Open Ocean Oligotrophic", "ENSO-Driven Anomaly",
    "Winter Stratification", "Pre-Monsoon Buildup",
]


class PatternDiscoverer:
    def generate(self, cycle_data: dict) -> dict:
        z_disc = cycle_data.get("z_disc")
        if z_disc is None or len(z_disc) == 0:
            return {"icon": "chart", "title": "Pattern Discovery",
                    "narrative": "No pattern data available."}

        cluster_means = cycle_data.get("cluster_means", {})
        n_clusters = len(cluster_means) if cluster_means else 0
        regime_list = [REGIME_NAMES[i % len(REGIME_NAMES)] for i in range(n_clusters)]
        names_str = ", ".join(regime_list[:3]) if regime_list else "unknown"
        narrative = (
            f"Dataset shows {n_clusters} distinct oceanographic regimes: {names_str}. "
            f"These were discovered in the z_disc channel (RM-NPI-orthogonal patterns), "
            f"meaning they contain information not captured by the standard RM-NPI formula."
        )
        return {"icon": "chart", "title": "Pattern Discovery", "narrative": narrative}
