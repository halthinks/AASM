from __future__ import annotations

import json
from pathlib import Path

from aasm.physical_effect_binding import (
    PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID,
    physical_effect_authority_binding_contract,
)
from aasm.physical_effect_integration_runtime import (
    PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID,
    physical_effect_integration_runtime_contract,
)


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def require_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    require(not missing, f"{path}: missing PR-3H contract tokens {missing}")


def forbid_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    present = [token for token in tokens if token in text]
    require(not present, f"{path}: forbidden PR-3H parallel-path tokens {present}")


def main() -> None:
    semantic = physical_effect_authority_binding_contract()
    runtime = physical_effect_integration_runtime_contract()
    require(semantic["contract_id"] == PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID, "physical effect binding contract drift")
    require(semantic["operation_source"] == "DERIVED_FROM_DURABLE_EFFECT_SPEC_NOT_CALLER_ASSERTION", "caller may assert physical operation")
    require(semantic["numeric_parameter_source"] == "DERIVED_FROM_DURABLE_EFFECT_COMMAND_PAYLOAD_NOT_CALLER_ASSERTION", "caller may assert physical numeric parameters")
    require(semantic["authorization_recheck"] == "MANDATORY_AT_EXISTING_AUTHORIZE_EFFECT_BOUNDARY", "authorization recheck missing")
    require(semantic["execution_recheck"] == "MANDATORY_AT_EXISTING_EXECUTE_EFFECT_BOUNDARY", "execution recheck missing")
    require(semantic["prior_use_validation_is_authorization"] is False, "old capability-use validation became authorization")
    require(runtime["contract_id"] == PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID, "PR-3H runtime contract drift")
    require(runtime["effect_authority"] == "EXISTING_V53_EFFECT_AUTHORIZE_AND_EFFECT_EXECUTE_REMAIN_REQUIRED", "PR-3H replaced scoped effect authority")
    require(runtime["task_lease"] == "EXISTING_V54_TASKLEASE_UNCHANGED", "PR-3H replaced TaskLease")
    require(runtime["resource_governance"] == "EXISTING_V54_RESOURCE_RESERVATIONS_UNCHANGED", "PR-3H replaced resource governance")
    require(runtime["ownership"] == "EXISTING_V54_EFFECT_OWNERSHIP_UNCHANGED", "PR-3H replaced EffectOwnership")
    require(runtime["unknown_and_reconciliation"] == "EXISTING_V54_UNKNOWN_AND_RECONCILIATION_UNCHANGED", "PR-3H replaced UNKNOWN/reconciliation")
    require(runtime["parallel_authority_evaluator"] == "NONE", "parallel authority evaluator introduced")
    require(runtime["parallel_effect_store"] == "NONE", "parallel effect store introduced")
    require(runtime["parallel_effect_lifecycle"] == "NONE", "parallel effect lifecycle introduced")
    require(runtime["parallel_dispatcher"] == "NONE", "parallel dispatcher introduced")

    schema = json.loads((ROOT / "schemas" / "physical-effect-authority-binding.schema.json").read_text(encoding="utf-8"))
    require(schema["properties"]["contract_id"]["const"] == PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID, "physical effect schema drift")

    require_tokens(
        ROOT / "src/aasm/physical_effect_integration_runtime.py",
        (
            'PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID = "aasm.effect.physical-authority-integration.runtime.v1"',
            'PHYSICAL_EFFECT_INTEGRATION_CAPABILITIES = {"bind": "physical.effect.bind"}',
            'record.spec.effect_type == "machine.transition"',
            'metadata.get("physical_authority_required") is True',
            'self.effect_capability_report(',
            'self.authority_lease_report(',
            'self.authority_domain_report(',
            'if set(numeric_parameters) != set(capability.numeric_bounds):',
            'if not capability.bounds_allow(numeric_parameters):',
            'boundary="AUTHORIZE"',
            '"reusable_authorization_token": False',
        ),
    )
    require_tokens(
        ROOT / "src/aasm/physical_effect_integration_boundary.py",
        (
            "owner_worker_id: str | None = None",
            "task_lease_id: str | None = None",
            "dispatch_metadata: Mapping[str, Any] | None = None",
            'boundary="EXECUTE"',
            "super(PhysicalEffectIntegrationRuntimeMixin, self).execute_effect(",
            "owner_worker_id=owner_worker_id",
            "task_lease_id=task_lease_id",
            "dispatch_metadata=dispatch_metadata",
        ),
    )
    forbid_tokens(
        ROOT / "src/aasm/physical_effect_integration_runtime.py",
        (
            "EffectOwnership(",
            "EffectDispatchRequest(",
            "EffectReconciliation(",
            "claim_effect",
            "find_effect_by_idempotency",
            "executor(",
        ),
    )
    require_tokens(
        ROOT / "tests/test_physical_effect_integration.py",
        (
            "test_machine_transition_effect_cannot_authorize_without_physical_binding",
            "test_capability_revoked_before_authorization_blocks_existing_authorize_effect",
            "test_capability_revoked_after_authorization_blocks_before_dispatch_request",
            "test_preemption_after_authorization_blocks_before_dispatch_and_next_epoch_does_not_resurrect_old_binding",
            "test_valid_bound_effect_uses_existing_tasklease_ownership_dispatch_and_terminal_reconciliation",
            "test_ordinary_unbound_effect_preserves_existing_behavior",
        ),
    )

    print("PR-3H physical-effect integration preserves the existing Effect lifecycle and rechecks bounded physical authority at point of use: PASS")


if __name__ == "__main__":
    main()
