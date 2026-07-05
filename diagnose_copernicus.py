# Copernicus Diagnostic Script (Updated June 2026)
# Runs in isolation to capture the FULL error from copernicusmarine
# Run with: venv\Scripts\python.exe diagnose_copernicus.py

import os
import sys
import traceback

# Force-load .env directly so VSCode terminal injection not needed
from pathlib import Path

env_path = Path(__file__).parent / ".env"
print(f"[1] Loading .env from: {env_path}")
if not env_path.exists():
    print("    ERROR: .env file not found!")
    sys.exit(1)

with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ[key.strip()] = val.strip()

USER = os.environ.get("COPERNICUS_USERNAME", "")
PASS = os.environ.get("COPERNICUS_PASSWORD", "")

print(f"[2] Credentials loaded:")
print(f"    USERNAME = {USER}")
print(f"    PASSWORD = {'*' * len(PASS)} ({len(PASS)} chars)")

if not USER or not PASS:
    print("    ERROR: Credentials not found in .env!")
    sys.exit(1)

print("\n[3] Importing copernicusmarine...")
try:
    import copernicusmarine
    print(f"    Version: {copernicusmarine.__version__}")
except ImportError as e:
    print(f"    ERROR: {e}")
    print("    Fix: venv\\Scripts\\pip install copernicusmarine")
    sys.exit(1)

print("\n[4] Testing login...")
try:
    ok = copernicusmarine.login(
        username=USER,
        password=PASS,
        force_overwrite=True,
        check_credentials_valid=True,
    )
    print(f"    login() returned: {ok}")
    if not ok:
        print("\n    DIAGNOSIS: Credentials rejected by Copernicus server.")
        print("    Possible causes:")
        print("    a) Wrong email  -> double-check at https://data.marine.copernicus.eu")
        print("    b) Wrong password -> try resetting at the portal")
        print("    c) Account not email-verified -> check your inbox")
        print("    d) Account uses OIDC/SSO (Google login) -> won't work with password auth")
except Exception as e:
    print(f"    EXCEPTION during login: {e}")
    traceback.print_exc()

print("\n[5] Attempting open_dataset WITH full error traceback...")
try:
    ds = copernicusmarine.open_dataset(
        dataset_id="cmems_mod_glo_phy_my_0.083deg_P1D-m",
        variables=["thetao"],
        minimum_longitude=70.0,
        maximum_longitude=72.0,
        minimum_latitude=10.0,
        maximum_latitude=12.0,
        start_datetime="2024-06-01T00:00:00",
        end_datetime="2024-06-03T00:00:00",
        minimum_depth=0.0,
        maximum_depth=1.0,
        username=USER,
        password=PASS,
    )
    print(f"\n    SUCCESS! Dataset fetched: {dict(ds.dims)}")
    print(f"    Variables: {list(ds.data_vars)}")
    print(f"    SST range: {float(ds['thetao'].min()):.2f} to {float(ds['thetao'].max()):.2f} C")
except Exception as e:
    print(f"\n    FULL ERROR from open_dataset:")
    print(f"    Type: {type(e).__name__}")
    print(f"    Message: {e}")
    print("\n    Full traceback:")
    traceback.print_exc()

print("\n[6] Diagnosis complete.")
