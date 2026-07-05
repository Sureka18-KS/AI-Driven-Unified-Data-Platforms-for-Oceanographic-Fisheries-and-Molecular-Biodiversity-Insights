# Data Quality Assessor — detects sensor drift and bad data
import numpy as np


class DataQualityAssessor:
    def generate(self, cycle_data: dict) -> dict:
        per_feat_errors = cycle_data.get("per_feature_errors")
        feat_names = cycle_data.get("feature_names", [])
        if per_feat_errors is None or len(per_feat_errors) == 0:
            return {"icon": "health_check", "title": "Data Quality",
                    "narrative": "No feature error data available."}

        mean_errors = np.mean(per_feat_errors, axis=0)
        top_idx = int(np.argmax(mean_errors))
        top_feat = feat_names[top_idx] if top_idx < len(feat_names) else f"feature_{top_idx}"
        quality_score = float(1.0 - np.mean(mean_errors))

        narrative = (
            f"Overall data quality score: {quality_score:.3f}/1.0. "
            f"Highest reconstruction error in feature '{top_feat}' "
            f"(mean error={mean_errors[top_idx]:.4f}) -- possible sensor drift or missing data. "
            f"{int(np.sum(mean_errors > 0.1))} features have elevated error (> 0.1)."
        )
        return {"icon": "health_check", "title": "Data Quality", "narrative": narrative}
