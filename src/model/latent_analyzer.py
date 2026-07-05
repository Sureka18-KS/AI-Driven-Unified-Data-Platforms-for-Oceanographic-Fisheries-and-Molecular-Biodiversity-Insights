# Dual-Channel Latent Analyzer — post-encoding analytics
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


class DualChannelAnalyzer:
    """
    Analyzes z_npi and z_disc channels to produce actionable signals.

    z_npi channel -> NPI risk zoning
    z_disc channel -> Discovery clustering, novel signal detection
    """

    def npi_analysis(self, z_npi: np.ndarray, npi_scores: np.ndarray) -> dict:
        """Flag high-risk zones from z_npi and RM-NPI scores."""
        high_threshold = np.percentile(npi_scores, 75)
        critical_threshold = np.percentile(npi_scores, 90)
        return {
            "high_risk_zones": npi_scores > high_threshold,
            "critical_zones": npi_scores > critical_threshold,
            "mean_npi": float(npi_scores.mean()),
            "max_npi": float(npi_scores.max()),
        }

    def discovery_analysis(self, z_disc: np.ndarray, recon_errors: np.ndarray) -> dict:
        """Cluster z_disc and detect novel patterns not in RM-NPI."""
        n = len(z_disc)
        n_clusters = max(2, min(8, n // 50))

        scaler = StandardScaler()
        z_scaled = scaler.fit_transform(z_disc)

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        labels = kmeans.fit_predict(z_scaled)

        # Distance from cluster center -> novelty score
        centers = kmeans.cluster_centers_
        novelty_scores = np.array([
            np.linalg.norm(z_scaled[i] - centers[labels[i]])
            for i in range(n)
        ])

        novel_threshold = np.percentile(novelty_scores, 90)
        novel_idx = np.where(novelty_scores > novel_threshold)[0]

        return {
            "labels": labels,
            "n_clusters": n_clusters,
            "novelty_scores": novelty_scores,
            "novel_signals": {str(i): float(novelty_scores[i]) for i in novel_idx[:20]},
            "cluster_means": {str(k): z_disc[labels == k].mean(axis=0).tolist()
                              for k in range(n_clusters)},
        }

    def full_analysis(
        self,
        z_npi: np.ndarray,
        z_disc: np.ndarray,
        npi_scores: np.ndarray,
        recon_errors: np.ndarray,
    ) -> dict:
        """Run both channel analyses and return combined results."""
        return {
            "npi": self.npi_analysis(z_npi, npi_scores),
            "discovery": self.discovery_analysis(z_disc, recon_errors),
        }
