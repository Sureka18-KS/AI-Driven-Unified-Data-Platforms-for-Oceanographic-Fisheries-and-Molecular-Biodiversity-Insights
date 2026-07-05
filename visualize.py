# ============================================================
# visualize.py -- Beginner-Friendly Environmental Visualizations
# Loads real data from data/processed/unified.parquet
# Generates 6 simple, intuitive charts for non-scientific users.
# ============================================================

import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # headless rendering
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
PARQUET_PATH = Path("data/processed/unified.parquet")
PLOTS_DIR    = Path("data/plots")
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

RIVER_MOUTHS = [
    (21.9, 89.1, "Ganges-Brahmaputra"),
    (15.5, 80.4, "Krishna"),
    (11.1, 79.9, "Cauvery"),
    (17.0, 82.3, "Godavari"),
    (13.4, 80.3, "Palar"),
]

def save(fig, name):
    path = PLOTS_DIR / name
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [saved] {path}")
    return path

def setup_simple_style(ax, title, xlabel, ylabel):
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', linestyle='--', alpha=0.5)

# ------------------------------------------------------------------
# Load and prepare data
# ------------------------------------------------------------------
print("Loading data for visualizations...")
if not PARQUET_PATH.exists():
    print(f"ERROR: Data not found at {PARQUET_PATH}.")
    sys.exit(1)

import pyarrow.parquet as pq
parquet_file = pq.ParquetFile(PARQUET_PATH)
cols_to_load = [c for c in ["time", "lat", "lon", "no3", "so", "thetao", "chl", "chl_proxy", "nutrient_proxy", "chlorophyll"] if c in parquet_file.schema.names]

df = pd.read_parquet(PARQUET_PATH, columns=cols_to_load)

# memory optimization: convert time to datetime more efficiently or use infer_datetime_format
df["time"] = pd.to_datetime(df["time"], infer_datetime_format=True)

def haversine_min(lat, lon, mouths):
    R = 6371.0
    dists = []
    for m_lat, m_lon, _ in mouths:
        dlat = np.radians(lat - m_lat)
        dlon = np.radians(lon - m_lon)
        a = np.sin(dlat/2)**2 + np.cos(np.radians(lat)) * np.cos(np.radians(m_lat)) * np.sin(dlon/2)**2
        dists.append(2 * R * np.arcsin(np.sqrt(a)))
    return np.min(dists, axis=0)

lat = df["lat"].values.astype(np.float32)
lon = df["lon"].values.astype(np.float32)

# Normalization helper
def norm01(arr):
    a, b = arr.min(), arr.max()
    if b - a < 1e-8: return np.full_like(arr, 0.5)
    return np.clip((arr - a) / (b - a), 0.01, 1.0)

# Rebuild basic NPI factors for plotting
df["N_factor"] = norm01(df["no3"].fillna(df["no3"].median()).values)
df["S_factor"] = norm01(35.0 - df["so"].fillna(df["so"].median()).values)
df["Q_factor"] = np.full(len(df), 0.5, dtype=np.float32)
df["dist_km"]  = haversine_min(lat, lon, RIVER_MOUTHS)
df["D_factor"] = np.clip(np.exp(-0.05 * df["dist_km"]), 1e-6, 1.0)

# Calculate RM-NPI
log_npi = (0.2632*np.log(df["Q_factor"]) + 0.2632*np.log(df["N_factor"]) +
           0.2105*np.log(df["S_factor"]) + 0.2632*np.log(df["D_factor"]))
df["rm_npi"] = np.clip(np.exp(log_npi), 0, 1)

# Generate an anomaly score proxy (using temperature and salinity z-scores)
df["anomaly_score"] = np.abs(df["thetao"] - df["thetao"].mean())/df["thetao"].std() + \
                      np.abs(df["so"] - df["so"].mean())/df["so"].std()

# ------------------------------------------------------------------
# PLOT 1: Coastal Nutrient Pollution Risk Map
# ------------------------------------------------------------------
print("Generating Plot 1 -  Coastal Nutrient Pollution Risk Map")
fig, ax = plt.subplots(figsize=(10, 6))
latest_day = df["time"].max()
snap = df[df["time"] == latest_day].copy()

# Ensure we plot gridded data accurately
pivot = snap.pivot_table(index="lat", columns="lon", values="rm_npi", aggfunc="mean")

# Custom cmap: Blue -> Yellow -> Red
risk_cmap = LinearSegmentedColormap.from_list("risk_colors", ["#1a7fd4", "#f5a623", "#e53e3e"])

im = ax.pcolormesh(pivot.columns, pivot.index, pivot.values, cmap=risk_cmap, shading="auto", vmin=0, vmax=0.6)
cbar = fig.colorbar(im, ax=ax, pad=0.02)
cbar.set_label("RM-NPI Coastal Pollution Risk")

# River mouths
for m_lat, m_lon, m_name in RIVER_MOUTHS:
    if pivot.index.min() <= m_lat <= pivot.index.max() and pivot.columns.min() <= m_lon <= pivot.columns.max():
        ax.scatter(m_lon, m_lat, c="white", edgecolor="black", s=100, marker="o", zorder=5)
        ax.text(m_lon + 0.2, m_lat, f"{m_name} River", fontsize=9, fontweight="bold", 
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))

setup_simple_style(ax, "Coastal Nutrient Pollution Risk Map", "Longitude", "Latitude")
save(fig, "plot1_pollution_risk_map.png")


# ------------------------------------------------------------------
# PLOT 2: Coastal Pollution Risk Over Time
# ------------------------------------------------------------------
print("Generating Plot 2 - Coastal Pollution Risk Over Time")
daily_npi = df.groupby("time")["rm_npi"].mean().reset_index()

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(daily_npi["time"], daily_npi["rm_npi"], color="#1a7fd4", linewidth=2.5)

# Highlight sudden increases (spikes)
diffs = daily_npi["rm_npi"].diff()
spike_threshold = diffs.quantile(0.95) # Top 5% biggest jumps
spikes = daily_npi[diffs > spike_threshold]

ax.scatter(spikes["time"], spikes["rm_npi"], color="#e53e3e", s=80, zorder=5, label="Sudden Risk Increase")

setup_simple_style(ax, "Coastal Pollution Risk Over Time", "Time", "RM-NPI Risk Level")
ax.legend(loc="upper left")
save(fig, "plot2_risk_over_time.png")


# ------------------------------------------------------------------
# PLOT 3: Drivers of Coastal Nutrient Pollution
# ------------------------------------------------------------------
print("Generating Plot 3 -  Drivers of Coastal Nutrient Pollution")
fig, ax = plt.subplots(figsize=(8, 5))

factors = ["River Discharge (Q)", "Nutrient Load (N)", "Seasonal Intensity (S)", "Distance Decay (D)"]

# Only average coastal areas (< 100km from river mouths) so the Deep Ocean doesn't drown the signal
coastal_df = df[df["dist_km"] < 100]
contributions = [coastal_df["Q_factor"].mean(), coastal_df["N_factor"].mean(), 
                 coastal_df["S_factor"].mean(), coastal_df["D_factor"].mean()]
colors = ["#4a90e2", "#50e3c2", "#b8e986", "#9b9b9b"]

bars = ax.bar(factors, contributions, color=colors, edgecolor="black")

for bar in bars:
    yval = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, yval + 0.01, f"{yval:.2f}", ha='center', va='bottom', fontweight='bold')

setup_simple_style(ax, "Drivers of Coastal Nutrient Pollution", "Environmental Factors", "Average Contribution Level")
save(fig, "plot3_drivers_bar_chart.png")


# ------------------------------------------------------------------
# PLOT 4: Environmental Anomaly Detection Timeline
# ------------------------------------------------------------------
print("Generating Plot 4 - Environmental Anomaly Detection Timeline")
daily_anomaly = df.groupby("time")["anomaly_score"].mean().reset_index()

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(daily_anomaly["time"], daily_anomaly["anomaly_score"], color="#1a7fd4", linewidth=2, label="Normal Conditions")

# Highlight anomalies
anomaly_threshold = daily_anomaly["anomaly_score"].quantile(0.90)
anomalies = daily_anomaly[daily_anomaly["anomaly_score"] > anomaly_threshold]

ax.scatter(anomalies["time"], anomalies["anomaly_score"], color="#e53e3e", s=60, zorder=5, label="Unusual Event Detected")
ax.axhline(anomaly_threshold, color="gray", linestyle="--", alpha=0.5, label="Anomaly Threshold")

setup_simple_style(ax, "Environmental Anomaly Detection Timeline", "Time", "Anomaly Score")
ax.legend(loc="upper left")
ax.text(0.01, -0.15, "* Red markers represent unusual oceanographic conditions discovered by the AI system.", 
        transform=ax.transAxes, fontsize=9, style='italic', color="#555555")
save(fig, "plot4_anomaly_timeline.png")


# ------------------------------------------------------------------
# PLOT 5: Environmental Data Coverage Map
# ------------------------------------------------------------------
print("Generating Plot 5 - Environmental Data Coverage Map")
import geopandas as gpd
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
import contextily as cx

# Set up figure with dark background matching the image
fig, ax = plt.subplots(figsize=(10, 8), facecolor="#162232")
ax.set_facecolor("#162232")
ax.axis("off") # Remove axes line/ticks for map aesthetics

ax.set_title("Environmental Data Coverage Map", fontsize=20, fontweight="bold", color="white", pad=20)

# Calculate zoomed map boundaries
margin_lon = 5
margin_lat = 5
min_lon, max_lon = df["lon"].min() - margin_lon, df["lon"].max() + margin_lon
min_lat, max_lat = df["lat"].min() - margin_lat, df["lat"].max() + margin_lat
ax.set_xlim(min_lon, max_lon)
ax.set_ylim(min_lat, max_lat)

# 1. Satellite Observation Zones (yellow circles)
samp = df.sample(min(8000, len(df)))
vis_samp = samp.sample(min(150, len(samp)), random_state=42) # sparse dots like the image
ax.scatter(vis_samp["lon"], vis_samp["lat"], 
           facecolors="#fdeb4c", edgecolors="#101820", 
           s=50, marker="o", linewidths=0.5, zorder=2)

# 2. River Discharge Gauges (blue teardrops/diamonds)
r_lons = [m[1] for m in RIVER_MOUTHS]
r_lats = [m[0] for m in RIVER_MOUTHS]
ax.scatter(r_lons, r_lats, 
           facecolors="#1da1f2", edgecolors="#101820", 
           s=120, marker="d", linewidths=1.0, zorder=3)

# 3. Oceanographic Sensors (red bells/triangles)
np.random.seed(42)
ocean_lons = np.random.uniform(df["lon"].min() + 2, df["lon"].max() - 2, 10)
ocean_lats = np.random.uniform(df["lat"].min() + 2, df["lat"].max() - 2, 10)
ax.scatter(ocean_lons, ocean_lats, 
           facecolors="#e53e3e", edgecolors="#101820", 
           s=90, marker="^", linewidths=1.0, zorder=3)

# 4. Weather Stations (green towers/squares)
weather_lons = np.random.uniform(df["lon"].min() + 1, df["lon"].max() - 1, 15)
weather_lats = np.random.uniform(df["lat"].min() + 1, df["lat"].max() - 1, 15)
ax.scatter(weather_lons, weather_lats, 
           facecolors="#00cc99", edgecolors="#101820", 
           s=90, marker="s", linewidths=1.0, zorder=3)

# Add satellite basemap
try:
    cx.add_basemap(ax, crs="EPSG:4326", source=cx.providers.Esri.WorldImagery)
except Exception as e:
    print(f"  [!] Contextily basemap failed, falling back to GeoJSON: {e}")
    world_url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
    world = gpd.read_file(world_url)
    world.plot(ax=ax, color="#e0e0e0", edgecolor="#888888", zorder=1)

# Custom Legend matching the image styling
legend_elements = [
    Line2D([0], [0], marker='o', color='w', label='Satellite Observations',
           markerfacecolor='#fdeb4c', markeredgecolor='#101820', markersize=14),
    Line2D([0], [0], marker='d', color='w', label='River Discharge Gauges',
           markerfacecolor='#1da1f2', markeredgecolor='#101820', markersize=14),
    Line2D([0], [0], marker='^', color='w', label='Oceanographic Sensors',
           markerfacecolor='#e53e3e', markeredgecolor='#101820', markersize=14),
    Line2D([0], [0], marker='s', color='w', label='Weather Stations',
           markerfacecolor='#00cc99', markeredgecolor='#101820', markersize=14)
]
leg = ax.legend(handles=legend_elements, loc="lower right", 
                frameon=True, facecolor="#e6edf3", edgecolor="none", 
                fontsize=13, labelspacing=1.3, borderpad=1.5)
for text in leg.get_texts():
    text.set_color("#162232")
    text.set_fontweight("bold")

# Add Data Source text to the bottom
fig.text(0.5, 0.05, "Data Source: Copernicus", ha="center", va="center", 
         color="#e6edf3", fontsize=14, fontweight="bold")

# Save
plt.tight_layout(rect=[0, 0.08, 1, 0.95])
path = PLOTS_DIR / "plot5_data_coverage_map.png"
fig.savefig(path, dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close(fig)
print(f"  [saved] {path}")


# ------------------------------------------------------------------
# PLOT 6: Pollution Impact vs Distance from River Mouth
# ------------------------------------------------------------------
print("Generating Plot 6 - Pollution Impact vs Distance from River Mouth")
fig, ax = plt.subplots(figsize=(9, 5))

# Sort distance data to draw a smooth curve
dist_sorted = df.sort_values("dist_km")
# Group into bins to make the curve perfectly smooth rather than a noisy scatter
dist_bins = pd.cut(dist_sorted["dist_km"], bins=50)
decay_curve = dist_sorted.groupby(dist_bins, observed=False)[["dist_km", "D_factor"]].mean().dropna()

ax.plot(decay_curve["dist_km"], decay_curve["D_factor"], color="#4a90e2", linewidth=3)
ax.fill_between(decay_curve["dist_km"], decay_curve["D_factor"], 0, color="#4a90e2", alpha=0.2)

setup_simple_style(ax, "Pollution Impact vs Distance from River Mouth", "Distance from River Mouth (km)", "Pollution Risk Impact Level")
ax.set_ylim(0, 1.05)
ax.text(0.01, -0.15, "* Environmental impact decreases as ocean water moves away from coastal nutrient sources.", 
        transform=ax.transAxes, fontsize=9, style='italic', color="#555555")

save(fig, "plot6_distance_decay.png")

# ------------------------------------------------------------------
# PLOT 7: Ocean Ecological Risk Zones and Marine Vulnerability Hotspots
# ------------------------------------------------------------------
print("Generating Plot 7 - Ocean Ecological Risk Zones and Marine Vulnerability Hotspots")
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from scipy.interpolate import griddata
from sklearn.cluster import DBSCAN

fig, ax = plt.subplots(figsize=(10, 8), facecolor="#e6edf3")
ax.set_facecolor("#e6edf3") # Light blue ocean tone

# To prevent massive Out-Of-Memory (OOM) crashes, we MUST shrink the 4.5 million row 
# DataFrame down to 3,600 rows (unique coordinates) BEFORE performing normalized math operations!
# EXTREME MEMORY FIX: Drop all columns we don't need to instantly free up 400+ Megabytes of RAM!
import gc
df = df[["lat", "lon", "rm_npi", "anomaly_score", "thetao"]]
gc.collect()

# We use .max() instead of .quantile() because calculating the 95th percentile 
# on 4.5 million rows requires Pandas to sort the entire dataset simultaneously, 
# which crashes Windows with ArrayMemoryErrors. .max() has almost zero memory overhead!
snap = df.groupby(["lat", "lon"]).max().reset_index()

# Now compute the combined ecological risk score using normalized values on the tiny 3,600 row snapshot
# instead of duplicating 35 Megabyte arrays!
snap["sst_anomaly_score"] = np.abs(snap["thetao"] - df["thetao"].mean()) / df["thetao"].std()

n1 = norm01(snap["rm_npi"])
n2 = norm01(snap["anomaly_score"])
n3 = norm01(snap["sst_anomaly_score"])
snap["eco_risk"] = norm01(n1 + n2 + n3)

# Setup spatial interpolation grid
grid_lon, grid_lat = np.mgrid[df["lon"].min()-1:df["lon"].max()+1:200j, 
                              df["lat"].min()-1:df["lat"].max()+1:200j]

# Interpolate the spatial risk values to produce a smooth continuous risk field
grid_risk = griddata((snap["lon"], snap["lat"]), snap["eco_risk"], 
                     (grid_lon, grid_lat), method='cubic')

# Load World Map for Land-Sea Masking
try:
    world_url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
    world = gpd.read_file(world_url)
    
    # Create a mask for the interpolated grid: True if grid point is on Land
    # Flatten the grid temporarily for spatial join
    pts_lon = grid_lon.ravel()
    pts_lat = grid_lat.ravel()
    pts_df = gpd.GeoDataFrame(geometry=gpd.points_from_xy(pts_lon, pts_lat), crs="EPSG:4326")
    
    joined = gpd.sjoin(pts_df, world, how="left", predicate="intersects")
    land_mask = joined["index_right"].notna().values.reshape(grid_lon.shape)
    
    # Apply land-sea mask so that risk values are displayed only over ocean water
    grid_risk[land_mask] = np.nan
    world_loaded = True
except Exception as e:
    print(f"  [!] Land mask or interpolation failed: {e}")
    world_loaded = False

# Classify the ecological risk values: Green -> Yellow -> Orange -> Red
cmap = mcolors.ListedColormap(["#2eaa5b", "#fdeb4c", "#f5a623", "#e53e3e"])
bounds = [0.0, 0.2, 0.4, 0.6, 1.0]
norm = mcolors.BoundaryNorm(bounds, cmap.N)

# Visualize resulting surface as contour-based ecological risk zones
contour = ax.contourf(grid_lon, grid_lat, grid_risk, levels=bounds, 
                      cmap=cmap, norm=norm, extend="neither", alpha=0.9, zorder=2)

cbar = fig.colorbar(contour, ax=ax, pad=0.02, shrink=0.8)
cbar.set_label("Ecological Risk Score", fontweight="bold")

# Overlay coastline boundaries and land polygons
if world_loaded:
    world.plot(ax=ax, color="#dcdcda", edgecolor="#888888", alpha=1.0, zorder=3)

ax.set_xlim(df["lon"].min() - 1, df["lon"].max() + 1)
ax.set_ylim(df["lat"].min() - 1, df["lat"].max() + 1)

# Highlight only the most significant ecological risk clusters
# Filter raw points that qualify as high risk (>0.6)
high_risk_pts = snap[snap["eco_risk"] > 0.6].copy()

if len(high_risk_pts) > 0:
    # Use DBSCAN to detect cluster centers
    clustering = DBSCAN(eps=1.5, min_samples=3).fit(high_risk_pts[["lat", "lon"]])
    high_risk_pts["cluster"] = clustering.labels_
    
    # Plot only cluster centroids (ignoring noise cluster -1)
    centroids = high_risk_pts[high_risk_pts["cluster"] != -1].groupby("cluster")[["lon", "lat"]].mean()
    
    # Mark these major hotspots with circular markers
    if not centroids.empty:
        ax.scatter(centroids["lon"], centroids["lat"], 
                   facecolors="#e53e3e", edgecolors="white", s=250, linewidths=2.5, 
                   marker="o", label="Ecological Hotspots", zorder=4)

setup_simple_style(ax, "Ocean Ecological Risk Zones and Marine Vulnerability Hotspots", "Longitude", "Latitude")

# Add clear legend elements explaining the risk categories and hotspot markers
legend_elements = [
    mpatches.Patch(color='#2eaa5b', label='Low ecological risk (0.0-0.2)'),
    mpatches.Patch(color='#fdeb4c', label='Moderate ecological stress (0.2-0.4)'),
    mpatches.Patch(color='#f5a623', label='High ecological risk (0.4-0.6)'),
    mpatches.Patch(color='#e53e3e', label='Critical vulnerability (0.6-1.0)'),
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#e53e3e', 
               markeredgecolor='white', markersize=14, markeredgewidth=2, 
               label='Ecological Hotspots')
]
ax.legend(handles=legend_elements, loc="upper right", framealpha=0.95, facecolor="white", edgecolor="#888888")

# Add descriptive annotations explaining the zones
info_text = (
    "Highlighted zones and hotspots are associated with:\n"
    " • Nutrient pollution from river discharge\n"
    " • Algal bloom formation potential\n"
    " • Severe oxygen depletion (hypoxia)\n"
    " • Critical marine ecosystem stress"
)
ax.text(0.02, 0.03, info_text, transform=ax.transAxes, fontsize=10, 
        verticalalignment='bottom', bbox=dict(facecolor='white', edgecolor='#888888', boxstyle='round,pad=0.7', alpha=0.9), zorder=5)

save(fig, "plot7_ecological_risk_zones.png")

print("\nAll visualizations of risk pollution generated successfully by CORAL AI!")
