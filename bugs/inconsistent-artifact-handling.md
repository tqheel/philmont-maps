# Bug: Inconsistent SRTM artifact handling between assign_elevations and extract_grid

**Status:** Open  
**Reported:** 2026-05-31  
**Severity:** High  

---

## Symptom

Elevation values used for the route profile (computed by `assign_elevations`)
and elevation values used for the hillshade/contour raster (computed by
`extract_grid`) apply different fallback strategies when SRTM merge-border
artifacts are detected. This causes the route elevation line to diverge from
the rendered terrain at affected locations — e.g., the profile may show a
notch or spike that does not correspond to any visible feature on the topo.

---

## Root cause

Two functions in `elevation_integrator.py` handle the same artifact condition
(`value < 1000 m`) differently:

```python
# assign_elevations (~line 85–92) — WRONG fallback
vals = np.where(vals < 1000.0, np.nan, vals)
if nans.all():
    vals[:] = 0.0                          # ← hardcoded 0.0

# extract_grid (~lines 178–181) — CORRECT fallback
sub = np.where(sub < 1000.0, np.nan, sub)
if np.isnan(sub).any():
    median = float(np.nanmedian(sub))
    sub = np.where(np.isnan(sub), median, sub)   # ← nanmedian
```

`extract_grid` is correct; `assign_elevations` is not.

---

## Affected code

| File | Lines | Function |
|------|-------|----------|
| `elevation_integrator.py` | ~85–92 | `assign_elevations()` |
| `elevation_integrator.py` | ~178–181 | `extract_grid()` — reference (correct) |

---

## Fix

Replace the `0.0` fallback in `assign_elevations` with the same `nanmedian`
strategy used in `extract_grid`:

```python
vals = np.where(vals < 1000.0, np.nan, vals)
if np.isnan(vals).any():
    median = float(np.nanmedian(vals[~np.isnan(vals)])) if not np.isnan(vals).all() else 2100.0
    vals = np.where(np.isnan(vals), median, vals)
```

This unifies the artifact handling and ensures profile elevations match the
rendered terrain.

---

## Impact

- Route elevation profile disagrees with the hillshade/contour rendering.
- Gain/loss calculations based on profile data are inaccurate at artifact
  locations.
- Difficult to reproduce deterministically because it only triggers at SRTM
  tile-merge seams.
