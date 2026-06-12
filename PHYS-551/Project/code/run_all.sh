#!/usr/bin/env bash
# ============================================================================
# PHYS 551 — Monte Carlo Methods Project
# Istanbul Power-Grid Cascading-Blackout Study — full pipeline runner
#
# Run it:        bash run_all.sh
# (or:           chmod +x run_all.sh   &&   ./run_all.sh )
#
# It executes every stage in the right order and writes all figures/CSVs to
# output/.  Total run time is a couple of minutes.
#
# ----------------------------------------------------------------------------
# WHAT EACH FILE DOES
# ----------------------------------------------------------------------------
#   city_config.py          The model. 38 Istanbul districts with population,
#                           electricity load, safety margin alpha (derived from
#                           real 2024 EPIAS "Asiri Yuk"/overload counts), the
#                           redistribution factor gamma, the adjacency graph, and
#                           the demand-volatility constants (city-wide surge S +
#                           per-district noise). Imported by everything; running
#                           it directly just prints a sanity table.
#
#   cascade.py              The shared physics engine: given a day's demand for
#                           every district, trips the overloaded ones and
#                           propagates the cascade to neighbours. Used by BOTH
#                           the naive and importance-sampling runs so they share
#                           identical dynamics.
#
#   fetch_outage_data.py    One-off data collection: pulls a year of EPIAS
#                           outage records and counts the "Asiri Yuk" (overload)
#                           events per district -> output/outage_stats.json,
#                           which city_config.py turns into the alpha margins.
#                           (Already run; needs a login cookie. Not run here.)
#
#   naive.py                NAIVE (crude) Monte Carlo. Samples the true demand
#                           model directly and measures P(at least X people lose
#                           power). Nails the common events, goes blind in the
#                           rare tail. -> naive_results.csv,
#                           naive_population_impact.csv, naive_convergence.csv
#
#   importance_sampling.py  IMPORTANCE SAMPLING. Biases the city-wide surge S
#                           upward (a small ladder of tilts) and reweights, so
#                           the rare city-wide blackouts that naive never sees
#                           are estimated with tight error bars.
#                           -> is_results.csv, is_population_impact.csv,
#                              is_convergence.csv
#
#   compare.py              Puts the two methods side by side:
#                           -> ep_curve.png         exceedance curve, both methods
#                           -> convergence.png      rarest bucket vs sample size
#                           -> variance_reduction.csv  how much IS beats naive
#
#   visualize_heatmap.py    Spatial risk map coloured by per-district blackout
#                           probability. -> heatmap_risk.png  (also exposes the
#                           reusable draw_heatmap() used by station_placement.py)
#
#   visualize_graph.py      Renders the district adjacency graph. -> grid_graph.png
#
#   station_placement.py    "Where to build new relief substations?" Adds new
#                           stations (each offloads 30% of up to 3 districts),
#                           greedily picks the two placements that minimise the
#                           expected number of people without power, and reports
#                           the before/after. -> heatmap_with_stations.png,
#                           placement_ep_curve.png, placement_summary.csv
# ============================================================================

set -e                                   # stop immediately if any stage fails
cd "$(dirname "$0")"                      # run from this code/ directory
PY=python3

banner () { echo; echo "================ $1 ================"; }

banner "0/5  Model sanity check (city_config.py)"
$PY city_config.py | tail -n 6

banner "1/5  Naive Monte Carlo (naive.py, N=100000)"
$PY naive.py 100000

banner "2/5  Importance Sampling (importance_sampling.py)"
$PY importance_sampling.py

banner "3/5  Compare naive vs IS (compare.py)"
$PY compare.py

banner "4/5  Risk heat-map (visualize_heatmap.py)"
$PY visualize_heatmap.py

banner "5/5  New-station placement (station_placement.py)"
$PY station_placement.py

banner "DONE"
echo "All figures and CSVs are in output/"
