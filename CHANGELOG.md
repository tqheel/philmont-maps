# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2026-05-31

### Added
- **Interactive crew website** — Next.js 15 frontend at `/web/` with Leaflet-based interactive route map, day-by-day pages with topo map image viewer, elevation profiles, and full itinerary table. Deployable as static export (no server required).
- **Asset generation pipeline** — `generate_web_assets.py` converts PDFs to PNG (150 DPI) and extracts GPX track data into `route.json` for the website.
- Comprehensive test suite (54 unit tests) covering KML parsing, elevation integration, route extraction, Garmin export, and coordinate system parsing.
- Per-day PDF output: each day's route now renders to a single `day_NN.pdf` file, with internal merging for multi-sheet days.
- Dashed continuation guide on multi-sheet days showing where the full daily route enters/exits the map window on adjacent pages.
- Warning logs for invalid MapScale strings (e.g., `"1:24,000"` with comma) instead of silent fallback to auto-scale.

### Fixed
- **Terrain N-S flip:** `imshow(origin="lower")` was reflecting SRTM raster north↔south; changed to `origin="upper"` for correct geographic alignment across split-sheet boundaries.
- **Elevation all-artifact fallback:** `assign_elevations` now uses `nanmedian` of pre-filter samples (floored at 2000m) instead of hardcoded `0.0m`, preventing ~6500 ft phantom spikes in gain/loss.
- **Iterator consumption:** `assign_elevations` now materializes input to `list()` at entry, fixing silent data loss when called with generators.
- **Sheet offset boundary:** Multi-sheet day's final sheet now correctly uses `cumulative_distance_mi[-1]` instead of `0.0` when start index lands at path boundary.
- **KML reversed paths:** `segment_path_by_camps` now correctly reverses segments when start index > end index.
- **Garmin deduplication:** `_simplify_track` tracks indices through recursion instead of using `list.index()`, preventing data loss on non-unique coordinates.
- **CLI intermediate cleanup:** `--keep-intermediates` flag now properly deletes per-day/summary PDFs when set to False.

### Changed
- Waypoint snapping log level upgraded from `INFO` to `WARNING` for better visibility of data discrepancies.
- Single-day CLI mode now always produces one merged PDF per day (not individual sheet files).
- Batch mode groups render output by day, merging multi-sheet PDFs automatically before final assembly.
- `main.py` refactored to use `itertools.groupby` for cleaner day-by-day PDF organization.
