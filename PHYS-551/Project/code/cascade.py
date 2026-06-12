"""
PHYS 551 — Monte Carlo Methods Project
Shared cascading-failure engine.

Single source of truth for the grid physics, imported by BOTH naive.py and
importance_sampling.py so the two estimators provably use identical dynamics.
Only the way the daily demand vector is *sampled* differs between the methods;
the cascade that follows is a deterministic function of that demand vector.

The breaker is a hard threshold: a district trips exactly when its load exceeds
its capacity. There is no randomness inside the cascade itself; all randomness
lives in the sampled demand (the systemic surge S and the per-district noise).
"""


def simulate_cascade(initial_loads, nodes, adjacency, gamma):
    """Run one day. Returns dict name -> status (1 = powered, 0 = blacked out).

    initial_loads : dict name -> sampled demand for the day (same units as capacity)
    nodes         : dict name -> {'capacity', 'alpha', ...}  (ISTANBUL_ALL_LAND_NODES)
    adjacency     : dict name -> list of bordering district names
    gamma         : dict name -> redistribution factor in (0, 1]
    """
    status = {name: 1 for name in nodes}
    loads = dict(initial_loads)            # mutated as load is pushed around
    failed_queue = []

    # Step 1 — initial trips from the random demand spikes themselves.
    for name in nodes:
        if loads[name] > nodes[name]['capacity']:
            status[name] = 0
            failed_queue.append(name)

    # Step 2 — propagate. A tripped node sheds gamma * excess onto its still-live
    # neighbours, split by each neighbour's spare headroom * its own margin alpha.
    # A node only ever enters the queue once its load is above capacity, so the
    # excess below is always positive.
    while failed_queue:
        curr = failed_queue.pop(0)

        excess = loads[curr] - nodes[curr]['capacity']
        load_to_move = excess * gamma[curr]

        live_neighbors = [n for n in adjacency[curr] if status[n] == 1]
        if not live_neighbors:
            continue

        scores = {}
        total = 0.0
        for n in live_neighbors:
            headroom = max(0.1, nodes[n]['capacity'] - loads[n])
            s = headroom * nodes[n]['alpha']
            scores[n] = s
            total += s

        for n in live_neighbors:
            share = (scores[n] / total) if total > 0 else (1.0 / len(live_neighbors))
            loads[n] += load_to_move * share
            if status[n] == 1 and loads[n] > nodes[n]['capacity']:
                status[n] = 0
                failed_queue.append(n)

    return status
