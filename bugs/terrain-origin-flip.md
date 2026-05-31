# Bug: Terrain displayed upside-down, inconsistent between split sheets

**Status:** Fixed  
**Reported:** 2026-05-31  
**Fixed in:** page_composer.py (all `origin="lower"` → `origin="upper"`)

---

## Symptom

On multi-sheet days (Day 3, Day 4, Day 5, Day 8, Day 11, Day 12), the terrain
features visible at the handoff edge between Sheet N and Sheet N+1 appeared at
different map positions relative to the UTM grid and route overlay. The same
7200' hill that terminated Sheet 1 of Day 3 appeared at a different northing on
Sheet 2 of Day 3, even though the UTM km-grid lines were aligned and the route
termination/start point was correct on both sheets.

The route and UTM grid were unaffected (they use true lat/lon coordinates).
Only the hillshade raster and contour lines were misaligned.

---

## Root cause

The SRTM GeoTIFF is stored **north-up**: `array[0, :]` = northernmost row
(highest latitude). Rasterio preserves this orientation when reading sub-windows.

`matplotlib.imshow(origin="lower")` places **row 0 at the bottom** (south) of
the axes. This reflects the terrain array north↔south within the display extent.

The reflection maps a feature at true latitude L to:

```
displayed_lat = lat_min + lat_max − L
```

Because each sheet is centered on a different sub-path segment, `lat_min` and
`lat_max` differ between sheets. The same geographic feature therefore appeared
at a different displayed latitude on each sheet, while the route (plotted in true
lat/lon coordinates) remained correct. The terrain and route appeared to agree
locally on any single sheet but drifted apart at inter-sheet boundaries.

The same bug inverted the hillshade illumination: shadows fell on the SE side of
hills instead of the correct NW (azimuth = 315°).

---

## Affected code

`page_composer.py` — five call sites:

| Line | Call |
|------|------|
| 169 | `ax.imshow(hs, ..., origin="lower", ...)` — per-sheet hillshade |
| 188 | `ax.contour(..., origin="lower", ...)` — minor contours |
| 194 | `ax.contour(..., origin="lower", ...)` — index contours |
| 523 | `ax_map.imshow(..., origin="lower", ...)` — summary hillshade |
| 535 | `ax_map.contour(..., origin="lower", ...)` — summary contours |

---

## Fix

Changed all five call sites from `origin="lower"` to `origin="upper"`.

With `origin="upper"`, matplotlib places row 0 at the **top** (lat_max), which
is the correct mapping for a north-up raster. A feature at true latitude L now
maps to:

```
displayed_lat = lat_min + (lat_max − L) / (lat_max − lat_min) × (lat_max − lat_min)
             = lat_max − (lat_max − L)
             = L   ✓
```

The fix is consistent: `imshow` and `contour` use the same orientation, so
hillshade and contours remain registered with each other and with the route
overlay across all sheets.

---

## Visual verification status

The fix was confirmed by regenerating Day 3 Sheets 1 and 2 at 150 DPI. The
code ran without errors and produced output. Direct visual inspection of the
PDF against reference imagery was **not performed** in the fix session — the
author did not view the rendered PDFs to confirm the terrain handoff visually.
A full 300 DPI batch re-render is recommended before printing.
