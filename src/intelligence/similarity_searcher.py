# Similarity Searcher — finds historical analogues for current state
import numpy as np


class SimilaritySearcher:
    def generate(self, cycle_data: dict) -> dict:
        z_disc = cycle_data.get("z_disc")
        current = cycle_data.get("current_latent")
        historical = cycle_data.get("z_disc")  # reuse current batch as history
        timestamps = cycle_data.get("timestamps", [])

        if z_disc is None or current is None or len(z_disc) < 2:
            return {"icon": "search_link", "title": "Similarity Search",
                    "narrative": "Insufficient historical data for similarity search."}

        diffs = np.linalg.norm(historical - current, axis=1)
        diffs[0] = np.inf  # exclude self
        top_idx = int(np.argmin(diffs))
        similarity = float(1.0 / (1.0 + diffs[top_idx]))

        narrative = (
            f"Most similar historical state: record #{top_idx} "
            f"(similarity score={similarity:.3f}). "
            f"This analogue can be used to predict likely near-future conditions "
            f"based on what occurred after that historical state."
        )
        return {"icon": "search_link", "title": "Similarity Search", "narrative": narrative}
