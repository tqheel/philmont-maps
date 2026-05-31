# Bug: Last map sheet may display "0.0 mi" offset when start index equals path length

**Status:** Open  
**Reported:** 2026-05-31  
**Severity:** Medium  

---

## Symptom

On a multi-sheet day where the final sheet begins exactly at the last point of
the path array, the "miles into day" offset shown on that sheet is `0.0 mi`
instead of the correct cumulative distance. All mileage annotations on the
final sheet are therefore shifted, showing smaller numbers than they should.

---

## Root cause

`route_extractor.py`, sheet offset calculation, lines ~388–391:

```python
offset_mi = (
    day.cumulative_distance_mi[start_idx]
    if start_idx < len(day.cumulative_distance_mi) else 0.0
)
```

When `start_idx == len(day.cumulative_distance_mi)` (the chunk begins exactly
at the boundary), the guard is `False` and the function returns `0.0` instead
of the final cumulative distance value. The correct fallback is the last
element, not zero.

---

## Affected code

| File | Lines | Note |
|------|-------|------|
| `route_extractor.py` | ~388–391 | Sheet offset guard in multi-sheet loop |

---

## Fix

Change the fallback to return the last cumulative distance rather than `0.0`:

```python
offset_mi = (
    day.cumulative_distance_mi[start_idx]
    if start_idx < len(day.cumulative_distance_mi)
    else day.cumulative_distance_mi[-1]
)
```

---

## Impact

- Mile markers on the final sheet of a multi-sheet day are incorrect.
- The bug is edge-triggered: only fires when a sheet boundary lands exactly on
  the last point of the day's path array.
- No existing test covers this boundary condition.
