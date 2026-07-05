# CHIRPS Rainfall Fetcher -- Climate Hazards Group InfraRed Precipitation
# Dataset: CHIRPS 2.0 monthly rainfall (0.25 degree resolution)
# Source: UC Santa Barbara -- public, no auth needed
# URL: https://data.chc.ucsb.edu/products/CHIRPS-2.0/

import os
import xarray as xr
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CHIRPS_BASE = os.getenv(
    "CHIRPS_BASE_URL", "https://data.chc.ucsb.edu/products/CHIRPS-2.0"
)


class CHIRPSFetcher:
    """
    Fetches monthly rainfall data from CHIRPS 2.0.

    CHIRPS = Climate Hazards Group InfraRed Precipitation with Station data
    - Resolution: 0.25 degree monthly
    - Coverage: 50S to 50N (land + near-coastal)
    - Variable: precip (mm/month)

    Used as Seasonal Factor (S) proxy in RM-NPI:
        High rainfall during monsoon -> S = 1
        Low rainfall during dry season -> S = 0
    """

    def __init__(self, output_dir: str = "data/raw/chirps"):
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
        Fetch monthly rainfall from CHIRPS directly from UCSB servers.
        Returns: xarray Dataset with 'precip' variable
        """
        print(f"[CHIRPS] Fetching rainfall: {start_date} to {end_date}")
        print(f"         Region: lat[{lat_min},{lat_max}], lon[{lon_min},{lon_max}]")

        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)

        # Clamp to available data (CHIRPS lags ~2 months)
        latest = pd.Timestamp(datetime.utcnow()) - pd.DateOffset(months=2)
        if end > latest:
            end = latest
            print(f"[CHIRPS] Adjusted end to {end.strftime('%Y-%m')} (data lag ~2 months)")

        all_data = []
        current = start

        while current <= end:
            year = current.year
            month = current.month

            filename = f"chirps-v2.0.{year}.{month:02d}.nc"
            url = f"{CHIRPS_BASE}/global_monthly/netcdf/{filename}"
            output_path = self.output_dir / filename

            if not output_path.exists():
                print(f"[CHIRPS] Downloading: {year}-{month:02d} ...")
                try:
                    response = requests.get(url, stream=True, timeout=120)
                    response.raise_for_status()
                    with open(output_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=65536):
                            f.write(chunk)
                    size_mb = output_path.stat().st_size / 1024 / 1024
                    print(f"         Downloaded {size_mb:.1f} MB")
                except requests.HTTPError as e:
                    print(f"  [!] Not available: {filename} ({e})")
                    current += pd.DateOffset(months=1)
                    continue
                except Exception as e:
                    print(f"  [!] Error downloading {filename}: {e}")
                    current += pd.DateOffset(months=1)
                    continue
            else:
                print(f"[CHIRPS] Using cached: {filename}")

            try:
                ds = xr.open_dataset(output_path)

                if not all_data:
                    print(f"         Variables: {list(ds.data_vars)}")
                    print(f"         Dimensions: {dict(ds.dims)}")

                # Identify lat/lon coord names
                lat_coord = next((c for c in ds.coords if "lat" in c.lower()), None)
                lon_coord = next((c for c in ds.coords if "lon" in c.lower()), None)

                if lat_coord and lon_coord:
                    lat_vals = ds[lat_coord].values
                    if lat_vals[0] > lat_vals[-1]:
                        ds = ds.sel(**{
                            lat_coord: slice(lat_max, lat_min),
                            lon_coord: slice(lon_min, lon_max),
                        })
                    else:
                        ds = ds.sel(**{
                            lat_coord: slice(lat_min, lat_max),
                            lon_coord: slice(lon_min, lon_max),
                        })

                    rename_map = {}
                    if lat_coord != "lat":
                        rename_map[lat_coord] = "lat"
                    if lon_coord != "lon":
                        rename_map[lon_coord] = "lon"
                    if rename_map:
                        ds = ds.rename(rename_map)

                if "time" not in ds.dims:
                    ds = ds.expand_dims(
                        time=[pd.Timestamp(f"{year}-{month:02d}-01")]
                    )

                all_data.append(ds)

            except Exception as e:
                print(f"  [!] Error reading {output_path}: {e}")

            current += pd.DateOffset(months=1)

        if not all_data:
            raise ValueError("No CHIRPS data downloaded successfully")

        combined = xr.concat(all_data, dim="time")
        n_time = combined.dims.get("time", 0)
        n_lat = combined.dims.get("lat", 0)
        n_lon = combined.dims.get("lon", 0)
        print(f"[CHIRPS] Combined: time={n_time}, lat={n_lat}, lon={n_lon}")
        print(f"         Total data points: {n_time * n_lat * n_lon:,}")
        return combined

    def fetch_latest(
        self,
        n_months: int = 3,
        lat_min: float = 0.0,
        lat_max: float = 25.0,
        lon_min: float = 65.0,
        lon_max: float = 90.0,
    ) -> xr.Dataset:
        end = datetime.utcnow()
        start = end - timedelta(days=n_months * 30)
        return self.fetch(
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
            lat_min, lat_max, lon_min, lon_max,
        )

    def rainfall_to_seasonal_factor(self, ds: xr.Dataset) -> xr.DataArray:
        """Convert rainfall -> Seasonal Factor (S for RM-NPI).
        Monsoon months (200+ mm/month) -> S = 1
        Dry months (< 10 mm/month) -> S = 0
        """
        var_name = next(
            (v for v in ds.data_vars if "prec" in v.lower() or "rain" in v.lower()),
            list(ds.data_vars)[0],
        )
        rain = ds[var_name]
        return (rain / 200.0).clip(0, 1)
