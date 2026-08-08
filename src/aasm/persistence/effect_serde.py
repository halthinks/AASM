from __future__ import annotations
from dataclasses import asdict
from ..effects import EffectRecord, EffectSpec, RetryPolicy


def effect_to_dict(record: EffectRecord) -> dict:
    return asdict(record)


def effect_from_dict(data: dict) -> EffectRecord:
    spec_data = dict(data["spec"])
    rp = spec_data.get("retry_policy", {})
    spec_data["retry_policy"] = RetryPolicy(**rp)
    spec = EffectSpec(**spec_data)
    payload = dict(data)
    payload["spec"] = spec
    return EffectRecord(**payload)
