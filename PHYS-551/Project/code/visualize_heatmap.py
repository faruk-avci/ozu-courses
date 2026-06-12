import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
from city_config import ISTANBUL_ALL_LAND_NODES, ADJACENCY

# green (safe) -> yellow -> orange -> red -> purple (critical); low nonzero risk
# reads as green so an "after" map shows improvement at a glance.
RISK_COLORS = ["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c", "#8e44ad"]


def draw_heatmap(prob_map, coords, pop, adjacency, out_path, title, stations=None,
                 vmax=None):
    """Spatial risk map.

    prob_map  : name -> blackout probability
    coords    : name -> (lon, lat)
    pop       : name -> population (0 for relief stations)
    adjacency : name -> list of neighbours
    stations  : optional list of new-station names to highlight as squares
    vmax      : optional fixed value mapped to the top of the colour scale, so an
                "after" map can be coloured on the same absolute scale as "before"
    """
    stations = stations or []
    cmap = LinearSegmentedColormap.from_list("risk_cmap", RISK_COLORS)
    if vmax is None:
        district_probs = [prob_map.get(n, 0) for n in coords if n not in stations]
        vmax = max(district_probs) if district_probs else 1.0
    max_prob = vmax if vmax > 0 else 1.0

    fig, ax = plt.subplots(figsize=(18, 12))

    drawn = set()
    for d, neigh in adjacency.items():
        for nb in neigh:
            key = tuple(sorted([d, nb]))
            if key in drawn or d not in coords or nb not in coords:
                continue
            drawn.add(key)
            is_station_link = d in stations or nb in stations
            ax.plot([coords[d][0], coords[nb][0]], [coords[d][1], coords[nb][1]],
                    color="#27ae60" if is_station_link else "#e0e6ed",
                    ls="--" if is_station_link else "-",
                    lw=1.8 if is_station_link else 1.0, zorder=2 if is_station_link else 1)

    for name, (lon, lat) in coords.items():
        if name in stations:
            ax.scatter(lon, lat, s=420, marker="s", color="#27ae60",
                       edgecolors="#145a32", linewidths=2, zorder=5)
            ax.text(lon, lat - 0.012, f"{name}\n(relief)", ha="center", va="top",
                    fontsize=10, color="#145a32", fontweight="bold", zorder=6)
            continue
        prob = prob_map.get(name, 0)
        color = cmap(min(prob / max_prob, 1.0)) if prob > 0 else "#2ecc71"
        size = max(150, pop.get(name, 0) / 600)
        ax.scatter(lon, lat, s=size, color=color, edgecolors="#2c3e50",
                   linewidths=1.5, zorder=3)
        ptxt = f"{prob*100:.2f}%" if prob > 1e-4 else (f"{prob:.1e}" if prob > 0 else "0%")
        ax.text(lon, lat + 0.007, f"{name}\n{ptxt}", ha="center", va="bottom",
                fontsize=9, color="#2c3e50", fontweight="bold", zorder=4)

    ax.set_title(title, fontsize=18, fontweight="bold", color="#2c3e50", pad=20)
    legend = [
        mpatches.Patch(color="#8e44ad", label="Critical risk"),
        mpatches.Patch(color="#e74c3c", label="High risk"),
        mpatches.Patch(color="#f1c40f", label="Low/moderate risk"),
        mpatches.Patch(color="#2ecc71", label="Zero/negligible risk"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="gray",
                   markersize=15, label="Size = population"),
    ]
    if stations:
        legend.append(plt.Line2D([0], [0], marker="s", color="w",
                                 markerfacecolor="#27ae60", markersize=15,
                                 label="New relief station"))
    ax.legend(handles=legend, loc="upper left", frameon=True, facecolor="white",
              edgecolor="#bdc3c7", fontsize=12)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, facecolor="white")
    plt.close(fig)
    print(f"✓ Heatmap saved to {os.path.relpath(out_path)}")


def main():
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "output"))
    csv_path = os.path.join(output_dir, "is_results.csv")
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Run importance_sampling.py first.")
        return

    df = pd.read_csv(csv_path)
    prob_map = dict(zip(df["District"], df["True_Blackout_Probability"]))
    coords = {n: (d["lon"], d["lat"]) for n, d in ISTANBUL_ALL_LAND_NODES.items()}
    pop = {n: d["population"] for n, d in ISTANBUL_ALL_LAND_NODES.items()}
    total_expected = df["Expected_People_Affected"].sum()

    title = ("Istanbul Grid Cascading Risk Heatmap\n"
             f"Total Expected Daily Population Affected: {total_expected:,.0f} people")
    draw_heatmap(prob_map, coords, pop, ADJACENCY,
                 os.path.join(output_dir, "heatmap_risk.png"), title)


if __name__ == "__main__":
    main()
