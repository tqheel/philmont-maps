"""Garmin GPX 1.1 exporter.

Produces a GPX file containing the full trek as a single track or as one
track per hiking day, plus all camp / passthrough waypoints. Optional
Douglas-Peucker simplification and elevation-sample-interval thinning.

Spec reference: §5 (Phase 5 — Garmin Format Export) and §12.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import gpxpy
import gpxpy.gpx

import config
import trek_data
from kml_parser import PathPoint, Waypoint, haversine_miles
from route_extractor import EnrichedDay

log = logging.getLogger(__name__)


# Standard Garmin waypoint symbols.
WAYPOINT_SYMBOLS = {
    "camp_staffed":    "Campground",
    "camp_trail":      "Campground",
    "camp_layover":    "Campground",
    "camp_dry":        "Campground",
    "passthrough":     "Waypoint",
    "trailhead_start": "Trail Head",
    "trailhead_end":   "Trail Head",
}


def _thin_by_distance_m(
    path: List[PathPoint], sample_interval_m: float
) -> List[PathPoint]:
    """Keep first/last points; drop intermediate points closer than the interval."""
    if sample_interval_m <= 0 or len(path) < 3:
        return list(path)
    sample_mi = sample_interval_m / 1609.34
    kept = [path[0]]
    accum = 0.0
    for k in range(1, len(path) - 1):
        seg = haversine_miles(
            path[k - 1].lat, path[k - 1].lon, path[k].lat, path[k].lon
        )
        accum += seg
        if accum >= sample_mi:
            kept.append(path[k])
            accum = 0.0
    kept.append(path[-1])
    return kept


def _simplify_track(path: List[PathPoint], tolerance_deg: float = 1e-5):
    """Douglas-Peucker simplification on lon/lat tuples."""
    if len(path) < 3:
        return list(path)
    # Manual implementation — avoids dragging shapely into the exporter.
    def perp_dist(p, a, b):
        if a == b:
            return ((p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2) ** 0.5
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))
        proj = (a[0] + t * dx, a[1] + t * dy)
        return ((p[0] - proj[0]) ** 2 + (p[1] - proj[1]) ** 2) ** 0.5

    def dp(points: List[tuple]) -> List[int]:
        """Douglas-Peucker that returns indices of original points list."""
        if len(points) < 3:
            return list(range(len(points)))
        
        a_idx, b_idx = 0, len(points) - 1
        a, b = points[a_idx], points[b_idx]
        max_d, idx = 0.0, 0
        for i in range(1, len(points) - 1):
            d = perp_dist(points[i], a, b)
            if d > max_d:
                max_d, idx = d, i
        if max_d > tolerance_deg:
            left_indices = dp(points[: idx + 1])
            right_indices = dp(points[idx:])
            # Adjust right_indices by adding the offset
            return left_indices[:-1] + [j + idx for j in right_indices]
        return [a_idx, b_idx]

    raw = [(p.lon, p.lat) for p in path]
    keep_indices = dp(raw)
    return [path[i] for i in keep_indices]


@dataclass
class GarminExportOptions:
    day_segments: bool = False
    include_elevation: bool = True
    include_waypoints: bool = True
    include_timestamps: bool = False
    sample_interval_m: float = config.GARMIN_SAMPLE_INTERVAL_M
    simplify_track: bool = False
    track_name: str = "Philmont South Country Loop (Crew 618-J)"


class GarminExporter:
    def __init__(
        self,
        trek_name: str = "Philmont Trek 2026",
        crew_id: str = "618-J",
    ):
        self.trek_name = trek_name
        self.crew_id = crew_id

    def export_to_gpx(
        self,
        days: Dict[int, EnrichedDay],
        waypoints: Dict[str, Waypoint],
        output_path: str | Path,
        opts: Optional[GarminExportOptions] = None,
    ) -> Path:
        opts = opts or GarminExportOptions()
        gpx = gpxpy.gpx.GPX()
        gpx.version = "1.1"
        gpx.creator = "Crew 618-J Topo Map Generator"
        gpx.name = self.trek_name
        gpx.description = (
            f"{trek_data.CREW_618J['route']}, "
            f"{trek_data.CREW_618J['total_distance_miles']} mi, "
            f"{trek_data.CREW_618J['start_date']} – "
            f"{trek_data.CREW_618J['end_date']}"
        )

        if opts.include_waypoints:
            self._add_waypoints(gpx, waypoints)

        if opts.day_segments:
            for day in sorted(days):
                d = days[day]
                if not d.path or d.distance_miles == 0:
                    continue
                info = trek_data.DAYS.get(day, {})
                trk = gpxpy.gpx.GPXTrack(
                    name=f"Day {day}: {d.from_camp} → {d.to_camp}",
                    description=(
                        f"{info.get('miles', d.distance_miles):.1f} miles, "
                        f"+{int(round(d.gain_ft))}' / "
                        f"-{int(round(d.loss_ft))}'"
                    ),
                )
                trk.type = "hiking"
                self._add_segment(trk, d.path, opts)
                gpx.tracks.append(trk)
        else:
            trk = gpxpy.gpx.GPXTrack(
                name=opts.track_name,
                description=(
                    f"{trek_data.CREW_618J['total_distance_miles']} miles, "
                    f"{trek_data.CREW_618J['total_elevation_gain_ft']}' total gain"
                ),
            )
            trk.type = "hiking"
            full_path: List[PathPoint] = []
            for day in sorted(days):
                d = days[day]
                if not d.path or d.distance_miles == 0:
                    continue
                full_path.extend(d.path)
            self._add_segment(trk, full_path, opts)
            gpx.tracks.append(trk)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w") as fh:
            fh.write(gpx.to_xml())
        log.info("Wrote %s (%d tracks, %d waypoints)",
                 output_path, len(gpx.tracks), len(gpx.waypoints))
        return output_path

    # ── Internal helpers ───────────────────────────────────────────────────

    def _add_waypoints(self, gpx, waypoints: Dict[str, Waypoint]) -> None:
        for name, wp in waypoints.items():
            sym = WAYPOINT_SYMBOLS.get(wp.type, "Waypoint")
            desc = self._waypoint_description(wp)
            gpx_wp = gpxpy.gpx.GPXWaypoint(
                latitude=wp.lat, longitude=wp.lon,
                elevation=wp.elev if wp.elev else None,
                name=wp.name,
                description=desc,
                symbol=sym,
            )
            gpx_wp.type = wp.type
            gpx.waypoints.append(gpx_wp)

    @staticmethod
    def _waypoint_description(wp: Waypoint) -> str:
        for day, camp in trek_data.CAMPS.items():
            base = camp["name"].split(" (")[0]
            if wp.name.startswith(base):
                return (
                    f"Day {day} {camp['type']} camp — "
                    f"{int(camp['elevation'])} ft"
                )
        if wp.type == "passthrough":
            return "Passthrough waypoint"
        if wp.type == "trailhead_start":
            return "Rayado Trailhead"
        if wp.type == "trailhead_end":
            return "Base Camp finish"
        return ""

    def _add_segment(self, track, path: List[PathPoint],
                     opts: GarminExportOptions) -> None:
        seg_path = path
        if opts.simplify_track:
            seg_path = _simplify_track(seg_path)
        seg_path = _thin_by_distance_m(seg_path, opts.sample_interval_m)
        seg = gpxpy.gpx.GPXTrackSegment()
        for p in seg_path:
            elev = p.elev if (opts.include_elevation and p.elev) else None
            seg.points.append(gpxpy.gpx.GPXTrackPoint(
                latitude=p.lat, longitude=p.lon, elevation=elev,
            ))
        track.segments.append(seg)
