#!/usr/bin/env python3
"""
generate_web_assets.py

Converts PDF maps to PNG images and writes route.json for the Philmont crew website.
Run once (or after regenerating PDFs) before `npm run dev` in web/.

Usage:
    python3 generate_web_assets.py
"""

import json
import math
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

REPO = Path(__file__).parent
OUTPUT = REPO / "output"
WEB = REPO / "web"
MAPS = WEB / "public" / "maps"
DATA = WEB / "public" / "data"
GPX = OUTPUT / "crew_618j.gpx"
NS = "http://www.topografix.com/GPX/1/1"

PNG_DPI = 150  # 150 DPI → ~1275×1650 px per page, good for retina web display

# Camp waypoints in trek order — used to split the single GPX track into day segments.
# (name, lat, lon)
CAMP_SEQUENCE = [
    ("Start",          36.36523,   -104.930362),
    ("Olympia",        36.371734,  -104.968928),
    ("Abreu",          36.379133,  -105.015701),
    ("Fish Camp",      36.38782,   -105.10272),
    ("Buck Creek",     36.411196,  -105.130419),
    ("Beaubien",       36.423576,  -105.103246),
    ("Miners Park",    36.423674,  -105.041596),
    ("Bear Caves",     36.404802,  -105.033858),
    ("Urraca",         36.408988,  -104.990507),
    ("Stockade Ridge", 36.437662,  -105.007633),
    ("End",            36.453513,  -104.96248),
]

# Hiking days in order (Day 7 is layover — no GPX segment)
HIKING_DAYS = [2, 3, 4, 5, 6, 8, 9, 10, 11, 12]

DAY_COLORS = {
    2: "#ef4444",   # red
    3: "#f97316",   # orange
    4: "#eab308",   # yellow-600
    5: "#22c55e",   # green
    6: "#14b8a6",   # teal
    7: "#6366f1",   # indigo (layover marker only)
    8: "#3b82f6",   # blue
    9: "#8b5cf6",   # violet
    10: "#ec4899",  # pink
    11: "#f59e0b",  # amber
    12: "#78716c",  # stone
}

# ── Utilities ─────────────────────────────────────────────────────────────────

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def haversine_mi(lat1, lon1, lat2, lon2):
    return haversine_m(lat1, lon1, lat2, lon2) / 1609.344


def nearest_index(points, lat, lon):
    return min(range(len(points)), key=lambda i: haversine_m(points[i][0], points[i][1], lat, lon))


# ── PDF → PNG ─────────────────────────────────────────────────────────────────

def generate_pngs():
    MAPS.mkdir(parents=True, exist_ok=True)
    pdfs = ["summary"] + [f"day_{d:02d}" for d in range(2, 13)]

    for stem in pdfs:
        pdf = OUTPUT / f"{stem}.pdf"
        if not pdf.exists():
            print(f"  SKIP {pdf.name} (not found)")
            continue
        prefix = str(MAPS / stem)
        subprocess.run(
            ["pdftoppm", "-r", str(PNG_DPI), "-png", str(pdf), prefix],
            check=True, capture_output=True,
        )
        imgs = sorted(MAPS.glob(f"{stem}-*.png"))
        print(f"  {stem}.pdf → {len(imgs)} image(s): {[p.name for p in imgs]}")


# ── GPX parsing ───────────────────────────────────────────────────────────────

def parse_gpx():
    """Return list of (lat, lon, elev_ft) tuples for the full track."""
    tree = ET.parse(GPX)
    root = tree.getroot()
    ns = {"g": NS}
    points = []
    for pt in root.findall(".//g:trkpt", ns):
        lat = float(pt.get("lat"))
        lon = float(pt.get("lon"))
        ele_el = pt.find("g:ele", ns)
        elev_m = float(ele_el.text) if ele_el is not None else 0.0
        elev_ft = round(elev_m * 3.28084, 1)
        points.append((lat, lon, elev_ft))
    return points


def split_track_by_day(points):
    """Split the full track into per-day sub-tracks using nearest-waypoint indices."""
    flat = [(lat, lon) for lat, lon, _ in points]
    indices = [nearest_index(flat, lat, lon) for _, lat, lon in CAMP_SEQUENCE]

    segments = {}
    for i, day in enumerate(HIKING_DAYS):
        start = indices[i]
        end = indices[i + 1] + 1  # inclusive
        segments[day] = points[start:end]
    segments[7] = []  # layover, no track
    return segments


def cumulative_distance(segment):
    """Return list of cumulative miles per point."""
    dist = [0.0]
    for i in range(1, len(segment)):
        d = haversine_mi(segment[i-1][0], segment[i-1][1], segment[i][0], segment[i][1])
        dist.append(round(dist[-1] + d, 3))
    return dist


# ── route.json ────────────────────────────────────────────────────────────────

def write_route_json(points, segments):
    DATA.mkdir(parents=True, exist_ok=True)

    days_data = {}
    for day in range(2, 13):
        seg = segments.get(day, [])
        if seg:
            dist = cumulative_distance(seg)
            days_data[str(day)] = {
                "track": [[lat, lon] for lat, lon, _ in seg],
                "elevFt": [e for _, _, e in seg],
                "distMi": dist,
            }
        else:
            days_data[str(day)] = {"track": [], "elevFt": [], "distMi": []}

    route = {
        "colors": {str(k): v for k, v in DAY_COLORS.items()},
        "days": days_data,
    }

    out = DATA / "route.json"
    with open(out, "w") as f:
        json.dump(route, f, separators=(",", ":"))
    total_pts = sum(len(v["track"]) for v in days_data.values())
    print(f"  route.json written ({out.stat().st_size // 1024} KB, {total_pts} total GPS points)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("▸ Converting PDFs to PNGs…")
    generate_pngs()

    print("▸ Parsing GPX track…")
    points = parse_gpx()
    print(f"  {len(points)} track points")
    segments = split_track_by_day(points)

    print("▸ Writing route.json…")
    write_route_json(points, segments)

    print("✓ Done. Run 'cd web && npm install && npm run dev' to start the site.")


if __name__ == "__main__":
    main()
