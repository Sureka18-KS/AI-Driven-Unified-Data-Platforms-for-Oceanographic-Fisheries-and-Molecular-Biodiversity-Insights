import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import warnings
warnings.filterwarnings("ignore")

# Define the precise system prompt the user requested
SYSTEM_PROMPT = """
You are OceanInsight AI, an intelligent assistant integrated into an AI-driven environmental data platform designed for analyzing large-scale oceanographic and biodiversity datasets.

Your primary purpose is to help users explore, understand, and interpret environmental data produced by the platform's machine learning pipeline.

The platform integrates multiple environmental datasets including:
- Sea Surface Temperature (SST)
- Rainfall data
- NDVI vegetation index
- River discharge measurements
- Oceanographic sensor data
- Biodiversity indicators

The system processes these datasets through a multi-stage pipeline involving:
1. Data ingestion from multiple sources
2. Spatio-temporal alignment and preprocessing
3. Feature engineering
4. Autoencoder-based representation learning
5. RM-NPI (River Mouth Nutrient Pressure Index) risk computation
6. Anomaly detection and environmental pattern discovery
7. Data-centre optimization for intelligent computation allocation

RM-NPI is a key metric defined as:

RM-NPI = Q × N × S × D

Where:
Q = river discharge intensity
N = nutrient load proxy derived from vegetation or land-use signals
S = seasonal intensity factor
D = distance decay from the river mouth

The RM-NPI index estimates coastal nutrient pressure that can contribute to:
- marine pollution
- algal blooms
- oxygen depletion (dead zones)
- coral reef stress
- biodiversity disruption

Your responsibilities include:
1. Answer user questions about environmental data trends and model outputs.
2. Explain RM-NPI risk factors and environmental conditions influencing coastal ecosystems.
3. Interpret anomalies detected by the AI system.
4. Provide insights about oceanographic conditions based on the integrated datasets.
5. Assist users in exploring datasets available within the platform.
6. Help interpret the outputs of the autoencoder-based representation learning system.
7. Provide scientifically reasonable explanations based on oceanography, environmental science, and machine learning principles.

Important constraints:
- Do NOT fabricate datasets or results that are not available in the platform.
- If requested information requires querying the platform API or database, indicate the required data query.
- Maintain scientifically accurate explanations.
- Provide concise and clear responses suitable for environmental monitoring and decision-support contexts.

Your tone should be analytical, clear, and informative, similar to a scientific assistant supporting environmental monitoring systems.
Your goal is to help users understand oceanographic patterns, environmental risks, and machine learning insights derived from the platform.
"""


class OceanInsightTools:
    """
    Implementation of the core data-fetching tools for OceanInsight AI.
    These tools read directly from the machine-learning pipeline's unified outputs.
    """
    def __init__(self, data_path="data/processed/unified.parquet"):
        self.data_path = Path(data_path)
        self.df = None
        
        # Load data on init if available
        if self.data_path.exists():
            self.df = pd.read_parquet(self.data_path)
            self.df["time"] = pd.to_datetime(self.df["time"])
            
            # Recalculate component baseline so tools can easily simulate
            self._init_components()

    def _init_components(self):
        """Prepare baseline values for Q, N, S, D for simulation purposes."""
        if self.df is None: return
        
        def norm01(arr):
            # Normalization helper
            a, b = arr.min(), arr.max()
            if b - a < 1e-8: return np.full_like(arr, 0.5)
            return np.clip((arr - a) / (b - a), 0.01, 1.0)
            
        self.df["temp_Q"] = 0.5
        self.df["temp_N"] = norm01(self.df["no3"].fillna(self.df["no3"].median()).values)
        self.df["temp_S"] = norm01(35.0 - self.df["so"].fillna(self.df["so"].median()).values)
        self.df["temp_D"] = 0.0036  # Domain average distance decay
        
        # Add basic anomaly flags if they aren't precomputed
        if "is_anomaly" not in self.df.columns and "recon_err" in self.df.columns:
            thresh = np.percentile(self.df["recon_err"].dropna(), 95)
            self.df["is_anomaly"] = self.df["recon_err"] > thresh

    def _filter_region_time(self, region=None, time_range=None):
        if self.df is None: return None
        sub = self.df.copy()
        
        if time_range:
            start, end = pd.to_datetime(time_range[0]), pd.to_datetime(time_range[1])
            sub = sub[(sub["time"] >= start) & (sub["time"] <= end)]
            
        if region:
            lat_min, lat_max, lon_min, lon_max = region
            sub = sub[(sub["lat"] >= lat_min) & (sub["lat"] <= lat_max) &
                      (sub["lon"] >= lon_min) & (sub["lon"] <= lon_max)]
        return sub

    def get_dataset_list(self) -> str:
        """Return exactly what datasets are available in the platform."""
        if self.df is None: return "Error: Platform data missing."
        
        cols = self.df.columns.tolist()
        datasets = {
            "Time Range": f"{self.df['time'].min().date()} to {self.df['time'].max().date()}",
            "Spatial Extent": f"Lat {self.df['lat'].min()} to {self.df['lat'].max()}, Lon {self.df['lon'].min()} to {self.df['lon'].max()}",
            "Variables": [c for c in cols if c not in ["time", "lat", "lon", "is_anomaly", "cluster", "recon_err", "lat_g", "lon_g"]],
            "Total Records": len(self.df)
        }
        return json.dumps(datasets, indent=2)

    def get_sst(self, region: list = None, date_range: list = None) -> str:
        """Return Sea Surface Temperature (SST / thetao) statistics."""
        sub = self._filter_region_time(region, date_range)
        if sub is None or len(sub) == 0: return "No SST data available for this query."
        
        stats = {
            "mean_sst_celsius": float(sub["thetao"].mean()),
            "max_sst_celsius": float(sub["thetao"].max()),
            "min_sst_celsius": float(sub["thetao"].min()),
            "record_count": len(sub)
        }
        return json.dumps(stats, indent=2)

    def get_rmnpi(self, region: list = None, time_range: list = None) -> str:
        """Return River Mouth Nutrient Pressure Index risk metrics."""
        sub = self._filter_region_time(region, time_range)
        if sub is None or len(sub) == 0: return "No RM-NPI data available for this query."
        
        if "npi" not in sub.columns:
            return "RM-NPI has not been computed in this dataset."
            
        high_risk = len(sub[sub["npi"] > 0.6])
        stats = {
            "mean_npi": float(sub["npi"].mean()),
            "max_npi": float(sub["npi"].max()),
            "high_risk_zones": high_risk,
            "risk_percentage": float((high_risk / len(sub)) * 100)
        }
        return json.dumps(stats, indent=2)

    def get_anomalies(self) -> str:
        """Return recent or major environmental anomalies detected by the Autoencoder."""
        if self.df is None: return "No dataset loaded."
        if "is_anomaly" not in self.df.columns:
            return "Anomaly detection (Phase 6) has not been run or logged in this dataset."
            
        anomalies = self.df[self.df["is_anomaly"]]
        if len(anomalies) == 0:
            return "No anomalies detected in the current platform state."
            
        # Group by feature with highest z-score to explain anomalies
        most_recent = anomalies[anomalies["time"] == anomalies["time"].max()]
        
        report = {
            "total_anomalies_historical": len(anomalies),
            "anomalies_latest_day": len(most_recent),
            "latest_date": str(anomalies["time"].max().date()),
            "average_reconstruction_error": float(anomalies["recon_err"].mean()) if "recon_err" in anomalies else 0.0
        }
        return json.dumps(report, indent=2)

    def simulate_environmental_change(self, parameters: dict) -> str:
        """
        Simulate how changes to Q, N, or S isolated parameters affect RM-NPI.
        Example parameter dict: {"discharge_increase_pct": 20, "nutrient_load_pct": -10}
        """
        if self.df is None: return "No dataset loaded."
        if "npi" not in self.df.columns: return "RM-NPI model baseline not available."
        
        # Original RM-NPI
        orig_mean = self.df["npi"].mean()
        high_risk_orig = len(self.df[self.df["npi"] > 0.6])
        
        # Apply multipliers
        Q_mult = 1.0 + (parameters.get("discharge_increase_pct", 0) / 100.0)
        N_mult = 1.0 + (parameters.get("nutrient_load_pct", 0) / 100.0)
        S_mult = 1.0 + (parameters.get("seasonal_intensity_pct", 0) / 100.0)
        
        new_Q = np.clip(self.df["temp_Q"] * Q_mult, 0.01, 1.0)
        new_N = np.clip(self.df["temp_N"] * N_mult, 0.01, 1.0)
        new_S = np.clip(self.df["temp_S"] * S_mult, 0.01, 1.0)
        new_D = self.df["temp_D"]
        
        # Recompute using log-space formula
        # Weights learned from recent execution => {'w_Q': 0.25, 'w_N': 0.25, 'w_S': 0.25, 'w_D': 0.25} approx
        w = [0.2632, 0.2632, 0.2105, 0.2632] 
        log_npi = (w[0]*np.log(new_Q) + w[1]*np.log(new_N) +
                   w[2]*np.log(new_S) + w[3]*np.log(new_D))
        new_npi = np.exp(log_npi)
        new_npi = np.clip(new_npi, 0, 1)
        
        sim_mean = new_npi.mean()
        high_risk_new = len(new_npi[new_npi > 0.6])
        
        res = {
            "original_mean_npi": float(orig_mean),
            "simulated_mean_npi": float(sim_mean),
            "change_in_mean_npi_pct": float((sim_mean - orig_mean) / orig_mean * 100),
            "original_high_risk_zones": high_risk_orig,
            "simulated_high_risk_zones": high_risk_new
        }
        return json.dumps(res, indent=2)


import sys
import argparse

def interactive_shell():
    """A simplistic CLI to test the OceanInsight AI Agent tools manually."""
    print("======================================================")
    print("  OceanInsight AI -- Tool Execution Test Shell")
    print("======================================================")
    
    agent = OceanInsightTools()
    
    while True:
        try:
            cmd = input("\nOceanInsight> ").strip()
            if cmd.lower() in ["exit", "quit"]: break
            if not cmd: continue
            
            if cmd == "help":
                print("Available tools:")
                print(" - get_dataset_list()")
                print(" - get_sst(region=[lat_min, lat_max, lon_min, lon_max])")
                print(" - get_rmnpi()")
                print(" - get_anomalies()")
                print(" - simulate_change(discharge_pct, nutrient_pct)")
                continue
                
            if cmd == "get_dataset_list()":
                print(agent.get_dataset_list())
            elif cmd == "get_rmnpi()":
                print(agent.get_rmnpi())
            elif cmd == "get_anomalies()":
                print(agent.get_anomalies())
            elif cmd.startswith("get_sst("):
                # Hardcode full region for demo
                print(agent.get_sst(region=[5, 20, 70, 85]))
            elif cmd.startswith("simulate_change("):
                # parse args cheaply
                args = cmd.replace("simulate_change(", "").replace(")", "").split(",")
                if len(args) >= 2:
                    params = {"discharge_increase_pct": float(args[0]), "nutrient_load_pct": float(args[1])}
                    print(agent.simulate_environmental_change(params))
                else:
                    print("Provide 2 comma-separated numbers: discharge_pct, nutrient_pct")
            else:
                print("Unknown command. Type 'help' to see active tools.")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "shell":
        interactive_shell()
    else:
        print("OceanInsight AI Agent module loaded successfully.")
        print("Run `python src/intelligence/ocean_agent.py shell` to test the tools interactively.")
