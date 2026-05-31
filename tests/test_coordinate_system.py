import logging
import pytest
from coordinate_system import MapScale, CoordinateSystem


# ── MapScale._parse ───────────────────────────────────────────────────────────

def test_map_scale_parse_ratio_string():
    assert MapScale("1:24000").scale_ratio == 24000
    assert MapScale("1:100000").scale_ratio == 100000


def test_map_scale_parse_bare_integer():
    assert MapScale("24000").scale_ratio == 24000


def test_map_scale_parse_auto_variants():
    assert MapScale("auto").scale_ratio is None
    assert MapScale("").scale_ratio is None
    assert MapScale(None).scale_ratio is None


def test_map_scale_parse_invalid_ratio_warns(caplog):
    """Bug 6: invalid scale string must log a warning and fall back to None."""
    with caplog.at_level(logging.WARNING, logger="coordinate_system"):
        ms = MapScale("1:invalid")
    assert ms.scale_ratio is None
    assert "1:invalid" in caplog.text


def test_map_scale_parse_comma_notation_warns(caplog):
    """'1:24,000' is a common user mistake — must warn, not silently ignore."""
    with caplog.at_level(logging.WARNING, logger="coordinate_system"):
        ms = MapScale("1:24,000")
    assert ms.scale_ratio is None
    assert "1:24,000" in caplog.text


def test_map_scale_parse_bare_invalid_warns(caplog):
    with caplog.at_level(logging.WARNING, logger="coordinate_system"):
        ms = MapScale("foo")
    assert ms.scale_ratio is None
    assert "foo" in caplog.text


# ── MapScale.calculate ────────────────────────────────────────────────────────

def test_map_scale_calculate_fixed():
    ms = MapScale("1:24000")
    ratio, label = ms.calculate((36.0, 36.1, -105.1, -105.0))
    assert ratio == 24000
    assert label == "1:24,000"


def test_map_scale_calculate_auto_returns_nice_number():
    ms = MapScale("auto")
    # Small Philmont-sized tile (~0.03°) → fits within the nice-scale list.
    ratio, label = ms.calculate((36.40, 36.43, -105.03, -105.00))
    nice = [10000, 12000, 15000, 20000, 24000, 25000, 30000,
            40000, 50000, 60000, 75000, 100000, 125000, 150000, 200000]
    assert ratio in nice
    assert str(ratio) in label.replace(",", "")


# ── CoordinateSystem UTM conversion ───────────────────────────────────────────

def test_utm_roundtrip():
    cs = CoordinateSystem(grid_type="utm", utm_zone=13, hemisphere="N")
    lon, lat = -105.0, 36.4
    e, n = cs.to_utm(lon, lat)
    lon2, lat2 = cs.from_utm(e, n)
    assert lon2 == pytest.approx(lon, abs=1e-8)
    assert lat2 == pytest.approx(lat, abs=1e-8)


def test_utm_bounds_ordering():
    cs = CoordinateSystem(grid_type="utm", utm_zone=13, hemisphere="N")
    e_min, e_max, n_min, n_max = cs.utm_bounds((36.0, 36.5, -105.5, -105.0))
    assert e_min < e_max
    assert n_min < n_max


def test_invalid_grid_type_raises():
    with pytest.raises(ValueError, match="Invalid grid_type"):
        CoordinateSystem(grid_type="bad")
