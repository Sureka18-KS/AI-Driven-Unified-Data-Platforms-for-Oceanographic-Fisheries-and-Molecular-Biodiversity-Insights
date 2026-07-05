# Copernicus Marine Service -- Primary Ocean Data Source
# Direct access via CMEMS OPeNDAP + copernicusmarine package
#
# HOW TO GET YOUR API KEY (works for ALL account types including Google SSO):
#   1. Go to: https://data.marine.copernicus.eu
#   2. Login (email, Google, or any SSO)
#   3. Click your profile -> "My Account" -> "API Key" tab
#   4. Copy the API token shown
#   5. Set in .env:
#        COPERNICUS_API_KEY=your_token_here
#      (OR use username+password if you set one in "Change Password")
#
# Install: pip install copernicusmarine requests xarray netCDF4

import os
import xarray as xr
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

COPERNICUS_USER    = os.getenv("COPERNICUS_USERNAME", "")
COPERNICUS_PASS    = os.getenv("COPERNICUS_PASSWORD", "")
COPERNICUS_API_KEY = os.getenv("COPERNICUS_API_KEY", "")

# NOAA ERDDAP fallback (public, no auth needed)
ERDDAP_BASE    = "https://coastwatch.pfeg.noaa.gov/erddap"
ERDDAP_LAG_DAYS = 5


class CopernicusFetcher:
    """
    Primary ocean data source: Copernicus Marine Service.

    AUTH OPTIONS (try in this order):
        1. API Key  -> set COPERNICUS_API_KEY in .env (works with Google SSO accounts)
        2. Username + Password -> set COPERNICUS_USERNAME + COPERNICUS_PASSWORD in .env
        3. Auto ERDDAP fallback -> if both fail, fetches real SST+Chl from NOAA ERDDAP

    Variables fetched (when Copernicus is available):
        Physics: thetao (SST), so (salinity), uo/vo (currents), zos (sea level)
        BGC:     no3 (nitrate -> nutrient N), po4, o2, chl
    """

    PHY_DATASET = "cmems_mod_glo_phy_my_0.083deg_P1D-m"
    PHY_VARS    = ["thetao", "so", "uo", "vo", "zos"]
    BGC_DATASET = "cmems_mod_glo_bgc_my_0.25deg_P1M-m"
    BGC_VARS    = ["no3", "po4", "o2", "chl"]

    ERDDAP_SST_ID = "ncdcOisst21Agg_LonPM180"
    ERDDAP_CHL_ID = "erdVH2018chla8day"

    def __init__(self, output_dir: str = "data/raw/copernicus"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #

    def fetch(
        self,
        start_date: str,
        end_date: str,
        lat_min: float = 5.0,
        lat_max: float = 20.0,
        lon_min: float = 70.0,
        lon_max: float = 85.0,
        depth_max: float = 5.49,
    ) -> xr.Dataset:
        """
        Tries Copernicus (API key, then user+pass), falls back to ERDDAP.
        """
        # -- Try API key first (works for Google SSO accounts) --
        if COPERNICUS_API_KEY:
            try:
                return self._fetch_with_api_key(
                    start_date, end_date,
                    lat_min, lat_max, lon_min, lon_max, depth_max,
                )
            except Exception as e:
                print(f"  [!] Copernicus API key fetch failed: {e}")

        # -- Try username + password --
        if COPERNICUS_USER and COPERNICUS_PASS:
            try:
                return self._fetch_with_password(
                    start_date, end_date,
                    lat_min, lat_max, lon_min, lon_max, depth_max,
                )
            except Exception as e:
                err_str = str(e)
                if "InvalidUsernameOrPassword" in err_str or "Invalid credentials" in err_str:
                    print(f"  [!] Copernicus credentials rejected.")
                    print(f"      Your account likely uses Google/SSO login.")
                    print(f"      FIX: Get an API token at https://data.marine.copernicus.eu")
                    print(f"           Profile -> My Account -> API Key")
                    print(f"           Then set COPERNICUS_API_KEY=<token> in .env")
                else:
                    print(f"  [!] Copernicus fetch failed: {e}")
                print(f"  [>] Using NOAA ERDDAP fallback for real ocean data...")

        else:
            print("  [i] No Copernicus credentials. Using NOAA ERDDAP for real ocean data.")

        return self._fetch_erddap_fallback(
            start_date, end_date,
            lat_min, lat_max, lon_min, lon_max,
        )

    # ------------------------------------------------------------------ #
    # Auth method 1: API Key
    # ------------------------------------------------------------------ #

    def _fetch_with_api_key(
        self,
        start_date, end_date,
        lat_min, lat_max, lon_min, lon_max, depth_max,
    ) -> xr.Dataset:
        """Use COPERNICUS_API_KEY to authenticate (works for Google SSO accounts)."""
        try:
            import copernicusmarine
        except ImportError:
            raise ImportError("Run: pip install copernicusmarine")

        # Set API key via env var (copernicusmarine reads this automatically)
        os.environ["COPERNICUSMARINE_SERVICE_USERNAME"] = COPERNICUS_API_KEY
        os.environ["COPERNICUSMARINE_SERVICE_PASSWORD"] = COPERNICUS_API_KEY

        print(f"[Copernicus/API-Key] Fetching PHY: {', '.join(self.PHY_VARS)}")
        print(f"  Period: {start_date} to {end_date}")

        phy_path = self.output_dir / f"phy_{start_date}_{end_date}.nc"
        if phy_path.exists():
            print(f"  [cache] {phy_path.name}")
            ds = xr.open_dataset(phy_path)
        else:
            ds = copernicusmarine.open_dataset(
                dataset_id=self.PHY_DATASET,
                variables=self.PHY_VARS,
                minimum_longitude=lon_min,  maximum_longitude=lon_max,
                minimum_latitude=lat_min,   maximum_latitude=lat_max,
                start_datetime=f"{start_date}T00:00:00",
                end_datetime=f"{end_date}T23:59:59",
                minimum_depth=0.495,          maximum_depth=depth_max,
            )
            if "depth" in ds.dims:
                ds = ds.isel(depth=0, drop=True)
            ds = ds.load()   # force full load into memory before saving
            ds.to_netcdf(phy_path)
            print(f"  [OK] PHY: {dict(ds.dims)}")

        return self._add_bgc(ds, start_date, end_date,
                             lat_min, lat_max, lon_min, lon_max, depth_max)

    # ------------------------------------------------------------------ #
    # Auth method 2: Username + Password
    # ------------------------------------------------------------------ #

    def _fetch_with_password(
        self,
        start_date, end_date,
        lat_min, lat_max, lon_min, lon_max, depth_max,
    ) -> xr.Dataset:
        try:
            import copernicusmarine
        except ImportError:
            raise ImportError("Run: pip install copernicusmarine")

        os.environ["COPERNICUSMARINE_SERVICE_USERNAME"] = COPERNICUS_USER
        os.environ["COPERNICUSMARINE_SERVICE_PASSWORD"] = COPERNICUS_PASS

        logged_in = copernicusmarine.login(
            username=COPERNICUS_USER,
            password=COPERNICUS_PASS,
            force_overwrite=True,
            check_credentials_valid=True,
        )
        if not logged_in:
            raise ValueError("InvalidUsernameOrPassword")

        print(f"[Copernicus/Password] Logged in as: {COPERNICUS_USER}")

        phy_path = self.output_dir / f"phy_{start_date}_{end_date}.nc"
        if phy_path.exists():
            print(f"  [cache] {phy_path.name}")
            ds = xr.open_dataset(phy_path)
        else:
            print(f"  Fetching PHY: {', '.join(self.PHY_VARS)}")
            ds = copernicusmarine.open_dataset(
                dataset_id=self.PHY_DATASET,
                variables=self.PHY_VARS,
                minimum_longitude=lon_min,  maximum_longitude=lon_max,
                minimum_latitude=lat_min,   maximum_latitude=lat_max,
                start_datetime=f"{start_date}T00:00:00",
                end_datetime=f"{end_date}T23:59:59",
                minimum_depth=0.495,          maximum_depth=depth_max,
                username=COPERNICUS_USER,   password=COPERNICUS_PASS,
            )
            if "depth" in ds.dims:
                ds = ds.isel(depth=0, drop=True)
            ds = ds.load()   # force full load into memory before saving
            ds.to_netcdf(phy_path)
            print(f"  [OK] PHY: {dict(ds.dims)}")

        return self._add_bgc(ds, start_date, end_date,
                             lat_min, lat_max, lon_min, lon_max, depth_max,
                             username=COPERNICUS_USER, password=COPERNICUS_PASS)

    # ------------------------------------------------------------------ #
    # BGC (optional layer, appended to PHY result)
    # ------------------------------------------------------------------ #

    def _add_bgc(self, ds_phy, start_date, end_date,
                 lat_min, lat_max, lon_min, lon_max, depth_max,
                 username=None, password=None) -> xr.Dataset:
        try:
            import copernicusmarine
            bgc_path = self.output_dir / f"bgc_{start_date}_{end_date}.nc"
            if bgc_path.exists():
                ds_bgc = xr.open_dataset(bgc_path)
            else:
                kw = {}
                if username:
                    kw["username"] = username
                    kw["password"] = password
                ds_bgc = copernicusmarine.open_dataset(
                    dataset_id=self.BGC_DATASET,
                    variables=self.BGC_VARS,
                    minimum_longitude=lon_min,  maximum_longitude=lon_max,
                    minimum_latitude=lat_min,   maximum_latitude=lat_max,
                    start_datetime=f"{start_date}T00:00:00",
                    end_datetime=f"{end_date}T23:59:59",
                    minimum_depth=0.495,          maximum_depth=depth_max,
                    **kw,
                )
                if "depth" in ds_bgc.dims:
                    ds_bgc = ds_bgc.isel(depth=0, drop=True)
                ds_bgc = ds_bgc.load()   # force load before save
                ds_bgc.to_netcdf(bgc_path)
                print(f"  [OK] BGC: {dict(ds_bgc.dims)}")

            ds_bgc_r = ds_bgc.interp(
                latitude=ds_phy.latitude, longitude=ds_phy.longitude, method="nearest"
            )
            return xr.merge([ds_phy, ds_bgc_r], join="left")
        except Exception as e:
            print(f"  [!] BGC optional, skipping: {e}")
            return ds_phy

    # ------------------------------------------------------------------ #
    # Fallback: NOAA ERDDAP (public, no auth)
    # ------------------------------------------------------------------ #

    def _fetch_erddap_fallback(
        self,
        start_date, end_date,
        lat_min, lat_max, lon_min, lon_max,
    ) -> xr.Dataset:
        today    = datetime.utcnow()
        safe_end = min(today - timedelta(days=ERDDAP_LAG_DAYS),
                       datetime.strptime(end_date, "%Y-%m-%d"))
        eff_end  = safe_end.strftime("%Y-%m-%d")

        print(f"  [ERDDAP fallback] SST from NOAA: {start_date} to {eff_end}")

        sst_path = self.output_dir / f"erddap_sst_{start_date}_{eff_end}.nc"
        if sst_path.exists():
            print(f"  [cache] {sst_path.name}")
            ds_sst = xr.open_dataset(sst_path)
        else:
            url = (
                f"{ERDDAP_BASE}/griddap/{self.ERDDAP_SST_ID}.nc?"
                f"sst,anom"
                f"[({start_date}T00:00:00Z):1:({eff_end}T00:00:00Z)]"
                f"[({lat_min}):1:({lat_max})]"
                f"[({lon_min}):1:({lon_max})]"
            )
            resp = requests.get(url, stream=True, timeout=180)
            resp.raise_for_status()
            with open(sst_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
            ds_sst = xr.open_dataset(sst_path)
            print(f"  [OK] ERDDAP SST: {dict(ds_sst.dims)}")

        if "sst" in ds_sst and "thetao" not in ds_sst:
            ds_sst = ds_sst.rename({"sst": "thetao"})

        # Chlorophyll via ERDDAP
        chl_path = self.output_dir / f"erddap_chl_{start_date}_{eff_end}.nc"
        if chl_path.exists():
            print(f"  [cache] {chl_path.name}")
            try:
                ds_chl = xr.open_dataset(chl_path)
                merged = xr.merge([ds_sst, ds_chl], join="outer", compat="override")
                return merged
            except Exception:
                return ds_sst
        else:
            chl_url = (
                f"{ERDDAP_BASE}/griddap/{self.ERDDAP_CHL_ID}.nc?"
                f"chla"
                f"[({start_date}T00:00:00Z):1:({eff_end}T00:00:00Z)]"
                f"[({lat_min}):1:({lat_max})]"
                f"[({lon_min}):1:({lon_max})]"
            )
            try:
                resp = requests.get(chl_url, stream=True, timeout=180)
                resp.raise_for_status()
                with open(chl_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        f.write(chunk)
                ds_chl = xr.open_dataset(chl_path)
                if "chla" in ds_chl and "chl" not in ds_chl:
                    ds_chl = ds_chl.rename({"chla": "chl"})
                print(f"  [OK] ERDDAP Chl: {dict(ds_chl.dims)}")
                return xr.merge([ds_sst, ds_chl], join="outer", compat="override")
            except Exception as e:
                print(f"  [!] ERDDAP Chl optional: {e}")
                return ds_sst

    # ------------------------------------------------------------------ #
    # DataFrame conversion
    # ------------------------------------------------------------------ #

    def to_dataframe(self, ds: xr.Dataset) -> pd.DataFrame:
        if "depth" in ds.dims:
            ds = ds.isel(depth=0, drop=True)

        df = ds.to_dataframe().reset_index()

        rename = {}
        for c in df.columns:
            cl = c.lower()
            if cl == "latitude"  and "lat" not in df.columns:
                rename[c] = "lat"
            elif cl == "longitude" and "lon" not in df.columns:
                rename[c] = "lon"
        df = df.rename(columns=rename)

        if "uo" in df.columns and "vo" in df.columns:
            df["current_speed"] = np.sqrt(df["uo"]**2 + df["vo"]**2)

        if "no3" in df.columns:
            no3_max = df["no3"].quantile(0.99) + 1e-8
            df["nutrient_proxy"] = (df["no3"] / no3_max).clip(0, 1)

        if "chl" in df.columns:
            chl_log = np.log10(df["chl"].clip(lower=0.01))
            df["chl_proxy"] = ((chl_log - (-2)) / 3).clip(0, 1)
            if "nutrient_proxy" not in df.columns:
                df["nutrient_proxy"] = df["chl_proxy"]

        return df.dropna(subset=["lat", "lon"])

    def fetch_latest(self, n_days=90, lat_min=5.0, lat_max=20.0,
                     lon_min=70.0, lon_max=85.0) -> xr.Dataset:
        end   = datetime.utcnow() - timedelta(days=ERDDAP_LAG_DAYS)
        start = end - timedelta(days=n_days)
        return self.fetch(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"),
                          lat_min, lat_max, lon_min, lon_max)
