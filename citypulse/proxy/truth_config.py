"""Proxy-only ground truth and evaluation pair. NEVER import from twin/ or branching/."""

# Detector pair bracketing the incident (used only for evaluation plots, chosen before any run).
EVAL_PAIR = {"U": "AID02110", "D": "AID02111", "U2": "AID02109"}

# Proxy-only ground truth.
PROXY_ONLY = {
    "incident": {"edge": "312049503", "lanes": [0, 1], "pos": 900.0, "t_start": 1200.0, "duration": 900.0},
    "vms_true_compliance": 0.35,
}
