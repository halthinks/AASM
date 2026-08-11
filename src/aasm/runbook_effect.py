from __future__ import annotations

from .effects import EffectSpec, EffectUnknownOutcome, RetryPolicy
from .model import ProblemSpec
from .runbook_common import OperatorRunbookResult, finish_runbook, store_or_memory
from .runtime_v25 import AASMEngine


def run_unknown_effect(*, store=None) -> OperatorRunbookResult:
    """Simulate process loss, block unsafe retry, and reconcile explicitly."""

    store = store_or_memory(store)
    engine = AASMEngine(
        ProblemSpec("Reconcile an external effect whose outcome is unknown"),
        store=store,
    )
    effect = engine.propose_effect(
        EffectSpec(
            "runbook.external-write",
            payload={"record_id": "external-42"},
            idempotency_key="runbook-unknown-effect",
            retry_policy=RetryPolicy(
                max_attempts=2,
                retry_on_failure=False,
                retry_on_unknown=False,
            ),
        )
    )
    engine.authorize_effect(effect.spec.effect_id, authority="human:operator")
    claimer = getattr(store, "claim_effect_attempt", None)
    if claimer is None:
        raise RuntimeError("selected store does not support durable effect attempts")
    running = claimer(engine.snapshot.machine_id, effect.spec.effect_id)
    resumed = AASMEngine.resume(
        engine.snapshot.machine_id,
        store,
        recover_effects=True,
    )
    unknown = store.load_effect(engine.snapshot.machine_id, effect.spec.effect_id)
    blocked_retry = False
    try:
        resumed.execute_effect(
            effect.spec.effect_id,
            lambda _spec, _key: {"duplicate": True},
        )
    except EffectUnknownOutcome:
        blocked_retry = True
    reconciled = resumed.reconcile_effect(
        effect.spec.effect_id,
        succeeded=True,
        result={"record_id": "external-42", "observed": "present"},
        evidence=["operator:external-system-check"],
    )
    checks = {
        "attempt_entered_running": running.status == "RUNNING",
        "resume_marked_unknown": unknown.status == "UNKNOWN",
        "unsafe_retry_blocked": blocked_retry,
        "operator_reconciled": reconciled.status == "SUCCEEDED",
        "external_result_preserved": reconciled.result == {
            "record_id": "external-42",
            "observed": "present",
        },
    }
    return finish_runbook(
        "unknown-effect",
        machine_id=resumed.snapshot.machine_id,
        checks=checks,
        summary={
            "effect_id": effect.spec.effect_id,
            "idempotency_key": effect.spec.idempotency_key,
            "status_after_recovery": unknown.status,
            "final_status": reconciled.status,
            "reconciliation_evidence": reconciled.evidence,
            "operator_action": "Observe the external system, then reconcile; never guess and retry.",
        },
        evidence=[
            {
                "kind": "effect-reconciliation",
                "effect_id": effect.spec.effect_id,
                "status": reconciled.status,
            }
        ],
    )
