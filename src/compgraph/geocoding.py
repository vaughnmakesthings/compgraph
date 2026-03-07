import asyncio
import logging
from functools import lru_cache

import h3

logger = logging.getLogger(__name__)

_MAX_CACHE_SIZE = 10_000
_geocode_cache: dict[str, tuple[float, float] | None] = {}


def _normalize_location(location: str) -> str:
    return location.strip().lower()


def _get_api_key() -> str | None:
    from compgraph.config import settings

    return settings.GOOGLE_MAPS_API_KEY


@lru_cache(maxsize=1)
def _get_geolocator():
    api_key = _get_api_key()
    if api_key:
        from geopy.geocoders import GoogleV3

        return GoogleV3(api_key=api_key)

    from geopy.geocoders import Nominatim

    return Nominatim(user_agent="compgraph-geocoder")


async def geocode_location(location_str: str) -> tuple[float, float] | None:
    if not location_str or not location_str.strip():
        return None

    cache_key = _normalize_location(location_str)
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    try:
        result = await asyncio.to_thread(_geocode_sync, location_str)
        if len(_geocode_cache) >= _MAX_CACHE_SIZE:
            _geocode_cache.clear()
        _geocode_cache[cache_key] = result
        return result
    except Exception:
        logger.warning("Geocoding failed for '%s'", location_str, exc_info=True)
        _geocode_cache[cache_key] = None
        return None


def _geocode_sync(location_str: str) -> tuple[float, float] | None:
    geolocator = _get_geolocator()
    location = geolocator.geocode(location_str, timeout=10)
    if location:
        return (location.latitude, location.longitude)
    return None


def compute_h3_index(lat: float, lng: float, resolution: int = 6) -> str:
    return str(h3.latlng_to_cell(lat, lng, resolution))
