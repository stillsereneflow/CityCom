# Consultation evidence notes

- Started 2026-10-03 00:45:59 UTC; 60-minute limit. Worktree initially clean at f7bf3e2, branch astra/step1.
- All writes confined to new experiment code and results in D:/CityCom-astra. Python bytecode disabled. No worker dispatch, recorder access, or main-checkout writes.
- Exact baseline replication: g100 totals, slope and GEH reproduced. Byte hashes differ for some tracked inputs; semantic/run comparison needed, rather than treating hash mismatch as a new network.
- Existing randomTrips fringe-factor=20 is a bias, not a boundary constraint. Original 26,020 routes: 45.06% nonboundary starts; only 15.68% both endpoints at topological boundary; mean 2.637 km; no direct SUMO U-turn connections or repeated edges.
- Strict boundary fastest-path pilot: 23,178 loaded, 12,429 pending, 3,818 running, +0.6106 veh/s, 0/40 GEH<5; worse backlog despite lower demand. Three targets have no direct fastest boundary path. Boundary stubs alone do not establish plausible OD gates.
- Stale target edge 1128468458: current AID07224 map uses 1128468457. Diagnostic silently drops the stale edge and evaluates 40 rather than 41.
- TD: low-speed/high-occupancy observations at AID07105/106 and AID02109/110. Counts cannot be equated with unconstrained arrivals. Sparse periods limit whole-hour inference.
- Optional optimization initially unavailable (SciPy absent); pip also absent. Installing SciPy only into results/astra_step1/packages through uv, with temporary files also inside the worktree.
- SciPy 1.18.1 installed successfully; count optimization 25,131 loaded, 11,782 pending, 2,376 running, +0.3338 veh/s, 4/40 simulation GEH<5. Route-space fit against noisy objective is 40/41; only 39 unique routes. No demand-only rescue demonstrated.
- Independent Pandas aggregation agrees for all 54 day-29 detectors. Boundary fastest paths checked by actual SUMO execution. Count conservation includes final-second scheduled departures (6, 5, 9).
- g100 differs from worktree hashes only by LF/CRLF; conversion recovers all four original hashes. Baseline full measured payload agrees exactly. All 33 original data/scenario/baseline inputs remain byte-identical.
- E1 API/XML nVehContrib comparison fails at one of 1,590 cells in a 300-s pilot (4 vs 3 at AID07108_0, end=240). Repeated check gives the same result. XML nVehEntered is not a general replacement (152 differing cells). Recorded unresolved; no diagnostic code was changed to force agreement.
- Stop simulation experiments after two interventions. Recommendation: fix the observation contract, bounded path-constrained OD with physically justified gates, and flow/speed/occupancy acceptance. Neither demand predominance nor capacity innocence established.
