# Bug: assign_elevations() iterates path four times — returns empty list for generators

**Status:** Open  
**Reported:** 2026-05-31  
**Severity:** Critical  

---

## Symptom

If any caller passes a generator or other single-use `Iterable[PathPoint]` to
`assign_elevations()`, the function silently returns an empty list. No exception
is raised; the downstream code receives `[]` and produces blank elevation
profiles or crashes later with an index error.

---

## Root cause

`elevation_integrator.py`, `assign_elevations()`, lines ~68–103:

```python
def assign_elevations(self, path: Iterable[PathPoint]) -> List[PathPoint]:
    lats = np.array([p.lat for p in path])   # Iteration 1 — exhausts a generator
    lons = np.array([p.lon for p in path])   # Iteration 2 — yields nothing
    ...
    for p, v in zip(path, vals):             # Iteration 3 — yields nothing
        p.elev = float(v)
    ...
    return list(path)                        # Iteration 4 — returns []
```

The type annotation promises `Iterable[PathPoint]` but the implementation
requires a re-iterable sequence. All four passes over `path` must see the same
elements.

Today all callers happen to pass lists, which re-iterate correctly, so the bug
is latent. It will silently activate if any future caller uses a generator
expression or `map()`.

---

## Affected code

| File | Lines | Note |
|------|-------|------|
| `elevation_integrator.py` | ~68–103 | `assign_elevations()` body |

---

## Fix

Add a single materialisation line at the top of the function:

```python
def assign_elevations(self, path: Iterable[PathPoint]) -> List[PathPoint]:
    path = list(path)   # Materialise once so all passes see the same elements
    lats = np.array([p.lat for p in path])
    lons = np.array([p.lon for p in path])
    ...
```

Alternatively, tighten the type signature to `List[PathPoint]` to make the
requirement explicit, though the fix above is more defensive.

---

## Impact

- Silent data loss: returns `[]` instead of a list of elevated points.
- Downstream crash or empty elevation profiles with no error message.
- Latent — does not affect current callers, but will affect any future refactor
  that passes a lazy iterable.
