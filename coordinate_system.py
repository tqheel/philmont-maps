"""Coordinate system & map-scale helpers.

Provides:
  - lat/lon ↔ UTM (Zone 13N for Philmont) projection.
  - Drawing grid lines + tick labels on a matplotlib Axes.
  - Computing automatic map scale that fits given bounds on the printed page.

Spec reference: §5.3 (Key Classes: CoordinateSystem, MapScale).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)
from typing import Tuple

import numpy as np
from pyproj import Transformer

import config


@dataclass
class GridStyle:
    line_color: str = config.GRID_LINE_COLOR
    line_width: float = config.GRID_LINE_WIDTH_PT
    label_color: str = config.GRID_LABEL_COLOR
    label_size: int = config.GRID_LABEL_SIZE
    utm_line_color: str = config.UTM_GRID_COLOR
    utm_line_width: float = config.UTM_GRID_WIDTH_PT
    utm_alpha: float = config.UTM_GRID_ALPHA
    utm_label_color: str = config.UTM_LABEL_COLOR


class CoordinateSystem:
    """Lat/lon and/or UTM grid drawing."""

    def __init__(
        self,
        grid_type: str = "latlon",
        utm_zone: int = config.UTM_ZONE,
        hemisphere: str = config.UTM_HEMISPHERE,
    ):
        if grid_type not in {"latlon", "utm", "both"}:
            raise ValueError(f"Invalid grid_type: {grid_type}")
        self.grid_type = grid_type
        self.utm_zone = utm_zone
        self.hemisphere = hemisphere
        epsg = 32600 + utm_zone if hemisphere.upper() == "N" else 32700 + utm_zone
        self._to_utm = Transformer.from_crs(
            "EPSG:4326", f"EPSG:{epsg}", always_xy=True
        )
        self._from_utm = Transformer.from_crs(
            f"EPSG:{epsg}", "EPSG:4326", always_xy=True
        )

    def to_utm(self, lon: float, lat: float) -> Tuple[float, float]:
        return self._to_utm.transform(lon, lat)

    def from_utm(self, easting: float, northing: float) -> Tuple[float, float]:
        return self._from_utm.transform(easting, northing)

    def utm_bounds(
        self, bounds_latlon: Tuple[float, float, float, float]
    ) -> Tuple[float, float, float, float]:
        """Convert (lat_min, lat_max, lon_min, lon_max) → (E_min, E_max, N_min, N_max)."""
        lat_min, lat_max, lon_min, lon_max = bounds_latlon
        corners = [
            self.to_utm(lon_min, lat_min),
            self.to_utm(lon_max, lat_min),
            self.to_utm(lon_min, lat_max),
            self.to_utm(lon_max, lat_max),
        ]
        eastings = [c[0] for c in corners]
        northings = [c[1] for c in corners]
        return (min(eastings), max(eastings), min(northings), max(northings))

    def draw(self, ax, extent_lonlat, num_labels: int = 5,
             style: GridStyle | None = None) -> None:
        """Draw grid lines on `ax` for the configured grid type.

        `extent_lonlat` is matplotlib-style (lon_min, lon_max, lat_min, lat_max).
        """
        style = style or GridStyle()
        if self.grid_type in {"latlon", "both"}:
            self._draw_latlon(ax, extent_lonlat, num_labels, style)
        if self.grid_type in {"utm", "both"}:
            self._draw_utm(ax, extent_lonlat, num_labels, style)

    # ── Lat/lon grid ───────────────────────────────────────────────────────

    def _draw_latlon(self, ax, extent, num_labels, style):
        """Draw lat/lon grid lines + inline labels.

        Tick labels are drawn as text() inside the axes (lower-left corner of
        each gridline) instead of via set_xticklabels — that way the axes
        rect equals the data area exactly (no margin stolen by tick labels).
        """
        lon_min, lon_max, lat_min, lat_max = extent
        lat_ticks = np.linspace(lat_min, lat_max, num_labels)
        lon_ticks = np.linspace(lon_min, lon_max, num_labels)
        for lat in lat_ticks:
            ax.axhline(
                lat, color=style.line_color, linewidth=style.line_width, alpha=0.6,
                zorder=1,
            )
        for lon in lon_ticks:
            ax.axvline(
                lon, color=style.line_color, linewidth=style.line_width, alpha=0.6,
                zorder=1,
            )
        # Inline labels just inside the axes edges.
        ox = (lon_max - lon_min) * 0.005
        oy = (lat_max - lat_min) * 0.005
        for lat in lat_ticks[1:-1]:  # skip corners — they collide with the neatline
            ax.text(
                lon_min + ox, lat, f"{lat:.3f}°",
                fontsize=style.label_size, color=style.label_color,
                ha="left", va="bottom", alpha=0.8,
                bbox=dict(boxstyle="round,pad=0.1",
                          facecolor="white", alpha=0.6, edgecolor="none"),
            )
        for lon in lon_ticks[1:-1]:
            ax.text(
                lon, lat_min + oy, f"{lon:.3f}°",
                fontsize=style.label_size, color=style.label_color,
                ha="left", va="bottom", alpha=0.8,
                bbox=dict(boxstyle="round,pad=0.1",
                          facecolor="white", alpha=0.6, edgecolor="none"),
            )

    # ── UTM grid (drawn in lat/lon axes) ───────────────────────────────────

    def _draw_utm(self, ax, extent, num_labels, style):
        """Draw a USGS-style UTM grid in blue, with km labels at every gridline.

        Lines are drawn as solid blue polylines because the underlying axes
        are lon/lat; constant-easting lines curve slightly across the page.
        """
        lon_min, lon_max, lat_min, lat_max = extent
        e_min, e_max, n_min, n_max = self.utm_bounds(
            (lat_min, lat_max, lon_min, lon_max)
        )
        # Pick a round-number interval (metres) — aim for ~5–8 grid cells.
        e_span = e_max - e_min
        target_cells = 6
        candidates = (250, 500, 1000, 2000, 5000, 10000)
        interval = candidates[-1]
        for c in candidates:
            if e_span / c <= target_cells + 1:
                interval = c
                break
        e_start = (int(e_min // interval) + 1) * interval
        n_start = (int(n_min // interval) + 1) * interval
        eastings = np.arange(e_start, e_max, interval)
        northings = np.arange(n_start, n_max, interval)
        mid_lat = (lat_min + lat_max) / 2.0

        # Vertical lines (constant easting) — back-project to lon along latitudes.
        lats_for_line = np.linspace(lat_min, lat_max, 30)
        for E in eastings:
            lons = [
                self.from_utm(E, self.to_utm(lon_min, lat)[1])[0]
                for lat in lats_for_line
            ]
            ax.plot(
                lons, lats_for_line,
                color=style.utm_line_color,
                linewidth=style.utm_line_width,
                alpha=style.utm_alpha,
                linestyle="-",
                zorder=3,
            )
            # Label just inside the top edge (avoids clashing with map title).
            lon_top = self.from_utm(E, self.to_utm(lon_min, lat_max)[1])[0]
            if lon_min <= lon_top <= lon_max:
                # Offset down by ~1% of latitude range so the label sits
                # below the neatline, on top of the hillshade.
                offset = (lat_max - lat_min) * 0.012
                ax.text(
                    lon_top, lat_max - offset,
                    f"{int(E)//1000}",
                    fontsize=style.label_size - 1,
                    color=style.utm_label_color,
                    ha="center", va="top",
                    weight="bold",
                    bbox=dict(boxstyle="round,pad=0.1",
                              facecolor="white", alpha=0.8,
                              edgecolor="none"),
                )

        # Horizontal lines (constant northing) — back-project to lat along longitudes.
        lons_for_line = np.linspace(lon_min, lon_max, 30)
        for N in northings:
            lats = [
                self.from_utm(self.to_utm(lon, mid_lat)[0], N)[1]
                for lon in lons_for_line
            ]
            ax.plot(
                lons_for_line, lats,
                color=style.utm_line_color,
                linewidth=style.utm_line_width,
                alpha=style.utm_alpha,
                linestyle="-",
                zorder=3,
            )
            lat_right = self.from_utm(
                self.to_utm(lon_max, mid_lat)[0], N
            )[1]
            if lat_min <= lat_right <= lat_max:
                # Offset left so the label sits just inside the right edge.
                offset_x = (lon_max - lon_min) * 0.008
                ax.text(
                    lon_max - offset_x, lat_right,
                    f"{int(N)//1000}",
                    fontsize=style.label_size - 1,
                    color=style.utm_label_color,
                    ha="right", va="center",
                    weight="bold",
                    bbox=dict(boxstyle="round,pad=0.1",
                              facecolor="white", alpha=0.8,
                              edgecolor="none"),
                )

        # UTM zone tag — top-right interior corner.
        ax.text(
            lon_max - (lon_max - lon_min) * 0.01,
            lat_max - (lat_max - lat_min) * 0.005,
            f"UTM 13{self.hemisphere} (km)",
            fontsize=style.label_size - 1,
            color=style.utm_label_color,
            ha="right", va="top", style="italic",
            bbox=dict(boxstyle="round,pad=0.15",
                      facecolor="white", alpha=0.85, edgecolor="none"),
        )


class MapScale:
    """Compute and label the map scale ratio."""

    def __init__(self, scale_string: str = "auto"):
        self.scale_string = scale_string
        self.scale_ratio = self._parse(scale_string)

    @staticmethod
    def _parse(scale_string: str):
        if scale_string in (None, "", "auto"):
            return None
        if ":" in scale_string:
            try:
                return int(scale_string.split(":")[1])
            except ValueError:
                log.warning(
                    "MapScale: could not parse %r; falling back to auto-scale.",
                    scale_string,
                )
                return None
        try:
            return int(scale_string)
        except ValueError:
            log.warning(
                "MapScale: could not parse %r; falling back to auto-scale.",
                scale_string,
            )
            return None

    def calculate(
        self,
        bounds_latlon: Tuple[float, float, float, float],
        page_width_in: float = config.PAGE_WIDTH_IN - 2 * config.MARGIN_IN,
    ) -> Tuple[int, str]:
        """Return (scale_ratio, "1:N") to fit the bounds within page_width_in."""
        if self.scale_ratio is not None:
            return self.scale_ratio, f"1:{self.scale_ratio:,}"
        lat_min, lat_max, lon_min, lon_max = bounds_latlon
        mid_lat = (lat_min + lat_max) / 2.0
        km_per_deg_lat = 111.0
        km_per_deg_lon = 111.0 * np.cos(np.radians(mid_lat))
        width_km = (lon_max - lon_min) * km_per_deg_lon
        height_km = (lat_max - lat_min) * km_per_deg_lat
        # Use the dimension that drives the ratio (page is wider than tall here).
        page_height_in = page_width_in * (height_km / width_km) if width_km else page_width_in
        scale_w = (width_km * 1000 * 100) / (page_width_in * 2.54)
        scale_h = (height_km * 1000 * 100) / (page_height_in * 2.54) if page_height_in else 0
        scale = max(scale_w, scale_h)
        # Round to nearest "nice" map scale.
        nice = [10000, 12000, 15000, 20000, 24000, 25000, 30000,
                40000, 50000, 60000, 75000, 100000, 125000, 150000, 200000]
        scale = next((n for n in nice if n >= scale), int(round(scale, -3)))
        return int(scale), f"1:{int(scale):,}"
