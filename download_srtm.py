"""
Download and clip SRTM 1-arc-second tiles for the Philmont region.

Tiles needed:
  N36W105 — covers lat 36-37N, lon 104-105W (eastern Philmont)
  N36W106 — covers lat 36-37N, lon 105-106W (western Philmont)

Source: AWS elevation tiles (no auth required)
Output: data/elevation_srtm.tif (clipped to Philmont bounds, WGS84)
"""

import gzip
import io
import os
import struct
import sys

import numpy as np
import requests
import rasterio
from rasterio.transform import from_bounds
from rasterio.merge import merge
from rasterio.mask import mask
from shapely.geometry import box
import tempfile

# Philmont bounds with 0.05-degree buffer
BOUNDS = (-105.20, 36.30, -104.88, 36.50)  # (west, south, east, north)

# SRTM tiles needed
TILES = [
    ("N36", "W105", "N36W105"),
    ("N36", "W106", "N36W106"),
]

SRTM_URL = "https://s3.amazonaws.com/elevation-tiles-prod/skadi/{lat}/{name}.hgt.gz"

# SRTM1: 3601x3601 samples per 1-degree tile
SRTM1_SIZE = 3601


def download_tile(lat_tag, lon_tag, name):
    url = SRTM_URL.format(lat=lat_tag, name=name)
    print(f"  Downloading {name} from {url}")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    data = gzip.decompress(r.content)
    print(f"  Downloaded {name}: {len(data):,} bytes")
    return data


def parse_hgt(data, name):
    """Parse SRTM .hgt binary → numpy array (3601x3601, int16, rows N→S)."""
    n = SRTM1_SIZE
    expected = n * n * 2
    if len(data) != expected:
        raise ValueError(f"{name}: expected {expected} bytes, got {len(data)}")
    arr = np.frombuffer(data, dtype=">i2").reshape((n, n)).astype(np.float32)
    arr[arr == -32768] = np.nan  # SRTM void fill
    return arr


def hgt_to_tif(arr, name, tmp_dir):
    """Write parsed HGT array to a GeoTIFF in tmp_dir. Returns path."""
    # Derive SW corner from tile name (e.g. N36W105 → lat=36, lon=-105)
    lat = int(name[1:3])
    lon = -int(name[4:7])

    # Transform: top-left corner is (lon, lat+1), resolution = 1/(SRTM1_SIZE-1)
    transform = from_bounds(lon, lat, lon + 1, lat + 1, SRTM1_SIZE, SRTM1_SIZE)

    path = os.path.join(tmp_dir, f"{name}.tif")
    with rasterio.open(
        path, "w",
        driver="GTiff",
        height=SRTM1_SIZE,
        width=SRTM1_SIZE,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=np.nan,
    ) as dst:
        dst.write(arr, 1)
    return path


def main():
    out_path = "data/elevation_srtm.tif"
    os.makedirs("data", exist_ok=True)

    print("Downloading SRTM tiles...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tile_paths = []
        for lat_tag, lon_tag, name in TILES:
            raw = download_tile(lat_tag, lon_tag, name)
            arr = parse_hgt(raw, name)
            tif_path = hgt_to_tif(arr, name, tmp_dir)
            tile_paths.append(tif_path)
            valid = arr[np.isfinite(arr)]
            print(f"  Parsed {name}: min={valid.min():.0f}m max={valid.max():.0f}m "
                  f"voids={np.isnan(arr).sum()}")

        print("Merging tiles and clipping to Philmont bounds...")
        datasets = [rasterio.open(p) for p in tile_paths]
        merged, merged_transform = merge(datasets)
        for ds in datasets:
            ds.close()

        # Clip to Philmont bounds
        west, south, east, north = BOUNDS
        clip_geom = box(west, south, east, north)

        # Reopen merged as in-memory dataset to use mask()
        profile = {
            "driver": "GTiff",
            "dtype": "float32",
            "width": merged.shape[2],
            "height": merged.shape[1],
            "count": 1,
            "crs": "EPSG:4326",
            "transform": merged_transform,
        }
        merged_path = os.path.join(tmp_dir, "merged.tif")
        with rasterio.open(merged_path, "w", **profile) as dst:
            dst.write(merged)

        with rasterio.open(merged_path) as src:
            clipped, clipped_transform = mask(src, [clip_geom], crop=True)
            out_meta = src.meta.copy()

        out_meta.update({
            "driver": "GTiff",
            "height": clipped.shape[1],
            "width": clipped.shape[2],
            "transform": clipped_transform,
            "compress": "deflate",
            "tiled": True,
        })

        with rasterio.open(out_path, "w", **out_meta) as dst:
            dst.write(clipped)

    # Verify
    with rasterio.open(out_path) as src:
        arr = src.read(1)
        valid = arr[np.isfinite(arr)]
        print(f"\nOutput: {out_path}")
        print(f"  Size: {src.width}x{src.height} pixels")
        print(f"  CRS: {src.crs}")
        print(f"  Bounds: {src.bounds}")
        print(f"  Nodata: {src.nodata}")
        print(f"  Elevation range: {valid.min():.0f}m – {valid.max():.0f}m "
              f"({valid.min()*3.28084:.0f}ft – {valid.max()*3.28084:.0f}ft)")
        print(f"  Voids: {np.isnan(arr).sum()} / {arr.size}")
        print(f"  File size: {os.path.getsize(out_path)/1024/1024:.1f} MB")
    print("Done.")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
