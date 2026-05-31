# Bug: Elevation fallback to 0.0 m corrupts gain/loss calculations

**Status:** Open  
**Reported:** 2026-05-31  
**Severity:** Critical  

---

## Symptom

When an entire path segment's elevation values are filtered as SRTM merge-border
artifacts (all values < 1000 m), the fallback sets every point in the segment to
`0.0` meters. Philmont's lowest point is ~2,050 m (Cimarron entrance, ~6,729 ft),
so `0.0` is physically impossible. The corrupted segment causes massive phantom
descent/ascent spikes in the elevation profile and wildly incorrect cumulative
gain/loss numbers for any day whose path crosses a filtered segment.

---

## Root cause

`elevation_integrator.py`, `assign_elevations()`, line ~92:

```python
nans = np.isnan(vals)
vals = np.where(vals < 1000.0, np.nan, vals)
if nans.all():
    vals[:] = 0.0          # ← Wrong: should never be 0 for Philmont terrain
```

When every interpolated sample for a segment falls below the 1000 m artifact
threshold, `nans.all()` is `True` and all values are set to `0.0`.

---

## Affected code

| File | Line | Call |
|------|------|------|
| `elevation_integrator.py` | ~92 | `vals[:] = 0.0` in `assign_elevations()` |

---

## Expected behavior

Use `np.nanmedian()` of the pre-filter values as the fallback, consistent with
the handling already in place in `extract_grid()` (lines ~178–181 of the same
file):

```python
if nans.all():
    vals[:] = float(np.nanmedian(vals_before_filter))
```

Or, if no valid pre-filter values exist, propagate the elevation from the nearest
valid neighboring point rather than writing a physically impossible constant.

---

## Impact

- Elevation profiles show sudden drops to 0 m and back.
- Cumulative gain/loss for affected days is incorrect by thousands of feet.
- Garmin `.gpx` export embeds 0 m elevations for those track points.
