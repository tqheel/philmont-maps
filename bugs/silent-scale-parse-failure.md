# Bug: MapScale._parse() silently returns None for invalid input

**Status:** Open  
**Reported:** 2026-05-31  
**Severity:** Low  

---

## Symptom

If a user provides a malformed map scale string in the configuration (e.g.,
`"1:invalid"`, `"foo"`, `"1:24,000"`), `MapScale._parse()` returns `None`
without any warning or error message. The map then renders at a default or
auto-computed scale with no indication that the user's configured value was
ignored.

---

## Root cause

`coordinate_system.py`, `MapScale._parse()`, lines ~245–256:

```python
@staticmethod
def _parse(scale_string: str):
    if scale_string in (None, "", "auto"):
        return None
    if ":" in scale_string:
        try:
            return int(scale_string.split(":")[1])
        except ValueError:
            return None          # ← Silent failure, no log
    try:
        return int(scale_string)
    except ValueError:
        return None              # ← Silent failure, no log
```

Both `ValueError` branches swallow the error and return `None`, which is
indistinguishable from the intentional `"auto"` / `""` case.

---

## Affected code

| File | Lines | Function |
|------|-------|----------|
| `coordinate_system.py` | ~245–256 | `MapScale._parse()` |

---

## Fix

Log a warning (or raise a `ValueError`) when an unexpected string fails to
parse, so the user knows their configuration value was not used:

```python
        except ValueError:
            import warnings
            warnings.warn(
                f"MapScale: could not parse scale string {scale_string!r}; "
                "falling back to auto-scale.",
                stacklevel=3,
            )
            return None
```

---

## Impact

- User configuration errors are invisible; maps silently render at the wrong
  scale.
- Difficult to debug without adding print statements manually.
