"""Route data loading for Itinerary 1 — Crew 618-J.

Two loaders are provided:
  load_route_json(json_path) — reads route_data.json (canonical; no license restrictions)
  load_kml(kml_path)        — reads PhilTrek KML (licensed; kept for re-extraction only)

Both return (path, waypoints, segments, warnings) with identical types.
"""

from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

import config
import trek_data

log = logging.getLogger(__name__)


KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}


@dataclass
class PathPoint:
    lon: float
    lat: float
    elev: float = 0.0     # raw KML elevation (typically 0; SRTM fills this in)
    index: int = 0


@dataclass
class Waypoint:
    name: str
    type: str             # "trailhead_start" | "trailhead_end" | "camp" | "passthrough"
    lon: float
    lat: float
    elev: float = 0.0
    path_index: Optional[int] = None       # snapped index into the path
    snap_distance_mi: Optional[float] = None


@dataclass
class DaySegment:
    day: int
    from_camp: str
    to_camp: str
    path: List[PathPoint] = field(default_factory=list)
    distance_miles: float = 0.0
    # passthrough waypoints assigned to this day (sub-segments)
    passthrough: List[Waypoint] = field(default_factory=list)


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = config.EARTH_RADIUS_MI
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlon / 2) ** 2
    return float(R * 2 * np.arcsin(np.sqrt(a)))


def _strip_passthrough_suffix(name: str) -> str:
    """Drop the "(passthrough)" / "(layover)" suffix used in PhilTrek names."""
    for suffix in (" (passthrough)", " (layover)"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


class KMLParser:
    """Parse PhilTrek-style KML into path + waypoints."""

    def __init__(self, kml_path: str | Path):
        self.kml_path = Path(kml_path)
        if not self.kml_path.exists():
            raise FileNotFoundError(f"KML not found: {self.kml_path}")
        self.tree = ET.parse(self.kml_path)
        self.root = self.tree.getroot()

    # ── Path ───────────────────────────────────────────────────────────────

    def extract_path(self) -> List[PathPoint]:
        line = self.root.find(".//kml:LineString/kml:coordinates", KML_NS)
        if line is None or not line.text:
            raise ValueError(f"No <LineString>/<coordinates> in {self.kml_path}")
        coords_text = line.text.strip()
        path: List[PathPoint] = []
        for raw in coords_text.split():
            raw = raw.strip().rstrip(",")
            if not raw:
                continue
            parts = raw.split(",")
            if len(parts) < 2:
                log.warning("Skipping malformed coordinate: %r", raw)
                continue
            try:
                lon = float(parts[0])
                lat = float(parts[1])
                elev = float(parts[2]) if len(parts) > 2 else 0.0
            except ValueError:
                log.warning("Skipping non-numeric coordinate: %r", raw)
                continue
            path.append(PathPoint(lon=lon, lat=lat, elev=elev, index=len(path)))
        if len(path) < 700:
            log.warning("Path has %d points (expected ≥700)", len(path))
        return path

    # ── Waypoints ──────────────────────────────────────────────────────────

    def extract_waypoints(self) -> Dict[str, Waypoint]:
        waypoints: Dict[str, Waypoint] = {}
        for pm in self.root.findall(".//kml:Placemark", KML_NS):
            name_elem = pm.find("kml:name", KML_NS)
            style_elem = pm.find("kml:styleUrl", KML_NS)
            coords_elem = pm.find(".//kml:Point/kml:coordinates", KML_NS)
            if name_elem is None or style_elem is None or coords_elem is None:
                continue                          # path placemark, not a marker
            name = (name_elem.text or "").strip()
            style = (style_elem.text or "").strip()
            try:
                parts = coords_elem.text.strip().split(",")
                lon, lat = float(parts[0]), float(parts[1])
                elev = float(parts[2]) if len(parts) > 2 else 0.0
            except (ValueError, AttributeError):
                log.warning("Skipping waypoint with invalid coords: %r", name)
                continue
            if "markerStart" in style:
                wp_type = "trailhead_start"
            elif "markerEnd" in style:
                wp_type = "trailhead_end"
            elif "markerCamp" in style:
                wp_type = "camp"
            elif "markerPass" in style:
                wp_type = "passthrough"
            else:
                wp_type = "poi"
            waypoints[name] = Waypoint(
                name=name, type=wp_type, lon=lon, lat=lat, elev=elev
            )
        return waypoints

    # ── Snapping ───────────────────────────────────────────────────────────

    @staticmethod
    def snap_to_path(
        waypoint: Waypoint, path: List[PathPoint]
    ) -> Tuple[int, float]:
        """Return (index of nearest path point, distance in miles)."""
        if not path:
            raise ValueError("Empty path passed to snap_to_path")
        lat_arr = np.array([p.lat for p in path])
        lon_arr = np.array([p.lon for p in path])
        # Vectorised haversine — fast enough for 762 points × 15 waypoints.
        p1 = np.radians(waypoint.lat)
        p2 = np.radians(lat_arr)
        dlat = np.radians(lat_arr - waypoint.lat)
        dlon = np.radians(lon_arr - waypoint.lon)
        a = np.sin(dlat / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlon / 2) ** 2
        d = 2 * config.EARTH_RADIUS_MI * np.arcsin(np.sqrt(a))
        idx = int(np.argmin(d))
        return idx, float(d[idx])

    # ── Day segmentation ──────────────────────────────────────────────────

    def segment_path_by_camps(
        self, path: List[PathPoint], waypoints: Dict[str, Waypoint]
    ) -> Dict[int, DaySegment]:
        return _build_segments(path, waypoints)


def _build_segments(
    path: List[PathPoint], waypoints: Dict[str, Waypoint]
) -> Dict[int, DaySegment]:
    """Snap waypoints to the path and return per-day DaySegment objects.

    Shared by both load_route_json() and KMLParser.segment_path_by_camps().
    """
    # Snap every camp in the canonical sequence to the path.
    for camp_name in trek_data.KML_CAMP_NAMES:
        wp = waypoints.get(camp_name)
        if wp is None:
            log.warning("Camp '%s' missing from route data; skipping", camp_name)
            continue
        idx, snap_mi = KMLParser.snap_to_path(wp, path)
        wp.path_index = idx
        wp.snap_distance_mi = snap_mi
        if snap_mi > 0.1:
            log.warning(
                "%s snapped %.2f mi from nearest path point (idx=%d)",
                camp_name, snap_mi, idx,
            )

    # Assign passthroughs to days by matching their name to DAYS metadata.
    passthrough_by_day: Dict[int, List[Waypoint]] = {}
    for wp in waypoints.values():
        if wp.type != "passthrough":
            continue
        idx, snap_mi = KMLParser.snap_to_path(wp, path)
        wp.path_index = idx
        wp.snap_distance_mi = snap_mi
        short = _strip_passthrough_suffix(wp.name)
        for day, info in trek_data.DAYS.items():
            if short in (info.get("passthrough") or []):
                passthrough_by_day.setdefault(day, []).append(wp)
                break

    segments: Dict[int, DaySegment] = {}
    for (from_camp, to_camp), day in trek_data.DAY_SEGMENT_MAP.items():
        wp_from = waypoints.get(from_camp)
        wp_to = waypoints.get(to_camp)
        if wp_from is None or wp_to is None:
            log.warning("Day %d skipped — missing %s or %s", day, from_camp, to_camp)
            continue
        i, j = wp_from.path_index, wp_to.path_index
        if i is None or j is None:
            continue
        if i <= j:
            seg_path = path[i : j + 1]
        else:
            seg_path = list(reversed(path[j : i + 1]))
        dist = 0.0
        for k in range(len(seg_path) - 1):
            dist += haversine_miles(
                seg_path[k].lat, seg_path[k].lon,
                seg_path[k + 1].lat, seg_path[k + 1].lon,
            )
        segments[day] = DaySegment(
            day=day,
            from_camp=from_camp,
            to_camp=to_camp,
            path=seg_path,
            distance_miles=dist,
            passthrough=passthrough_by_day.get(day, []),
        )

    # Day 7 — Beaubien layover (no path, but list it for completeness).
    if 7 not in segments:
        beaubien = waypoints.get("Beaubien (layover)")
        if beaubien is not None and beaubien.path_index is not None:
            segments[7] = DaySegment(
                day=7,
                from_camp="Beaubien (layover)",
                to_camp="Beaubien (layover)",
                path=[path[beaubien.path_index]],
                distance_miles=0.0,
            )
    return segments


def validate(
    path: List[PathPoint], waypoints: Dict[str, Waypoint]
) -> List[str]:
    """Lightweight sanity checks; returns a list of warnings."""
    warnings: List[str] = []
    if len(path) < 700:
        warnings.append(f"Path has only {len(path)} points (expected ≥700)")
    n_camps = sum(1 for w in waypoints.values() if w.type == "camp")
    n_pass = sum(1 for w in waypoints.values() if w.type == "passthrough")
    n_trail = sum(
        1 for w in waypoints.values()
        if w.type in {"trailhead_start", "trailhead_end"}
    )
    if n_camps < 9:
        warnings.append(f"Only {n_camps} camps (expected ≥9)")
    if n_pass < 3:
        warnings.append(f"Only {n_pass} passthrough markers (expected ≥3)")
    if n_trail < 2:
        warnings.append(f"Only {n_trail} trailhead markers (expected 2)")
    for p in path:
        if not (36.30 <= p.lat <= 36.60 and -105.25 <= p.lon <= -104.85):
            warnings.append(
                f"Path point {p.index} out of Philmont bounds: "
                f"lat={p.lat:.4f}, lon={p.lon:.4f}"
            )
            break
    return warnings


def load_route_json(json_path: str | Path):
    """Load route from route_data.json. Returns (path, waypoints, segments, warnings).

    The JSON has no source attribution — it contains only coordinate arrays
    extracted from the original licensed KML.
    """
    data = json.loads(Path(json_path).read_text())
    path: List[PathPoint] = [
        PathPoint(lon=pt[0], lat=pt[1], elev=pt[2] if len(pt) > 2 else 0.0, index=i)
        for i, pt in enumerate(data["track"])
    ]
    waypoints: Dict[str, Waypoint] = {
        wp["name"]: Waypoint(
            name=wp["name"],
            type=wp["type"],
            lon=wp["lon"],
            lat=wp["lat"],
            elev=wp.get("elev", 0.0),
        )
        for wp in data["waypoints"]
    }
    warnings = validate(path, waypoints)
    segments = _build_segments(path, waypoints)
    return path, waypoints, segments, warnings


def load_kml(kml_path: str | Path):
    """Load route from PhilTrek KML. Returns (path, waypoints, segments, warnings).

    Kept for re-extraction when the licensed KML source changes.
    Prefer load_route_json() for normal use.
    """
    parser = KMLParser(kml_path)
    path = parser.extract_path()
    waypoints = parser.extract_waypoints()
    warnings = validate(path, waypoints)
    segments = _build_segments(path, waypoints)
    return path, waypoints, segments, warnings
