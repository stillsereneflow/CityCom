"""B-lite CONTROL mapping (simplified research model, see docs/blite-spec.md).

Infrastructure only: a traffic-management centre knows its own VMS, signals and
cross-street assumptions.  Proxy ground truth lives in citypulse/proxy/truth_blite.py and
must never be imported from twin/ or branching/.
"""

# Shared, infrastructure-level knowledge.
CONTROL = {
    "vms_edge": "tko_vms",
    "rejoin_edge": "rejoin",
    "vms_target_edge": "ktb_n1",
    "corridor_b": ["tko_vms", "tko_a1", "ktr_w1", "ktr_w2", "ktr_w3", "ktr_w4", "ktr_w5",
                   "ktr_w6", "rejoin"],
    "tls_plan": ["S1", "S2", "S3", "S4"],
}

# Cross-street demand is scenario-assumed (TD/HK plans for these junctions are unknown).
CROSS_STREET_DEFAULT_VPH = 400      # declared default per stub
CROSS_STREET_RANGE_VPH = (0, 1800)  # declared range per stub

TWIN_ASSUMED_COMPLIANCE = 0.30
