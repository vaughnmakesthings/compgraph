from unittest.mock import patch

import pytest

from compgraph.geocoding import _geocode_cache, _normalize_location, compute_h3_index


@pytest.fixture(autouse=True)
def _clear_geocode_cache():
    _geocode_cache.clear()
    yield
    _geocode_cache.clear()


def test_normalize_location_strips_and_lowercases():
    assert _normalize_location("  New York, NY  ") == "new york, ny"


def test_normalize_location_empty():
    assert _normalize_location("") == ""


def test_normalize_location_already_normalized():
    assert _normalize_location("chicago, il") == "chicago, il"


@patch("compgraph.geocoding._geocode_sync")
async def test_geocode_location_returns_coords(mock_sync):
    mock_sync.return_value = (40.7128, -74.0060)
    from compgraph.geocoding import geocode_location

    result = await geocode_location("New York, NY")

    assert result == (40.7128, -74.0060)
    mock_sync.assert_called_once_with("New York, NY")


@patch("compgraph.geocoding._geocode_sync")
async def test_geocode_location_cache_hit(mock_sync):
    mock_sync.return_value = (34.0522, -118.2437)
    from compgraph.geocoding import geocode_location

    first = await geocode_location("Los Angeles, CA")
    second = await geocode_location("Los Angeles, CA")

    assert first == second
    mock_sync.assert_called_once()


@patch("compgraph.geocoding._geocode_sync")
async def test_geocode_location_cache_case_insensitive(mock_sync):
    mock_sync.return_value = (41.8781, -87.6298)
    from compgraph.geocoding import geocode_location

    await geocode_location("Chicago, IL")
    await geocode_location("chicago, il")

    mock_sync.assert_called_once()


async def test_geocode_location_empty_string():
    from compgraph.geocoding import geocode_location

    result = await geocode_location("")
    assert result is None


async def test_geocode_location_whitespace_only():
    from compgraph.geocoding import geocode_location

    result = await geocode_location("   ")
    assert result is None


@patch("compgraph.geocoding._geocode_sync")
async def test_geocode_location_not_found(mock_sync):
    mock_sync.return_value = None
    from compgraph.geocoding import geocode_location

    result = await geocode_location("xyznonexistent123")
    assert result is None


@patch("compgraph.geocoding._geocode_sync")
async def test_geocode_location_caches_none_result(mock_sync):
    mock_sync.return_value = None
    from compgraph.geocoding import geocode_location

    await geocode_location("Remote")
    await geocode_location("Remote")

    mock_sync.assert_called_once()


@patch("compgraph.geocoding._geocode_sync")
async def test_geocode_location_exception_returns_none(mock_sync):
    mock_sync.side_effect = Exception("network error")
    from compgraph.geocoding import geocode_location

    result = await geocode_location("Error City, XX")
    assert result is None


def test_compute_h3_index_valid_coords():
    result = compute_h3_index(40.7128, -74.0060)
    assert isinstance(result, str)
    assert len(result) > 0


def test_compute_h3_index_different_resolution():
    res6 = compute_h3_index(40.7128, -74.0060, resolution=6)
    res8 = compute_h3_index(40.7128, -74.0060, resolution=8)
    assert res6 != res8


def test_compute_h3_index_nearby_same_cell():
    idx1 = compute_h3_index(40.7128, -74.0060)
    idx2 = compute_h3_index(40.7130, -74.0062)
    assert idx1 == idx2


def test_compute_h3_index_distant_different_cell():
    nyc = compute_h3_index(40.7128, -74.0060)
    la = compute_h3_index(34.0522, -118.2437)
    assert nyc != la
