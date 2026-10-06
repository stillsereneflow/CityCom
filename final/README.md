# 《城脉·涟控》 — final evidence package

| File | What it is |
|---|---|
| `FINAL_REPORT.md` | Results (frozen test audit vs development audit), verification, supporting studies, deviations, how to reproduce |
| `CLAIMS.md` | The exact claims allowed: verified facts, limitations, interpretations, unproven hypotheses, forbidden claims (English + 中文摘要) |
| `METHOD.md` | Method summary as frozen |
| `figures/` | fig1 BEE dev vs frozen; fig2 predicted vs realised A3 gain; fig3 gains per action; fig4 missing-queue diagnostic; fig5 state at decision time; `figure_data.csv` (every plotted number); `generate_figures.py` |
| `tables/` | t1 frozen per seed; t2 development vs frozen (side by side, never pooled); t3 event-engine coverage; t4 missing-queue; t5 replay diagnosis; t6 frozen-audit integrity; `build_tables.py` |
| `demo/` | `decision_card.py` (per-seed Twin-vs-Proxy decision card), `decision_cards.txt` (all 8 test seeds), `README.md` (reproduction and the `sumo-gui` command to show the incident queue at the decision time) |

Provenance: freeze `docs/freeze-2026-10-06.md` and `results/freeze/freeze_manifest.json`; frozen audit data `results/frozen_audit/` (results commit `aa7de30`); decision records in `docs/decision-2026-10-0*.md`.
