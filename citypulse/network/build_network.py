"""Download the corridor OSM extract (Overpass) and build the full left-hand SUMO network (net_full.net.xml).

The network actually used (net.net.xml) is the motorway/trunk + named-corridor pruning of it (see README)."""
import argparse
import subprocess

import requests

from citypulse.config import BBOX, NET_FILE, OSM_FILE, RESULTS, sumo_bin

FULL_NET = NET_FILE.parent / "net_full.net.xml"

HIGHWAYS = "motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|tertiary|tertiary_link"
OVERPASS = "https://overpass-api.de/api/interpreter"

NETCONVERT_ARGS = [
    "--lefthand", "--geometry.remove", "--ramps.guess", "--junctions.join",
    "--tls.guess-signals", "--tls.discard-simple", "--tls.join", "--tls.default-type", "static",
    "--roundabouts.guess", "--remove-edges.isolated", "--keep-edges.components", "1",
    "--no-turnarounds", "--output.street-names", "--output.original-names", "--edges.join",
    "--proj.utm", "true",
]


def download():
    s, w, n, e = BBOX
    q = (f'[out:xml][timeout:120];(way["highway"~"^({HIGHWAYS})$"]({s},{w},{n},{e}););(._;>;);out body;')
    r = requests.post(OVERPASS, data={"data": q}, headers={"User-Agent": "CityPulse-research/0.1"}, timeout=300)
    r.raise_for_status()
    OSM_FILE.parent.mkdir(parents=True, exist_ok=True)
    OSM_FILE.write_bytes(r.content)
    print(f"OSM: {len(r.content)} bytes -> {OSM_FILE}")


def build():
    FULL_NET.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sumo_bin("netconvert"), "--osm-files", str(OSM_FILE), "-o", str(FULL_NET)] + NETCONVERT_ARGS
    with open(RESULTS / "netconvert.log", "w") as fh:
        subprocess.run(cmd, check=True, stderr=fh)
    print(f"net -> {FULL_NET}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-download", action="store_true")
    a = ap.parse_args()
    if not a.skip_download:
        download()
    build()
