"""
Istanbul Power Grid Adjacency Graph & Redistribution Factors.
Simple backward-compatibility forwarder redirecting imports to city_config.py.
"""
from city_config import ADJACENCY, GAMMA, ISTANBUL_ALL_LAND_NODES

if __name__ == "__main__":
    print("=" * 80)
    print("Istanbul Grid Adjacency Graph Summary (Forwarded from city_config.py)")
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
