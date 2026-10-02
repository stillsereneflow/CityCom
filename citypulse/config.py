"""Paths and constants shared by all modules."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HK_DIR = DATA / "hk"
OSM_FILE = DATA / "osm" / "kwuntong.osm.xml"
SCEN = ROOT / "scenarios" / "kwuntong"
NET_FILE = SCEN / "net.net.xml"
RESULTS = ROOT / "results"
FIGS = ROOT / "docs" / "figures"

# Corridor bounding box (lat_min, lon_min, lat_max, lon_max), from TD detector coordinates + margin.
BBOX = (22.300, 114.196, 22.338, 114.240)

# Hong Kong TD feeds (URLs taken from the data.gov.hk CKAN package metadata, 2026-10-02).
HK_RAW_URL = "https://resource.data.one.gov.hk/td/traffic-detectors/rawSpeedVol-all.xml"
HK_LOC_URL = "https://static.data.gov.hk/td/traffic-data-strategic-major-roads/info/traffic_speed_volume_occ_info.csv"
HK_ARCHIVE_LIST = "https://api.data.gov.hk/v1/historical-archive/list-file-versions"
HK_ARCHIVE_GET = "https://api.data.gov.hk/v1/historical-archive/get-file"

# Detector id prefixes on the corridor: Kwun Tong Bypass (AID02), Kai Fuk Road (AID05), Kwun Tong Road (AID07).
CORRIDOR_PREFIXES = ("AID02", "AID05", "AID07")

SENSOR_PERIOD = 30  # s, matches TD raw data aggregation


def sumo_home() -> str:
    """The eclipse-sumo wheel's SUMO_HOME. Read from the package, not the environment: importing libsumo
    rewrites os.environ['SUMO_HOME'] to the sumo_data package, which has no bin/ or tools/."""
    import sumo
    os.environ["SUMO_HOME"] = sumo.SUMO_HOME
    return sumo.SUMO_HOME


def sumo_bin(name: str = "sumo") -> str:
    from pathlib import Path as P
    exe = P(sumo_home()) / "bin" / (name + (".exe" if os.name == "nt" else ""))
    return str(exe)
