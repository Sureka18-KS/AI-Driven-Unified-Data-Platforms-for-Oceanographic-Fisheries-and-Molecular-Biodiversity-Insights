# Retention Reporter — how many cells kept vs dropped to cold storage
import numpy as np


class RetentionReporter:
    def generate(self, cycle_data: dict) -> dict:
        npi_history = cycle_data.get("npi_history")
        if npi_history is None or len(npi_history) == 0:
            return {"icon": "pie_chart", "title": "Retention Report",
                    "narrative": "No NPI data for retention reporting."}

        hot = int(np.sum(npi_history > 0.6))
        warm = int(np.sum((npi_history > 0.3) & (npi_history <= 0.6)))
        cold = int(np.sum(npi_history <= 0.3))
        total = len(npi_history)

        narrative = (
            f"Data retention this cycle ({total} cells): "
            f"HOT={hot} ({100*hot//total}%), "
            f"WARM={warm} ({100*warm//total}%), "
            f"COLD={cold} ({100*cold//total}%). "
            f"OPT-4 compression applied to {cold} cold-tier latent vectors "
            f"(est. ~{cold * 0.54:.0f} vectors saved at 54% compression ratio)."
        )
        return {"icon": "pie_chart", "title": "Retention Report", "narrative": narrative}
