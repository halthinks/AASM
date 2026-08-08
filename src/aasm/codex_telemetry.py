from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .economics import CallPurpose, ModelUsageRecord


@dataclass
class CodexTelemetryImport:
    records: list[ModelUsageRecord]
    ignored_events: int = 0


def _walk(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield path, child
            yield from _walk(child, path)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from _walk(child, f"{prefix}[{i}]")


def _first(flat: dict[str, Any], endings: tuple[str, ...], default=None):
    for key, value in flat.items():
        low = key.lower()
        if any(low.endswith(s) for s in endings):
            return value
    return default


def _purpose(model: str, source: str) -> str:
    text = f"{model} {source}".lower()
    if "auto-review" in text or "auto_review" in text or "subagent_guardian" in text or "guardian" in text:
        return CallPurpose.PERMISSION_REVIEW.value
    if "review" in text or "verify" in text:
        return CallPurpose.VERIFICATION.value
    return CallPurpose.PRODUCTIVE.value


def import_otel_events(events: Iterable[dict[str, Any]]) -> CodexTelemetryImport:
    """Convert Codex OpenTelemetry-style token metrics into AASM usage records.

    The importer intentionally accepts loose JSON structures because OTLP
    collectors/exporters wrap attributes differently. It looks for model,
    session source, token type and numeric usage fields, then groups compatible
    records without requiring one specific collector vendor's envelope.
    """
    grouped: dict[tuple[str, str, str], dict[str, int]] = {}
    ignored = 0
    for event in events:
        flat = dict(_walk(event))
        model = str(_first(flat, ("model", "model_id"), "codex-unspecified"))
        source = str(_first(flat, ("session_source", "originator", "source"), ""))
        token_type = str(_first(flat, ("token_type",), "")).lower()
        raw_value = _first(flat, ("value", "sum", "token_count", "tokens"), None)
        if raw_value is None:
            # Prometheus/OTLP JSON sometimes leaves the metric number at a
            # top-level value whose key includes token_usage_sum.
            for key, value in flat.items():
                if "token_usage" in key.lower() and isinstance(value, (int, float)):
                    raw_value = value
                    break
        try:
            count = int(raw_value)
        except (TypeError, ValueError):
            ignored += 1
            continue
        if count < 0:
            ignored += 1
            continue
        purpose = _purpose(model, source)
        key = (model, purpose, source)
        bucket = grouped.setdefault(key, {"input": 0, "cached_input": 0, "output": 0})
        if token_type in {"cached_input", "cached", "cache_read"}:
            bucket["cached_input"] += count
            bucket["input"] += count
        elif token_type in {"output", "reasoning_output"}:
            bucket["output"] += count
        elif token_type in {"input", "non_cached_input", "uncached_input"}:
            bucket["input"] += count
        else:
            # Unknown token classes are ignored rather than silently charged as
            # fresh input; callers can inspect ignored_events/telemetry source.
            ignored += 1
            continue
    records = [
        ModelUsageRecord(
            model_id=model,
            purpose=purpose,
            input_tokens=counts["input"],
            cached_input_tokens=counts["cached_input"],
            output_tokens=counts["output"],
            metadata={"source": "codex_otel", "session_source": source},
        )
        for (model, purpose, source), counts in grouped.items()
    ]
    return CodexTelemetryImport(records=records, ignored_events=ignored)


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    events=[]
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line=line.strip()
            if not line:
                continue
            try:
                value=json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                events.append(value)
    return events


def import_otel_jsonl(path: str | Path) -> CodexTelemetryImport:
    return import_otel_events(load_jsonl(path))
