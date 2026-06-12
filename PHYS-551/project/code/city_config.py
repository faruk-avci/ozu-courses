# Save this directly into your upgraded city_config.py
import os
import json
import numpy as np

# ----------------------------------------------------------------------------
# DEMAND VOLATILITY MODEL (shared by naive + importance sampling)
#
# Each district's daily demand is  L_i = mu_i * (S + eps_i)  where
#   S      ~ Normal(1, VOL_SYS)   -- a CITY-WIDE demand multiplier. One value per
#                                    day, shared by every district. This is the
#                                    common-mode driver (a heatwave turns on every
#                                    AC at once); large S is the rare event that
#                                    triggers a system-wide cascade.
#   eps_i  ~ Normal(0, VOL_IDIO)  -- small district-specific noise, independent.
#
# A district trips when L_i exceeds capacity_i = mu_i*(1+alpha_i), i.e. roughly
# when S + eps_i > 1 + alpha_i.  Almost all tail risk therefore comes from S,
# which is why Importance Sampling biases S alone (a clean 1-D tilt).
# ----------------------------------------------------------------------------
VOL_SYS  = 0.03   # city-wide systemic demand swing (std of S)
VOL_IDIO = 0.02   # district idiosyncratic demand noise (std of eps_i)

ISTANBUL_ALL_LAND_NODES = {
    "Arnavutköy":    {"population": 358469,  "lat": 41.1852, "lon": 28.7412, "side": "Europe"},
    "Ataşehir":      {"population": 412125,  "lat": 40.9847, "lon": 29.1064, "side": "Asia"},
    "Avcılar":       {"population": 440663,  "lat": 40.9926, "lon": 28.7208, "side": "Europe"},
    "Bağcılar":      {"population": 707635,  "lat": 41.0336, "lon": 28.8427, "side": "Europe"},
    "Bahçelievler":  {"population": 539035,  "lat": 41.0001, "lon": 28.8633, "side": "Europe"},
    "Bakırköy":      {"population": 218204,  "lat": 40.9782, "lon": 28.8724, "side": "Europe"},
    "Başakşehir":    {"population": 536797,  "lat": 41.0965, "lon": 28.7884, "side": "Europe"},
    "Bayrampaşa":    {"population": 272978,  "lat": 41.0351, "lon": 28.8953, "side": "Europe"},
    "Beşiktaş":      {"population": 165895,  "lat": 41.0428, "lon": 29.0075, "side": "Europe"},
    "Beykoz":        {"population": 246833,  "lat": 41.1171, "lon": 29.0983, "side": "Asia"},
    "Beylikdüzü":    {"population": 422988,  "lat": 40.9898, "lon": 28.6431, "side": "Europe"},
    "Beyoğlu":       {"population": 215991,  "lat": 41.0369, "lon": 28.9774, "side": "Europe"},
    "Büyükçekmece":  {"population": 283239,  "lat": 41.0212, "lon": 28.5954, "side": "Europe"},
    "Çatalca":       {"population": 81143,   "lat": 41.1425, "lon": 28.4611, "side": "Europe"},
    "Çekmeköy":      {"population": 315959,  "lat": 41.0351, "lon": 29.2152, "side": "Asia"},
    "Esenler":       {"population": 419878,  "lat": 41.0425, "lon": 28.8774, "side": "Europe"},
    "Esenyurt":      {"population": 1003905, "lat": 41.0343, "lon": 28.6801, "side": "Europe"},
    "Eyüpsultan":    {"population": 425216,  "lat": 41.1394, "lon": 28.8952, "side": "Europe"},
    "Fatih":         {"population": 351786,  "lat": 41.0131, "lon": 28.9378, "side": "Europe"},
    "Gaziosmanpaşa": {"population": 478395,  "lat": 41.0694, "lon": 28.9135, "side": "Europe"},
    "Güngören":      {"population": 251242,  "lat": 41.0223, "lon": 28.8721, "side": "Europe"},
    "Kadıköy":       {"population": 458573,  "lat": 40.9910, "lon": 29.0234, "side": "Asia"},
    "Kağıthane":     {"population": 446420,  "lat": 41.0805, "lon": 28.9742, "side": "Europe"},
    "Kartal":        {"population": 475630,  "lat": 40.8994, "lon": 29.1912, "side": "Asia"},
    "Küçükçekmece":  {"population": 785270,  "lat": 41.0003, "lon": 28.7818, "side": "Europe"},
    "Maltepe":       {"population": 525044,  "lat": 40.9412, "lon": 29.1764, "side": "Asia"},
    "Pendik":        {"population": 752033,  "lat": 40.9126, "lon": 29.2634, "side": "Asia"},
    "Sancaktepe":    {"population": 507500,  "lat": 41.0044, "lon": 29.2312, "side": "Asia"},
    "Sarıyer":       {"population": 344883,  "lat": 41.1671, "lon": 29.0415, "side": "Europe"},
    "Silivri":       {"population": 240029,  "lat": 41.0742, "lon": 28.2481, "side": "Europe"},
    "Sultanbeyli":   {"population": 378908,  "lat": 40.9664, "lon": 29.2667, "side": "Asia"},
    "Sultangazi":    {"population": 529306,  "lat": 41.1044, "lon": 28.8681, "side": "Europe"},
    "Şile":          {"population": 50090,   "lat": 41.1744, "lon": 29.6125, "side": "Asia"},
    "Şişli":         {"population": 261959,  "lat": 41.0602, "lon": 28.9875, "side": "Europe"},
    "Tuzla":         {"population": 313865,  "lat": 40.8164, "lon": 29.3033, "side": "Asia"},
    "Ümraniye":      {"population": 728913,  "lat": 41.0249, "lon": 29.1244, "side": "Asia"},
    "Üsküdar":       {"population": 514294,  "lat": 41.0264, "lon": 29.0152, "side": "Asia"},
    "Zeytinburnu":   {"population": 275471,  "lat": 40.9881, "lon": 28.9036, "side": "Europe"}
}

N_DISTRICTS = len(ISTANBUL_ALL_LAND_NODES)

# 1. Distribute Load by Population within Sides
# Monthly MWh Consumption Data (2023)
BOGAZICI_MONTHLY_MWH = [
    2484223.63, 2408805.03, 2505057.67, 2245391.69,
    2281477.75, 2126404.57, 2529030.02, 2566872.94,
    2469351.59, 2246808.06, 2217702.47, 2221627.95
]

ANADOLU_MONTHLY_MWH = [
    1258092.18, 1244379.52, 1232838.64, 1117897.93,
    1145213.92, 1013960.20, 1263538.34, 1277695.05,
    1233537.56, 1128226.23, 1093679.90, 1203546.83
]

# Calculate the average monthly consumption for the year
TOTAL_EUROPE_MWH = sum(BOGAZICI_MONTHLY_MWH) / len(BOGAZICI_MONTHLY_MWH)
TOTAL_ASIA_MWH = sum(ANADOLU_MONTHLY_MWH) / len(ANADOLU_MONTHLY_MWH)

europe_pop = sum(d["population"] for d in ISTANBUL_ALL_LAND_NODES.values() if d["side"] == "Europe")
asia_pop = sum(d["population"] for d in ISTANBUL_ALL_LAND_NODES.values() if d["side"] == "Asia")

for name, data in ISTANBUL_ALL_LAND_NODES.items():
    if data["side"] == "Europe":
        data["initial_load"] = TOTAL_EUROPE_MWH * (data["population"] / europe_pop)
    else:
        data["initial_load"] = TOTAL_ASIA_MWH * (data["population"] / asia_pop)

# 2. Load API Outage Data and Distribute Safety Margins (alpha)
stats_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output", "outage_stats.json"))
if os.path.exists(stats_file):
    with open(stats_file, 'r', encoding='utf-8') as f:
        outage_counts = json.load(f)
else:
    # Fallback to zero if not run yet
    outage_counts = {name: 0 for name in ISTANBUL_ALL_LAND_NODES.keys()}

# Normalize outages to alpha range — SEPARATELY per side (different providers)
# Europe = Boğaziçi Dağıtım, Asia = İstanbul Anadolu Yakası Dağıtım
# Calibrated so the weakest district is safe on an average day but trips under a
# rare city-wide surge: with VOL_SYS=0.03, alpha=0.08 means S must exceed ~1.08
# (a ~2.7 sigma systemic surge) before the most fragile district fails.
ALPHA_MAX = 0.25  # Healthy buffer for districts with 0 overloads
ALPHA_MIN = 0.08  # Degraded buffer for the worst district on each side

# Split outage counts by side
europe_counts = {n: outage_counts.get(n, 0) for n, d in ISTANBUL_ALL_LAND_NODES.items() if d["side"] == "Europe"}
asia_counts   = {n: outage_counts.get(n, 0) for n, d in ISTANBUL_ALL_LAND_NODES.items() if d["side"] == "Asia"}

max_europe = max(europe_counts.values()) if europe_counts else 1
max_asia   = max(asia_counts.values())   if asia_counts   else 1

for name, data in ISTANBUL_ALL_LAND_NODES.items():
    count = outage_counts.get(name, 0)
    side_max = max_europe if data["side"] == "Europe" else max_asia

    if side_max > 0:
        # α_i = 0.30 - 0.20 × (count_i / max_count_on_same_side)
        ratio = count / side_max
        data["alpha"] = ALPHA_MAX - ratio * (ALPHA_MAX - ALPHA_MIN)
    else:
        data["alpha"] = ALPHA_MAX  # No overloads at all on this side

    # Calculate final capacity
    data["capacity"] = data["initial_load"] * (1 + data["alpha"])

# 3. Redistribution Factor (gamma) — population-based
# γ_i = GAMMA_SCALE × (1.0 - 0.3 × Pop_i / Pop_max)
# Fraction of a tripped district's excess load that spills onto its neighbours;
# small districts pass a larger share than big ones. GAMMA_SCALE is kept modest
# so a single trip does NOT cascade across the whole city: a system-wide blackout
# then requires a genuinely large city-wide surge S, which is the rare event we
# want Importance Sampling to resolve. Raising it makes catastrophes less rare.
GAMMA_SCALE = 0.35
POP_MAX = max(d["population"] for d in ISTANBUL_ALL_LAND_NODES.values())
for name, data in ISTANBUL_ALL_LAND_NODES.items():
    data["gamma"] = GAMMA_SCALE * (1.0 - 0.3 * (data["population"] / POP_MAX))

# Expose standard arrays for visualization and MC engine
names = list(ISTANBUL_ALL_LAND_NODES.keys())
populations = np.array([ISTANBUL_ALL_LAND_NODES[n]["population"] for n in names])
lats = np.array([ISTANBUL_ALL_LAND_NODES[n]["lat"] for n in names])
lons = np.array([ISTANBUL_ALL_LAND_NODES[n]["lon"] for n in names])
initial_loads = np.array([ISTANBUL_ALL_LAND_NODES[n]["initial_load"] for n in names])
alphas = np.array([ISTANBUL_ALL_LAND_NODES[n]["alpha"] for n in names])
capacities = np.array([ISTANBUL_ALL_LAND_NODES[n]["capacity"] for n in names])
gammas = np.array([ISTANBUL_ALL_LAND_NODES[n]["gamma"] for n in names])
outage_array = np.array([outage_counts.get(n, 0) for n in names])

# Expose mapping from district name to its gamma
GAMMA = {name: ISTANBUL_ALL_LAND_NODES[name]["gamma"] for name in names}

# 4. Physical Adjacency Graph (who borders who)
def _get_or_create_adjacency():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "real_adjacency.json")
    
    adjacency_graph = None
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                adjacency_graph = json.load(f)
        except Exception:
            pass  # Rebuild if corrupt or empty
            
    if adjacency_graph is None:
        # Rebuild programmatically using GeoJSON
        geojson_path = os.path.join(script_dir, "istanbul_districts.geojson")
        try:
            import geopandas as gpd
            gdf = gpd.read_file(geojson_path)
            gdf["name"] = gdf["name"].replace({"Eyüp": "Eyüpsultan"})
            
            adjacency_graph = {}
            for idx, row in gdf.iterrows():
                district_name = row["name"]
                if district_name == "Adalar":
                    continue
                    
                # Use topological touches operator
                true_neighbors = gdf[gdf.geometry.touches(row.geometry)]["name"].tolist()
                if "Adalar" in true_neighbors:
                    true_neighbors.remove("Adalar")
                    
                adjacency_graph[district_name] = sorted(true_neighbors)
        except Exception as e:
            print(f"⚠️ Error computing adjacency dynamically: {e}")
            raise e

    # Apply manual adjustments (Bosphorus bridges and user directives)
    def connect(u, v):
        if u in adjacency_graph and v not in adjacency_graph[u]:
            adjacency_graph[u].append(v)
        if v in adjacency_graph and u not in adjacency_graph[v]:
            adjacency_graph[v].append(u)

    def disconnect(u, v):
        if u in adjacency_graph and v in adjacency_graph[u]:
            adjacency_graph[u].remove(v)
        if v in adjacency_graph and u in adjacency_graph[v]:
            adjacency_graph[v].remove(u)

    # 1. Connect Gaziosmanpaşa ↔ Kağıthane
    connect("Gaziosmanpaşa", "Kağıthane")
    # 2. Remove Kağıthane ↔ Beşiktaş
    disconnect("Kağıthane", "Beşiktaş")
    # 3. Fatih must connect to Beyoğlu, Bayrampaşa, and Gaziosmanpaşa
    connect("Fatih", "Beyoğlu")
    connect("Fatih", "Bayrampaşa")
    connect("Fatih", "Gaziosmanpaşa")
    # 4. Eyüpsultan is disconnected from Zeytinburnu, Bayrampaşa, Fatih, Beyoğlu, and Gaziosmanpaşa
    disconnect("Eyüpsultan", "Zeytinburnu")
    disconnect("Eyüpsultan", "Bayrampaşa")
    disconnect("Eyüpsultan", "Fatih")
    disconnect("Eyüpsultan", "Beyoğlu")
    disconnect("Eyüpsultan", "Gaziosmanpaşa")
    # 5. Zeytinburnu is disconnected from Esenler
    disconnect("Zeytinburnu", "Esenler")
    # 6. Sarıyer ↔ Beykoz connected
    connect("Sarıyer", "Beykoz")
    # 7. Beşiktaş ↔ Üsküdar connected
    connect("Beşiktaş", "Üsküdar")

    # Remove duplicates and sort
    for district in adjacency_graph:
        adjacency_graph[district] = sorted(list(set(adjacency_graph[district])))

    # Always save/update the json to stay in sync
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(adjacency_graph, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Warning: Could not write adjacency cache: {e}")

    return adjacency_graph

ADJACENCY = _get_or_create_adjacency()

if __name__ == "__main__":
    print("=" * 80)
    print(f"{'District':<16} {'Pop':>9} {'Load(MWh)':>11} {'Out':>4} {'α':>6} {'γ':>6} {'Capacity':>10}")
    print("=" * 80)
    for i in range(N_DISTRICTS):
        print(f"{names[i]:<16} {populations[i]:>9,} {initial_loads[i]:>11,.1f} {outage_array[i]:>4} "
              f"{alphas[i]:>6.3f} {gammas[i]:>6.3f} {capacities[i]:>10,.1f}")
    
    print("\n" + "=" * 80)
    print("TOPOLOGY VALIDATION")
    print("=" * 80)
    print(f"Total districts: {len(ADJACENCY)}")
    print(f"Total edges: {sum(len(v) for v in ADJACENCY.values()) // 2}")
    
    # Verify symmetry: if A lists B, B must list A
    errors = []
    for district, neighbors in ADJACENCY.items():
        for n in neighbors:
            if district not in ADJACENCY.get(n, []):
                errors.append(f"  ⚠️ {district} → {n} but {n} does NOT → {district}")
    if errors:
        print("\nSYMMETRY ERRORS:")
        for e in errors:
            print(e)
    else:
        print("✓ All adjacency links are symmetric.")