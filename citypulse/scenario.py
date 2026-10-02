"""D1–D4 scenario definition (Kwun Tong Bypass northbound incident, VMS diversion via Kwun Tong Road).

Shared, infrastructure-level knowledge only. Proxy ground truth lives in citypulse/proxy/truth_config.py,
which twin/ and branching/ must never import (tests/test_firewall.py enforces this).
"""

# Shared, infrastructure-level knowledge (a traffic-management centre knows its own VMS and signals).
CONTROL = {
    "vms_edge": "1132732696",                 # Tseung Kwan O Road, upstream of the diverge
    "rejoin_edge": "1133765806",              # Tate's Cairn Tunnel approach
    "vms_target_edge": "312049503",    # KTB northbound section the VMS sign is installed for (fixed infrastructure, not incident truth)
    "corridor_b": ['1132732696', '1132732693', '297494082', '255259364#0', '1134206885', '28112913', '1134206883',
                   '1134206882', '1134206881', '1134206879', '1134206878', '1134206877', '539253996', '494474294',
                   '494474297', '85649754', '288199315', '1134206868', '1134206867', '255261943#0', '253359186',
                   '40529830', '759904151', '1126541184', '1126541183', '675826410#0', '85649711', '813597924',
                   '1198062837', '299215766', '1138078312', '249229836', '808072503', '813908414', '813908411',
                   '997443411', '813908417', '252844448', '813904823', '1133472571', '252844596', '1133472570',
                   '808442420', '1133472559', '1133472554', '808442418', '1133472552', '491908105', '1133426139',
                   '1133426136', '1133765809', '590544888', '1133765818', '1133765806'],
    "tls_plan": ["cluster_1023011761_491588483_991762813", "GS_474385689",
                 "GS_cluster_2296597387_2296597394_479758923",
                 "joinedS_3688277387_cluster_1691725984_993701523_cluster_519547925_993701172"],
}

TWIN_ASSUMED_COMPLIANCE = 0.30
