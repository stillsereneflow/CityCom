"""Pre-build the A1 incident signal plans ("P_inc") as an additional file.

Snapshot tests showed SUMO 1.27.1 cannot load a state whose active program was created at runtime
via setProgramLogic ("Unknown program"). So every plan an action may switch to must be predefined
and loaded by Proxy, Twin and every branch.
"""
from xml.sax.saxutils import quoteattr

import sumolib

from citypulse.config import NET_FILE, SCEN
from citypulse.scenario import CONTROL

FACTOR, MIN_GREEN = 1.5, 5


def main(argv=None):
    import argparse
    from pathlib import Path
    ap = argparse.ArgumentParser(description="Pre-build A1 incident signal plans")
    ap.add_argument("--net", default=str(NET_FILE), help="SUMO network file")
    ap.add_argument("--output", default=str(SCEN / "tls_incident.add.xml"), help="Output XML file")
    args = ap.parse_args(argv)

    net = sumolib.net.readNet(args.net, withPrograms=True)
    all_tls = {tl.getID() for tl in net.getTrafficLights()}
    missing = [t for t in CONTROL["tls_plan"] if t not in all_tls]
    if missing:
        print(f"Warning: signals in CONTROL['tls_plan'] missing from {args.net}: {missing}")
    else:
        print(f"All {len(CONTROL['tls_plan'])} signals exist in network.")

    fav = set(CONTROL["corridor_b"])
    out = ["<additional>"]
    written = 0
    for tid in CONTROL["tls_plan"]:
        if tid not in all_tls:
            continue
        tl = net.getTLS(tid)
        prog = list(tl.getPrograms().values())[0]
        fav_idx = {idx for (inl, _outl, idx) in tl.getConnections() if inl.getEdge().getID() in fav}
        out.append(f'  <tlLogic id={quoteattr(tid)} programID="P_inc" offset="0" type="static">')
        for ph in prog.getPhases():
            serves = any(i < len(ph.state) and ph.state[i] in "Gg" for i in fav_idx) and "G" in ph.state
            dur = ph.duration * FACTOR if serves else max(MIN_GREEN, ph.duration)
            out.append(f'    <phase duration="{dur:.0f}" state="{ph.state}"/>')
        out.append("  </tlLogic>")
        written += 1
    out.append("</additional>")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote P_inc for {written} signals")


if __name__ == "__main__":
    main()
