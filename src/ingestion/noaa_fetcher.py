# NOAA ERDDAP Fetcher — Sea Surface Temperature (SST)
# Dataset: NOAA OI SST V2.1 High Resolution (daily, 0.25° grid)
# Dataset ID: ncdcOisst21Agg_LonPM180
# No authentication required — public ERDDAP server

import os
import xarray as xr
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ERDDAP_BASE = os.getenv("NOAA_ERDDAP_BASE_URL", "https://coastwatch.pfeg.noaa.gov/erddap")

# ERDDAP datasets lag behind real-time by a few days
ERDDAP_LAG_DAYS = 3


class NOAAFetcher:
    """
    Fetches Sea Surface Temperature from NOAA ERDDAP.

    Dataset: NOAA OI SST V2.1 (Optimum Interpolation)
    - Resolution: 0.25° × 0.25° daily
    - Coverage: Global
    - Variables: sst (°C), anom (SST anomaly)
    - URL: https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21Agg_LonPM180
    """

    DATASET_ID = "ncdcOisst21Agg_LonPM180"
    VARIABLES = ["sst", "anom"]

    def __init__(self, output_dir: str = "data/raw/noaa"):
        self.base_url = f"{ERDDAP_BASE}/griddap/{self.DATASET_ID}"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def fetch(
        self,
        start_date: str,
        end_date: str,
        lat_min: float = 0.0,
        lat_max: float = 25.0,
        lon_min: float = 65.0,
        lon_max: float = 90.0,
    ) -> xr.Dataset:
        """
        Fetch SST data from NOAA ERDDAP for the Indian Ocean region.

        Automatically adjusts dates to stay within dataset availability.
        """
        # Clamp end date: ERDDAP data lags ~3 days behind today
        today = datetime.utcnow()
        safe_end = today - timedelta(days=ERDDAP_LAG_DAYS)
        parsed_end = datetime.strptime(end_date, "%Y-%m-%d")
        if parsed_end > safe_end:
            end_date = safe_end.strftime("%Y-%m-%d")
            print(f"[NOAA] Adjusted end date to {end_date} (dataset lags {ERDDAP_LAG_DAYS} days)")

        variables = ",".join(self.VARIABLES)

        # ERDDAP uses ISO time format
        url = (
            f"{self.base_url}.nc?"
            f"{variables}"
            f"[({start_date}T00:00:00Z):1:({end_date}T00:00:00Z)]"
            f"[({lat_min}):1:({lat_max})]"
            f"[({lon_min}):1:({lon_max})]"
        )

        print(f"[NOAA] Fetching SST: {start_date} -> {end_date}")
        print(f"       Region: lat[{lat_min},{lat_max}], lon[{lon_min},{lon_max}]")

        # Download as NetCDF
        output_path = self.output_dir / f"sst_{start_date}_{end_date}.nc"

        # Check if already downloaded
        if output_path.exists():
            print(f"[NOAA] Using cached file: {output_path}")
            ds = xr.open_dataset(output_path)
            return ds

        response = requests.get(url, stream=True, timeout=180)

        # If 500, try reducing the date range further
        if response.status_code == 500:
            print(f"[NOAA] Server error. Trying with 5 more days of lag...")
            extra_safe_end = today - timedelta(days=ERDDAP_LAG_DAYS + 5)
            # Never exceed the originally requested end_date
            parsed_requested_end = datetime.strptime(end_date, "%Y-%m-%d")
            adjusted_end = min(extra_safe_end, parsed_requested_end)
            if adjusted_end < datetime.strptime(start_date, "%Y-%m-%d"):
                raise ValueError(
                    f"[NOAA] Adjusted end date {adjusted_end.strftime('%Y-%m-%d')} "
                    f"is before start date {start_date}. "
                    f"Data not yet available for this period."
                )
            end_date = adjusted_end.strftime("%Y-%m-%d")
            url = (
                f"{self.base_url}.nc?"
                f"{variables}"
                f"[({start_date}T00:00:00Z):1:({end_date}T00:00:00Z)]"
                f"[({lat_min}):1:({lat_max})]"
                f"[({lon_min}):1:({lon_max})]"
            )
            output_path = self.output_dir / f"sst_{start_date}_{end_date}.nc"
            response = requests.get(url, stream=True, timeout=180)

        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Load into xarray
        ds = xr.open_dataset(output_path)
        print(f"[NOAA] Downloaded: {ds.dims}")
        print(f"       SST range: {float(ds['sst'].min()):.1f}°C -> "
              f"{float(ds['sst'].max()):.1f}°C")

        return ds

    def fetch_latest(
        self,
        n_days: int = 30,
        lat_min: float = 0.0,
        lat_max: float = 25.0,
        lon_min: float = 65.0,
        lon_max: float = 90.0,
    ) -> xr.Dataset:
        """Fetch the most recent N days of SST data."""
        end = datetime.utcnow() - timedelta(days=ERDDAP_LAG_DAYS)
        start = end - timedelta(days=n_days)
        return self.fetch(
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
            lat_min, lat_max, lon_min, lon_max,
        )

    def to_dataframe(self, ds: xr.Dataset) -> pd.DataFrame:
        """Convert xarray Dataset to a flat DataFrame."""
        df = ds.to_dataframe().reset_index()
        df = df.dropna(subset=["sst"])
        return df
