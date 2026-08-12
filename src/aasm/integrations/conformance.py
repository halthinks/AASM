from __future__ import annotations

"""Framework-neutral adapter conformance for the canonical AASM authority path.

The conformance kit is an observer and test harness. It does not replace the
runtime, reducer, scheduler, effect ledger, worker/lease system, or persistence.
Adapters receive an audited Store and the current AASMEngine class, execute a
bounded scenario, and return observations. The kit independently checks the
persisted event history, replay, provenance, authority declaration, and
scenario-specific outcomes.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import inspect
import json
import re
import traceback
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from ..persistence.memory import MemoryStore


ADAPTER_CONFORMANCE_ID = "aasm.adapter.conformance.v1"
ADAPTER_CONFORMANCE_VERSION = "0.1.0"

CONFORMANCE_SCENARIOS: tuple[str, ...] = (
    "success",
    "contradiction",
    "requirement_change",
    "lease_loss",
    "unknown_effect",
    "restart",
    "replay",
    "fork",
)

_MUTATING_STORE_METHODS = {
    "initialize_run",
    "append",
    "save_checkpoint",
    "save_effect",
    "claim_effect_attempt",
    "finish_effect_attempt",
    "mark_running_effects_unknown",
    "acquire_task_claim",
    "renew_task_claim",
    "release_task_claim",
}

_CANONICAL_MUTATION_MODULES = (
    "aasm.engine",
    "aasm.runtime",
    "aasm.persistence",
)

_EXTERNAL_OPERATION: ContextVar[str | None] = ContextVar(
    "aasm_conformance_external_operation", default=None
)

_SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?$")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _module_chain() -> list[str]:
    modules: list[str] = []
    frame = inspect.currentframe()
    try:
        frame = frame.f_back if frame is not None else None
        while frame is not None and len(modules) < 32:
            module = str(frame.f_globals.get("__name__") or "")
            if module:
                modules.append(module)
            frame = frame.f_back
    finally:
        del frame
    return modules


class ConformanceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass
class AdapterCapabilityDeclaration:
    adapter_id: str
    adapter_version: str
    driver_id: str
    driver_version: str
    scenarios: dict[str, bool]
    authority: dict[str, Any]
    recovery_actions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    schema_version: int = 1

    def __post_init__(self) -> None:
        if not self.adapter_id or not self.driver_id:
            raise ValueError("adapter_id and driver_id are required")
        if not _SEMVER_RE.fullmatch(self.adapter_version):
            raise ValueError(f"invalid adapter_version: {self.adapter_version}")
        if not _SEMVER_RE.fullmatch(self.driver_version):
            raise ValueError(f"invalid driver_version: {self.driver_version}")
        unknown = sorted(set(self.scenarios) - set(CONFORMANCE_SCENARIOS))
        if unknown:
            raise ValueError(f"unknown conformance scenarios: {unknown}")
        self.scenarios = {
            scenario: bool(self.scenarios.get(scenario, False))
            for scenario in CONFORMANCE_SCENARIOS
        }
        self.recovery_actions = sorted(set(str(value) for value in self.recovery_actions))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AdapterScenarioOutcome:
    scenario_id: str
    machine_id: str
    observations: dict[str, Any] = field(default_factory=dict)
    adapter_report: dict[str, Any] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)
    framework_state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.scenario_id not in CONFORMANCE_SCENARIOS:
            raise ValueError(f"unknown scenario_id: {self.scenario_id}")
        if not self.machine_id:
            raise ValueError("scenario outcome requires machine_id")
        self.evidence_ids = sorted(set(str(value) for value in self.evidence_ids))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConformanceFinding:
    code: str
    severity: str
    message: str
    scenario_id: str | None = None
    event_id: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConformanceScenarioResult:
    scenario_id: str
    status: str
    machine_id: str | None
    checks: dict[str, bool | None] = field(default_factory=dict)
    findings: list[ConformanceFinding] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    replay_snapshot_hash: str | None = None
    persisted_snapshot_hash: str | None = None

    @property
    def valid(self) -> bool:
        return self.status == ConformanceStatus.PASS.value and all(
            value is True for value in self.checks.values()
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["findings"] = [finding.to_dict() for finding in self.findings]
        value["valid"] = self.valid
        return value


@dataclass
class AdapterConformanceReport:
    adapter: AdapterCapabilityDeclaration
    status: str
    scenarios: list[ConformanceScenarioResult]
    coverage: dict[str, Any]
    audit: dict[str, Any]
    contract_id: str = ADAPTER_CONFORMANCE_ID
    contract_version: str = ADAPTER_CONFORMANCE_VERSION
    schema_version: int = 1
    report_fingerprint: str = ""

    @property
    def valid(self) -> bool:
        return self.status == ConformanceStatus.PASS.value

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        value = {
            "schema_version": self.schema_version,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "adapter": self.adapter.to_dict(),
            "status": self.status,
            "valid": self.valid,
            "scenarios": [result.to_dict() for result in self.scenarios],
            "coverage": deepcopy(self.coverage),
            "audit": deepcopy(self.audit),
        }
        if include_fingerprint:
            value["report_fingerprint"] = self.report_fingerprint
        return value

    def seal(self) -> "AdapterConformanceReport":
        self.report_fingerprint = _fingerprint(self.to_dict(include_fingerprint=False))
        return self


@runtime_checkable
class AdapterConformanceDriver(Protocol):
    def capability_declaration(self) -> AdapterCapabilityDeclaration: ...

    def run_scenario(
        self,
        scenario_id: str,
        context: "AdapterConformanceContext",
    ) -> AdapterScenarioOutcome: ...


class AuditedStore:
    """Store proxy that records mutation provenance.

    This is a conformance hook, not a security sandbox. It detects ordinary
    adapter calls that bypass AASMEngine and records explicitly authorized
    external-executor operations. Python code with access to private internals
    can evade any in-process hook; the report states that limitation.
    """

    def __init__(self, store: Any | None = None) -> None:
        self._store = store if store is not None else MemoryStore()
        self.mutations: list[dict[str, Any]] = []
        self.violations: list[dict[str, Any]] = []

    @property
    def raw_store(self) -> Any:
        """Expose the wrapped store for diagnostics and deliberate negative tests."""

        return self._store

    @contextmanager
    def external_operation(self, role: str):
        token = _EXTERNAL_OPERATION.set(str(role))
        try:
            yield
        finally:
            _EXTERNAL_OPERATION.reset(token)

    def _record_mutation(self, method: str) -> None:
        modules = _module_chain()
        external_role = _EXTERNAL_OPERATION.get()
        canonical = any(
            any(module == prefix or module.startswith(prefix + "_v") for prefix in _CANONICAL_MUTATION_MODULES)
            for module in modules
        )
        allowed = canonical or external_role is not None
        caller = next(
            (
                module
                for module in modules
                if not module.startswith("aasm.persistence")
                and module != __name__
            ),
            modules[0] if modules else "unknown",
        )
        record = {
            "method": method,
            "caller": caller,
            "canonical_aasm_path": canonical,
            "external_role": external_role,
            "allowed": allowed,
        }
        self.mutations.append(record)
        if not allowed:
            self.violations.append(deepcopy(record))

    def __getattr__(self, name: str) -> Any:
        target = getattr(self._store, name)
        if not callable(target) or name not in _MUTATING_STORE_METHODS:
            return target

        def audited(*args: Any, **kwargs: Any) -> Any:
            self._record_mutation(name)
            return target(*args, **kwargs)

        return audited

    def close(self) -> None:
        closer = getattr(self._store, "close", None)
        if closer is not None:
            closer()


@dataclass
class AdapterConformanceContext:
    scenario_id: str
    store: AuditedStore
    engine_class: type[Any]
    namespace: str

    def claim_external_effect_attempt(self, machine_id: str, effect_id: str) -> Any:
        claimer = getattr(self.store, "claim_effect_attempt", None)
        if claimer is None:
            raise RuntimeError("selected store does not support durable effect attempts")
        with self.store.external_operation("EXTERNAL_EFFECT_EXECUTOR"):
            return claimer(machine_id, effect_id)


class AdapterConformanceKit:
    def __init__(
        self,
        *,
        engine_class: type[Any] | None = None,
        store_factory: Any = MemoryStore,
    ) -> None:
        if engine_class is None:
            from .. import AASMEngine as engine_class
        self.engine_class = engine_class
        self.store_factory = store_factory

    @staticmethod
    def _authority_checks(declaration: AdapterCapabilityDeclaration) -> tuple[dict[str, bool], list[ConformanceFinding]]:
        authority = declaration.authority
        checks = {
            "machine_truth_is_aasm_event_history": authority.get("machine_truth_authority") == "AASM_EVENT_HISTORY",
            "decision_authority_is_aasm": authority.get("decision_authority") == "AASM",
            "effect_authority_is_aasm": authority.get("effect_authority") == "AASM",
            "worker_lease_authority_is_aasm": authority.get("worker_lease_authority") == "AASM",
            "recovery_authority_is_aasm": authority.get("recovery_authority") == "AASM",
            "no_declared_direct_storage_writes": authority.get("direct_storage_writes") is False,
            "no_declared_duplicate_authorities": not list(authority.get("duplicate_authorities") or []),
            "uses_public_aasm_api": authority.get("uses_public_aasm_api") is True,
        }
        findings: list[ConformanceFinding] = []
        if not all(checks.values()):
            findings.append(
                ConformanceFinding(
                    "DUPLICATE_OR_BYPASSED_AUTHORITY",
                    "ERROR",
                    "adapter authority declaration does not preserve the canonical AASM boundary",
                    detail={"authority": deepcopy(authority), "checks": checks},
                )
            )
        return checks, findings

    @staticmethod
    def _evidence_ids(engine: Any) -> set[str]:
        return {
            str(row.get("evidence_id"))
            for row in engine.snapshot.evidence.get("records", [])
            if row.get("evidence_id")
        }

    @staticmethod
    def _semantic_evidence_ids(engine: Any) -> set[str]:
        references: set[str] = set()
        for result in getattr(engine.snapshot, "semantic_results", []) or []:
            for row in result.get("evidence", []) or []:
                if isinstance(row, Mapping) and row.get("evidence_id"):
                    references.add(str(row["evidence_id"]))
        return references

    def _generic_checks(
        self,
        declaration: AdapterCapabilityDeclaration,
        outcome: AdapterScenarioOutcome,
        store: AuditedStore,
    ) -> tuple[dict[str, bool], list[ConformanceFinding], dict[str, Any], Any]:
        checks, findings = self._authority_checks(declaration)
        try:
            engine = self.engine_class.resume(outcome.machine_id, store, load_history=True)
        except TypeError:
            engine = self.engine_class.resume(outcome.machine_id, store)
        history = engine.check_durable_history(persist=False)
        replay_hash = engine.replay().canonical_hash()
        persisted_hash = store.load_snapshot(outcome.machine_id).canonical_hash()
        evidence_ids = self._evidence_ids(engine)
        semantic_references = self._semantic_evidence_ids(engine)
        report = outcome.adapter_report or {}
        checks.update(
            {
                "machine_exists": bool(outcome.machine_id),
                "no_direct_storage_write": not store.violations,
                "durable_history_valid": bool(history.get("valid")),
                "replay_exact": replay_hash == persisted_hash,
                "declared_evidence_exists": set(outcome.evidence_ids).issubset(evidence_ids),
                "semantic_evidence_resolves": semantic_references.issubset(evidence_ids),
                "adapter_report_machine_matches": (
                    not report or report.get("machine_id") == outcome.machine_id
                ),
                "adapter_report_replay_exact": (
                    not report
                    or report.get("replay_snapshot_hash")
                    == report.get("persisted_snapshot_hash")
                ),
                "adapter_report_rejects_direct_storage": (
                    not report or report.get("direct_storage_mutation") is False
                ),
            }
        )
        if store.violations:
            findings.append(
                ConformanceFinding(
                    "DIRECT_STORAGE_WRITE",
                    "ERROR",
                    "adapter or driver called a mutating Store operation outside the canonical AASM path",
                    scenario_id=outcome.scenario_id,
                    detail={"violations": deepcopy(store.violations)},
                )
            )
        if not history.get("valid"):
            event_id = None
            issues = history.get("issues") or []
            if issues:
                event_id = issues[0].get("event_id")
            findings.append(
                ConformanceFinding(
                    "DURABLE_HISTORY_INVALID",
                    "ERROR",
                    "adapter scenario produced a durable history that failed verification",
                    scenario_id=outcome.scenario_id,
                    event_id=event_id,
                    detail={"history": history},
                )
            )
        if replay_hash != persisted_hash:
            findings.append(
                ConformanceFinding(
                    "REPLAY_MISMATCH",
                    "ERROR",
                    "replayed snapshot does not match the persisted canonical snapshot",
                    scenario_id=outcome.scenario_id,
                    event_id=engine.events[-1].event_id if engine.events else None,
                    detail={
                        "replay_snapshot_hash": replay_hash,
                        "persisted_snapshot_hash": persisted_hash,
                    },
                )
            )
        summary = {
            "history_status": history.get("status"),
            "history_issues": history.get("issues") or [],
            "event_count": len(engine.events),
            "evidence_count": len(evidence_ids),
            "semantic_result_count": len(getattr(engine.snapshot, "semantic_results", []) or []),
            "replay_snapshot_hash": replay_hash,
            "persisted_snapshot_hash": persisted_hash,
        }
        return checks, findings, summary, engine

    @staticmethod
    def _scenario_checks(
        scenario_id: str,
        outcome: AdapterScenarioOutcome,
        engine: Any,
        store: AuditedStore,
    ) -> tuple[dict[str, bool], list[ConformanceFinding], dict[str, Any]]:
        observations = outcome.observations
        calculus = engine.calculus_report()
        checks: dict[str, bool] = {}
        findings: list[ConformanceFinding] = []
        summary: dict[str, Any] = deepcopy(observations)

        if scenario_id == "success":
            committed = [
                row
                for row in calculus["obligations"].values()
                if row.get("mandatory") and row.get("status") == "COMMITTED"
            ]
            evidence_ids = {
                str(row.get("evidence_id"))
                for row in engine.snapshot.evidence.get("records", [])
                if row.get("evidence_id")
            }
            semantic_results = getattr(engine.snapshot, "semantic_results", []) or []
            checks = {
                "original_output_preserved": observations.get("original_output_preserved") is True,
                "mandatory_obligation_committed": bool(committed),
                "committed_obligation_has_evidence": bool(committed)
                and all(set(row.get("evidence_ids") or []).issubset(evidence_ids) and row.get("evidence_ids") for row in committed),
                "semantic_pass_recorded": any(row.get("classification") == "PASS" for row in semantic_results),
                "semantic_result_has_provenance": any(row.get("producer") and row.get("evidence") for row in semantic_results),
            }
        elif scenario_id == "contradiction":
            conflict_id = observations.get("conflict_id")
            constraint_id = observations.get("constraint_id")
            certificate_id = observations.get("certificate_id")
            conflict = calculus["conflicts"].get(conflict_id, {})
            constraint = calculus["constraints"].get(constraint_id, {})
            certificate = engine.snapshot.assurance_state.get("certificates", {}).get(certificate_id, {})
            checks = {
                "conflict_resolved": conflict.get("status") == "RESOLVED",
                "learned_constraint_active": constraint.get("status") == "ACTIVE",
                "learned_constraint_hard": constraint.get("strength") == "HARD",
                "certificate_verified": certificate.get("status") == "VERIFIED",
                "causal_backjump_recorded": bool(observations.get("backjump_target")),
                "unrelated_work_preserved": observations.get("unrelated_work_preserved") is True,
                "failed_combination_blocked_on_reuse": observations.get("repeat_blocked") is True,
            }
        elif scenario_id == "requirement_change":
            checks = {
                "affected_region_identified": observations.get("affected_region_identified") is True,
                "unrelated_work_preserved": observations.get("unrelated_work_preserved") is True,
                "only_affected_region_paused": observations.get("only_affected_region_paused") is True,
                "impact_resolved": observations.get("impact_resolved") is True,
                "plan_resumed": observations.get("plan_resumed") is True,
            }
        elif scenario_id == "lease_loss":
            checks = {
                "stale_worker_detected": observations.get("stale_worker_detected") is True,
                "lost_lease_expired": observations.get("lost_lease_expired") is True,
                "task_reclaimed": observations.get("task_reclaimed") is True,
                "attempt_incremented": observations.get("attempt_incremented") is True,
                "recovery_lease_completed": observations.get("recovery_lease_completed") is True,
            }
        elif scenario_id == "unknown_effect":
            effects = engine.list_effects()
            checks = {
                "attempt_entered_running": observations.get("attempt_entered_running") is True,
                "resume_marked_unknown": observations.get("resume_marked_unknown") is True,
                "unsafe_retry_blocked": observations.get("unsafe_retry_blocked") is True,
                "explicit_reconciliation": observations.get("explicit_reconciliation") is True,
                "single_effect_identity": len(effects) == 1,
                "effect_succeeded_after_reconciliation": bool(effects) and effects[0].status == "SUCCEEDED",
            }
        elif scenario_id == "restart":
            pinned_id = observations.get("pinned_decision_id")
            speculative_id = observations.get("speculative_decision_id")
            constraint_id = observations.get("constraint_id")
            checks = {
                "pinned_decision_retained": calculus["decisions"].get(pinned_id, {}).get("status") == "ACTIVE",
                "speculative_decision_suspended": calculus["decisions"].get(speculative_id, {}).get("status") == "SUSPENDED",
                "hard_knowledge_retained": calculus["constraints"].get(constraint_id, {}).get("strength") == "HARD",
                "hard_knowledge_active": calculus["constraints"].get(constraint_id, {}).get("status") == "ACTIVE",
                "restart_recorded": observations.get("restart_recorded") is True,
            }
        elif scenario_id == "replay":
            checks = {
                "history_valid": observations.get("history_valid") is True,
                "replay_exact": observations.get("replay_exact") is True,
                "source_event_count_nonzero": int(observations.get("event_count", 0)) > 0,
            }
        elif scenario_id == "fork":
            fork_machine_id = observations.get("fork_machine_id")
            source_sequence = int(observations.get("source_sequence", -1))
            fork_snapshot = store.load_snapshot(fork_machine_id) if fork_machine_id else None
            lineage = deepcopy((fork_snapshot.metadata if fork_snapshot else {}).get("lineage") or {})
            fork_events = store.load_events(fork_machine_id) if fork_machine_id else []
            fork_engine = None
            if fork_machine_id:
                try:
                    fork_engine = type(engine).resume(fork_machine_id, store, load_history=True)
                except TypeError:
                    fork_engine = type(engine).resume(fork_machine_id, store)
            checks = {
                "fork_has_new_identity": bool(fork_machine_id) and fork_machine_id != outcome.machine_id,
                "lineage_names_source": lineage.get("source_machine_id") == outcome.machine_id,
                "lineage_names_sequence": int(lineage.get("source_sequence", -1)) == source_sequence,
                "fork_has_history": bool(fork_events),
                "fork_replay_exact": bool(fork_engine) and fork_engine.replay().canonical_hash() == fork_engine.snapshot.canonical_hash(),
            }
            summary["fork_lineage"] = lineage
        else:  # pragma: no cover - guarded by constants
            checks = {"known_scenario": False}

        failed = [name for name, value in checks.items() if not value]
        if failed:
            findings.append(
                ConformanceFinding(
                    "SCENARIO_CONTRACT_VIOLATION",
                    "ERROR",
                    f"scenario {scenario_id} failed checks: {failed}",
                    scenario_id=scenario_id,
                    event_id=engine.events[-1].event_id if engine.events else None,
                    detail={"checks": checks, "observations": deepcopy(observations)},
                )
            )
        return checks, findings, summary

    def _run_one(
        self,
        driver: AdapterConformanceDriver,
        declaration: AdapterCapabilityDeclaration,
        scenario_id: str,
    ) -> tuple[ConformanceScenarioResult, dict[str, Any]]:
        if not declaration.scenarios.get(scenario_id, False):
            finding = ConformanceFinding(
                "SCENARIO_UNSUPPORTED",
                "WARNING",
                f"adapter does not declare support for required scenario {scenario_id}",
                scenario_id=scenario_id,
            )
            return (
                ConformanceScenarioResult(
                    scenario_id,
                    ConformanceStatus.INCONCLUSIVE.value,
                    None,
                    checks={"scenario_supported": None},
                    findings=[finding],
                    summary={"supported": False},
                ),
                {
                    "scenario_id": scenario_id,
                    "mutation_count": 0,
                    "violation_count": 0,
                    "mutations": [],
                    "violations": [],
                },
            )

        store = AuditedStore(self.store_factory())
        context = AdapterConformanceContext(
            scenario_id=scenario_id,
            store=store,
            engine_class=self.engine_class,
            namespace=f"conformance-{declaration.adapter_id}",
        )
        try:
            outcome = driver.run_scenario(scenario_id, context)
            if not isinstance(outcome, AdapterScenarioOutcome):
                raise TypeError("driver must return AdapterScenarioOutcome")
            if outcome.scenario_id != scenario_id:
                raise ValueError(
                    f"driver returned scenario {outcome.scenario_id!r}; expected {scenario_id!r}"
                )
            generic, findings, generic_summary, engine = self._generic_checks(
                declaration, outcome, store
            )
            specific, specific_findings, specific_summary = self._scenario_checks(
                scenario_id, outcome, engine, store
            )
            checks: dict[str, bool | None] = {**generic, **specific}
            findings.extend(specific_findings)
            status = (
                ConformanceStatus.PASS.value
                if checks and all(value is True for value in checks.values())
                else ConformanceStatus.FAIL.value
            )
            summary = {
                **generic_summary,
                "observations": specific_summary,
                "adapter_report": deepcopy(outcome.adapter_report),
                "framework_state": deepcopy(outcome.framework_state),
            }
            result = ConformanceScenarioResult(
                scenario_id,
                status,
                outcome.machine_id,
                checks=checks,
                findings=findings,
                summary=summary,
                replay_snapshot_hash=generic_summary["replay_snapshot_hash"],
                persisted_snapshot_hash=generic_summary["persisted_snapshot_hash"],
            )
        except Exception as exc:
            result = ConformanceScenarioResult(
                scenario_id,
                ConformanceStatus.FAIL.value,
                None,
                checks={"driver_completed": False},
                findings=[
                    ConformanceFinding(
                        "DRIVER_EXCEPTION",
                        "ERROR",
                        f"{type(exc).__name__}: {exc}",
                        scenario_id=scenario_id,
                        detail={
                            "traceback": traceback.format_exc().splitlines()[-20:]
                        },
                    )
                ],
                summary={},
            )
        audit = {
            "scenario_id": scenario_id,
            "mutation_count": len(store.mutations),
            "violation_count": len(store.violations),
            "mutations": deepcopy(store.mutations),
            "violations": deepcopy(store.violations),
        }
        store.close()
        return result, audit

    def run(
        self,
        driver: AdapterConformanceDriver,
        *,
        scenarios: Sequence[str] | None = None,
    ) -> AdapterConformanceReport:
        if not isinstance(driver, AdapterConformanceDriver):
            raise TypeError("driver does not implement AdapterConformanceDriver")
        declaration = driver.capability_declaration()
        if not isinstance(declaration, AdapterCapabilityDeclaration):
            raise TypeError("capability_declaration must return AdapterCapabilityDeclaration")
        selected = list(scenarios or CONFORMANCE_SCENARIOS)
        unknown = sorted(set(selected) - set(CONFORMANCE_SCENARIOS))
        if unknown:
            raise ValueError(f"unknown conformance scenarios: {unknown}")
        selected = [scenario for scenario in CONFORMANCE_SCENARIOS if scenario in selected]
        results: list[ConformanceScenarioResult] = []
        audits: list[dict[str, Any]] = []
        for scenario_id in selected:
            result, audit = self._run_one(driver, declaration, scenario_id)
            results.append(result)
            audits.append(audit)

        statuses = [result.status for result in results]
        if any(status == ConformanceStatus.FAIL.value for status in statuses):
            overall = ConformanceStatus.FAIL.value
        elif any(status == ConformanceStatus.INCONCLUSIVE.value for status in statuses):
            overall = ConformanceStatus.INCONCLUSIVE.value
        else:
            overall = ConformanceStatus.PASS.value
        coverage = {
            "required_scenarios": list(CONFORMANCE_SCENARIOS),
            "selected_scenarios": selected,
            "declared_supported": [
                scenario
                for scenario in CONFORMANCE_SCENARIOS
                if declaration.scenarios.get(scenario, False)
            ],
            "passed": [result.scenario_id for result in results if result.status == "PASS"],
            "failed": [result.scenario_id for result in results if result.status == "FAIL"],
            "inconclusive": [
                result.scenario_id for result in results if result.status == "INCONCLUSIVE"
            ],
        }
        audit = {
            "hook_model": "IN_PROCESS_MUTATION_PROVENANCE",
            "security_boundary": "CONFORMANCE_HOOK_NOT_SANDBOX",
            "total_mutations": sum(row["mutation_count"] for row in audits),
            "total_violations": sum(row["violation_count"] for row in audits),
            "scenarios": audits,
        }
        return AdapterConformanceReport(
            adapter=declaration,
            status=overall,
            scenarios=results,
            coverage=coverage,
            audit=audit,
        ).seal()


def conformance_contract() -> dict[str, Any]:
    return {
        "contract_id": ADAPTER_CONFORMANCE_ID,
        "contract_version": ADAPTER_CONFORMANCE_VERSION,
        "schema_version": 1,
        "required_scenarios": list(CONFORMANCE_SCENARIOS),
        "statuses": [status.value for status in ConformanceStatus],
        "authority_requirements": {
            "machine_truth_authority": "AASM_EVENT_HISTORY",
            "decision_authority": "AASM",
            "effect_authority": "AASM",
            "worker_lease_authority": "AASM",
            "recovery_authority": "AASM",
            "direct_storage_writes": False,
            "duplicate_authorities": [],
            "uses_public_aasm_api": True,
        },
        "audit_boundary": (
            "The in-process Store proxy detects ordinary bypasses but is not a security sandbox. "
            "Adapters executing untrusted code require process or host isolation outside this kit."
        ),
    }


__all__ = [
    "ADAPTER_CONFORMANCE_ID",
    "ADAPTER_CONFORMANCE_VERSION",
    "CONFORMANCE_SCENARIOS",
    "ConformanceStatus",
    "AdapterCapabilityDeclaration",
    "AdapterScenarioOutcome",
    "ConformanceFinding",
    "ConformanceScenarioResult",
    "AdapterConformanceReport",
    "AdapterConformanceDriver",
    "AuditedStore",
    "AdapterConformanceContext",
    "AdapterConformanceKit",
    "conformance_contract",
]
