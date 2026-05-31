import pytest
from garmin_exporter import _simplify_track, _thin_by_distance_m
from kml_parser import PathPoint


# ── _simplify_track ───────────────────────────────────────────────────────────

def test_simplify_track_collinear_with_duplicates():
    """Four collinear points with a duplicate in the middle.
    Endpoints must be preserved and all retained points must be from the
    original list in their original order (no index confusion from the old
    list.index() bug pattern)."""
    path = [
        PathPoint(lon=-105.0, lat=36.0, index=0),
        PathPoint(lon=-105.1, lat=36.1, index=1),
        PathPoint(lon=-105.1, lat=36.1, index=2),   # duplicate of index 1
        PathPoint(lon=-105.2, lat=36.2, index=3),
    ]
    simplified = _simplify_track(path, tolerance_deg=1e-9)
    # Endpoints always kept.
    assert simplified[0] is path[0]
    assert simplified[-1] is path[-1]
    # All retained objects must be from the original path.
    assert all(p in path for p in simplified)
    # Points must appear in their original lon order (no index jump).
    lons = [p.lon for p in simplified]
    assert lons == sorted(lons, reverse=True)


def test_simplify_track_non_unique_coordinates():
    """Path that doubles back to the start: all three points must be kept
    because the middle point is farthest from the A→A baseline."""
    path = [
        PathPoint(lon=0.0, lat=0.0, index=0),
        PathPoint(lon=1.0, lat=1.0, index=1),
        PathPoint(lon=0.0, lat=0.0, index=2),   # doubles back
    ]
    simplified = _simplify_track(path, tolerance_deg=0.1)
    assert len(simplified) == 3
    assert simplified[0] is path[0]
    assert simplified[1] is path[1]
    assert simplified[2] is path[2]


def test_simplify_track_short_path():
    """Paths shorter than 3 points are returned unchanged."""
    one = [PathPoint(lon=0, lat=0, index=0)]
    assert _simplify_track(one) == one

    two = [PathPoint(lon=0, lat=0, index=0), PathPoint(lon=1, lat=1, index=1)]
    assert _simplify_track(two) == two


def test_simplify_track_preserves_endpoints():
    """First and last points are always kept regardless of geometry."""
    path = [PathPoint(lon=float(i), lat=0.0, index=i) for i in range(10)]
    simplified = _simplify_track(path, tolerance_deg=0.001)
    assert simplified[0] is path[0]
    assert simplified[-1] is path[-1]


def test_simplify_track_large_tolerance_keeps_endpoints_only():
    """With a very large tolerance, only the two endpoints survive."""
    path = [PathPoint(lon=float(i) * 0.001, lat=0.0, index=i) for i in range(20)]
    simplified = _simplify_track(path, tolerance_deg=10.0)
    assert len(simplified) == 2
    assert simplified[0] is path[0]
    assert simplified[-1] is path[-1]


def test_simplify_track_result_is_subset_of_input():
    """Every point in the simplified result must be an object from the input."""
    path = [PathPoint(lon=float(i) * 0.01, lat=float(i) * 0.005, index=i)
            for i in range(15)]
    simplified = _simplify_track(path, tolerance_deg=1e-4)
    assert all(p in path for p in simplified)


# ── _thin_by_distance_m ───────────────────────────────────────────────────────

def test_thin_by_distance_preserves_endpoints():
    path = [PathPoint(lon=float(i) * 0.01, lat=36.0, index=i) for i in range(10)]
    thinned = _thin_by_distance_m(path, sample_interval_m=500)
    assert thinned[0] is path[0]
    assert thinned[-1] is path[-1]


def test_thin_by_distance_zero_interval_returns_all():
    path = [PathPoint(lon=float(i) * 0.01, lat=36.0, index=i) for i in range(5)]
    assert _thin_by_distance_m(path, sample_interval_m=0) == path


def test_thin_by_distance_large_interval_keeps_endpoints():
    path = [PathPoint(lon=float(i) * 0.0001, lat=36.0, index=i) for i in range(20)]
    thinned = _thin_by_distance_m(path, sample_interval_m=100_000)
    assert thinned[0] is path[0]
    assert thinned[-1] is path[-1]
    # Very large interval → only endpoints remain.
    assert len(thinned) == 2
