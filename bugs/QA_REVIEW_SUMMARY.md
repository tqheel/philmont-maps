# QA Review Bug Report - May 31, 2026

Summary of bugs identified and fixed during the QA review of the Philmont Map Rendering project.

## Bug 1: Reversed Hiking Routes in Day Segmentation
**Status:** Fixed  
**Module:** `kml_parser.py`

### Symptom
On days where the KML LineString was drawn in the opposite direction of the hiking sequence (e.g., from End to Start), the `segment_path_by_camps` function would extract the points but maintain their original "backwards" order. 

### Impact
*   The path displayed on the map would be oriented backwards.
*   The elevation profile would be reversed (gain shown as loss and vice versa).
*   Cumulative distance and gain/loss statistics were incorrect for these segments.

### Fix
Modified `segment_path_by_camps` to compare the path indices of the start and end waypoints. If the start index is greater than the end index, the extracted path segment is now automatically reversed to match the intended hiking direction.

---

## Bug 2: Elevation Artifacts (0.0m) causing Gain/Loss Spikes
**Status:** Fixed  
**Module:** `elevation_integrator.py`

### Symptom
Out-of-bounds points or merge-border artifacts in the SRTM DEM often returned `0.0` meters. The code defaulted to `0.0` for any `NaN` or artifactual values.

### Impact
Since Philmont's base elevation is ~6,500ft, a single point dropping to `0.0m` (0ft) and returning to ~6,500ft created a massive ~13,000ft "spike" (6,500ft loss + 6,500ft gain) in the daily statistics, rendering the elevation profile and gain/loss totals useless.

### Fix
Implemented linear interpolation for `NaN` and artifactual values in `assign_elevations`. Missing data points now take the value of their nearest valid neighbors along the path, preventing artificial spikes.

---

## Bug 3: Douglas-Peucker Simplification Data Loss
**Status:** Fixed  
**Module:** `garmin_exporter.py`

### Symptom
The `_simplify_track` function used `list.index()` to map simplified coordinates back to their original `PathPoint` objects.

### Impact
`list.index()` always returns the *first* occurrence of a value. If a route doubled back on itself or stopped at the same coordinate twice (common at campsites or trail junctions), the simplification logic would "jump" the track to the first time that coordinate appeared, potentially deleting large sections of the intervening trail.

### Fix
Rewrote the Douglas-Peucker implementation to track and return original list indices throughout the recursion, ensuring the correct `PathPoint` is retained even when coordinates are non-unique.

---

## Bug 4: Inconsistent CLI Flag for Intermediates
**Status:** Fixed  
**Module:** `main.py`

### Symptom
The `--keep-intermediates` flag used `action="store_true"` but the help text suggested it defaulted to `True`. Additionally, no logic existed to actually delete the intermediate files.

### Impact
Intermediate per-sheet PDFs were always kept, cluttering the `output/` directory even if the user wanted only the final merged PDF.

### Fix
Converted the flag to `argparse.BooleanOptionalAction` with a default of `True`. Implemented explicit cleanup logic to `unlink()` intermediate PDFs and the summary PDF if `--no-keep-intermediates` is specified.

---

## Quality Improvements

### 1. Snapping Warnings
Upgraded the log level for waypoint snapping from `INFO` to `WARNING` in `kml_parser.py`. This ensures users are alerted if a camp or passthrough is located more than 0.1 miles from the trail, which usually indicates a KML data error or a significant detour (like the RMSC detour mentioned in the spec).

### 2. Test Coverage
Created a new `tests/` suite with 19 unit tests verifying:
*   KML haversine and segmentation logic.
*   Elevation smoothing and interpolation.
*   Route extraction and sheet splitting.
*   Garmin track simplification.
