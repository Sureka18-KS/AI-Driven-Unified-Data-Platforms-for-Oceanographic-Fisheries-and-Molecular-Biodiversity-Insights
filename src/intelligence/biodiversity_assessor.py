import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

class BiodiversityAssessor:
    """
    Evaluates physical and biogeochemical ocean data to predict 
    immediate biodiversity threats, such as Coral Bleaching, 
    Harmful Algal Blooms (Dead Zones), and Ecosystem Disruption.

    All evaluated insights are exported as JSON for further LLM parsing.
    """

    def __init__(self, output_dir="data/insights/biodiversity"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def assess_biodiversity(self, df: pd.DataFrame, npi_scores: np.ndarray) -> dict:
        """
        Analyzes the unified dataframe and RM-NPI scores to output biodiversity predictions.
        """
        insights = []

        # -----------------------------------------------------------------
        # 1. Coral Bleaching (Marine Heatwave Detection)
        # -----------------------------------------------------------------
        # Bleaching generally occurs when SST (thetao) persistently exceeds normal summer max.
        # We proxy this by finding points where the temperature anomaly is highly extreme.
        if "thetao" in df.columns:
            mean_temp = df["thetao"].mean()
            std_temp = df["thetao"].std()
            bleaching_threshold = mean_temp + (2 * std_temp)  # +2 StdDev proxy for heatwave
            
            bleaching_zones = df[df["thetao"] > bleaching_threshold]
            pct_bleaching = (len(bleaching_zones) / len(df)) * 100
            
            if len(bleaching_zones) > 0:
                insights.append({
                    "threat_type": "Coral Bleaching / Marine Heatwave",
                    "severity": "HIGH" if pct_bleaching > 5 else "MODERATE",
                    "affected_cells": len(bleaching_zones),
                    "percentage_of_ocean": round(pct_bleaching, 2),
                    "trigger_metric": "Sea Surface Temperature (thetao)",
                    "description": f"Temperatures exceeded the heatwave threshold of {bleaching_threshold:.2f}°C, "
                                   f"putting coral reefs and stationary marine life at high risk of thermal stress and bleaching."
                })
        
        # -----------------------------------------------------------------
        # 2. Harmful Algal Blooms & Hypoxia (Dead Zones)
        # -----------------------------------------------------------------
        # Very high RM-NPI combined with high Chlorophyll highly correlates with deadly algal blooms.
        # We look for cells where NPI > 0.8.
        dead_zones = int(np.sum(npi_scores > 0.8))
        if dead_zones > 0:
            insights.append({
                "threat_type": "Hypoxic 'Dead Zones' / Algal Blooms",
                "severity": "CRITICAL",
                "affected_cells": dead_zones,
                "percentage_of_ocean": round((dead_zones / len(df)) * 100, 2),
                "trigger_metric": "RM-NPI (River Mouth Nutrient Pressure Index)",
                "description": f"Extreme nutrient pollution detected in {dead_zones} zones. "
                               f"This triggers explosive algal growth that depletes ocean oxygen, "
                               f"leading to mass suffocation of fish, crabs, and bottom-dwellers."
            })

        # -----------------------------------------------------------------
        # 3. Marine Food Web Disruption
        # -----------------------------------------------------------------
        # A massive drop in Chlorophyll or extreme physical current disruption (uo/vo)
        # forces plankton and major fisheries to migrate.
        if "chl_proxy" in df.columns or "chl" in df.columns:
            target_col = "chl_proxy" if "chl_proxy" in df.columns else "chl"
            starvation_threshold = df[target_col].quantile(0.05) # Bottom 5% of chlorophyll
            starving_zones = len(df[df[target_col] <= starvation_threshold])
            
            if starving_zones > 0:
                insights.append({
                    "threat_type": "Food Web Collapse / Fish Migration",
                    "severity": "WARNING",
                    "affected_cells": starving_zones,
                    "percentage_of_ocean": round((starving_zones / len(df)) * 100, 2),
                    "trigger_metric": "Chlorophyll (Phytoplankton base)",
                    "description": f"A severe drop in foundational phytoplankton detected in {starving_zones} zones. "
                                   f"This disrupts the exact base of the marine food web, forcing massive "
                                   f"commercial fish populations, dolphins, and whales to migrate elsewhere to survive."
                })

        # Compile final JSON report
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "region_metrics": {
                "total_grid_cells_analyzed": len(df),
                "date_range": str(df["time"].min().date()) + " to " + str(df["time"].max().date())
            },
            "biodiversity_threats": insights,
        }

        # Save to the local output folder
        filename = f"biodiversity_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename
        with open(filepath, "w") as f:
            json.dump(report, f, indent=4)
            
        return report, filepath
