from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID


def new_row_id() -> str:
    return str(uuid.uuid4())


def safe_uuid_str(val: UUID | str | None) -> str | None:
    return str(val) if val is not None else None


def safe_float(val: Any) -> float | None:
    return float(val) if val is not None else None


def today_utc() -> date:
    return datetime.now(UTC).date()
