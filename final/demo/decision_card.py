"""Decision card CLI (offline decision audit).

Reads only from results/frozen_audit/raw.parquet and prints a decision card
for the specified seed and belief.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import pandas as pd

ACTIONS = ("A0", "A1", "A2", "A3", "A4")
ACTION_DESCRIPTIONS = {
    "A0": "Do nothing (base signal timing)",
    "A1": "Local signal offset adjustment",
    "A2": "Corridor VMS diversion advisory",
    "A3": "VMS advisory + arterial priority",
    "A4": "Emergency diversion rerouting",
}


def compute_card(raw_df: pd.DataFrame, seed: int, belief: str = "B"):
    # Filter rows
    sub = raw_df[(raw_df["seed"] == seed) & (raw_df["status"] == "ok")].copy()
    if sub.empty:
        raise ValueError(f"No valid rows found for seed {seed}")

    tw = sub[(sub["world"] == "twin") & (sub["belief"] == belief)]
    px = sub[sub["world"] == "proxy"]

    if tw.empty:
        raise ValueError(f"No Twin rows for seed {seed} with belief {belief}")
    if px.empty:
        raise ValueError(f"No Proxy rows for seed {seed}")

    # Replications
    # R1: selection (1-3), R2: evaluation (4-6)
    # M1: oracle selection (1-3), M2: evaluation (4-6)
    tw_r1 = tw[tw["replication"].isin([1, 2, 3])].groupby("action")["J"].mean()
    tw_r2 = tw[tw["replication"].isin([4, 5, 6])].groupby("action")["J"].mean()
    px_m1 = px[px["replication"].isin([1, 2, 3])].groupby("action")["J"].mean()
    px_m2 = px[px["replication"].isin([4, 5, 6])].groupby("action")["J"].mean()

    a_star = str(tw_r1.idxmin())
    oracle = str(px_m1.idxmin())

    g_t_a_star = float(tw_r2["A0"] - tw_r2[a_star])
    g_p_a_star = float(px_m2["A0"] - px_m2[a_star])
    bee = g_t_a_star - g_p_a_star
    regret = float(px_m2[a_star] - px_m2[oracle])

    rows = []
    for a in ACTIONS:
        j_t = float(tw_r2[a])
        gain_t = float(tw_r2["A0"] - tw_r2[a])
        j_p = float(px_m2[a])
        gain_p = float(px_m2["A0"] - px_m2[a])
        tags = []
        if a == a_star:
            tags.append("Twin Choice (a*)")
        if a == oracle:
            tags.append("Proxy Oracle")
        tag_str = ", ".join(tags) if tags else ""
        rows.append({
            "action": a,
            "desc": ACTION_DESCRIPTIONS.get(a, ""),
            "j_t": j_t,
            "gain_t": gain_t,
            "j_p": j_p,
            "gain_p": gain_p,
            "tags": tag_str,
        })

    return {
        "seed": seed,
        "belief": belief,
        "a_star": a_star,
        "oracle": oracle,
        "bee": bee,
        "regret": regret,
        "g_t_a_star": g_t_a_star,
        "g_p_a_star": g_p_a_star,
        "rows": rows,
    }


def format_card(card: dict) -> str:
    lines = []
    lines.append("=" * 86)
    lines.append(f"DECISION CARD: Seed {card['seed']} (Twin Belief: {card['belief']})")
    lines.append("=" * 86)
    lines.append(
        f"{'Action':<8} {'Twin J (R2)':>12} {'Twin Gain':>12} {'Proxy J (M2)':>14} {'Proxy Gain':>12}   {'Role / Status':<22}"
    )
    lines.append(
        f"{'':<8} {'(veh.h)':>12} {'(veh.h)':>12} {'(veh.h)':>14} {'(veh.h)':>12}"
    )
    lines.append("-" * 86)

    for r in card["rows"]:
        tag_disp = f"[{r['tags']}]" if r["tags"] else ""
        lines.append(
            f"{r['action']:<8} {r['j_t']:>12.3f} {r['gain_t']:>12.3f} {r['j_p']:>14.3f} {r['gain_p']:>12.3f}   {tag_disp:<22}"
        )

    lines.append("-" * 86)
    lines.append("Key Decision Quantities:")
    lines.append(f"  - Twin chosen action (R1):        {card['a_star']}")
    lines.append(f"  - Proxy oracle action (M1):       {card['oracle']}")
    lines.append(f"  - Twin predicted benefit G_T(a*): {card['g_t_a_star']:+.3f} veh.h")
    lines.append(f"  - Proxy realised benefit G_P(a*): {card['g_p_a_star']:+.3f} veh.h")
    lines.append(f"  - Benefit Estimation Error (BEE): {card['bee']:+.3f} veh.h")
    lines.append(f"  - Realised Decision Regret:       {card['regret']:+.3f} veh.h")
    lines.append("-" * 86)
    lines.append("Note: The Proxy side represents the hidden 'real world' environment used only offline.")
    lines.append("=" * 86)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Offline Decision Audit Decision Card")
    parser.add_argument("--seed", type=int, required=True, help="Random seed (e.g. 4501)")
    parser.add_argument("--belief", type=str, default="B", help="Twin belief variant (default: B)")
    parser.add_argument("--raw-path", type=str, default="results/frozen_audit/raw.parquet",
                        help="Path to raw.parquet")
    args = parser.parse_args()

    raw_file = Path(args.raw_path)
    if not raw_file.exists():
        # Try relative to repo root
        repo_root = Path(__file__).resolve().parents[2]
        raw_file = repo_root / "results" / "frozen_audit" / "raw.parquet"
    if not raw_file.exists():
        print(f"Error: raw file not found at {args.raw_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_parquet(raw_file)
    card = compute_card(df, args.seed, args.belief)
    print(format_card(card))


if __name__ == "__main__":
    main()
