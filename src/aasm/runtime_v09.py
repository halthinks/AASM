from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from .runtime_v08 import AASMEngine as V08Engine
from .economics import EconomicsLedger, ModelPricing, ModelUsageRecord, ReviewGatePolicy
from .model import EventType


# Convenience snapshot for current GPT-5.6 public API pricing. Callers can
# always pass their own pricing table to economics_summary(). Cache writes are
# represented explicitly because GPT-5.6 bills explicit writes differently
# from cache reads and ordinary uncached input.
DEFAULT_GPT56_PRICING = {
    "gpt-5.6-luna": ModelPricing(
        "gpt-5.6-luna", 1.00, 0.10, 6.00,
        cache_write_per_million=1.25,
        long_context_threshold=272_000,
        long_input_multiplier=2.0,
        long_output_multiplier=1.5,
    ),
    "gpt-5.6-terra": ModelPricing(
        "gpt-5.6-terra", 2.50, 0.25, 15.00,
        cache_write_per_million=3.125,
        long_context_threshold=272_000,
        long_input_multiplier=2.0,
        long_output_multiplier=1.5,
    ),
    "gpt-5.6-sol": ModelPricing(
        "gpt-5.6-sol", 5.00, 0.50, 30.00,
        cache_write_per_million=6.25,
        long_context_threshold=272_000,
        long_input_multiplier=2.0,
        long_output_multiplier=1.5,
    ),
    "gpt-5.6": ModelPricing(
        "gpt-5.6", 5.00, 0.50, 30.00,
        cache_write_per_million=6.25,
        long_context_threshold=272_000,
        long_input_multiplier=2.0,
        long_output_multiplier=1.5,
    ),
}


class AASMEngine(V08Engine):
    """v0.9 runtime: control-center, economics, and governance accounting."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.review_policy = ReviewGatePolicy()

    @classmethod
    def _hydrate(cls, snapshot, events, store, authority=None, definition=None):
        self = super()._hydrate(snapshot, events, store, authority=authority, definition=definition)
        self.review_policy = ReviewGatePolicy()
        return self

    def record_model_usage(self, record: ModelUsageRecord, *, reason: str = "model usage recorded"):
        resources = deepcopy(self.snapshot.resources)
        economics = resources.setdefault("economics", {})
        economics.setdefault("pricing_effective", "2026-08")
        calls = economics.setdefault("calls", [])
        calls.append(asdict(record))
        self.patch_snapshot({"resources": resources}, reason)
        return deepcopy(calls[-1])

    def record_model_usage_batch(self, records: list[ModelUsageRecord], *, reason: str = "model usage batch recorded"):
        resources = deepcopy(self.snapshot.resources)
        economics = resources.setdefault("economics", {})
        economics.setdefault("pricing_effective", "2026-08")
        calls = economics.setdefault("calls", [])
        calls.extend(asdict(record) for record in records)
        self.patch_snapshot({"resources": resources}, reason)
        return deepcopy(calls[-len(records):] if records else [])

    def economics_summary(self, pricing: dict[str, ModelPricing] | None = None):
        calls = deepcopy(self.snapshot.resources.get("economics", {}).get("calls", []))
        ledger = EconomicsLedger(calls)
        return ledger.summary(pricing or DEFAULT_GPT56_PRICING)

    def review_gate(self, action_class: str, **signals):
        decision = self.review_policy.decide(action_class, **signals)
        resources = deepcopy(self.snapshot.resources)
        economics = resources.setdefault("economics", {})
        economics.setdefault("review_decisions", []).append({"action_class": action_class, **deepcopy(signals), **decision})
        self.patch_snapshot({"resources": resources}, "review gate evaluated")
        return decision

    def import_codex_telemetry(self, batch, *, reason: str = "Codex telemetry imported"):
        """Persist a CodexTelemetryImport without one event per token bucket."""
        records = list(getattr(batch, "records", []) or [])
        self.record_model_usage_batch(records, reason=reason)
        resources = deepcopy(self.snapshot.resources)
        economics = resources.setdefault("economics", {})
        imports = economics.setdefault("telemetry_imports", [])
        imports.append({
            "source": "codex_otel",
            "records": len(records),
            "ignored_events": int(getattr(batch, "ignored_events", 0) or 0),
        })
        self.patch_snapshot({"resources": resources}, "Codex telemetry import metadata recorded")
        return {
            "records_imported": len(records),
            "ignored_events": int(getattr(batch, "ignored_events", 0) or 0),
            "economics": self.economics_summary(),
        }

    def user_interrupt(self, note: str, *, metadata: dict | None = None):
        self.emit(
            EventType.USER_INTERRUPT.value,
            self.state_value,
            self.state_value,
            note,
            data={"note": note, "metadata": deepcopy(metadata or {})},
        )
        control = deepcopy(self.snapshot.metadata.get("control", {}))
        control.setdefault("interrupts", []).append({"note": note, "metadata": deepcopy(metadata or {})})
        self.patch_snapshot({"metadata": {"control": control}}, "user steering recorded")
        return deepcopy(control)

    def dashboard(self):
        return {
            "machine_id": self.snapshot.machine_id,
            "state": self.state_value,
            "version": self.snapshot.version,
            "problem": asdict(self.snapshot.problem),
            "graph": deepcopy(self.snapshot.graph),
            "frontier": deepcopy(self.snapshot.frontier),
            "workers": self.list_workers(),
            "leases": self.list_leases(),
            "resources": self.list_resources(),
            "models": self.list_model_profiles(),
            "last_model_route": self.last_model_route(),
            "economics": self.economics_summary(),
            "evidence": deepcopy(self.snapshot.evidence),
            "allowed_transitions": self.allowed(),
            "control": deepcopy(self.snapshot.metadata.get("control", {})),
        }
