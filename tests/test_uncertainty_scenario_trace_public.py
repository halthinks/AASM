from __future__ import annotations

import aasm
import aasm.public_active_semantic_projection as parent
import aasm.public_active_uncertainty_scenario_trace as active


def test_ust_public_adoption_is_additive_over_qualified_03218_parent():
    assert parent.validate_public_api_contract()["valid"] is True
    assert active.validate_public_api_contract()["valid"] is True
    assert aasm.validate_public_api_contract()["valid"] is True
    assert parent.PUBLIC_API_CONTRACT["contract_version"] == "0.32.18"
    assert active.PUBLIC_API_CONTRACT["contract_version"] == "0.32.19"
    assert active.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.18"
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.20"
    assert aasm.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.19"
    assert active.AASMEngine is parent.AASMEngine
    assert active.AASMEngine is aasm.AASMEngine


def test_ust_remains_qualified_03219_parent_beneath_active_03220():
    assert active.PUBLIC_API_CONTRACT["contract_version"] == "0.32.19"
    assert active.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.18"
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.20"
    assert aasm.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.19"
    assert aasm.public_api_contract()["uncertainty"] == active.public_api_contract()["uncertainty"]
    assert aasm.public_api_contract()["scenario"] == active.public_api_contract()["scenario"]
    assert aasm.public_api_contract()["trace_property"] == active.public_api_contract()["trace_property"]
    assert aasm.AASMEngine is active.AASMEngine


def test_ust_public_adoption_preserves_complete_parent_import_and_engine_surfaces():
    assert set(parent.SUPPORTED_PUBLIC_IMPORTS).issubset(active.SUPPORTED_PUBLIC_IMPORTS)
    assert set(active.SUPPORTED_PUBLIC_IMPORTS).issubset(aasm.SUPPORTED_PUBLIC_IMPORTS)
    assert active.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    assert aasm.SUPPORTED_ENGINE_METHODS == active.SUPPORTED_ENGINE_METHODS
    assert active.SUPPORTED_CLI_COMMANDS == parent.SUPPORTED_CLI_COMMANDS
    for name in active.SUPPORTED_PUBLIC_IMPORTS:
        assert hasattr(aasm, name), name
    assert "uncertainty-scenario-trace" in aasm.SUPPORTED_INSPECTION_SURFACES


def test_ust_public_contract_claim_ceiling_and_parallel_planes_remain_strict():
    contract = aasm.public_api_contract()
    for key in ("uncertainty", "scenario", "trace_property"):
        value = contract[key]
        assert value["runtime_admission"] == "PRE_ADMISSION_ONLY"
        assert value["engine_state_integration"] == "NONE_SEMANTIC_IR_ONLY"
        assert all(entry == "NONE" for entry in value["public_claim_ceiling"].values())
    assert contract["uncertainty"]["parallel_uncertainty_registry"] == "NONE"
    assert contract["uncertainty"]["current_uncertainty_pointer"] == "NONE"
    assert contract["scenario"]["parallel_scenario_registry"] == "NONE"
    assert contract["scenario"]["hidden_current_scenario"] == "NONE"
    assert contract["scenario"]["scenario_activation"] == "NONE_FOUNDATION_ONLY"
    assert contract["trace_property"]["parallel_trace_store"] == "NONE"
    assert contract["trace_property"]["parallel_property_registry"] == "NONE"
    assert contract["trace_property"]["static_constraint_lowering"] == "NONE"
    assert contract["trace_property"]["invariant_classification"] == "DYNAMIC_KERNEL"


def test_ust_public_types_remain_root_accessible_without_runtime_methods():
    for name in (
        "UncertaintySpec", "ScenarioBinding", "Scenario", "TraceEventPattern", "TraceProperty",
        "TraceEvaluationContext", "TracePropertyAssessment", "evaluate_trace_property",
        "uncertainty_contract", "scenario_contract", "trace_property_contract",
    ):
        assert hasattr(aasm, name), name
        assert name in aasm.SUPPORTED_PUBLIC_IMPORTS
    assert not any(name.startswith(("uncertainty_", "scenario_", "trace_property_")) for name in aasm.SUPPORTED_ENGINE_METHODS)
