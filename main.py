"""Crew 618-J topo map generator — CLI entry point.

Wires KML parsing + SRTM elevation + page composition + Garmin export into
one command. Use ``--day N`` to render a single day; default is full batch
(summary + Days 2–12) merged into a single PDF.
"""

from __future__ import annotations

import argparse
import logging
import sys
from itertools import groupby
from pathlib import Path

import config
import trek_data
from coordinate_system import CoordinateSystem, MapScale
from elevation_integrator import ElevationIntegrator
from garmin_exporter import GarminExporter, GarminExportOptions
from page_composer import (
    generate_sheet,
    generate_summary_map,
    merge_pdfs,
)
from route_extractor import (
    build_enriched_days,
    build_sheets_for_all_days,
    split_day_into_sheets,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate Philmont Crew 618-J topo maps + Garmin GPX.",
    )
    p.add_argument("--route-data", default="route_data.json",
                   help="Route data file: route_data.json (default) or a .kml file.")
    p.add_argument("--elevation-raster", required=True,
                   help="Path to SRTM DEM GeoTIFF (data/elevation_srtm.tif).")
    p.add_argument("--output-pdf", default=None,
                   help="Output merged PDF (default: output/crew_618j_maps.pdf).")
    p.add_argument("--output-garmin", default=None,
                   help="Output GPX file (omit to skip GPX export).")
    p.add_argument("--day", type=int, default=None,
                   help="Generate single day map (2-12).")
    p.add_argument("--summary-only", action="store_true",
                   help="Generate summary/overview page only.")
    p.add_argument("--output", default=None,
                   help="Output PDF for --day or --summary-only mode.")
    p.add_argument("--grid-type", choices=["latlon", "utm", "both"],
                   default=config.GRID_TYPE)
    p.add_argument("--map-scale", default=config.MAP_SCALE,
                   help="'auto' or '1:24000' etc.")
    p.add_argument("--dpi", type=int, default=config.DPI)
    p.add_argument("--utm-zone", type=int, default=config.UTM_ZONE)
    p.add_argument("--utm-hemisphere", choices=["N", "S"],
                   default=config.UTM_HEMISPHERE)
    p.add_argument("--garmin-day-segments", action="store_true",
                   help="Split GPX into per-day tracks.")
    p.add_argument("--garmin-include-elevation",
                   action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--garmin-include-timestamps",
                   action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--elevation-sample-interval", type=int,
                   default=config.GARMIN_SAMPLE_INTERVAL_M)
    p.add_argument("--simplify-track", action="store_true")
    p.add_argument("--keep-intermediates",
                   action=argparse.BooleanOptionalAction, default=True,
                   help="Keep per-day PDFs (default: True).")
    p.add_argument("-v", "--verbose", action="count", default=0)
    return p.parse_args()


def _render_day_pdf(
    day_sheets: list,
    out_path: Path,
    integrator: ElevationIntegrator,
    coord_sys: CoordinateSystem,
) -> Path:
    """Render all sheets for one day into a single PDF file.

    Single-sheet days write directly; multi-sheet days write to temp files,
    merge them, then remove the temps.
    """
    if len(day_sheets) == 1:
        return generate_sheet(day_sheets[0], integrator, coord_sys, out_path)
    tmp_paths = []
    for sheet in day_sheets:
        tmp = out_path.parent / f"_tmp_{out_path.stem}_s{sheet.sheet_index}.pdf"
        generate_sheet(sheet, integrator, coord_sys, tmp)
        tmp_paths.append(tmp)
    merge_pdfs(tmp_paths, out_path)
    for tmp in tmp_paths:
        tmp.unlink(missing_ok=True)
    return out_path


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.WARNING - 10 * min(args.verbose, 2),
        format="%(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger("main")

    # Apply DPI override into config (used by composer at render time).
    config.DPI = args.dpi

    out_dir = Path(config.OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("Loading route data and SRTM …")
    days, waypoints, _full_path, warnings = build_enriched_days(
        args.route_data, args.elevation_raster,
    )
    for w in warnings:
        log.warning(w)
    log.info("Loaded %d day segments, %d waypoints",
             len(days), len(waypoints))

    integrator = ElevationIntegrator(args.elevation_raster)
    coord_sys = CoordinateSystem(
        grid_type=args.grid_type,
        utm_zone=args.utm_zone,
        hemisphere=args.utm_hemisphere,
    )
    # Per-sheet maps are fixed scale (parsed from --map-scale, default 1:24000).
    # MapScale is only consulted for the summary page (variable, fits trek).
    sheet_scale_obj = MapScale(args.map_scale)
    sheet_scale = sheet_scale_obj.scale_ratio or 24000
    summary_scale = MapScale("auto")

    # ── Single-day mode ───────────────────────────────────────────────────
    if args.day is not None:
        if args.day not in days:
            log.error("Day %d not found in segments (have %s)",
                      args.day, sorted(days))
            return 2
        day_sheets = split_day_into_sheets(days[args.day], scale=sheet_scale)
        out = Path(args.output or f"output/day_{args.day:02d}.pdf")
        _render_day_pdf(day_sheets, out, integrator, coord_sys)
        print(f"Wrote {out}")
        return 0

    # ── Summary-only mode ─────────────────────────────────────────────────
    if args.summary_only:
        output = Path(args.output or "output/summary.pdf")
        generate_summary_map(
            days, waypoints, integrator, coord_sys, summary_scale, output,
        )
        print(f"Wrote {output}")
        return 0

    # ── Full batch mode ───────────────────────────────────────────────────
    summary_path = out_dir / "summary.pdf"
    generate_summary_map(
        days, waypoints, integrator, coord_sys, summary_scale, summary_path,
    )

    sheets = build_sheets_for_all_days(days, scale=sheet_scale)
    day_pdfs: list[Path] = []
    for day_num, day_sheets_iter in groupby(sheets, key=lambda s: s.day):
        day_sheets = list(day_sheets_iter)
        pdf = out_dir / f"day_{day_num:02d}.pdf"
        _render_day_pdf(day_sheets, pdf, integrator, coord_sys)
        day_pdfs.append(pdf)

    merged = Path(args.output_pdf or "output/crew_618j_maps.pdf")
    merge_pdfs([summary_path] + day_pdfs, merged)
    print(f"Wrote {merged}  ({1 + len(day_pdfs)} days)")

    if not args.keep_intermediates:
        log.info("Cleaning up intermediate PDFs …")
        summary_path.unlink(missing_ok=True)
        for p in day_pdfs:
            p.unlink(missing_ok=True)

    # ── Garmin export ─────────────────────────────────────────────────────
    if args.output_garmin:
        exporter = GarminExporter()
        opts = GarminExportOptions(
            day_segments=args.garmin_day_segments,
            include_elevation=args.garmin_include_elevation,
            include_timestamps=args.garmin_include_timestamps,
            sample_interval_m=args.elevation_sample_interval,
            simplify_track=args.simplify_track,
        )
        exporter.export_to_gpx(days, waypoints, args.output_garmin, opts)
        print(f"Wrote {args.output_garmin}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
