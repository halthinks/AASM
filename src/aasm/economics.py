from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class CallPurpose(str, Enum):
    PRODUCTIVE = "productive"
    VERIFICATION = "verification"
    GOVERNANCE = "governance"
    PERMISSION_REVIEW = "permission_review"
    SYNTHESIS = "synthesis"
    RETRY = "retry"


@dataclass
class ModelPricing:
    model_id: str
    input_per_million: float
    cached_input_per_million: float
    output_per_million: float
    cache_write_per_million: float | None = None
    long_context_threshold: int | None = None
    long_input_multiplier: float = 1.0
    long_output_multiplier: float = 1.0

    def __post_init__(self):
        for name in (
            "input_per_million",
            "cached_input_per_million",
            "output_per_million",
            "long_input_multiplier",
            "long_output_multiplier",
        ):
            if float(getattr(self, name)) < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.cache_write_per_million is not None and self.cache_write_per_million < 0:
            raise ValueError("cache_write_per_million must be non-negative")
        if self.long_context_threshold is not None and self.long_context_threshold < 0:
            raise ValueError("long_context_threshold must be non-negative")


@dataclass
class ModelUsageRecord:
    model_id: str
    purpose: str
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    task_id: str | None = None
    checkpoint_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        for name in ("input_tokens", "cached_input_tokens", "cache_write_tokens", "output_tokens"):
            value = int(getattr(self, name))
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
            setattr(self, name, value)

    def estimated_cost(self, pricing: ModelPricing) -> float:
        # input_tokens is the total provider-reported input token count. Cached
        # reads and explicit cache writes are subsets when the provider exposes
        # them. Clamp the residual instead of silently producing negative cost
        # when a telemetry exporter reports overlapping counters.
        cached = min(self.cached_input_tokens, self.input_tokens)
        write = min(self.cache_write_tokens, max(0, self.input_tokens - cached))
        uncached = max(0, self.input_tokens - cached - write)
        write_rate = pricing.cache_write_per_million
        if write_rate is None:
            write_rate = pricing.input_per_million

        input_cost = (
            uncached * pricing.input_per_million
            + cached * pricing.cached_input_per_million
            + write * write_rate
        ) / 1_000_000.0
        output_cost = self.output_tokens * pricing.output_per_million / 1_000_000.0

        if pricing.long_context_threshold is not None and self.input_tokens > pricing.long_context_threshold:
            input_cost *= pricing.long_input_multiplier
            output_cost *= pricing.long_output_multiplier
        return input_cost + output_cost


@dataclass
class ReviewGatePolicy:
    """Deterministic first-pass governance policy.

    The goal is not to weaken sandboxing. It is to avoid paying a model to
    repeatedly rediscover permission decisions that can be expressed as rules.
    Semantic review is reserved for materially changed information or risky
    actions where model judgment adds value.
    """

    benign_action_classes: set[str] = field(default_factory=lambda: {
        "read", "search", "list", "test", "lint", "format", "build", "local_status"
    })
    model_review_action_classes: set[str] = field(default_factory=lambda: {
        "destructive", "credential", "security_sensitive", "external_write",
        "network_unknown", "irreversible", "unknown"
    })
    require_review_on_assumption_change: bool = True
    require_review_on_failed_tests: bool = True
    require_review_on_large_diff: bool = True
    large_diff_lines: int = 500
    coalesce_same_class: bool = True

    def decide(
        self,
        action_class: str,
        *,
        assumption_changed: bool = False,
        tests_failed: bool = False,
        diff_lines: int = 0,
        prior_reviewed_action_class: str | None = None,
    ) -> dict[str, Any]:
        if action_class in self.model_review_action_classes:
            return {"requires_model_review": True, "reason": f"risk class: {action_class}"}
        if self.require_review_on_assumption_change and assumption_changed:
            return {"requires_model_review": True, "reason": "governing assumption changed"}
        if self.require_review_on_failed_tests and tests_failed:
            return {"requires_model_review": True, "reason": "verification failed"}
        if self.require_review_on_large_diff and diff_lines >= self.large_diff_lines:
            return {"requires_model_review": True, "reason": "large material change"}
        if action_class in self.benign_action_classes:
            return {"requires_model_review": False, "reason": "deterministic benign policy"}
        if self.coalesce_same_class and prior_reviewed_action_class == action_class:
            return {"requires_model_review": False, "reason": "same reviewed action class; coalesced"}
        return {"requires_model_review": True, "reason": "unclassified action"}


class EconomicsLedger:
    def __init__(self, records: list[dict[str, Any]] | None = None):
        self.records = [ModelUsageRecord(**r) for r in (records or [])]

    def add(self, record: ModelUsageRecord) -> ModelUsageRecord:
        self.records.append(record)
        return record

    def summary(self, pricing: dict[str, ModelPricing]) -> dict[str, Any]:
        by_purpose: dict[str, dict[str, float]] = {}
        total_cost = 0.0
        total_tokens = 0
        total_cache_reads = 0
        total_cache_writes = 0
        unpriced_tokens = 0
        unpriced_models: set[str] = set()
        long_context_calls = 0

        for record in self.records:
            tokens = record.input_tokens + record.output_tokens
            is_priced = record.model_id in pricing
            model_pricing = pricing.get(record.model_id)
            cost = record.estimated_cost(model_pricing) if model_pricing is not None else 0.0
            if (
                model_pricing is not None
                and model_pricing.long_context_threshold is not None
                and record.input_tokens > model_pricing.long_context_threshold
            ):
                long_context_calls += 1
            if not is_priced and tokens:
                unpriced_tokens += tokens
                unpriced_models.add(record.model_id)

            total_tokens += tokens
            total_cache_reads += record.cached_input_tokens
            total_cache_writes += record.cache_write_tokens
            total_cost += cost
            bucket = by_purpose.setdefault(
                record.purpose,
                {
                    "calls": 0,
                    "tokens": 0,
                    "cached_input_tokens": 0,
                    "cache_write_tokens": 0,
                    "estimated_cost": 0.0,
                    "unpriced_tokens": 0,
                },
            )
            bucket["calls"] += 1
            bucket["tokens"] += tokens
            bucket["cached_input_tokens"] += record.cached_input_tokens
            bucket["cache_write_tokens"] += record.cache_write_tokens
            bucket["estimated_cost"] += cost
            if not is_priced:
                bucket["unpriced_tokens"] += tokens

        governance_purposes = {
            CallPurpose.GOVERNANCE.value,
            CallPurpose.PERMISSION_REVIEW.value,
            CallPurpose.VERIFICATION.value,
        }
        governance_cost = sum(v["estimated_cost"] for k, v in by_purpose.items() if k in governance_purposes)
        governance_tokens = sum(v["tokens"] for k, v in by_purpose.items() if k in governance_purposes)
        cost_complete = unpriced_tokens == 0
        return {
            "calls": len(self.records),
            "tokens": total_tokens,
            "cached_input_tokens": total_cache_reads,
            "cache_write_tokens": total_cache_writes,
            "long_context_calls": long_context_calls,
            "estimated_cost": total_cost,
            "by_purpose": by_purpose,
            "governance_cost_ratio": (governance_cost / total_cost) if total_cost and cost_complete else None,
            "governance_token_ratio": (governance_tokens / total_tokens) if total_tokens else 0.0,
            "unpriced_tokens": unpriced_tokens,
            "unpriced_models": sorted(unpriced_models),
            "cost_complete": cost_complete,
        }

    def to_dict(self) -> list[dict[str, Any]]:
        return [asdict(r) for r in self.records]
