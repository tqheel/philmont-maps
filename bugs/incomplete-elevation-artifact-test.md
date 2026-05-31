# Bug: Placeholder test for elevation artifact has no assertions

**Status:** Open  
**Reported:** 2026-05-31  
**Severity:** Medium  

---

## Symptom

The test suite passes even when the `0.0`-elevation fallback bug
(see `elevation-fallback-zero.md`) is present, because the test function
that was written to cover this case contains no assertions. The CI green
status is therefore misleading.

---

## Root cause

`tests/test_elevation_integrator.py`, lines ~111–115:

```python
def test_gain_loss_with_zero_elevation_artifact():
    # This test stays to show what happens if 0.0 actually makes it into gain_loss
    integrator = DummyIntegrator()
    # ...
```

The function body stops before any `assert` statement. A comment documents
the intent but no behavior is verified.

---

## Affected code

| File | Lines | Note |
|------|-------|------|
| `tests/test_elevation_integrator.py` | ~111–115 | `test_gain_loss_with_zero_elevation_artifact` |

---

## Fix

Complete the test so it verifies that a path containing a 0-meter artifact
point is either:

1. **Rejected** — `assign_elevations` raises a `ValueError` or warning when
   a post-filter value of 0.0 would be returned, or
2. **Corrected** — the returned elevations never contain a value below the
   minimum credible Philmont elevation (~1800 m), e.g.:

```python
def test_gain_loss_with_zero_elevation_artifact():
    # Simulate a path where all SRTM samples fall below the 1000 m threshold
    points = [PathPoint(lat=36.5, lon=-105.0, elev=None) for _ in range(5)]
    integrator = ElevationIntegrator(...)  # configured with mock raster
    result = integrator.assign_elevations(points)
    elevations = [p.elev for p in result]
    assert all(e >= 1800.0 for e in elevations), (
        f"Elevation fallback produced physically impossible values: {elevations}"
    )
```

---

## Impact

- The artifact-handling code path has zero test coverage.
- Future regressions (e.g., re-introducing `0.0` fallback) will not be caught
  by CI.
