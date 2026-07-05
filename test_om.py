import requests
import pandas as pd
import numpy as np
import xarray as xr

lat_min, lat_max, resolution = 5.0, 10.0, 1.0
lon_min, lon_max = 70.0, 75.0
start_date, end_date = "2023-01-01", "2023-02-28"

lats = np.arange(lat_min, lat_max + resolution, resolution)
lons = np.arange(lon_min, lon_max + resolution, resolution)
grid_points = [(lat, lon) for lat in lats for lon in lons]

chunk_size = 90
url = "https://archive-api.open-meteo.com/v1/archive"

print(f"Total points: {len(grid_points)}")
all_data = []

chunk = grid_points[:chunk_size]
chunk_lats = [p[0] for p in chunk]
chunk_lons = [p[1] for p in chunk]

params = {
    "latitude": chunk_lats,
    "longitude": chunk_lons,
    "start_date": start_date,
    "end_date": end_date,
    "daily": "precipitation_sum",
    "timezone": "GMT"
}

response = requests.get(url, params=params)
print(response.status_code)
data = response.json()

if isinstance(data, list):
    for j, loc_data in enumerate(data):
        lat = chunk_lats[j]
        lon = chunk_lons[j]
        df = pd.DataFrame(loc_data["daily"])
        df["lat"] = lat
        df["lon"] = lon
        all_data.append(df)
else:
    print("Not a list!")
    print(data.keys() if isinstance(data, dict) else "Unknown")
    
if all_data:
    df = pd.concat(all_data)
    print(df.head())
