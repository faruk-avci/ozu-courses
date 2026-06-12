"""
Visualize the Istanbul grid graph with adjacency edges and γ factors.
"""
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from city_config import ISTANBUL_ALL_LAND_NODES, ADJACENCY, GAMMA

def main():
    fig, ax = plt.subplots(figsize=(18, 12))
    
    # 1. Draw edges first so they are behind nodes
    drawn_edges = set()
    for district, neighbors in ADJACENCY.items():
        d1 = ISTANBUL_ALL_LAND_NODES[district]
        for neighbor in neighbors:
            edge_key = tuple(sorted([district, neighbor]))
            if edge_key in drawn_edges:
                continue
            drawn_edges.add(edge_key)
            
            d2 = ISTANBUL_ALL_LAND_NODES[neighbor]
            
            # Identify bridges (both Beşiktaş-Üsküdar and Sarıyer-Beykoz)
            is_bridge = edge_key in {
                tuple(sorted(["Beşiktaş", "Üsküdar"])),
                tuple(sorted(["Sarıyer", "Beykoz"]))
            }
            
            if is_bridge:
                ax.plot([d1["lon"], d2["lon"]], [d1["lat"], d2["lat"]],
                        color="red", linestyle="--", linewidth=3.5, zorder=2)
            else:
                ax.plot([d1["lon"], d2["lon"]], [d1["lat"], d2["lat"]],
                        color="#bcc4cc", linestyle="-", linewidth=1.2, zorder=1)
                
    # 2. Draw nodes
    for name, data in ISTANBUL_ALL_LAND_NODES.items():
        color = "#3498db" if data["side"] == "Europe" else "#e67e22" # Nice blue and orange
        size = max(120, data["population"] / 800) # Size proportional to pop
        
        # Plot node
        ax.scatter(data["lon"], data["lat"], s=size, color=color, edgecolors="#2c3e50", linewidths=1.5, zorder=3)
        
        # Add labels: District name and gamma value
        # Shift text slightly up so it's centered nicely above the node
        ax.text(data["lon"], data["lat"] + 0.007, f"{name}\nγ={data['gamma']:.3f}",
                ha="center", va="bottom", fontsize=8, color="#2c3e50", fontweight="bold", zorder=4)
        
    # 3. Beautify layout
    ax.set_title("Istanbul Power Grid Network Topology\n(Bosphorus Bridge Links Highlighted in Dashed Red)",
                 fontsize=16, fontweight="bold", color="#2c3e50", pad=20)
    
    # Create legend
    europe_patch = mpatches.Patch(color='#3498db', label='Europe (Boğaziçi Dağıtım)')
    asia_patch = mpatches.Patch(color='#e67e22', label='Asia (Anadolu Yakası Dağıtım)')
    bridge_line = plt.Line2D([0], [0], color='red', linestyle='--', linewidth=2, label='Bosphorus Bridge Link 🌉')
    grid_line = plt.Line2D([0], [0], color='#bcc4cc', linestyle='-', linewidth=1.5, label='Physical Adjacency Grid')
    
    ax.legend(handles=[europe_patch, asia_patch, bridge_line, grid_line],
              loc="upper left", frameon=True, facecolor="white", edgecolor="#bdc3c7", fontsize=11)
    
    # Remove axis ticks and borders for a clean "no border just nodes" abstract view
    ax.set_axis_off()
    
    plt.tight_layout()
    
    # Save the output image
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.abspath(os.path.join(script_dir, "output"))
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "grid_graph.png")
    
    plt.savefig(output_path, dpi=150, facecolor="white")
    plt.close()
    print(f"✓ Saved to {os.path.relpath(output_path)}")

if __name__ == "__main__":
    main()
