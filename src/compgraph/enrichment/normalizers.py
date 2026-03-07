from __future__ import annotations

import re

_COMPANY_NAMES = [
    "2020 companies",
    "bds connected solutions",
    "marketsource",
    "t-roc",
    "mosaic sales solutions",
    "advantage solutions",
    "acosta",
]

_LOCATION_SUFFIX = re.compile(
    r"\s*[-|\u2013\u2014]\s*[A-Za-z\s]+,\s*[A-Z]{2}(?:,\s*(?:US|CA))?\s*$"
    r"|\s*\([A-Za-z\s]+,\s*[A-Z]{2}(?:,\s*(?:US|CA))?\)\s*$",
    re.IGNORECASE,
)

_COMPANY_SUFFIX_PATTERNS: list[re.Pattern[str]] = [
    re.compile(rf"\s*[-|\u2013\u2014]\s*{re.escape(name)}\s*$", re.IGNORECASE)
    for name in _COMPANY_NAMES
]

_STORE_NUMBER = re.compile(
    r"\s*[-\u2013\u2014]\s*(?:store\s*)?#?\d{3,5}\s*$"
    r"|\s+store\s+#?\d{3,5}\s*$",
    re.IGNORECASE,
)

_CA_PROVINCES = frozenset(
    {
        "AB",
        "BC",
        "MB",
        "NB",
        "NL",
        "NS",
        "NT",
        "NU",
        "ON",
        "PE",
        "QC",
        "SK",
        "YT",
    }
)

_ZIP_CODE = re.compile(r"\s+\d{5}(?:-\d{4})?")

_COUNTRY_SUFFIX = re.compile(r",\s*(?:US|CA)\s*$", re.IGNORECASE)


def normalize_title_for_grouping(title: str | None) -> str | None:
    if not title or not title.strip():
        return None

    result = title.strip().lower()

    result = _LOCATION_SUFFIX.sub("", result)

    result = _STORE_NUMBER.sub("", result)

    for pattern in _COMPANY_SUFFIX_PATTERNS:
        result = pattern.sub("", result)

    result = re.sub(r"\s+", " ", result).strip()

    return result if result else None


def normalize_location_raw(location: str | None) -> tuple[str, str, str] | None:
    if not location or not location.strip():
        return None

    loc = location.strip()

    country_match = re.search(r",\s*(US|CA)\s*$", loc, re.IGNORECASE)
    explicit_country = country_match.group(1).upper() if country_match else None
    loc = _COUNTRY_SUFFIX.sub("", loc)

    loc = _ZIP_CODE.sub("", loc)

    parts = [p.strip() for p in loc.split(",") if p.strip()]
    if len(parts) < 2:
        return None

    city = parts[0].title()
    state = parts[1].strip().upper()

    if explicit_country:
        country = explicit_country
    elif state in _CA_PROVINCES:
        country = "CA"
    else:
        country = "US"

    return (city, state, country)
