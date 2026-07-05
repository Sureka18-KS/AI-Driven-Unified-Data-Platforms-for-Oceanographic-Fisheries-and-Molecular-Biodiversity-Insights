# Trend Analyst — temporal trend and component attribution
import numpy as np


class TrendAnalyst:
    def generate(self, cycle_data: dict) -> dict:
        npi_history = cycle_data.get("npi_history")
        comp_history = cycle_data.get("component_history", {})
        if npi_history is None or len(npi_history) < 2:
            return {"icon": "trending_up", "title": "Trend Analysis",
                    "narrative": "Not enough history for trend analysis."}

        mean_npi = float(np.mean(npi_history))
        std_npi = float(np.std(npi_history))

        # Find which component has highest mean (main driver)
        comp_means = {k: float(np.mean(v)) for k, v in comp_history.items()}
        top_driver = max(comp_means, key=comp_means.get) if comp_means else "N/A"

        narrative = (
            f"Current cycle RM-NPI: mean={mean_npi:.4f}, std={std_npi:.4f}. "
            f"Primary driver this cycle: component {top_driver} "
            f"(mean={comp_means.get(top_driver, 0):.3f}). "
            f"Learned weights: {cycle_data.get('learned_weights', {})}."
        )
        return {"icon": "trending_up", "title": "Trend Analysis", "narrative": narrative}
