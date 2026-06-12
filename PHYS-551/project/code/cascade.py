"""
PHYS 551 — Monte Carlo Methods Project
Shared cascading-failure engine.

Single source of truth for the grid physics, imported by BOTH naive.py and
importance_sampling.py so the two estimators provably use identical dynamics.
Only the way the daily demand vector is *sampled* differs between the methods;
the cascade that follows is the same function of that demand vector.
"""

import numpy as np

# Fragility sharpness. prob_fail = min(1, (load/capacity) ** FRAGILITY_EXP).
# With a large exponent this is an almost-deterministic breaker: a district is
# safe below its capacity and trips essentially for sure once load reaches it.
FRAGILITY_EXP = 150


def simulate_cascade(initial_loads, nodes, adjacency, gamma):
    """Run one day. Returns dict name -> status (1 = powered, 0 = blacked out).

    initial_loads : dict name -> sampled daily demand (MWh)
    nodes         : dict name -> {'capacity', 'alpha', ...}  (ISTANBUL_ALL_LAND_NODES)
    adjacency     : dict name -> list of bordering district names
    gamma         : dict name -> redistribution factor in [0, 1]
    """
    status = {name: 1 for name in nodes}
    loads = dict(initial_loads)            # mutated as load is pushed around
    failed_queue = []

    # Step 1 — initial trips from the random demand spikes themselves.
    for name in nodes:
        if _trips(loads[name], nodes[name]['capacity']):
            status[name] = 0
            failed_queue.append(name)

    # Step 2 — propagate. A tripped node sheds gamma * excess onto its still-live
    # neighbours, split by each neighbour's spare headroom * its own margin alpha.
    while failed_queue:
        curr = failed_queue.pop(0)

        excess = loads[curr] - nodes[curr]['capacity']
        if excess <= 0:                    # tripped via redistribution, not its own spike
            excess = loads[curr]
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
            if status[n] == 1 and _trips(loads[n], nodes[n]['capacity']):
                status[n] = 0
                failed_queue.append(n)

    return status


def _trips(load, capacity):
    """Probabilistic breaker check."""
    ratio = load / capacity
    prob_fail = min(1.0, ratio ** FRAGILITY_EXP)
    return np.random.random() < prob_fail
