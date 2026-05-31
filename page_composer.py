"""8.5×11" page composer (fixed 1:24,000 scale, sheet-based).

Each page is one `PageSheet`. Layout uses explicit inch-based positions
(via `fig.add_axes`) so the map cell is exactly 7.5" × 5.0" — which at
1:24,000 covers 2.84 mi E-W × 1.89 mi N-S. Short days render as a single
sheet; long days split into multiple sheets that all share the same optics.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")           # headless backend
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

import config
import trek_data
from coordinate_system import CoordinateSystem, MapScale
from elevation_integrator import ElevationIntegrator, hillshade
from kml_parser import Waypoint
from route_extractor import (
    EnrichedDay,
    PageSheet,
    overview_bounds,
)

log = logging.getLogger(__name__)


# ── Page geometry (inches) ────────────────────────────────────────────────
# Computed so the map cell at 1:24,000 covers exactly 2.84 × 1.89 mi.

PAGE_W = config.PAGE_WIDTH_IN          # 8.5
PAGE_H = config.PAGE_HEIGHT_IN         # 11.0
MARGIN = config.MARGIN_IN              # 0.5
INNER_W = PAGE_W - 2 * MARGIN          # 7.5
HEADER_H = 0.75
MAP_H = 5.0                             # → 1:24,000 vertical span at 36.4°N
PROFILE_H = 1.45
BRIEF_H = 1.85
GAP_MAP_TO_PROFILE = 0.35
GAP_OTHER = 0.15
GAP = GAP_OTHER                         # backwards-compat alias (unused)


def _frac(left_in: float, bottom_in: float,
          width_in: float, height_in: float):
    """Convert inch-rect to fractional [left, bottom, w, h] for fig.add_axes."""
    return [
        left_in / PAGE_W,
        bottom_in / PAGE_H,
        width_in / PAGE_W,
        height_in / PAGE_H,
    ]


def _add_axes_inch(fig, left_in, bottom_in, width_in, height_in):
    return fig.add_axes(_frac(left_in, bottom_in, width_in, height_in))


# ── Waypoint styling ──────────────────────────────────────────────────────

WAYPOINT_STYLE = {
    "camp_staffed":    ("o", config.CAMP_STAFFED_COLOR),
    "camp_trail":      ("o", config.CAMP_TRAIL_COLOR),
    "camp_layover":    ("D", config.CAMP_LAYOVER_COLOR),
    "camp_dry":        ("s", config.CAMP_DRY_COLOR),
    "passthrough":     ("v", config.PASSTHROUGH_COLOR),
    "trailhead_start": ("^", config.TRAILHEAD_COLOR),
    "trailhead_end":   ("^", config.TRAILHEAD_COLOR),
}


def _waypoint_style(wp: Waypoint, day_camp: Optional[dict] = None):
    if wp.type == "camp" and day_camp:
        return WAYPOINT_STYLE.get(
            f"camp_{day_camp['type']}", WAYPOINT_STYLE["camp_trail"]
        )
    if wp.type == "camp":
        return WAYPOINT_STYLE["camp_trail"]
    return WAYPOINT_STYLE.get(wp.type, ("^", "#666666"))


# ── Header ────────────────────────────────────────────────────────────────

def _draw_header(ax, sheet: PageSheet) -> None:
    ax.axis("off")
    # Top row
    crew_line = (
        f"Crew {trek_data.CREW_618J['expedition']}  |  Itinerary "
        f"{trek_data.CREW_618J['itinerary']}"
    )
    if sheet.sheet_count > 1:
        crew_line += f"   ·   Sheet {sheet.sheet_index} of {sheet.sheet_count}"
    ax.text(
        0.0, 0.95, crew_line,
        fontsize=8, weight="bold", va="top", transform=ax.transAxes,
    )
    ax.text(
        1.0, 0.95, f"Generated: {datetime.date.today()}",
        fontsize=7, ha="right", va="top", style="italic", color="#666",
        transform=ax.transAxes,
    )
    # Centred title
    if sheet.sheet_count > 1:
        title = (
            f"Day {sheet.day}: {sheet.from_camp} → {sheet.to_camp}   "
            f"({sheet.full_day_distance_official:.1f} mi total, "
            f"+{sheet.full_day_official_gain_ft:,}′ / "
            f"-{sheet.full_day_official_loss_ft:,}′)"
        )
        subtitle = (
            f"This sheet: miles {sheet.sub_path_offset_mi:.2f}"
            f" – {sheet.sub_path_offset_mi + sheet.sub_distance_mi:.2f}"
        )
    else:
        title = (
            f"Day {sheet.day}: {sheet.from_camp} → {sheet.to_camp}   "
            f"({sheet.full_day_distance_official:.1f} mi, "
            f"+{sheet.full_day_official_gain_ft:,}′ / "
            f"-{sheet.full_day_official_loss_ft:,}′)"
        )
        subtitle = None

    # Title sits in the upper-middle of the header band; subtitle below it.
    title_y = 0.55 if subtitle else 0.40
    ax.text(
        0.5, title_y, title,
        fontsize=12, weight="bold", ha="center", va="center",
        transform=ax.transAxes,
    )
    if subtitle:
        ax.text(
            0.5, 0.18, subtitle,
            fontsize=9, ha="center", va="center",
            color="#444", style="italic", transform=ax.transAxes,
        )


# ── Map cell ──────────────────────────────────────────────────────────────

def _draw_map(
    ax,
    sheet: PageSheet,
    integrator: ElevationIntegrator,
    coord_sys: CoordinateSystem,
) -> None:
    if not sheet.sub_path:
        ax.axis("off")
        ax.text(0.5, 0.5, "Layover day", ha="center", va="center",
                fontsize=20, weight="bold", color="#888", transform=ax.transAxes)
        return

    lon_min, lon_max, lat_min, lat_max = sheet.sheet_extent
    extent = (lon_min, lon_max, lat_min, lat_max)

    # USGS-style: white BG, grayscale hillshade, brown contours.
    ax.set_facecolor(config.MAP_BACKGROUND)
    grid, _grid_extent = integrator.extract_grid((lat_min, lat_max, lon_min, lon_max))
    grid_ft = grid * config.FT_PER_M
    hs = hillshade(grid)
    ax.imshow(
        hs, extent=extent, origin="upper", cmap="gray",
        vmin=0.0, vmax=1.0,
        alpha=config.HILLSHADE_ALPHA, aspect="auto", zorder=1,
    )

    # Brown contours: minor + index lines.
    minor_levels = np.arange(
        np.floor(grid_ft.min() / config.CONTOUR_INTERVAL_FT) * config.CONTOUR_INTERVAL_FT,
        np.ceil(grid_ft.max() / config.CONTOUR_INTERVAL_FT) * config.CONTOUR_INTERVAL_FT,
        config.CONTOUR_INTERVAL_FT,
    )
    major_step = config.CONTOUR_INTERVAL_FT * config.CONTOUR_MAJOR_INTERVAL
    major_levels = np.arange(
        np.floor(grid_ft.min() / major_step) * major_step,
        np.ceil(grid_ft.max() / major_step) * major_step,
        major_step,
    )
    if len(minor_levels):
        ax.contour(
            grid_ft, levels=minor_levels, extent=extent, origin="upper",
            colors=config.CONTOUR_COLOR, linewidths=config.CONTOUR_WEIGHT_PT,
            alpha=0.7, zorder=2,
        )
    if len(major_levels):
        cs = ax.contour(
            grid_ft, levels=major_levels, extent=extent, origin="upper",
            colors=config.CONTOUR_COLOR,
            linewidths=config.CONTOUR_MAJOR_WEIGHT_PT,
            alpha=0.85, zorder=2,
        )
        ax.clabel(
            cs, inline=True, fontsize=config.CONTOUR_LABEL_SIZE, fmt="%d′",
            colors=config.CONTOUR_COLOR,
        )

    # On split-sheet days draw the full day route as a dashed red guide so
    # the reader can see where the trail enters/exits the map window on the
    # adjacent sheet(s). Matplotlib clips to the axes extent automatically.
    if sheet.sheet_count > 1 and sheet.full_day_path:
        ax.plot(
            [p.lon for p in sheet.full_day_path],
            [p.lat for p in sheet.full_day_path],
            color=config.DAY_ROUTE_COLOR,
            linewidth=1.5,
            linestyle=(0, (5, 4)),
            alpha=0.50,
            zorder=3,
        )
    # Today's sub-path in bold solid red (drawn on top of the dashed guide).
    ax.plot(
        [p.lon for p in sheet.sub_path],
        [p.lat for p in sheet.sub_path],
        color=config.DAY_ROUTE_COLOR,
        linewidth=config.DAY_ROUTE_WIDTH_PT,
        zorder=5,
    )

    # Waypoints visible on this sheet.
    for wp in sheet.waypoints:
        camp_info = None
        if wp.type == "camp":
            for c in trek_data.CAMPS.values():
                if c["name"].startswith(wp.name.split(" (")[0]):
                    camp_info = c
                    break
        marker, color = _waypoint_style(wp, camp_info)
        ax.scatter(
            wp.lon, wp.lat, s=config.MARKER_SIZE, marker=marker,
            color=color, edgecolors="black", linewidths=0.9, zorder=10,
        )
        ax.annotate(
            wp.name, xy=(wp.lon, wp.lat),
            xytext=(6, 6), textcoords="offset points",
            fontsize=config.FONT_LABEL["size"],
            weight=config.FONT_LABEL["weight"],
            bbox=dict(boxstyle="round,pad=0.25",
                      facecolor="white", alpha=0.9, edgecolor="none"),
            zorder=11,
        )

    coord_sys.draw(ax, extent)

    # No matplotlib title or tick labels — the rect we placed must equal
    # the data area exactly so the 1:24,000 scale is geometrically true.
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_edgecolor("black")
        spine.set_linewidth(0.8)
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)

    # Scale tag in bottom-right interior corner.
    ax.text(
        lon_max - (lon_max - lon_min) * 0.01,
        lat_min + (lat_max - lat_min) * 0.01,
        f"Scale 1:{sheet.scale:,}",
        fontsize=8, weight="bold",
        ha="right", va="bottom", color="black",
        bbox=dict(boxstyle="round,pad=0.2",
                  facecolor="white", alpha=0.9, edgecolor="#888"),
        zorder=20,
    )
    _draw_scale_bar(ax, lat_min, lat_max, lon_min, lon_max)
    _draw_north_arrow(ax, lat_max, lon_max)


def _draw_scale_bar(ax, lat_min, lat_max, lon_min, lon_max,
                    target_miles: float = 0.5) -> None:
    mid_lat = (lat_min + lat_max) / 2
    deg_per_mile = 1.0 / (69.0 * np.cos(np.radians(mid_lat)))
    bar_deg = target_miles * deg_per_mile
    x0 = lon_min + (lon_max - lon_min) * 0.04
    y0 = lat_min + (lat_max - lat_min) * 0.05
    tick = (lat_max - lat_min) * 0.012
    ax.plot([x0, x0 + bar_deg], [y0, y0], color="black", linewidth=2.5, zorder=20)
    ax.plot([x0, x0], [y0, y0 + tick], color="black", linewidth=2.5, zorder=20)
    ax.plot([x0 + bar_deg, x0 + bar_deg], [y0, y0 + tick],
            color="black", linewidth=2.5, zorder=20)
    ax.text(
        x0 + bar_deg / 2, y0 + tick * 1.4,
        f"{target_miles} mi", ha="center", fontsize=7, weight="bold", zorder=20,
    )


def _draw_north_arrow(ax, lat_max, lon_max) -> None:
    x = lon_max - (lon_max - ax.get_xlim()[0]) * 0.04
    y = lat_max - (lat_max - ax.get_ylim()[0]) * 0.06
    ax.annotate(
        "N", xy=(x, y), xytext=(x, y - 0.005),
        ha="center", fontsize=10, weight="bold",
        arrowprops=dict(facecolor="black", width=2, headwidth=8, headlength=8),
        zorder=20,
    )


# ── Elevation profile ────────────────────────────────────────────────────

def _draw_profile(ax, sheet: PageSheet) -> None:
    if not sheet.sub_path or sheet.sub_distance_mi == 0:
        ax.axis("off")
        if sheet.sheet_count == 1 and sheet.day == 7:
            ax.text(0.5, 0.5,
                    "Layover at Beaubien — no hike",
                    ha="center", va="center",
                    fontsize=11, weight="bold", color="#666")
        return

    # X: real-day mileage (offset added so values match the day, not the sheet)
    sub_cum = np.array(sheet.cumulative_distance_mi)
    x = sub_cum + sheet.sub_path_offset_mi
    elev_ft = np.array([p.elev for p in sheet.sub_path]) * config.FT_PER_M

    ax.fill_between(
        x, elev_ft.min() - 200, elev_ft,
        color=config.PROFILE_FILL_COLOR, alpha=config.PROFILE_FILL_ALPHA,
    )
    ax.plot(
        x, elev_ft, color=config.PROFILE_LINE_COLOR,
        linewidth=config.PROFILE_LINE_WIDTH,
    )

    # Mark visible waypoints on the profile.
    for wp in sheet.waypoints:
        sub_lats = np.array([p.lat for p in sheet.sub_path])
        sub_lons = np.array([p.lon for p in sheet.sub_path])
        if not len(sub_lats):
            continue
        d = (sub_lats - wp.lat) ** 2 + (sub_lons - wp.lon) ** 2
        idx = int(np.argmin(d))
        xv = x[idx]
        yv = elev_ft[idx]
        ax.scatter(
            xv, yv, s=60, marker="o", facecolor=config.DAY_ROUTE_COLOR,
            edgecolor="black", linewidths=0.8, zorder=5,
        )
        ax.annotate(
            wp.name, xy=(xv, yv),
            xytext=(0, 8), textcoords="offset points",
            ha="center", fontsize=7, weight="bold",
        )

    ax.set_xlabel("Distance into Day (miles)",
                  fontsize=config.FONT_AXIS["size"])
    ax.set_ylabel("Elevation (ft)", fontsize=config.FONT_AXIS["size"])

    if sheet.sheet_count > 1:
        title = (
            f"Elevation Profile  —  Sheet {sheet.sheet_index} of "
            f"{sheet.sheet_count}  ·  miles "
            f"{sheet.sub_path_offset_mi:.2f}-"
            f"{sheet.sub_path_offset_mi + sheet.sub_distance_mi:.2f} "
            f"of {sheet.full_day_distance_official:.1f}"
        )
    else:
        title = (
            f"Elevation Profile  —  Official: "
            f"+{sheet.full_day_official_gain_ft:,}′ / "
            f"-{sheet.full_day_official_loss_ft:,}′   "
            f"DEM range: {int(round(sheet.full_day_elev_min_ft))}′ – "
            f"{int(round(sheet.full_day_elev_max_ft))}′"
        )
    ax.set_title(title, fontsize=config.FONT_AXIS["size"] + 1,
                 weight="bold", pad=6)
    ax.grid(True, alpha=0.3, linestyle=":", linewidth=0.5)
    ax.tick_params(labelsize=7)


# ── Briefing box ─────────────────────────────────────────────────────────

def _draw_notes(ax, sheet: PageSheet) -> None:
    ax.axis("off")
    camp = trek_data.CAMPS.get(sheet.day, {})
    lines: List[str] = []
    lines.append(
        f"Camp: {camp.get('name', sheet.to_camp)} "
        f"({camp.get('elevation', '?')} ft, {camp.get('type', '?')})"
    )
    if sheet.callout:
        lines.append(f"⚑ {sheet.callout}")
    if sheet.highlight:
        lines.append(f"★ {sheet.highlight}")
    if sheet.warning:
        lines.append(f"⚠ {sheet.warning}")
    if sheet.special:
        lines.append(f"• {sheet.special}")
    if sheet.kml_note:
        lines.append(f"ℹ KML note: {sheet.kml_note}")
    tomorrow = trek_data.DAYS.get(sheet.day + 1)
    if tomorrow:
        lines.append(
            f"Tomorrow: Day {sheet.day + 1} — "
            f"{tomorrow['from']} → {tomorrow['to']} "
            f"({tomorrow['miles']:.1f} mi, +{tomorrow['gain']:,}′)"
        )

    box = FancyBboxPatch(
        (0.0, 0.0), 1.0, 1.0, boxstyle="round,pad=0.02",
        linewidth=0.8, edgecolor="#888", facecolor="#FAFAFA",
        transform=ax.transAxes, zorder=0,
    )
    ax.add_patch(box)
    heading = f"DAY {sheet.day} BRIEFING"
    if sheet.sheet_count > 1:
        heading += f"   (Sheet {sheet.sheet_index} of {sheet.sheet_count})"
    ax.text(
        0.02, 0.94, heading, transform=ax.transAxes,
        fontsize=9, weight="bold", va="top",
    )
    for i, line in enumerate(lines):
        ax.text(
            0.02, 0.80 - i * 0.11, line,
            transform=ax.transAxes, fontsize=8, va="top",
        )


# ── Single-sheet render ──────────────────────────────────────────────────

def generate_sheet(
    sheet: PageSheet,
    integrator: ElevationIntegrator,
    coord_sys: CoordinateSystem,
    output_path: str | Path,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(PAGE_W, PAGE_H), dpi=config.DPI, facecolor="white")

    # Inch positions (bottom-up).
    bottom_brief = MARGIN
    bottom_profile = bottom_brief + BRIEF_H + GAP_OTHER
    bottom_map = bottom_profile + PROFILE_H + GAP_MAP_TO_PROFILE
    bottom_header = bottom_map + MAP_H + GAP_OTHER

    _draw_header(
        _add_axes_inch(fig, MARGIN, bottom_header, INNER_W, HEADER_H),
        sheet,
    )
    _draw_map(
        _add_axes_inch(fig, MARGIN, bottom_map, INNER_W, MAP_H),
        sheet, integrator, coord_sys,
    )
    _draw_profile(
        _add_axes_inch(fig, MARGIN, bottom_profile, INNER_W, PROFILE_H),
        sheet,
    )
    _draw_notes(
        _add_axes_inch(fig, MARGIN, bottom_brief, INNER_W, BRIEF_H),
        sheet,
    )

    fig.savefig(
        output_path, dpi=config.DPI, format="pdf",
        facecolor="white", edgecolor="none",
    )
    plt.close(fig)
    log.info("Wrote %s", output_path)
    return output_path


# ── Summary / overview ───────────────────────────────────────────────────

def generate_summary_map(
    days: Dict[int, EnrichedDay],
    waypoints: Dict[str, Waypoint],
    integrator: ElevationIntegrator,
    coord_sys: CoordinateSystem,
    map_scale: MapScale,
    output_path: str | Path,
) -> Path:
    """Single-page overview at variable scale (the trek doesn't fit at 1:24k)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bounds = overview_bounds(days)
    lat_min, lat_max, lon_min, lon_max = bounds
    extent = (lon_min, lon_max, lat_min, lat_max)

    fig = plt.figure(figsize=(PAGE_W, PAGE_H), dpi=config.DPI, facecolor="white")

    # Reuse the same vertical inch layout.
    bottom_brief = MARGIN
    bottom_profile = bottom_brief + BRIEF_H + GAP_OTHER
    bottom_map = bottom_profile + PROFILE_H + GAP_MAP_TO_PROFILE
    bottom_header = bottom_map + MAP_H + GAP_OTHER

    # Header
    ax_header = _add_axes_inch(fig, MARGIN, bottom_header, INNER_W, HEADER_H)
    ax_header.axis("off")
    ax_header.text(
        0.0, 0.95,
        f"Crew {trek_data.CREW_618J['expedition']}  |  Itinerary "
        f"{trek_data.CREW_618J['itinerary']}",
        fontsize=8, weight="bold", va="top", transform=ax_header.transAxes,
    )
    ax_header.text(
        1.0, 0.95, f"Generated: {datetime.date.today()}",
        fontsize=7, ha="right", va="top", style="italic", color="#666",
        transform=ax_header.transAxes,
    )
    ax_header.text(
        0.5, 0.15,
        f"{trek_data.CREW_618J['route']} — "
        f"{trek_data.CREW_618J['start_date']} → "
        f"{trek_data.CREW_618J['end_date']}",
        fontsize=13, weight="bold", ha="center", va="bottom",
        transform=ax_header.transAxes,
    )

    # Map
    ax_map = _add_axes_inch(fig, MARGIN, bottom_map, INNER_W, MAP_H)
    grid, _ = integrator.extract_grid(bounds)
    grid_ft = grid * config.FT_PER_M
    ax_map.set_facecolor(config.MAP_BACKGROUND)
    ax_map.imshow(
        hillshade(grid), extent=extent, origin="upper", cmap="gray",
        vmin=0.0, vmax=1.0,
        alpha=config.HILLSHADE_ALPHA, aspect="auto", zorder=1,
    )
    overview_step = 200
    overview_levels = np.arange(
        np.floor(grid_ft.min() / overview_step) * overview_step,
        np.ceil(grid_ft.max() / overview_step) * overview_step,
        overview_step,
    )
    if len(overview_levels):
        cs = ax_map.contour(
            grid_ft, levels=overview_levels, extent=extent, origin="upper",
            colors=config.CONTOUR_COLOR, linewidths=0.5, alpha=0.7, zorder=2,
        )
        ax_map.clabel(
            cs, inline=True, fontsize=5, fmt="%d′",
            colors=config.CONTOUR_COLOR,
        )

    cmap = plt.get_cmap("plasma")
    day_nums = sorted(days.keys())
    for i, day in enumerate(day_nums):
        d = days[day]
        if not d.path or d.distance_miles == 0:
            continue
        color = cmap(i / max(len(day_nums) - 1, 1))
        ax_map.plot(
            [p.lon for p in d.path], [p.lat for p in d.path],
            color=color, linewidth=1.8, zorder=4, alpha=0.95,
            label=f"Day {day}",
        )
    for name, wp in waypoints.items():
        if wp.type not in {"camp", "trailhead_start", "trailhead_end"}:
            continue
        marker, color = _waypoint_style(wp)
        ax_map.scatter(
            wp.lon, wp.lat, s=70, marker=marker, color=color,
            edgecolors="black", linewidths=0.6, zorder=10,
        )
        ax_map.annotate(
            wp.name, xy=(wp.lon, wp.lat),
            xytext=(4, 4), textcoords="offset points",
            fontsize=6, weight="bold",
            bbox=dict(boxstyle="round,pad=0.15",
                      facecolor="white", alpha=0.8, edgecolor="none"),
        )
    coord_sys.draw(ax_map, extent)
    ax_map.set_xlim(lon_min, lon_max)
    ax_map.set_ylim(lat_min, lat_max)
    _, scale_label = map_scale.calculate(bounds)
    ax_map.set_title(
        f"Full Trek Overview   Scale {scale_label}",
        fontsize=11, weight="bold", pad=8,
    )
    ax_map.legend(loc="upper right", fontsize=6, ncol=2, framealpha=0.9)
    _draw_scale_bar(ax_map, lat_min, lat_max, lon_min, lon_max, target_miles=2.0)
    _draw_north_arrow(ax_map, lat_max, lon_max)

    # Cumulative profile
    ax_profile = _add_axes_inch(fig, MARGIN, bottom_profile, INNER_W, PROFILE_H)
    total_miles = 0.0
    xs: List[float] = []
    ys: List[float] = []
    camp_marks: List[tuple] = []
    for day in day_nums:
        d = days[day]
        if not d.cumulative_distance_mi:
            continue
        offsets = [total_miles + m for m in d.cumulative_distance_mi]
        elevs = [p.elev * config.FT_PER_M for p in d.path]
        xs += offsets
        ys += elevs
        if elevs:
            camp_marks.append((offsets[0], elevs[0], d.from_camp, day))
            if d.distance_miles > 0:
                camp_marks.append((offsets[-1], elevs[-1], d.to_camp, day))
        total_miles += d.distance_miles
    if ys:
        ax_profile.fill_between(
            xs, min(ys) - 200, ys,
            color=config.PROFILE_FILL_COLOR, alpha=config.PROFILE_FILL_ALPHA,
        )
        ax_profile.plot(xs, ys, color=config.PROFILE_LINE_COLOR, linewidth=1.3)
    seen = set()
    for x, y, name, day in camp_marks:
        if name in seen:
            continue
        seen.add(name)
        ax_profile.scatter(x, y, s=20, color=config.DAY_ROUTE_COLOR,
                           edgecolor="black", linewidths=0.5, zorder=5)
        ax_profile.annotate(
            f"{name}", xy=(x, y), xytext=(0, 6),
            textcoords="offset points", ha="center", fontsize=6, weight="bold",
            rotation=35,
        )
    ax_profile.set_xlabel("Cumulative distance (miles)", fontsize=8)
    ax_profile.set_ylabel("Elevation (ft)", fontsize=8)
    ax_profile.set_title(
        "Full-Trek Elevation Profile", fontsize=9, weight="bold", pad=4,
    )
    ax_profile.tick_params(labelsize=7)
    ax_profile.grid(True, alpha=0.3, linestyle=":", linewidth=0.5)

    # Stats
    ax_stats = _add_axes_inch(fig, MARGIN, bottom_brief, INNER_W, BRIEF_H)
    ax_stats.axis("off")
    total_gain = sum(d.gain_ft for d in days.values())
    total_loss = sum(d.loss_ft for d in days.values())
    total_dist_kml = sum(d.distance_miles for d in days.values())
    total_dist_official = sum(
        trek_data.DAYS[day]["miles"] for day in days if day in trek_data.DAYS
    )
    official_total_gain = sum(
        trek_data.DAYS[day]["gain"] for day in days if day in trek_data.DAYS
    )
    official_total_loss = sum(
        trek_data.DAYS[day]["loss"] for day in days if day in trek_data.DAYS
    )
    hardest = max(
        (d for d in days.values() if d.day in trek_data.DAYS),
        key=lambda d: trek_data.DAYS[d.day]["gain"],
    ) if days else None
    lines = [
        f"Total distance: {total_dist_official:.1f} mi official "
        f"({total_dist_kml:.1f} mi KML)",
        f"Official cumulative gain/loss: +{official_total_gain:,}′ / "
        f"-{official_total_loss:,}′",
        f"DEM-derived gain/loss: +{int(round(total_gain)):,}′ / "
        f"-{int(round(total_loss)):,}′ (underestimate — see below)",
        f"Elevation range: {trek_data.CREW_618J['elevation_range'][0]:,} – "
        f"{trek_data.CREW_618J['elevation_range'][1]:,} ft",
        f"Hardest day: Day {hardest.day} "
        f"({hardest.from_camp} → {hardest.to_camp}, "
        f"+{trek_data.DAYS[hardest.day]['gain']:,}′ official)"
        if hardest else "",
        "DEM gain is lower than official because 30m SRTM misses short undulations.",
    ]
    ax_stats.add_patch(FancyBboxPatch(
        (0.0, 0.0), 1.0, 1.0, boxstyle="round,pad=0.02",
        linewidth=0.8, edgecolor="#888", facecolor="#FAFAFA",
        transform=ax_stats.transAxes, zorder=0,
    ))
    ax_stats.text(
        0.02, 0.93, "TREK STATISTICS", transform=ax_stats.transAxes,
        fontsize=9, weight="bold", va="top",
    )
    for i, line in enumerate(lines):
        ax_stats.text(
            0.02, 0.80 - i * 0.12, line,
            transform=ax_stats.transAxes, fontsize=8, va="top",
        )

    fig.savefig(
        output_path, dpi=config.DPI, format="pdf",
        facecolor="white", edgecolor="none",
    )
    plt.close(fig)
    log.info("Wrote %s", output_path)
    return output_path


def merge_pdfs(pdf_paths: List[Path], output_path: str | Path) -> Path:
    from PyPDF2 import PdfMerger
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merger = PdfMerger()
    for p in pdf_paths:
        merger.append(str(p))
    merger.write(str(output_path))
    merger.close()
    log.info("Merged %d PDFs → %s", len(pdf_paths), output_path)
    return output_path
