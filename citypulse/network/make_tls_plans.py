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


def main():
    net = sumolib.net.readNet(str(NET_FILE), withPrograms=True)
    fav = set(CONTROL["corridor_b"])
    out = ["<additional>"]
    for tid in CONTROL["tls_plan"]:
        tl = net.getTLS(tid)
        prog = list(tl.getPrograms().values())[0]
        fav_idx = {idx for (inl, _outl, idx) in tl.getConnections() if inl.getEdge().getID() in fav}
        out.append(f'  <tlLogic id={quoteattr(tid)} programID="P_inc" offset="0" type="static">')
        for ph in prog.getPhases():
            serves = any(i < len(ph.state) and ph.state[i] in "Gg" for i in fav_idx) and "G" in ph.state
            dur = ph.duration * FACTOR if serves else max(MIN_GREEN, ph.duration)
            out.append(f'    <phase duration="{dur:.0f}" state="{ph.state}"/>')
        out.append("  </tlLogic>")
    out.append("</additional>")
    (SCEN / "tls_incident.add.xml").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote P_inc for {len(CONTROL['tls_plan'])} signals")


if __name__ == "__main__":
    main()
