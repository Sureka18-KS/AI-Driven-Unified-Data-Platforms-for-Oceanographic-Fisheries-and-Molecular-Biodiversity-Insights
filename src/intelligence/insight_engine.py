# Intelligence Layer Orchestrator — runs all 6 generators
from .anomaly_narrator import AnomalyNarrator
from .pattern_discoverer import PatternDiscoverer
from .trend_analyst import TrendAnalyst
from .data_quality_assessor import DataQualityAssessor
from .similarity_searcher import SimilaritySearcher
from .retention_reporter import RetentionReporter


class InsightEngine:
    """Run all 6 generators and return list of insight dicts."""

    def __init__(self, historical_data: dict = None, config: dict = None):
        self.historical_data = historical_data or {}
        self.config = config or {}
        self.generators = [
            AnomalyNarrator(),
            PatternDiscoverer(),
            TrendAnalyst(),
            DataQualityAssessor(),
            SimilaritySearcher(),
            RetentionReporter(),
        ]

    def generate_report(self, cycle_data: dict) -> list:
        insights = []
        for gen in self.generators:
            try:
                result = gen.generate(cycle_data)
                insights.append(result)
            except Exception as e:
                insights.append({
                    "icon": "warning",
                    "title": type(gen).__name__,
                    "narrative": f"Generator failed: {e}",
                })
        return insights
