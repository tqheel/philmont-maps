import pytest
import numpy as np
from unittest.mock import MagicMock
from rasterio.transform import from_bounds as _rasterio_from_bounds
from elevation_integrator import ElevationIntegrator, hillshade
from kml_parser import PathPoint


# ── Helpers ───────────────────────────────────────────────────────────────────

class DummyIntegrator:
    """Minimal stand-in that only exercises the pure-Python gain_loss logic."""
    def gain_loss(self, path, smooth_window=7, min_step_ft=3.0):
        return ElevationIntegrator.gain_loss(self, path, smooth_window, min_step_ft)


def _make_integrator(dem_values: np.ndarray, nodata=None) -> ElevationIntegrator:
    """Build an ElevationIntegrator directly from a numpy array.

    Uses a real affine transform (from_bounds) so rasterio.transform.rowcol
    works without any mocking — path points at pixel-centre lons round to the
    correct column index.
    """
    n = dem_values.size
    integrator = object.__new__(ElevationIntegrator)
    # 1-row raster: n columns spanning lon [0, n*0.01] lat [0, 0.01].
    # Pixel i centre: lon=(i+0.5)*0.01, lat=0.005.
    integrator.transform = _rasterio_from_bounds(
        0.0, 0.0, n * 0.01, 0.01, n, 1
    )
    integrator.array = dem_values.reshape(1, n).astype(np.float32)
    integrator.height = 1
    integrator.width = n
    integrator.nodata = nodata
    integrator.src = MagicMock()
    integrator.bounds = MagicMock()
    integrator.dem_path = MagicMock()
    return integrator


def _make_path(n: int, base_elev: float = 0.0):
    """Points at the pixel centres of the raster built by _make_integrator."""
    return [PathPoint(lon=(i + 0.5) * 0.01, lat=0.005, elev=base_elev)
            for i in range(n)]


# ── gain_loss tests ───────────────────────────────────────────────────────────

def test_gain_loss_flat():
    integrator = DummyIntegrator()
    path = [PathPoint(lon=0, lat=0, elev=2000),
            PathPoint(lon=0.1, lat=0.1, elev=2000)]
    gl = integrator.gain_loss(path, smooth_window=1)
    assert gl.gain_ft == 0.0
    assert gl.loss_ft == 0.0


def test_gain_loss_simple_climb():
    integrator = DummyIntegrator()
    path = [PathPoint(lon=0, lat=0, elev=1000),
            PathPoint(lon=0.01, lat=0.01, elev=1010)]
    gl = integrator.gain_loss(path, smooth_window=1)
    assert gl.gain_ft == pytest.approx(32.8084, abs=1e-3)
    assert gl.loss_ft == 0.0


def test_gain_loss_descent():
    integrator = DummyIntegrator()
    path = [PathPoint(lon=0, lat=0, elev=1010),
            PathPoint(lon=0.01, lat=0.01, elev=1000)]
    gl = integrator.gain_loss(path, smooth_window=1)
    assert gl.gain_ft == 0.0
    assert gl.loss_ft == pytest.approx(32.8084, abs=1e-3)


def test_gain_loss_threshold():
    integrator = DummyIntegrator()
    # 0.5 m ≈ 1.64 ft — below the 3 ft threshold.
    path = [PathPoint(lon=0, lat=0, elev=1000.0),
            PathPoint(lon=0.01, lat=0.01, elev=1000.5)]
    gl = integrator.gain_loss(path, smooth_window=1, min_step_ft=3.0)
    assert gl.gain_ft == 0.0

    # 2 m ≈ 6.56 ft — above threshold.
    path = [PathPoint(lon=0, lat=0, elev=1000.0),
            PathPoint(lon=0.01, lat=0.01, elev=1002.0)]
    gl = integrator.gain_loss(path, smooth_window=1, min_step_ft=3.0)
    assert gl.gain_ft == pytest.approx(6.56168, abs=1e-3)


def test_gain_loss_min_max():
    integrator = DummyIntegrator()
    path = [PathPoint(lon=0, lat=0, elev=2000),
            PathPoint(lon=0.01, lat=0, elev=2200),
            PathPoint(lon=0.02, lat=0, elev=2100)]
    gl = integrator.gain_loss(path, smooth_window=1, min_step_ft=0)
    assert gl.min_ft == pytest.approx(2000 * 3.28084, abs=1.0)
    assert gl.max_ft == pytest.approx(2200 * 3.28084, abs=1.0)


def test_gain_loss_smoothing():
    integrator = DummyIntegrator()
    path = [PathPoint(lon=0, lat=0, elev=1000),
            PathPoint(lon=0.01, lat=0.01, elev=1005),
            PathPoint(lon=0.02, lat=0.02, elev=1000),
            PathPoint(lon=0.03, lat=0.03, elev=1005)]
    gl_no_smooth = integrator.gain_loss(path, smooth_window=1, min_step_ft=0)
    gl_smooth    = integrator.gain_loss(path, smooth_window=3, min_step_ft=0)
    assert gl_smooth.gain_ft < gl_no_smooth.gain_ft


def test_gain_loss_single_point():
    integrator = DummyIntegrator()
    gl = integrator.gain_loss([PathPoint(lon=0, lat=0, elev=2000)], smooth_window=1)
    assert gl.gain_ft == 0.0
    assert gl.loss_ft == 0.0


# ── assign_elevations tests ───────────────────────────────────────────────────

def test_elevation_interpolation():
    """Middle artifact point (0 m) is interpolated from its neighbours."""
    integrator = _make_integrator(np.array([2000, 0, 2000], dtype=np.float32))
    path = _make_path(3)
    integrator.assign_elevations(path)
    assert path[0].elev == pytest.approx(2000, abs=1)
    assert path[1].elev == pytest.approx(2000, abs=1)   # interpolated, not 0
    assert path[2].elev == pytest.approx(2000, abs=1)


def test_assign_elevations_all_artifacts_fallback():
    """Bug 1: when every sample is a merge-border artifact the fallback must
    not be 0 m (physically impossible at Philmont ~2000 m+)."""
    # All raw values 500 m → below 1000 m filter → all NaN → fallback fires.
    integrator = _make_integrator(np.array([500, 500, 500], dtype=np.float32))
    path = _make_path(3)
    integrator.assign_elevations(path)
    for p in path:
        assert p.elev >= 2000.0, (
            f"Fallback produced physically impossible elevation {p.elev} m "
            "(should be ≥ 2000 m for Philmont terrain)"
        )


def test_assign_elevations_accepts_generator():
    """Bug 4: assign_elevations must handle any Iterable, not just lists."""
    integrator = _make_integrator(np.array([2100, 2200, 2300], dtype=np.float32))
    gen = ((i + 0.5) * 0.01 for i in range(3))   # generator of lons
    path_gen = (PathPoint(lon=lon, lat=0.005) for lon in gen)
    result = integrator.assign_elevations(path_gen)
    assert len(result) == 3
    assert all(p.elev > 1000 for p in result)


def test_assign_elevations_empty_input():
    integrator = _make_integrator(np.array([2100], dtype=np.float32))
    assert integrator.assign_elevations([]) == []


def test_assign_elevations_valid_values_unchanged():
    """Valid elevations well above 1000 m pass through without modification."""
    integrator = _make_integrator(np.array([2100, 2500, 2200], dtype=np.float32))
    path = _make_path(3)
    integrator.assign_elevations(path)
    assert path[0].elev == pytest.approx(2100, abs=1)
    assert path[1].elev == pytest.approx(2500, abs=1)
    assert path[2].elev == pytest.approx(2200, abs=1)


def test_gain_loss_with_zero_elevation_artifact():
    """Bug 2: verify the all-artifact fallback never lets a 0 m point reach
    gain_loss, which would produce phantom ~6500 ft spikes."""
    integrator = _make_integrator(np.array([500, 500, 500], dtype=np.float32))
    path = _make_path(3)
    integrator.assign_elevations(path)
    elevations = [p.elev for p in path]
    assert all(e >= 2000.0 for e in elevations), (
        f"Elevation fallback produced physically impossible values: {elevations}"
    )
    # With corrected elevations, gain_loss must not produce a massive spike.
    dummy = DummyIntegrator()
    gl = dummy.gain_loss(path, smooth_window=1, min_step_ft=3.0)
    assert gl.gain_ft < 100.0, (
        f"Unexpected gain spike {gl.gain_ft:.0f} ft — 0 m artifact leaked through"
    )


# ── hillshade tests ───────────────────────────────────────────────────────────

def test_hillshade_output_range():
    grid = np.array([[2000, 2100, 2000],
                     [2100, 2500, 2100],
                     [2000, 2100, 2000]], dtype=np.float32)
    hs = hillshade(grid)
    assert hs.shape == grid.shape
    assert hs.min() >= 0.0
    assert hs.max() <= 1.0


def test_hillshade_flat_terrain():
    """Flat terrain → uniform illumination (only the sin(alt) term survives)."""
    flat = np.full((5, 5), 2000.0, dtype=np.float32)
    hs = hillshade(flat)
    assert np.allclose(hs, hs[0, 0]), "Flat terrain should produce uniform hillshade"
