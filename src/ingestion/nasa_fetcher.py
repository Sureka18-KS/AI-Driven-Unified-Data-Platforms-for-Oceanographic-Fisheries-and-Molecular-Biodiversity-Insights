# NASA Earthdata Fetcher — Ocean Color (Chlorophyll-a) as Nutrient Proxy
# Dataset: MODIS-Aqua Level 3 Mapped Chlorophyll-a (monthly, 4km)
# Source: NASA Ocean Biology DAAC (OB.DAAC)
# Auth: NASA Earthdata Login (https://urs.earthdata.nasa.gov/)
import os
import xarray as xr
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
NASA_USERNAME = os.getenv("NASA_EARTHDATA_USERNAME", "")
NASA_PASSWORD = os.getenv("NASA_EARTHDATA_PASSWORD", "")
class NASAFetcher:
    """
    Fetches Chlorophyll-a concentration from NASA Earthdata.
    Chlorophyll-a is a proxy for NUTRIENT LOAD (N component in RM-NPI):
    High chlorophyll → high phytoplankton → high nutrient runoff.
    Dataset: MODIS-Aqua Ocean Color (Level 3 SMI)
    - Resolution: ~4 km monthly
    - Variable: chlor_a (mg/m³)
    - Source: https://oceandata.sci.gsfc.nasa.gov/
    Alternative (no auth): NOAA ERDDAP mirror of the same dataset:
    erdMH1chlamday (MODIS Aqua monthly chlorophyll)
    """
    # ERDDAP mirror (no NASA auth needed — fallback)
    ERDDAP_DATASET = "erdMH1chlamday"
    ERDDAP_BASE = os.getenv(
        "NOAA_ERDDAP_BASE_URL", "https://coastwatch.pfeg.noaa.gov/erddap"
    )
    # NASA OPeNDAP direct (needs auth)
    NASA_OPENDAP_BASE = "https://oceandata.sci.gsfc.nasa.gov/opendap"
    def __init__(self, output_dir: str = "data/raw/nasa", prefer_erddap: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.prefer_erddap = prefer_erddap
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
        Fetch Chlorophyll-a data.
        Strategy:
        1. Try ERDDAP mirror first (no auth needed)
        2. Fall back to NASA OPeNDAP if ERDDAP fails
        Returns: xarray Dataset with chlorophyll field
        """
        if self.prefer_erddap:
            try:
                return self._fetch_via_erddap(
                    start_date, end_date, lat_min, lat_max, lon_min, lon_max
                )
            except Exception as e:
                print(f"[NASA] ERDDAP mirror failed: {e}")
                print("[NASA] Falling back to NASA Earthdata direct...")
        return self._fetch_via_earthdata(
            start_date, end_date, lat_min, lat_max, lon_min, lon_max
        )
    def _fetch_via_erddap(
        self, start_date, end_date, lat_min, lat_max, lon_min, lon_max
    ) -> xr.Dataset:
        """Fetch from NOAA ERDDAP mirror of MODIS chlorophyll."""
        url = (
            f"{self.ERDDAP_BASE}/griddap/{self.ERDDAP_DATASET}.nc?"
            f"chlorophyll"
            f"[({start_date}T00:00:00Z):1:({end_date}T00:00:00Z)]"
            f"[({lat_min}):1:({lat_max})]"
            f"[({lon_min}):1:({lon_max})]"
        )
        print(f"[NASA/ERDDAP] Fetching Chlorophyll-a: {start_date} → {end_date}")
        output_path = self.output_dir / f"chlor_{start_date}_{end_date}.nc"
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        ds = xr.open_dataset(output_path)
        print(f"[NASA/ERDDAP] Downloaded: {ds.dims}")
        return ds
    def _fetch_via_earthdata(
        self, start_date, end_date, lat_min, lat_max, lon_min, lon_max
    ) -> xr.Dataset:
        """
        Fetch directly from NASA Earthdata using authenticated session.
        Uses the earthaccess package if available, otherwise raw requests.
        """
        if not NASA_USERNAME or not NASA_PASSWORD:
            raise ValueError(
                "NASA Earthdata credentials not set. "
                "Set NASA_EARTHDATA_USERNAME and NASA_EARTHDATA_PASSWORD in .env\n"
                "Register at: https://urs.earthdata.nasa.gov/"
            )
        try:
            import earthaccess
            auth = earthaccess.login(
                strategy="environment",  # reads from env vars
            )
            results = earthaccess.search_data(
                short_name="MODISA_L3m_CHL",
                temporal=(start_date, end_date),
                bounding_box=(lon_min, lat_min, lon_max, lat_max),
                count=10,
            )
            if not results:
                raise ValueError(f"No MODIS Chlorophyll data found for {start_date} – {end_date}")
            files = earthaccess.download(
                results,
                str(self.output_dir),
            )
            # Load all downloaded files as a single dataset
            ds = xr.open_mfdataset(files, combine="by_coords")
            print(f"[NASA/Direct] Downloaded {len(files)} files: {ds.dims}")
            return ds
        except ImportError:
            # earthaccess not installed — use raw OPeNDAP with session auth
            session = requests.Session()
            session.auth = (NASA_USERNAME, NASA_PASSWORD)
            # NASA Earthdata requires URS redirect authentication
            auth_url = "https://urs.earthdata.nasa.gov"
            session.get(auth_url)  # Establish auth cookies
            print("[NASA/Direct] earthaccess not installed. "
                  "Install with: pip install earthaccess")
            raise
    def fetch_latest(
        self,
        n_months: int = 3,
        lat_min: float = 0.0,
        lat_max: float = 25.0,
        lon_min: float = 65.0,
        lon_max: float = 90.0,
    ) -> xr.Dataset:
        """Fetch the most recent N months of chlorophyll data."""
        end = datetime.utcnow()
        start = end - timedelta(days=n_months * 30)
        return self.fetch(
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
            lat_min, lat_max, lon_min, lon_max,
        )
    def chlor_to_nutrient_proxy(self, ds: xr.Dataset) -> xr.DataArray:
        """
        Convert chlorophyll-a → nutrient load proxy (N for RM-NPI).
        Scaling: log10(chlor_a) normalized to 0-1
        Low chlorophyll (~0.01 mg/m³) → N ≈ 0 (oligotrophic)
        High chlorophyll (~10 mg/m³)  → N ≈ 1 (eutrophic/runoff)
        """
        var_name = "chlorophyll" if "chlorophyll" in ds else "chlor_a"
        chlor = ds[var_name]
        log_chlor = np.log10(chlor.clip(min=0.01))
        # Normalize: log10(0.01)=-2 → 0, log10(10)=1 → 1
        N = (log_chlor - (-2)) / (1 - (-2))
        return N.clip(0, 1)
