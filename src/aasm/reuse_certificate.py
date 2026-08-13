from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class ReuseValidation:
    usable: bool
    mode: str | None
