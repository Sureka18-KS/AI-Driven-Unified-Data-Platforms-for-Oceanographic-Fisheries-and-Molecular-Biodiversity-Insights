# Feature Registry — dynamic feature group manager
import yaml
from pathlib import Path
from typing import Dict


class FeatureRegistry:
    """Reads feature_registry.yaml and provides group dimensions."""

    def __init__(self, config_path: str = "config/feature_registry.yaml"):
        with open(config_path) as f:
            self._cfg = yaml.safe_load(f)

    def get_feature_groups(self) -> Dict[str, int]:
        """Return {group_name: feature_count} from registry."""
        groups: Dict[str, int] = {}
        for feat, meta in self._cfg.get("features", {}).items():
            grp = meta.get("group", "temporal")
            groups[grp] = groups.get(grp, 0) + 1
        return groups

    def total_input_dim(self) -> int:
        return sum(self.get_feature_groups().values())

    def get_all_feature_names(self):
        return list(self._cfg.get("features", {}).keys())
