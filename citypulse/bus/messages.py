"""Information firewall: the ONLY two message types allowed between Proxy and the online Twin.

SensorMsg (Proxy -> Twin):  {"type": "sensor", "t": float, "period": int, "obs": [ObsItem, ...]}
    ObsItem: {"detector": str, "q": int|None, "v": float|None, "o": float|None, "valid": bool}
ReplyMsg  (Twin -> Proxy):  {"type": "reply", "t": float, "actions": [ActionItem, ...]}
    ActionItem: {"action": str, "params": dict}   # infrastructure-level only (see control/actions.py)

Anything else is rejected. Validation runs on BOTH sides, so a Proxy bug that adds a field
(e.g. an incident flag) is caught at the Twin boundary instead of silently leaking.
"""

SENSOR_KEYS = {"type", "t", "period", "obs"}
OBS_KEYS = {"detector", "q", "v", "o", "valid"}
REPLY_KEYS = {"type", "t", "actions"}
ACTION_KEYS = {"action", "params"}
ALLOWED_ACTIONS = {"A0", "A1", "A2", "A3", "A4"}
ALLOWED_PARAM_KEYS = {"tls_program", "vms_corridor", "compliance_claim"}


class FirewallViolation(ValueError):
    pass


def _exact(d, keys, what):
    if not isinstance(d, dict) or set(d) != keys:
        raise FirewallViolation(f"{what}: keys {sorted(d) if isinstance(d, dict) else type(d)} != {sorted(keys)}")


def validate_sensor(msg):
    _exact(msg, SENSOR_KEYS, "SensorMsg")
    if msg["type"] != "sensor" or not isinstance(msg["obs"], list):
        raise FirewallViolation("SensorMsg: bad type/obs")
    for o in msg["obs"]:
        _exact(o, OBS_KEYS, "ObsItem")
        if not isinstance(o["detector"], str) or not isinstance(o["valid"], bool):
            raise FirewallViolation("ObsItem: bad field types")
        for k in ("q", "v", "o"):
            if o[k] is not None and not isinstance(o[k], (int, float)):
                raise FirewallViolation(f"ObsItem.{k}: not numeric")
    return msg


def validate_reply(msg):
    _exact(msg, REPLY_KEYS, "ReplyMsg")
    if msg["type"] != "reply":
        raise FirewallViolation("ReplyMsg: bad type")
    for a in msg["actions"]:
        _exact(a, ACTION_KEYS, "ActionItem")
        if a["action"] not in ALLOWED_ACTIONS or not set(a["params"]) <= ALLOWED_PARAM_KEYS:
            raise FirewallViolation(f"ActionItem not allowed: {a}")
    return msg
