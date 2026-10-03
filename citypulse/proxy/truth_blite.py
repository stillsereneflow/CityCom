"""B-lite Proxy-only ground truth and evaluation pair. NEVER import from twin/ or branching/."""

# Detector triple bracketing the incident (evaluation plots only, chosen before any run).
EVAL_PAIR = {"U2": "AID02109", "U": "AID02110", "D": "AID02111"}

# Proxy-only ground truth: stopped vehicles on ktb_n1 (B-lite naming, see docs/blite-spec.md).
PROXY_ONLY = {
    "incident": {"edge": "ktb_n1", "lanes": [0, 1], "pos": 900.0, "t_start": 4500.0, "duration": 900.0},
    "vms_true_compliance": 0.35,
}
