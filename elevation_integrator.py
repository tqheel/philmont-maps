"""SRTM DEM integration.

Reads `data/elevation_srtm.tif` (clipped 1-arc-second SRTM, EPSG:4326) and
populates elevation values for path points / arbitrary lat-lon queries.

Spec reference: §3 (Phase 3 — Elevation Grid).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

import numpy as np
import rasterio
from rasterio.windows import from_bounds as window_from_bounds

import config
from kml_parser import PathPoint

log = logging.getLogger(__name__)


@dataclass
class GainLoss:
    gain_ft: float
    loss_ft: float
    min_ft: float
    max_ft: float


class ElevationIntegrator:
    """Cheap wrapper around a SRTM GeoTIFF."""

    def __init__(self, dem_path: str | Path):
        self.dem_path = Path(dem_path)
        if not self.dem_path.exists():
            raise FileNotFoundError(
                f"SRTM DEM not found: {self.dem_path}. "
                f"Run `python download_srtm.py` first."
            )
        self.src = rasterio.open(self.dem_path)
        # Read the whole DEM into memory once — Philmont clip is ~3 MB.
        self.array = self.src.read(1).astype(np.float32)
        self.transform = self.src.transform
        self.nodata = self.src.nodata
        self.bounds = self.src.bounds       # (left, bottom, right, top)
        self.height, self.width = self.array.shape

    # ── Single-point lookup ────────────────────────────────────────────────

    def elevation_at(self, lat: float, lon: float) -> float:
        """Return elevation in metres at (lat, lon), or NaN if outside DEM."""
        row, col = rasterio.transform.rowcol(self.transform, lon, lat)
        if not (0 <= row < self.height and 0 <= col < self.width):
            return float("nan")
        v = float(self.array[row, col])
        if self.nodata is not None and np.isclose(v, self.nodata):
            return float("nan")
        return v

    # ── Path enrichment ────────────────────────────────────────────────────

    def assign_elevations(self, path: Iterable[PathPoint]) -> List[PathPoint]:
        """Mutate path points in place, populating .elev (metres). Returns it."""
        path = list(path)   # materialise once; caller may pass any Iterable
        if not path:
            return []
        lats = np.array([p.lat for p in path])
        lons = np.array([p.lon for p in path])
        rows, cols = rasterio.transform.rowcol(self.transform, lons, lats)
        rows = np.asarray(rows, dtype=np.int64)
        cols = np.asarray(cols, dtype=np.int64)
        in_bounds = (
            (rows >= 0) & (rows < self.height)
            & (cols >= 0) & (cols < self.width)
        )
        # Clip and sample; fill out-of-bounds with NaN.
        rows_c = np.clip(rows, 0, self.height - 1)
        cols_c = np.clip(cols, 0, self.width - 1)
        vals = self.array[rows_c, cols_c].astype(np.float32)
        vals[~in_bounds] = np.nan
        if self.nodata is not None and not np.isnan(self.nodata):
            vals = np.where(np.isclose(vals, self.nodata), np.nan, vals)
        # Save pre-filter samples for the all-NaN fallback (see below).
        vals_raw = vals.copy()
        # Filter the merge-border artifact (see extract_grid).
        vals = np.where(vals < 1000.0, np.nan, vals)

        # Interpolate NaNs if any exist.
        if np.isnan(vals).any():
            nans = np.isnan(vals)
            if nans.all():
                # Every sample is an artifact or out-of-bounds.  Use the
                # median of the pre-filter raw samples floored at a minimum
                # credible Philmont elevation (~2000 m / 6562 ft) so we
                # never write the physically-impossible 0 m default.
                raw_finite = vals_raw[np.isfinite(vals_raw)]
                fallback = float(np.median(raw_finite)) if len(raw_finite) else 2100.0
                fallback = max(fallback, 2000.0)
                log.warning(
                    "assign_elevations: all %d samples are artifacts; "
                    "using fallback %.0f m",
                    len(path), fallback,
                )
                vals[:] = fallback
            else:
                x = lambda z: z.nonzero()[0]
                vals[nans] = np.interp(x(nans), x(~nans), vals[~nans])

        for p, v in zip(path, vals):
            p.elev = float(v)

        oob = int((~in_bounds).sum())
        if oob:
            log.warning("%d path points fell outside DEM bounds", oob)
        return path

    def gain_loss(
        self,
        path: List[PathPoint],
        smooth_window: int = 7,
        min_step_ft: float = 3.0,
    ) -> GainLoss:
        """Compute total gain/loss in feet over a path.

        SRTM 1-arc-second has ~5-10 m vertical noise. To avoid inflating gain
        with that noise we:
          1. Smooth elevation along the path with a centred moving average.
          2. Apply a minimum-step threshold (only count ascents/descents that
             persist past `min_step_ft` from the last counted pivot).
        """
        if len(path) < 2:
            return GainLoss(0.0, 0.0, 0.0, 0.0)
        elev_m = np.array([p.elev for p in path], dtype=np.float32)
        if smooth_window > 1 and len(elev_m) > smooth_window:
            kernel = np.ones(smooth_window) / smooth_window
            # Pad with edge values to avoid sagging at endpoints.
            pad = smooth_window // 2
            padded = np.pad(elev_m, pad, mode="edge")
            elev_m = np.convolve(padded, kernel, mode="valid")[: len(elev_m)]
        elev_ft = elev_m * config.FT_PER_M
        gain = 0.0
        loss = 0.0
        pivot = float(elev_ft[0])
        for v in elev_ft[1:]:
            d = float(v) - pivot
            if d >= min_step_ft:
                gain += d
                pivot = float(v)
            elif d <= -min_step_ft:
                loss += -d
                pivot = float(v)
        return GainLoss(
            gain_ft=gain,
            loss_ft=loss,
            min_ft=float(elev_ft.min()),
            max_ft=float(elev_ft.max()),
        )

    # ── Bounded grid extraction (for hillshade / contours) ────────────────

    def extract_grid(
        self, bounds_latlon: Tuple[float, float, float, float],
        resolution: int = config.GRID_RESOLUTION,
    ):
        """Return (Z, extent) for the given bounds.

        Args:
            bounds_latlon: (lat_min, lat_max, lon_min, lon_max)
            resolution:    samples per axis on the regular output grid

        Returns:
            Z: 2D float32 array, (resolution, resolution), origin=lower
            extent: (lon_min, lon_max, lat_min, lat_max) for imshow
        """
        lat_min, lat_max, lon_min, lon_max = bounds_latlon
        # Clip to DEM bounds.
        lon_min = max(lon_min, self.bounds.left)
        lon_max = min(lon_max, self.bounds.right)
        lat_min = max(lat_min, self.bounds.bottom)
        lat_max = min(lat_max, self.bounds.top)
        win = window_from_bounds(
            lon_min, lat_min, lon_max, lat_max, transform=self.transform,
        )
        sub = self.src.read(1, window=win).astype(np.float32)
        if self.nodata is not None and not np.isnan(self.nodata):
            sub = np.where(np.isclose(sub, self.nodata), np.nan, sub)
        # The merge/clip border in `download_srtm.py` occasionally writes 0 m
        # along the very outermost row/column. Philmont is 6500 ft (1980 m)
        # minimum everywhere — any sample below ~1000 m is a known artifact.
        sub = np.where(sub < 1000.0, np.nan, sub)
        if np.isnan(sub).any():
            median = float(np.nanmedian(sub))
            sub = np.where(np.isnan(sub), median, sub)
        # Resample to requested resolution via scipy zoom.
        if sub.shape != (resolution, resolution):
            try:
                from scipy.ndimage import zoom
                zy = resolution / sub.shape[0]
                zx = resolution / sub.shape[1]
                sub = zoom(sub, (zy, zx), order=1).astype(np.float32)
            except ImportError:
                log.warning("scipy not available; returning raw window")
        extent = (lon_min, lon_max, lat_min, lat_max)
        return sub, extent


def hillshade(
    elevation_grid: np.ndarray,
    azimuth: float = config.HILLSHADE_AZIMUTH,
    altitude: float = config.HILLSHADE_ALTITUDE,
    z_factor: float = 1.0,
) -> np.ndarray:
    """Compute a hillshade in [0, 1] using the standard cartographic formula."""
    az = np.radians(360.0 - azimuth + 90.0)
    alt = np.radians(altitude)
    dy, dx = np.gradient(elevation_grid * z_factor)
    slope = np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(-dx, dy)
    shaded = (
        np.sin(alt) * np.cos(slope)
        + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    )
    return np.clip(shaded, 0.0, 1.0)


def slope_aspect(elevation_grid: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    dy, dx = np.gradient(elevation_grid)
    slope = np.degrees(np.arctan(np.hypot(dx, dy)))
    aspect = np.degrees(np.arctan2(-dx, dy))
    return slope, aspect
