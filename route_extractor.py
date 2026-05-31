"""Per-day route enrichment.

Wraps route loading + `ElevationIntegrator` to produce per-day objects
ready for the page composer and the Garmin exporter.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

import config
import trek_data
from elevation_integrator import ElevationIntegrator, GainLoss
from kml_parser import (
    DaySegment,
    PathPoint,
    Waypoint,
    haversine_miles,
    load_kml,
    load_route_json,
)

log = logging.getLogger(__name__)


# Fixed map-cell geometry that drives 1:24,000 sheet sizing.
# Map cell is placed with `fig.add_axes` at exactly these inch dimensions.
MAP_CELL_WIDTH_IN = 7.5
MAP_CELL_HEIGHT_IN = 5.0
PHILMONT_MID_LAT = 36.4

# Margin around the trail inside a sheet window — leaves room for camp
# labels, contour labels, and a small visual buffer at the bbox edge.
SHEET_FIT_FRACTION = 0.85


def sheet_window_degrees(
    scale: int = 24000,
    map_width_in: float = MAP_CELL_WIDTH_IN,
    map_height_in: float = MAP_CELL_HEIGHT_IN,
    mid_lat: float = PHILMONT_MID_LAT,
) -> Tuple[float, float]:
    """Return (lat_range_deg, lon_range_deg) covered by the map cell at scale."""
    inches_per_mile = 63360.0
    width_mi = map_width_in * scale / inches_per_mile
    height_mi = map_height_in * scale / inches_per_mile
    lat_range = height_mi / 69.0
    lon_range = width_mi / (69.0 * math.cos(math.radians(mid_lat)))
    return lat_range, lon_range


@dataclass
class EnrichedDay:
    day: int
    from_camp: str
    to_camp: str
    path: List[PathPoint] = field(default_factory=list)
    distance_miles: float = 0.0
    distance_official: float = 0.0
    gain_ft: float = 0.0
    loss_ft: float = 0.0
    elev_min_ft: float = 0.0
    elev_max_ft: float = 0.0
    bounds: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    # (lat_min, lat_max, lon_min, lon_max) with buffer applied
    cumulative_distance_mi: List[float] = field(default_factory=list)
    waypoints: List[Waypoint] = field(default_factory=list)   # camps + passthrough on this day
    callout: Optional[str] = None
    warning: Optional[str] = None
    highlight: Optional[str] = None
    special: Optional[str] = None
    kml_note: Optional[str] = None


def _cumulative_distance(path: List[PathPoint]) -> List[float]:
    cum = [0.0]
    for k in range(1, len(path)):
        d = haversine_miles(
            path[k - 1].lat, path[k - 1].lon,
            path[k].lat, path[k].lon,
        )
        cum.append(cum[-1] + d)
    return cum


def _bounds_with_buffer(
    path: List[PathPoint], buffer_deg: float
) -> Tuple[float, float, float, float]:
    lats = [p.lat for p in path]
    lons = [p.lon for p in path]
    return (
        min(lats) - buffer_deg,
        max(lats) + buffer_deg,
        min(lons) - buffer_deg,
        max(lons) + buffer_deg,
    )


def _camp_waypoints_for_day(
    day: int,
    segments: Dict[int, DaySegment],
    waypoints: Dict[str, Waypoint],
) -> List[Waypoint]:
    """Return start/end camp waypoints plus passthroughs for the given day."""
    out: List[Waypoint] = []
    seg = segments[day]
    if seg.from_camp in waypoints:
        out.append(waypoints[seg.from_camp])
    if seg.to_camp != seg.from_camp and seg.to_camp in waypoints:
        out.append(waypoints[seg.to_camp])
    out.extend(seg.passthrough)
    return out


def build_enriched_days(
    route_path: str | Path, dem_path: str | Path,
) -> Tuple[Dict[int, EnrichedDay], Dict[str, Waypoint], List[PathPoint], List[str]]:
    """Load route data, enrich with SRTM elevations, return per-day rich objects.

    Accepts either route_data.json (preferred) or a .kml file (legacy).
    """
    route_path = Path(route_path)
    if route_path.suffix.lower() == ".json":
        path, waypoints, segments, warnings = load_route_json(route_path)
    else:
        path, waypoints, segments, warnings = load_kml(route_path)
    if warnings:
        for w in warnings:
            log.warning("KML validation: %s", w)
    integrator = ElevationIntegrator(dem_path)
    integrator.assign_elevations(path)
    # Fill waypoint elevations from DEM too (KML elevations are 0).
    for wp in waypoints.values():
        v = integrator.elevation_at(wp.lat, wp.lon)
        wp.elev = float(v) if not np.isnan(v) else 0.0

    days: Dict[int, EnrichedDay] = {}
    for day, seg in segments.items():
        info = trek_data.DAYS.get(day, {})
        gl: GainLoss = integrator.gain_loss(seg.path)
        cum = _cumulative_distance(seg.path)
        bounds = _bounds_with_buffer(seg.path, config.DAY_BBOX_BUFFER_DEG)
        days[day] = EnrichedDay(
            day=day,
            from_camp=seg.from_camp,
            to_camp=seg.to_camp,
            path=seg.path,
            distance_miles=seg.distance_miles,
            distance_official=float(info.get("miles", seg.distance_miles)),
            gain_ft=gl.gain_ft,
            loss_ft=gl.loss_ft,
            elev_min_ft=gl.min_ft,
            elev_max_ft=gl.max_ft,
            bounds=bounds,
            cumulative_distance_mi=cum,
            waypoints=_camp_waypoints_for_day(day, segments, waypoints),
            callout=info.get("callout"),
            warning=info.get("warning"),
            highlight=info.get("highlight"),
            special=info.get("special"),
            kml_note=info.get("kml_note"),
        )
    return days, waypoints, path, warnings


@dataclass
class PageSheet:
    """One printable 8.5x11 page at fixed 1:24,000.

    A short day → 1 sheet. A long day → N sheets, with single-point overlap
    between adjacent sheets so route continuity is visible.
    """
    day: int
    sheet_index: int                       # 1-based
    sheet_count: int
    from_camp: str
    to_camp: str
    # The sub-path covered by this sheet
    sub_path: List[PathPoint] = field(default_factory=list)
    sub_path_offset_mi: float = 0.0        # how far into the full day we are
    sub_distance_mi: float = 0.0
    cumulative_distance_mi: List[float] = field(default_factory=list)
    waypoints: List[Waypoint] = field(default_factory=list)
    # Fixed-scale display window centered on the sub-path
    sheet_extent: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    # (lon_min, lon_max, lat_min, lat_max) for imshow/axes
    scale: int = 24000
    # Full-day context (repeated on every sheet of the same day)
    full_day_distance_mi: float = 0.0
    full_day_distance_official: float = 0.0
    full_day_official_gain_ft: int = 0
    full_day_official_loss_ft: int = 0
    full_day_gain_ft: float = 0.0
    full_day_loss_ft: float = 0.0
    full_day_elev_min_ft: float = 0.0
    full_day_elev_max_ft: float = 0.0
    full_day_path: List[PathPoint] = field(default_factory=list)
    full_day_cumulative_mi: List[float] = field(default_factory=list)
    # Day-level briefing fields
    callout: Optional[str] = None
    warning: Optional[str] = None
    highlight: Optional[str] = None
    special: Optional[str] = None
    kml_note: Optional[str] = None


def _split_path_to_chunks(
    path: List[PathPoint],
    max_lat_range: float,
    max_lon_range: float,
) -> List[Tuple[int, List[PathPoint]]]:
    """Greedy split: walk path, accumulate points until bbox would exceed
    the sheet window, then start a new chunk with a single-point overlap.

    Returns list of (start_index_in_full_path, chunk_points).
    """
    if not path:
        return []
    if len(path) == 1:
        return [(0, list(path))]
    chunks: List[Tuple[int, List[PathPoint]]] = []
    start = 0
    cur_min_lat = cur_max_lat = path[0].lat
    cur_min_lon = cur_max_lon = path[0].lon
    for i in range(1, len(path)):
        p = path[i]
        new_min_lat = min(cur_min_lat, p.lat)
        new_max_lat = max(cur_max_lat, p.lat)
        new_min_lon = min(cur_min_lon, p.lon)
        new_max_lon = max(cur_max_lon, p.lon)
        if (
            (new_max_lat - new_min_lat) > max_lat_range
            or (new_max_lon - new_min_lon) > max_lon_range
        ):
            chunks.append((start, path[start:i]))
            start = i - 1                   # single-point overlap
            anchor = path[start]
            cur_min_lat = min(anchor.lat, p.lat)
            cur_max_lat = max(anchor.lat, p.lat)
            cur_min_lon = min(anchor.lon, p.lon)
            cur_max_lon = max(anchor.lon, p.lon)
        else:
            cur_min_lat, cur_max_lat = new_min_lat, new_max_lat
            cur_min_lon, cur_max_lon = new_min_lon, new_max_lon
    chunks.append((start, path[start:]))
    return chunks


def _chunk_bbox_fits(
    chunk: List[PathPoint], max_lat_range: float, max_lon_range: float
) -> bool:
    if not chunk:
        return True
    lats = [p.lat for p in chunk]
    lons = [p.lon for p in chunk]
    return (max(lats) - min(lats)) <= max_lat_range and \
           (max(lons) - min(lons)) <= max_lon_range


def _rebalance_chunks(
    path: List[PathPoint],
    n: int,
    max_lat_range: float,
    max_lon_range: float,
) -> Optional[List[Tuple[int, List[PathPoint]]]]:
    """Try to split the path into n sheets of roughly equal trail length.

    Returns the new chunks if every chunk fits the window, otherwise None.
    """
    cum = _sub_path_cumulative(path)
    total_mi = cum[-1] if cum else 0.0
    if total_mi <= 0 or n < 2:
        return None
    break_points = [(i + 1) * total_mi / n for i in range(n - 1)]
    indices: List[int] = []
    j = 0
    for target in break_points:
        while j < len(cum) - 1 and cum[j] < target:
            j += 1
        indices.append(j)
    chunks: List[Tuple[int, List[PathPoint]]] = []
    starts = [0] + indices
    ends = indices + [len(path) - 1]
    for s, e in zip(starts, ends):
        # include +1 so e is inclusive
        chunk = path[s: e + 1]
        if not _chunk_bbox_fits(chunk, max_lat_range, max_lon_range):
            return None
        chunks.append((s, chunk))
    return chunks


def _sub_path_cumulative(path: List[PathPoint]) -> List[float]:
    cum = [0.0]
    for k in range(1, len(path)):
        d = haversine_miles(
            path[k - 1].lat, path[k - 1].lon, path[k].lat, path[k].lon
        )
        cum.append(cum[-1] + d)
    return cum


def _sheet_extent(
    sub_path: List[PathPoint],
    lat_range: float,
    lon_range: float,
) -> Tuple[float, float, float, float]:
    """Center the fixed-scale window on the sub-path centroid.

    Returns matplotlib-style (lon_min, lon_max, lat_min, lat_max).
    """
    lats = [p.lat for p in sub_path]
    lons = [p.lon for p in sub_path]
    bbox_min_lat, bbox_max_lat = min(lats), max(lats)
    bbox_min_lon, bbox_max_lon = min(lons), max(lons)
    center_lat = (bbox_min_lat + bbox_max_lat) / 2.0
    center_lon = (bbox_min_lon + bbox_max_lon) / 2.0
    return (
        center_lon - lon_range / 2.0,
        center_lon + lon_range / 2.0,
        center_lat - lat_range / 2.0,
        center_lat + lat_range / 2.0,
    )


def _waypoints_within_extent(
    waypoints: List[Waypoint],
    extent: Tuple[float, float, float, float],
) -> List[Waypoint]:
    lon_min, lon_max, lat_min, lat_max = extent
    return [
        w for w in waypoints
        if lon_min <= w.lon <= lon_max and lat_min <= w.lat <= lat_max
    ]


def split_day_into_sheets(
    day: EnrichedDay,
    scale: int = 24000,
) -> List[PageSheet]:
    """Split one EnrichedDay into 1+ PageSheets sized for a 1:24,000 page."""
    win_lat, win_lon = sheet_window_degrees(scale=scale)
    fit_lat = win_lat * SHEET_FIT_FRACTION
    fit_lon = win_lon * SHEET_FIT_FRACTION

    if not day.path:
        # Layover day — produce a single placeholder sheet centered on the camp.
        return [PageSheet(
            day=day.day,
            sheet_index=1,
            sheet_count=1,
            from_camp=day.from_camp,
            to_camp=day.to_camp,
            sub_path=[],
            sheet_extent=(0.0, 0.0, 0.0, 0.0),
            scale=scale,
            full_day_distance_mi=day.distance_miles,
            full_day_distance_official=day.distance_official,
            full_day_official_gain_ft=trek_data.DAYS.get(day.day, {}).get("gain", 0),
            full_day_official_loss_ft=trek_data.DAYS.get(day.day, {}).get("loss", 0),
            full_day_gain_ft=day.gain_ft,
            full_day_loss_ft=day.loss_ft,
            full_day_elev_min_ft=day.elev_min_ft,
            full_day_elev_max_ft=day.elev_max_ft,
            full_day_path=day.path,
            full_day_cumulative_mi=day.cumulative_distance_mi,
            callout=day.callout,
            warning=day.warning,
            highlight=day.highlight,
            special=day.special,
            kml_note=day.kml_note,
        )]

    chunks = _split_path_to_chunks(day.path, fit_lat, fit_lon)
    # Rebalance: if greedy produced N chunks, try N evenly-sized chunks so a
    # tiny tail (e.g. 0.2 mi) doesn't get its own page. Fall back to greedy if
    # the balanced split would exceed the window.
    if len(chunks) > 1:
        balanced = _rebalance_chunks(day.path, len(chunks), fit_lat, fit_lon)
        if balanced is not None:
            chunks = balanced
    sheets: List[PageSheet] = []
    info = trek_data.DAYS.get(day.day, {})
    off_gain = int(info.get("gain", int(round(day.gain_ft))))
    off_loss = int(info.get("loss", int(round(day.loss_ft))))

    for idx, (start_idx, chunk) in enumerate(chunks, start=1):
        extent = _sheet_extent(chunk, win_lat, win_lon)
        cum = _sub_path_cumulative(chunk)
        offset_mi = (
            day.cumulative_distance_mi[start_idx]
            if start_idx < len(day.cumulative_distance_mi)
            else day.cumulative_distance_mi[-1]
        )
        sub_distance = cum[-1] if cum else 0.0
        sheet_waypoints = _waypoints_within_extent(day.waypoints, extent)
        sheets.append(PageSheet(
            day=day.day,
            sheet_index=idx,
            sheet_count=len(chunks),
            from_camp=day.from_camp,
            to_camp=day.to_camp,
            sub_path=chunk,
            sub_path_offset_mi=offset_mi,
            sub_distance_mi=sub_distance,
            cumulative_distance_mi=cum,
            waypoints=sheet_waypoints,
            sheet_extent=extent,
            scale=scale,
            full_day_distance_mi=day.distance_miles,
            full_day_distance_official=day.distance_official,
            full_day_official_gain_ft=off_gain,
            full_day_official_loss_ft=off_loss,
            full_day_gain_ft=day.gain_ft,
            full_day_loss_ft=day.loss_ft,
            full_day_elev_min_ft=day.elev_min_ft,
            full_day_elev_max_ft=day.elev_max_ft,
            full_day_path=day.path,
            full_day_cumulative_mi=day.cumulative_distance_mi,
            callout=day.callout,
            warning=day.warning,
            highlight=day.highlight,
            special=day.special,
            kml_note=day.kml_note,
        ))
    return sheets


def build_sheets_for_all_days(
    days: Dict[int, EnrichedDay], scale: int = 24000,
) -> List[PageSheet]:
    """Return a flat ordered list of all PageSheets for the trek."""
    sheets: List[PageSheet] = []
    for day in sorted(days):
        sheets.extend(split_day_into_sheets(days[day], scale=scale))
    return sheets


def overview_bounds(
    days: Dict[int, EnrichedDay], buffer_deg: float = 0.015
) -> Tuple[float, float, float, float]:
    """Bounding box covering every day's route."""
    lats: List[float] = []
    lons: List[float] = []
    for d in days.values():
        lats += [p.lat for p in d.path]
        lons += [p.lon for p in d.path]
    return (
        min(lats) - buffer_deg,
        max(lats) + buffer_deg,
        min(lons) - buffer_deg,
        max(lons) + buffer_deg,
    )
