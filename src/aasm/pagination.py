from __future__ import annotations

import base64
import json
from copy import deepcopy
from hashlib import sha256
from typing import Any, Iterable


class CursorError(ValueError):
    pass


def _encode(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode(cursor: str) -> dict[str, Any]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
    except Exception as exc:
        raise CursorError("invalid cursor") from exc
    if not isinstance(payload, dict) or payload.get("v") != 1 or not payload.get("after"):
        raise CursorError("unsupported cursor")
    return payload


def _row_id(row: dict[str, Any], original_index: int, id_field: str) -> str:
    value = row.get(id_field)
    if value:
        return str(value)
    # Compatibility for records created before stable IDs existed. The original
    # index keeps duplicate legacy rows distinct until bounded retention prunes
    # them, after which the cursor intentionally expires rather than mispaging.
    canonical = json.dumps(row, sort_keys=True, separators=(",", ":"), default=str)
    digest = sha256(f"{original_index}:{canonical}".encode("utf-8")).hexdigest()[:24]
    return f"legacy-{digest}"


def page_records(
    rows: Iterable[dict[str, Any]],
    *,
    cursor: str | None = None,
    limit: int = 100,
    id_field: str = "record_id",
    newest_first: bool = True,
) -> dict[str, Any]:
    limit = int(limit)
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")

    materialized = [(deepcopy(row), index) for index, row in enumerate(rows)]
    if newest_first:
        materialized.reverse()
    identities = [_row_id(row, index, id_field) for row, index in materialized]

    start = 0
    if cursor:
        after = str(_decode(cursor)["after"])
        try:
            start = identities.index(after) + 1
        except ValueError as exc:
            raise CursorError("cursor expired because its anchor is no longer retained") from exc

    selected = materialized[start : start + limit]
    items = [row for row, _ in selected]
    has_more = start + len(selected) < len(materialized)
    next_cursor = None
    if has_more and selected:
        row, original_index = selected[-1]
        next_cursor = _encode({"v": 1, "after": _row_id(row, original_index, id_field)})

    return {
        "items": items,
        "returned": len(items),
        "total_matching": len(materialized),
        "has_more": has_more,
        "next_cursor": next_cursor,
    }
