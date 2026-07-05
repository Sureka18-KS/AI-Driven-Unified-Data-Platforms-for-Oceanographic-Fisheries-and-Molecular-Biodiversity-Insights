# Anomaly Narrator — explains WHY a grid cell is anomalous
import numpy as np


class AnomalyNarrator:
    def generate(self, cycle_data: dict) -> dict:
        anomalies = cycle_data.get("flagged_anomalies", [])
        feature_names = cycle_data.get("feature_names", [])
        if not anomalies:
            return {"icon": "search", "title": "Anomaly Detection",
                    "narrative": "No significant anomalies detected this cycle."}

        a = anomalies[0]
        orig = np.array(a["original"])
        recon = np.array(a["reconstructed"])
        errors = (orig - recon) ** 2
        top_idx = int(np.argmax(errors))
        feat_name = feature_names[top_idx] if top_idx < len(feature_names) else f"feature_{top_idx}"
        direction = "elevated" if orig[top_idx] > recon[top_idx] else "depressed"
        narrative = (
            f"Sample #{a['sample_id']} is anomalous "
            f"(reconstruction error={a['recon_error']:.4f}). "
            f"Primary driver: {feat_name} is {direction} beyond expected range. "
            f"z_disc divergence={float(np.linalg.norm(a['z_disc'])):.3f}."
        )
        return {"icon": "search", "title": "Anomaly Detection", "narrative": narrative}
