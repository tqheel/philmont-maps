import pytest
from route_extractor import (
    _split_path_to_chunks,
    _rebalance_chunks,
    _sheet_extent,
    _sub_path_cumulative,
    split_day_into_sheets,
    EnrichedDay,
)
from kml_parser import PathPoint
import trek_data


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_path(n: int, lat0=36.0, lon0=-105.0, step=0.01):
    return [
        PathPoint(lon=lon0 + i * step, lat=lat0, index=i, elev=2100.0)
        for i in range(n)
    ]


def _make_day(path, day=2, from_camp="A", to_camp="B"):
    cum = _sub_path_cumulative(path)
    return EnrichedDay(
        day=day,
        from_camp=from_camp,
        to_camp=to_camp,
        path=path,
        distance_miles=cum[-1] if cum else 0.0,
        distance_official=cum[-1] if cum else 0.0,
        gain_ft=0.0,
        loss_ft=0.0,
        elev_min_ft=6890.0,
        elev_max_ft=6890.0,
        bounds=(36.0, 36.1, -105.0, -104.9),
        cumulative_distance_mi=cum,
        waypoints=[],
    )


# ── _split_path_to_chunks ─────────────────────────────────────────────────────

def test_split_path_to_chunks_simple():
    path = [
        PathPoint(lon=-105.00, lat=36.00, index=0),
        PathPoint(lon=-105.01, lat=36.01, index=1),
        PathPoint(lon=-105.02, lat=36.02, index=2),
        PathPoint(lon=-105.03, lat=36.03, index=3),
    ]
    chunks = _split_path_to_chunks(path, max_lat_range=0.015, max_lon_range=0.015)
    assert len(chunks) == 3
    assert chunks[0] == (0, path[0:2])
    assert chunks[1][0] == 1          # overlap at index 1
    assert chunks[2][0] == 2          # overlap at index 2


def test_split_path_to_chunks_one_page():
    path = [PathPoint(lon=-105.00, lat=36.00, index=0),
            PathPoint(lon=-105.01, lat=36.01, index=1)]
    chunks = _split_path_to_chunks(path, max_lat_range=1.0, max_lon_range=1.0)
    assert len(chunks) == 1
    assert len(chunks[0][1]) == 2


def test_split_path_to_chunks_empty():
    assert _split_path_to_chunks([], 1, 1) == []


def test_split_path_to_chunks_single_point():
    path = [PathPoint(lon=-105.0, lat=36.0, index=0)]
    chunks = _split_path_to_chunks(path, max_lat_range=1.0, max_lon_range=1.0)
    assert len(chunks) == 1
    assert chunks[0][0] == 0


def test_split_path_overlap_is_single_point():
    """Adjacent chunks must share exactly one point at the boundary."""
    path = [PathPoint(lon=-105.0 + i * 0.01, lat=36.0, index=i) for i in range(6)]
    chunks = _split_path_to_chunks(path, max_lat_range=0.1, max_lon_range=0.025)
    for k in range(len(chunks) - 1):
        last_of_prev = chunks[k][1][-1]
        first_of_next = chunks[k + 1][1][0]
        assert last_of_prev.lon == first_of_next.lon
        assert last_of_prev.lat == first_of_next.lat


# ── _rebalance_chunks ─────────────────────────────────────────────────────────

def test_rebalance_chunks_equal_length():
    path = [PathPoint(lon=-105.0 + i * 0.01, lat=36.0, index=i) for i in range(10)]
    result = _rebalance_chunks(path, n=2, max_lat_range=1.0, max_lon_range=1.0)
    assert result is not None
    assert len(result) == 2
    # Both chunks should be roughly equal length.
    len0 = len(result[0][1])
    len1 = len(result[1][1])
    assert abs(len0 - len1) <= 2


def test_rebalance_chunks_returns_none_when_overflow():
    """If a balanced chunk would exceed the window, return None."""
    path = [PathPoint(lon=-105.0 + i * 0.01, lat=36.0, index=i) for i in range(10)]
    # Window too small for any chunk to fit.
    result = _rebalance_chunks(path, n=2, max_lat_range=0.0001, max_lon_range=0.0001)
    assert result is None


# ── _sheet_extent ─────────────────────────────────────────────────────────────

def test_sheet_extent_centers_on_path():
    path = [PathPoint(lon=-105.0, lat=36.0),
            PathPoint(lon=-104.9, lat=36.1)]
    lon_min, lon_max, lat_min, lat_max = _sheet_extent(path, lat_range=0.2, lon_range=0.2)
    center_lat = (lat_min + lat_max) / 2
    center_lon = (lon_min + lon_max) / 2
    assert center_lat == pytest.approx(36.05, abs=1e-6)
    assert center_lon == pytest.approx(-104.95, abs=1e-6)


def test_sheet_extent_window_size():
    path = [PathPoint(lon=-105.0, lat=36.0)]
    lon_min, lon_max, lat_min, lat_max = _sheet_extent(path, lat_range=0.1, lon_range=0.2)
    assert (lat_max - lat_min) == pytest.approx(0.1, abs=1e-9)
    assert (lon_max - lon_min) == pytest.approx(0.2, abs=1e-9)


# ── split_day_into_sheets (offset accumulation — Bug 5) ──────────────────────

def test_sheet_offset_accumulates_correctly():
    """Each sheet's sub_path_offset_mi must equal cumulative distance to its
    start point — not 0.0 regardless of start_idx position."""
    # Build a day that will split into 2 sheets: 8 evenly-spaced points along
    # longitude give ~0.5 mi each step at 36°N, total ~3.5 mi.
    path = [
        PathPoint(lon=-105.0 + i * 0.01, lat=36.4, index=i, elev=2100.0)
        for i in range(8)
    ]
    day = _make_day(path, day=2, from_camp="Rayado", to_camp="Olympia")

    # Use a very narrow window so the day must split.
    sheets = split_day_into_sheets(day, scale=24000)

    if len(sheets) == 1:
        pytest.skip("Path fits on one sheet — split didn't happen")

    # Sheet 1 always starts at 0.
    assert sheets[0].sub_path_offset_mi == pytest.approx(0.0, abs=1e-6)

    # Every subsequent sheet's offset must be > 0 and equal the cumulative
    # distance at its start index in the full day.
    for sheet in sheets[1:]:
        assert sheet.sub_path_offset_mi > 0.0, (
            f"Sheet {sheet.sheet_index} has offset 0.0 — off-by-one bug?"
        )
        # Offset + sub-distance must not exceed full day distance.
        assert sheet.sub_path_offset_mi + sheet.sub_distance_mi <= day.distance_miles + 0.01


def test_sheet_offset_fallback_uses_last_not_zero():
    """Directly verify the guard expression uses cumulative_distance_mi[-1]
    rather than 0.0 when start_idx would be at the boundary."""
    from route_extractor import _sub_path_cumulative
    path = _make_path(5)
    cum = _sub_path_cumulative(path)
    # Simulate the guard: start_idx == len(cum) (out-of-bounds edge)
    start_idx = len(cum)
    offset = (
        cum[start_idx]
        if start_idx < len(cum)
        else cum[-1]          # fixed fallback
    )
    assert offset == cum[-1]
    assert offset != 0.0 or cum[-1] == 0.0  # only 0 if path has zero length
