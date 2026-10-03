"""Run the production Twin service in-process with an insertion recorder (verification harness).

Executes exactly ``citypulse.twin.service.main()``. The only change is a wrapper around
``TwinDemandStream.insert_due``: the original method is called unchanged (same SUMO calls, same
order), and the ids it inserted are then reconstructed from the same acceptance rule
(``u_n < acceptance(entry)``) over the candidates it consumed. Used by the NA-300 replay check to
compare the online Twin's insertions with a branch replay's insertions.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from citypulse.twin.demand_stream import TwinDemandStream  # noqa: E402

_orig_insert_due = TwinDemandStream.insert_due
INSERTS = []


def _recording_insert_due(self, tc, t, vtype="tdist"):
    ptr0 = self.ptr
    n = _orig_insert_due(self, tc, t, vtype)
    for i in range(ptr0, self.ptr):
        _dep, vid, edges = self.cands[i]
        if self.u[i] < self.acceptance(edges[0]):
            INSERTS.append({"t": float(t), "vid": vid, "entry": edges[0]})
    return n


TwinDemandStream.insert_due = _recording_insert_due

from citypulse.twin.service import main  # noqa: E402


if __name__ == "__main__":
    _out = None
    for _i, _a in enumerate(sys.argv):
        if _a == "--out":
            _out = Path(sys.argv[_i + 1])
    main()
    if _out is not None:
        (_out / "twin_inserts.json").write_text(json.dumps(INSERTS), encoding="utf-8")
        print(f"recorded {len(INSERTS)} insertions -> {_out / 'twin_inserts.json'}")
