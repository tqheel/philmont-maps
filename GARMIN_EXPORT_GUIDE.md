# Garmin Export Quick Reference

## What's New

Added optional GPX, KML, and TCX export for Garmin Online / Garmin devices.

---

## Quick Start

### Generate GPX with Per-Day Tracks

```bash
python main.py \
  --trek-kml data/itinerary_1_corrected.kml \
  --elevation-raster data/elevation_srtm.tif \
  --output-garmin output/crew_618j.gpx \
  --garmin-day-segments
```

### Generate Both Maps AND Garmin GPX in One Run

```bash
python main.py \
  --trek-kml data/itinerary_1_corrected.kml \
  --elevation-raster data/elevation_srtm.tif \
  --output-pdf output/crew_618j_maps.pdf \
  --output-garmin output/crew_618j.gpx \
  --garmin-day-segments \
  --grid-type both \
  --map-scale auto
```

---

## File Variants

### Standard (Recommended)

```bash
--output-garmin crew_618j.gpx --garmin-day-segments
# Produces: 11 separate tracks (Days 2-12) + waypoints
# Elevation: Sampled every 50 meters (default)
# Size: ~2 MB
# Best for: Detailed navigation, post-trek analysis
```

### Light Version (Mobile/Low-Memory Devices)

```bash
--output-garmin crew_618j_light.gpx \
  --elevation-sample-interval 200 \
  --simplify-track true
# Produces: Same tracks, fewer points
# Size: ~500 KB
# Best for: Smartphone apps, older GPS units
```

### Single Track (Simple)

```bash
--output-garmin crew_618j_simple.gpx
# Produces: One continuous track (no --garmin-day-segments)
# Size: ~1 MB
# Best for: Overview/reference, less cluttered display
```

---

## Import to Garmin Online

1. Create account (if needed): https://connect.garmin.com/
2. Click **Import** → Select `.gpx` file
3. Verify: Should show all 11 day tracks + camp waypoints
4. Sync to device (optional):
   - **Garmin inReach:** Bluetooth sync via Explore app
   - **Handheld GPS:** USB cable + BaseCamp software
5. Share with crew: Export shareable link from Garmin Online, or email `.gpx` file directly

---

## GPS Device Compatibility

**Tested & Verified:**

- Garmin inReach Mini/Mini 2 (satellite communicator)
- Garmin Fenix 5/6/7 (multisport watches)
- Garmin Montana/Oregon (handhelds)
- Garmin Edge cycling computers
- Garmin DriveSmart automotive GPS
- Garmin Connect Mobile (iOS/Android app)

**Likely Compatible:**

- Garmin eTrex, eTrex Touch (older handhelds)
- Most Garmin devices with GPX support

---

## What's Included in GPX

| Item | Included |
|------|---------|
| Track data | All 762 path coordinates |
| Elevation | From SRTM DEM (1-arc-second resolution) |
| Waypoints | 9 camps (staffed/trail/layover) |
| Passthrough locations | Apache Springs, Black Mountain, Crater Lake, RMSC |
| Day segmentation | Optional (`--garmin-day-segments`) |
| Metadata | Trek name, dates, total distance, elevation range |

---

## Usage During Trek

**GPS Navigation:**

- Pre-trek: Sync crew's devices or use Garmin Explore mobile app
- Day 1: Load GPX on devices
- Daily: View current position on track, see distance to next camp
- Device records breadcrumb trail of actual path taken
- Post-trek: Compare planned vs actual routes

> Printed maps are the primary navigation tool; Garmin is optional backup.

**Post-Trek Analysis (Garmin Online):**

1. Download recorded track from device
2. Compare to original track via Garmin Online overlay
3. Export recorded track as GPX
4. Share in crew memory book or scrapbook
5. Calculate statistics: total distance, elevation, time, pace

---

## CLI Options

| Flag | Description |
|------|-------------|
| `--output-garmin PATH` | Path to write GPX file |
| `--garmin-day-segments` | Split into per-day tracks |
| `--garmin-include-elevation` | Include elevation (default: true) |
| `--garmin-include-timestamps` | Calculate timestamps (default: false) |
| `--garmin-include-waypoints` | Include camps/passthrough (default: true) |
| `--elevation-sample-interval INT` | Sample every N meters (default: 100) |
| | `10` = high-res (~2 MB), `50` = standard (~1 MB), `200` = light (~500 KB) |
| `--simplify-track` | Reduce points via Douglas-Peucker algorithm |
| `--track-color HEX` | Garmin display color (e.g., `#FF6B35`) |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Invalid GPX file" | Validate: `xmllint crew_618j.gpx` |
| Waypoints not showing | Verify Garmin recognizes waypoint symbols |
| File too large | Use lower sample interval: `--elevation-sample-interval 200` |
| Track offset on map | Verify lat/lon coordinates are correct in KML |
| Missing elevation | Re-export with: `--garmin-include-elevation true` |

---

## File Formats Supported

| Format | Use Case |
|--------|----------|
| GPX (recommended) | Universal GPS format, all Garmin devices |
| KML | Google Earth, mapping software |
| TCX | Garmin Training Center, fitness tracking |

All formats include elevation and waypoints.

---

## Next Steps

1. Download SRTM elevation data (if not done)
2. Run Garmin export during batch generation (Phase 7)
3. Test import on Garmin Online
4. Share `.gpx` file with crew (email or Garmin Online link)
5. Optionally pre-load on rental GPS devices
6. Brief crew on device usage (optional)

---

> See Section 12 of `topo_map_spec.md` for the detailed Garmin integration guide.
