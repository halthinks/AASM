from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import subprocess
import textwrap

ROOT = Path.cwd()


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"required S4.10 patch anchor not found in {path}: {old!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_once(path: str, marker: str, content: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if marker in text:
        return
    target.write_text(text.rstrip() + "\n\n" + textwrap.dedent(content).strip() + "\n", encoding="utf-8")


write(
    "fixtures/textpcb/s4-safety-governance-fixtures.json",
    r'''
    {
      "contract_id": "aasm.textpcb.s4-safety-fixtures.v1",
      "contract_version": "0.1.0",
      "fixture_suite": "TextPCB S4 Safety Governance",
      "required_aggregate_context": "aasm/safety-governance",
      "runtime_admission": "QUALIFICATION_ONLY_NO_RUNTIME_SURFACE",
      "cases": [
        {
          "fixture_id": "dimensional-mismatch",
          "requirement": "dimensionally inconsistent engineering quantities fail closed before solving or verification",
          "contracts": ["aasm.quantity.v1"],
          "expected": "FAIL_CLOSED_DIMENSION_MISMATCH",
          "forbidden_claims": ["implicit unit coercion", "solver may repair dimensions"]
        },
        {
          "fixture_id": "trace-width-clearance-manufacturing",
          "requirement": "trace width, clearance, and manufacturing limits remain exact typed quantities and rules",
          "contracts": ["aasm.quantity.v1", "aasm.rule.v1"],
          "expected": "EXACT_TYPED_MANUFACTURING_SEMANTICS",
          "forbidden_claims": ["binary float identity", "hidden unit registry"]
        },
        {
          "fixture_id": "drc-erc-hard-vs-preference",
          "requirement": "DRC and ERC hard floors dominate routing and production preferences",
          "contracts": ["aasm.rule.v1"],
          "expected": "HARD_FLOOR_DOMINATES_PREFERENCE",
          "forbidden_claims": ["objective priority overrides hard floor"]
        },
        {
          "fixture_id": "controlled-waiver-provenance",
          "requirement": "a controlled waiver records principal, rule, scope, duration, risk, authority evidence, and resulting obligations without performing a waiver",
          "contracts": ["aasm.manual.override.v1", "aasm.epistemic.debt.v1"],
          "expected": "REVIEW_ONLY_APPEND_ONLY_OVERRIDE_RECORD",
          "forbidden_claims": ["waiver performed", "history deleted", "authority hitchhiked"]
        },
        {
          "fixture_id": "thermal-power-signal-scenarios",
          "requirement": "thermal, power, and signal analyses are explicit scenarios rather than a hidden current scenario",
          "contracts": ["aasm.scenario.v1"],
          "expected": "EXPLICIT_DISTINCT_SCENARIOS",
          "forbidden_claims": ["scenario activation", "scenario equals ProblemRevision"]
        },
        {
          "fixture_id": "tolerance-quantization",
          "requirement": "tolerance and quantization are explicit and conservative at safety boundaries",
          "contracts": ["aasm.quantity.v1", "aasm.safety.envelope.v1", "aasm.hybrid.state.v1"],
          "expected": "BOUNDARY_OVERLAP_OR_UNSUPPORTED_IS_INDETERMINATE",
          "forbidden_claims": ["rounding proves safety", "nominal value alone is decisive"]
        },
        {
          "fixture_id": "production-alternative-equivalence-diversity",
          "requirement": "production alternatives may be projection-equivalent while retaining distinct exact identities",
          "contracts": ["aasm.quantity.v1", "aasm.semantic.projection.v1"],
          "expected": "PROJECTION_EQUIVALENCE_WITH_IDENTITY_DIVERSITY",
          "forbidden_claims": ["same enough becomes exact identity"]
        },
        {
          "fixture_id": "degraded-dependency-loss",
          "requirement": "dependency loss can only preserve or reduce the existing EffectCapability operation set",
          "contracts": ["aasm.degraded.operation.v1"],
          "expected": "NO_AUTHORITY_AMPLIFICATION",
          "forbidden_claims": ["degraded mode creates authority"]
        },
        {
          "fixture_id": "degraded-unknown",
          "requirement": "UNKNOWN degraded dependency state fails closed to no new effects",
          "contracts": ["aasm.degraded.operation.v1"],
          "expected": "SAFE_HOLD_NO_NEW_EFFECTS",
          "forbidden_claims": ["unknown treated as available", "safe hold proves physical safety"]
        },
        {
          "fixture_id": "hard-hazard-dominance",
          "requirement": "present and unknown hard hazards dominate optimization and proposal admissibility",
          "contracts": ["aasm.risk.envelope.v1", "aasm.rule.v1"],
          "expected": "BLOCKED_HARD_OR_INDETERMINATE_HAZARD",
          "forbidden_claims": ["objective improvement waives hazard"]
        },
        {
          "fixture_id": "irreversibility-assurance",
          "requirement": "irreversible and unknown operations require monotonic maximum assurance",
          "contracts": ["aasm.effect.irreversibility.v1", "aasm.risk.assessment.v1"],
          "expected": "ADDITIONAL_ASSURANCE_REQUIRED",
          "forbidden_claims": ["recovery claimed for irreversible effect"]
        },
        {
          "fixture_id": "scarcity-cannot-relax-floor",
          "requirement": "solver, provider, time, and resource scarcity cannot relax hard hazard or evidence floors",
          "contracts": ["aasm.risk.assessment.v1", "aasm.rule.v1"],
          "expected": "HARD_FLOOR_AND_ASSURANCE_PRESERVED",
          "forbidden_claims": ["resource exhaustion weakens legality", "provider absence lowers evidence floor"]
        }
      ],
      "suite_fingerprint": ""
    }
    ''',
)

write(
    "schemas/textpcb-s4-safety-fixture.schema.json",
    r'''
    {
      "$schema": "https://json-schema.org/draft/2020-12/schema",
      "$id": "https://aasm.dev/schemas/textpcb-s4-safety-fixture.schema.json",
      "title": "AASM TextPCB S4 Safety Governance Fixture Suite",
      "type": "object",
      "additionalProperties": false,
      "required": [
        "contract_id", "contract_version", "fixture_suite",
        "required_aggregate_context", "runtime_admission", "cases",
        "suite_fingerprint"
      ],
      "properties": {
        "contract_id": {"const": "aasm.textpcb.s4-safety-fixtures.v1"},
        "contract_version": {"const": "0.1.0"},
        "fixture_suite": {"const": "TextPCB S4 Safety Governance"},
        "required_aggregate_context": {"const": "aasm/safety-governance"},
        "runtime_admission": {"const": "QUALIFICATION_ONLY_NO_RUNTIME_SURFACE"},
        "cases": {
          "type": "array",
          "minItems": 12,
          "maxItems": 12,
          "items": {"$ref": "#/$defs/case"}
        },
        "suite_fingerprint": {"type": "string", "pattern": "^[0-9a-f]{64}$"}
      },
      "$defs": {
        "uniqueStrings": {
          "type": "array",
          "minItems": 1,
          "items": {"type": "string", "minLength": 1},
          "uniqueItems": true
        },
        "case": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "fixture_id", "requirement", "contracts", "expected",
            "forbidden_claims"
          ],
          "properties": {
            "fixture_id": {"type": "string", "pattern": "^[a-z][a-z0-9-]+$"},
            "requirement": {"type": "string", "minLength": 1},
            "contracts": {"$ref": "#/$defs/uniqueStrings"},
            "expected": {"type": "string", "minLength": 1},
            "forbidden_claims": {"$ref": "#/$defs/uniqueStrings"}
          }
        }
      }
    }
    ''',
)

write(
    "docs/implementation/TEXTPCB_S4_SAFETY_GOVERNANCE_FIXTURES.md",
    r'''
    # TextPCB S4 Permanent Safety-Governance Fixture Corpus

    **Status:** permanent aggregate qualification corpus  
    **Fixture contract:** `aasm.textpcb.s4-safety-fixtures.v1`  
    **Required context:** `aasm/safety-governance`  
    **Runtime admission:** none; qualification only

    ## Purpose

    The S4 foundations are intentionally narrow and separately gated. S4.10 proves that their boundaries compose without allowing information, solver results, resource pressure, degraded state, human intervention, or representation changes to acquire authority or weaken hard semantics.

    The fixture manifest under `fixtures/textpcb/` is closed-schema, fingerprinted, and permanent. It names twelve required failure and composition cases covering Quantity, Rule, Projection, Scenario, Degraded Operation, Risk/Irreversibility, Obligation Phases, Safety Envelope/Hybrid State, Epistemic Debt, and Manual Override.

    ## Required cases

    1. Dimensional mismatch fails before solving or verification.
    2. Trace width, clearance, and manufacturing limits remain typed and exact.
    3. DRC/ERC hard floors dominate preferences.
    4. Controlled waiver provenance remains review-only and append-only.
    5. Thermal, power, and signal contexts remain explicit distinct scenarios.
    6. Tolerance and quantization are conservative at safety boundaries.
    7. Production alternatives may be projection-equivalent while exact identities remain diverse.
    8. Degraded dependency loss never amplifies capability or authority.
    9. UNKNOWN degraded state fails closed to no new effects.
    10. Present and unknown hard hazards dominate optimization.
    11. Irreversible or unknown operations escalate assurance monotonically.
    12. Provider, solver, time, and resource scarcity cannot relax hard hazard or evidence floors.

    ## Aggregate gate

    `aasm/safety-governance` independently runs:

    - the fixture manifest/schema/source firewall;
    - the integrated TextPCB fixture tests;
    - every dedicated S4 foundation and public-adoption test corpus from Quantity through S4.9;
    - cumulative release/public-boundary checks.

    The gate creates no new runtime contract and exposes no TextPCB-specific engine methods. TextPCB is the permanent stress corpus; the semantics remain domain-neutral AASM contracts.
    ''',
)

write(
    "tests/test_textpcb_s4_safety_governance.py",
    r'''
    from __future__ import annotations

    from copy import deepcopy
    import hashlib
    import json
    from pathlib import Path

    import pytest
    from jsonschema import Draft202012Validator, ValidationError, validate

    import aasm
    from aasm.calculus import ObligationRecord, default_calculus_state, normalize_calculus_state
    from aasm.degraded_operation import degraded_operation_contract
    from aasm.epistemic_debt_manual_override import (
        OverrideValidityWindow,
        bind_manual_override,
        evaluate_manual_override,
        project_epistemic_debt,
    )
    from aasm.quantity import (
        DimensionVector,
        ExactNumber,
        IntervalValue,
        Quantity,
        QuantizationSpec,
        ToleranceSpec,
        UnitBinding,
        require_dimensionally_compatible,
    )
    from aasm.risk_irreversibility import (
        EffectIrreversibility,
        HazardObservation,
        HazardRef,
        IrreversibilityAssurancePolicy,
        RiskAssessment,
        RiskEnvelope,
        evaluate_risk,
        risk_irreversibility_contract,
    )
    from aasm.rule import (
        EngineeringRule,
        RuleApplicabilityPredicate,
        RuleClauseRef,
        RuleControlPolicy,
        RuleScopeSelector,
        RuleSourceAuthorityRef,
    )
    from aasm.safety_envelope_hybrid_state import (
        HybridState,
        SafetyEnvelope,
        SafetyModeEnvelope,
        assess_safety_envelope,
        bind_safety_constraint,
        observe_hybrid_quantity,
    )
    from aasm.semantic_projection import SemanticSubjectRef
    from aasm.semantic_result import semantic_fingerprint
    from aasm.uncertainty_scenario_trace import Scenario, ScenarioBinding


    ROOT = Path(__file__).resolve().parents[1]
    MANIFEST_PATH = ROOT / "fixtures/textpcb/s4-safety-governance-fixtures.json"
    REVISION_ID = "problem-revision-textpcb-s4"
    REVISION_FINGERPRINT = "4" * 64


    def number(value: str) -> ExactNumber:
        return ExactNumber.decimal(value)


    def length_dimension() -> DimensionVector:
        return DimensionVector({"length": 1})


    def subject() -> SemanticSubjectRef:
        return SemanticSubjectRef(
            "aasm.textpcb.design.v1",
            "textpcb-board-1",
            "d" * 64,
            REVISION_ID,
            REVISION_FINGERPRINT,
        )


    def rule(
        rule_id: str,
        *,
        strength: str,
        clause_kind: str = "CONSTRAINT",
        waivable: bool = False,
    ) -> EngineeringRule:
        clause_id = f"{rule_id}-{strength}-{clause_kind}"
        control = (
            RuleControlPolicy("EXPLICIT_AUTHORIZED", "FORBIDDEN", "rule.waive")
            if waivable
            else RuleControlPolicy()
        )
        return EngineeringRule(
            rule_id,
            RuleClauseRef(
                "aasm.semantic.constraint.v1",
                clause_id,
                hashlib.sha256(clause_id.encode()).hexdigest(),
                clause_kind,
            ),
            strength,
            RuleScopeSelector("workspace-textpcb", "board", "EXACT", ("textpcb-board-1",)),
            RuleApplicabilityPredicate("ALWAYS"),
            "textpcb-safety",
            priority=100,
            specificity=10,
            control_policy=control,
            severity="CRITICAL" if strength == "HARD_FLOOR" else "MEDIUM",
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
        )


    def state_with(record: ObligationRecord) -> dict:
        state = default_calculus_state()
        state["obligations"][record.obligation_id] = record.to_dict()
        return normalize_calculus_state(state)


    def manifest() -> dict:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


    def test_fixture_manifest_is_closed_fingerprinted_and_complete():
        document = manifest()
        schema = json.loads(
            (ROOT / "schemas/textpcb-s4-safety-fixture.schema.json").read_text(
                encoding="utf-8"
            )
        )
        Draft202012Validator.check_schema(schema)
        validate(document, schema)
        payload = deepcopy(document)
        supplied = payload.pop("suite_fingerprint")
        assert supplied == semantic_fingerprint(payload)
        changed = deepcopy(document)
        changed["unknown_field"] = True
        with pytest.raises(ValidationError):
            validate(changed, schema)
        required = {
            "dimensional-mismatch",
            "trace-width-clearance-manufacturing",
            "drc-erc-hard-vs-preference",
            "controlled-waiver-provenance",
            "thermal-power-signal-scenarios",
            "tolerance-quantization",
            "production-alternative-equivalence-diversity",
            "degraded-dependency-loss",
            "degraded-unknown",
            "hard-hazard-dominance",
            "irreversibility-assurance",
            "scarcity-cannot-relax-floor",
        }
        assert {case["fixture_id"] for case in document["cases"]} == required


    def test_dimensional_mismatch_fixture_fails_before_solving():
        width = Quantity(
            "DECIMAL",
            number("0.2"),
            length_dimension(),
            UnitBinding("mm", "mm"),
        )
        current = Quantity(
            "DECIMAL",
            number("1.0"),
            DimensionVector({"electric_current": 1}),
            UnitBinding("A", "A"),
        )
        with pytest.raises(ValueError, match="dimensionally inconsistent"):
            require_dimensionally_compatible(width, current)


    def test_trace_width_clearance_and_drc_erc_hard_floor_dominate_preferences():
        width = Quantity(
            "DECIMAL",
            number("0.15"),
            length_dimension(),
            UnitBinding("mm", "mm"),
        )
        clearance = Quantity(
            "DECIMAL",
            number("0.1"),
            length_dimension(),
            UnitBinding("mm", "mm"),
        )
        require_dimensionally_compatible(width, clearance)
        drc = rule("minimum-clearance", strength="HARD_FLOOR")
        routing = rule("short-route-preference", strength="PREFERENCE")
        assert drc.precedence_key > routing.precedence_key
        assert drc.control_policy.waiver_mode == "FORBIDDEN"
        assert routing.strength == "PREFERENCE"


    def test_controlled_waiver_provenance_is_review_only_and_creates_debt():
        policy = rule("approved-fab-exception", strength="POLICY", waivable=True)
        risk = RiskAssessment(
            envelope_id="risk-envelope-textpcb",
            envelope_fingerprint="a" * 64,
            irreversibility_profile_id="profile-textpcb",
            irreversibility_fingerprint="b" * 64,
            status="REQUIRES_EXPLICIT_ACCEPTANCE",
            required_assurance_level="ELEVATED",
            available_assurance_level="STRONG",
            acceptance_hazard_ids=("reduced-manufacturing-margin",),
        )
        obligation = ObligationRecord(
            "O-post-fab-inspection",
            "Perform post-fabrication inspection and attach evidence",
            status="AVAILABLE",
            required_evidence_types=["inspection-report"],
            scope={"scope_id": "board"},
        )
        state = state_with(obligation)
        authority = RuleSourceAuthorityRef(
            "principal-textpcb",
            "authority-grant-textpcb",
            "c" * 64,
            "rule.waive",
        )
        override = bind_manual_override(
            policy,
            risk,
            (state["obligations"][obligation.obligation_id],),
            principal_id="principal-textpcb",
            authority=authority,
            reason="Use the qualified alternate fabricator for this exact revision",
            validity=OverrideValidityWindow("textpcb-sequence", 100, 120),
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
            authority_evidence_ids=("evidence-authority-textpcb",),
            evidence_ids=("evidence-fab-qualification",),
        )
        assessment = evaluate_manual_override(
            override,
            (policy,),
            (risk,),
            state,
            clock_id="textpcb-sequence",
            sequence=110,
        )
        assert assessment.status == "ADMISSIBLE_FOR_AUTHORIZATION_REVIEW"
        assert assessment.waiver_performed is False
        assert assessment.authority_granted is False
        assert assessment.history_deleted is False
        debt = project_epistemic_debt(
            state,
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
        )
        assert tuple(value.obligation_id for value in debt.items) == (
            "O-post-fab-inspection",
        )


    def test_thermal_power_and_signal_scenarios_are_explicit_and_distinct():
        scenarios = tuple(
            Scenario(
                f"TextPCB {domain.title()} Analysis",
                REVISION_ID,
                REVISION_FINGERPRINT,
                (ScenarioBinding("analysis_domain", "LITERAL", literal_value=domain),),
                tags=(domain.lower(), "textpcb"),
            )
            for domain in ("THERMAL", "POWER", "SIGNAL")
        )
        assert len({value.scenario_id for value in scenarios}) == 3
        assert len({value.fingerprint for value in scenarios}) == 3
        assert {value.bindings[0].literal_value for value in scenarios} == {
            "THERMAL",
            "POWER",
            "SIGNAL",
        }


    def test_tolerance_and_quantization_are_conservative_at_safety_boundary():
        safety_rule = rule(
            "maximum-board-temperature",
            strength="HARD_FLOOR",
            clause_kind="SAFETY_INVARIANT",
        )
        allowed = Quantity(
            "INTERVAL",
            IntervalValue(number("0"), number("100")),
            DimensionVector({"temperature": 1}),
            UnitBinding("degC", "degC"),
        )
        observed = Quantity(
            "DECIMAL",
            number("99.5"),
            DimensionVector({"temperature": 1}),
            UnitBinding("degC", "degC"),
            tolerance=ToleranceSpec("ABSOLUTE", number("1")),
        )
        envelope = SafetyEnvelope(
            "TextPCB thermal envelope",
            subject(),
            REVISION_ID,
            REVISION_FINGERPRINT,
            (
                SafetyModeEnvelope(
                    "THERMAL_TEST",
                    (
                        bind_safety_constraint(
                            "board-temperature",
                            "temperature",
                            safety_rule,
                            allowed,
                            evidence_ids=("evidence-thermal-rule",),
                        ),
                    ),
                ),
            ),
        )
        state = HybridState(
            "TextPCB observed thermal state",
            subject(),
            "THERMAL_TEST",
            REVISION_ID,
            REVISION_FINGERPRINT,
            (
                observe_hybrid_quantity(
                    "temperature",
                    observed,
                    evidence_ids=("evidence-temperature",),
                ),
            ),
            mode_evidence_ids=("evidence-mode",),
        )
        result = assess_safety_envelope(
            envelope,
            state,
            (safety_rule,),
            (allowed, observed),
        )
        assert result.status == "INDETERMINATE"
        quantized = Quantity(
            "DECIMAL",
            number("95"),
            DimensionVector({"temperature": 1}),
            UnitBinding("degC", "degC"),
            quantization=QuantizationSpec(number("1"), rounding_rule="HALF_UP"),
        )
        quantized_state = HybridState(
            "TextPCB quantized thermal state",
            subject(),
            "THERMAL_TEST",
            REVISION_ID,
            REVISION_FINGERPRINT,
            (
                observe_hybrid_quantity(
                    "temperature",
                    quantized,
                    evidence_ids=("evidence-quantized-temperature",),
                ),
            ),
            mode_evidence_ids=("evidence-mode",),
        )
        result = assess_safety_envelope(
            envelope,
            quantized_state,
            (safety_rule,),
            (allowed, quantized),
        )
        assert result.status == "INDETERMINATE"
        assert result.constraint_assessments[0].relation == "UNSUPPORTED"


    def test_production_alternatives_are_projection_equivalent_but_identity_diverse():
        millimetres = Quantity(
            "DECIMAL",
            number("10"),
            length_dimension(),
            UnitBinding(
                "mm",
                "m",
                ExactNumber.rational(1, 1000),
                ExactNumber.integer(0),
            ),
            metadata={"fabricator": "A"},
        )
        metres = Quantity(
            "DECIMAL",
            number("0.01"),
            length_dimension(),
            UnitBinding("m", "m"),
            metadata={"fabricator": "B"},
        )
        assert millimetres.fingerprint != metres.fingerprint
        assert (
            millimetres.canonical_projection_fingerprint
            == metres.canonical_projection_fingerprint
        )
        assert millimetres.quantity_id != metres.quantity_id


    def test_degraded_dependency_loss_and_unknown_never_amplify_authority():
        contract = degraded_operation_contract()
        serialized = json.dumps(contract, sort_keys=True)
        assert "FAIL_CLOSED_TO_SAFE_HOLD_WITH_NO_NEW_EFFECTS" in serialized
        assert (
            "EMERGENCY_RESPONSE_INTENT_ONLY_NEVER_CREATES_OR_EXPANDS_AUTHORITY"
            in serialized
        )
        assert contract["assessment_is_authorization"] is False
        assert contract["assessment_activates_mode"] is False
        assert contract["assessment_proves_safety"] is False
        assert contract["parallel_mode_store"] == "NONE"


    def risk_fixture() -> tuple[
        EngineeringRule,
        RiskEnvelope,
        EffectIrreversibility,
        IrreversibilityAssurancePolicy,
    ]:
        hard = rule(
            "no-overtemperature-fabrication",
            strength="HARD_FLOOR",
            clause_kind="SAFETY_INVARIANT",
        )
        envelope = RiskEnvelope(
            "TextPCB fabrication risk envelope",
            subject(),
            REVISION_ID,
            REVISION_FINGERPRINT,
            (
                HazardRef(
                    "overtemperature",
                    hard.rule_revision_id,
                    hard.fingerprint,
                    "CATASTROPHIC",
                    "PROHIBITED",
                    evidence_ids=("evidence-hazard-rule",),
                ),
            ),
        )
        policy = IrreversibilityAssurancePolicy(
            {
                "REVERSIBLE": "BASELINE",
                "CONDITIONALLY_REVERSIBLE": "ELEVATED",
                "COSTLY_TO_REVERSE": "STRONG",
                "IRREVERSIBLE": "MAXIMUM",
                "UNKNOWN": "MAXIMUM",
            }
        )
        return hard, envelope, EffectIrreversibility(
            "fabricate",
            subject(),
            "REVERSIBLE",
            recovery_operations=("discard-unfabricated-order",),
            evidence_ids=("evidence-irreversibility",),
        ), policy


    def test_present_and_unknown_hard_hazards_dominate_all_assurance():
        hard, envelope, reversible, policy = risk_fixture()
        present = evaluate_risk(
            envelope,
            (hard,),
            (HazardObservation("overtemperature", "PRESENT", ("obs-present",)),),
            reversible,
            policy,
            available_assurance_level="MAXIMUM",
        )
        assert present.status == "BLOCKED_HARD_HAZARD"
        unknown = evaluate_risk(
            envelope,
            (hard,),
            (HazardObservation("overtemperature", "UNKNOWN", ("obs-unknown",)),),
            reversible,
            policy,
            available_assurance_level="MAXIMUM",
        )
        assert unknown.status == "BLOCKED_INDETERMINATE_HAZARD"
        assert present.effect_authority_granted is False
        assert present.resource_override_performed is False
        assert present.objective_override_performed is False


    def test_irreversibility_escalates_assurance_and_scarcity_never_relaxes_floor():
        hard, envelope, _, policy = risk_fixture()
        irreversible = EffectIrreversibility(
            "fabricate",
            subject(),
            "IRREVERSIBLE",
            recovery_operations=(),
            evidence_ids=("evidence-irreversible",),
        )
        result = evaluate_risk(
            envelope,
            (hard,),
            (HazardObservation("overtemperature", "ABSENT", ("obs-absent",)),),
            irreversible,
            policy,
            available_assurance_level="BASELINE",
        )
        assert result.status == "REQUIRES_ADDITIONAL_ASSURANCE"
        contract = risk_irreversibility_contract()
        assert (
            contract["resource_relation"]
            == "RESOURCE_SCARCITY_CANNOT_RELAX_HARD_HAZARD_OR_ASSURANCE_REQUIREMENT"
        )
        assert (
            contract["optimization_relation"]
            == "OBJECTIVE_IMPROVEMENT_CANNOT_OVERRIDE_PRESENT_OR_UNKNOWN_HARD_HAZARD"
        )


    def test_fixture_suite_creates_no_public_or_runtime_surface():
        assert not hasattr(aasm, "TextPCBSafetyFixture")
        assert not any(
            name.startswith(("textpcb_", "safety_governance_"))
            for name in aasm.SUPPORTED_ENGINE_METHODS
        )
        document = manifest()
        assert document["runtime_admission"] == "QUALIFICATION_ONLY_NO_RUNTIME_SURFACE"
    ''',
)

write(
    "scripts/check_safety_governance_contracts.py",
    r'''
    from __future__ import annotations

    import json
    from pathlib import Path


    ROOT = Path(__file__).resolve().parents[1]
    REQUIRED_FIXTURES = {
        "dimensional-mismatch",
        "trace-width-clearance-manufacturing",
        "drc-erc-hard-vs-preference",
        "controlled-waiver-provenance",
        "thermal-power-signal-scenarios",
        "tolerance-quantization",
        "production-alternative-equivalence-diversity",
        "degraded-dependency-loss",
        "degraded-unknown",
        "hard-hazard-dominance",
        "irreversibility-assurance",
        "scarcity-cannot-relax-floor",
    }
    REQUIRED_S4_TESTS = (
        "tests/test_quantity_foundation.py",
        "tests/test_quantity_public.py",
        "tests/test_rule_foundation.py",
        "tests/test_rule_public.py",
        "tests/test_semantic_projection_foundation.py",
        "tests/test_semantic_projection_textpcb.py",
        "tests/test_semantic_projection_adversarial.py",
        "tests/test_semantic_projection_public.py",
        "tests/test_uncertainty_scenario_trace_foundation.py",
        "tests/test_uncertainty_scenario_trace_public.py",
        "tests/test_degraded_operation_foundation.py",
        "tests/test_degraded_operation_public.py",
        "tests/test_risk_irreversibility_foundation.py",
        "tests/test_obligation_phase_foundation.py",
        "tests/test_safety_envelope_hybrid_state_foundation.py",
        "tests/test_epistemic_debt_manual_override_foundation.py",
        "tests/test_textpcb_s4_safety_governance.py",
    )


    def fail(message: str) -> None:
        raise SystemExit(message)


    def text(path: str) -> str:
        target = ROOT / path
        if not target.exists():
            fail(f"missing safety-governance contract file: {path}")
        return target.read_text(encoding="utf-8")


    def main() -> None:
        manifest = json.loads(text("fixtures/textpcb/s4-safety-governance-fixtures.json"))
        schema = json.loads(text("schemas/textpcb-s4-safety-fixture.schema.json"))
        if schema.get("additionalProperties") is not False:
            fail("TextPCB S4 fixture schema must be closed")
        if manifest.get("contract_id") != "aasm.textpcb.s4-safety-fixtures.v1":
            fail("TextPCB S4 fixture contract identity drift")
        if manifest.get("required_aggregate_context") != "aasm/safety-governance":
            fail("TextPCB S4 aggregate context drift")
        if manifest.get("runtime_admission") != "QUALIFICATION_ONLY_NO_RUNTIME_SURFACE":
            fail("TextPCB S4 fixture suite claims runtime admission")
        fixture_ids = {case.get("fixture_id") for case in manifest.get("cases", [])}
        if fixture_ids != REQUIRED_FIXTURES:
            fail(
                f"TextPCB S4 fixture coverage drift: missing={sorted(REQUIRED_FIXTURES - fixture_ids)}, extra={sorted(fixture_ids - REQUIRED_FIXTURES)}"
            )
        tests = text("tests/test_textpcb_s4_safety_governance.py")
        for token in (
            "test_fixture_manifest_is_closed_fingerprinted_and_complete",
            "test_dimensional_mismatch_fixture_fails_before_solving",
            "test_trace_width_clearance_and_drc_erc_hard_floor_dominate_preferences",
            "test_controlled_waiver_provenance_is_review_only_and_creates_debt",
            "test_thermal_power_and_signal_scenarios_are_explicit_and_distinct",
            "test_tolerance_and_quantization_are_conservative_at_safety_boundary",
            "test_production_alternatives_are_projection_equivalent_but_identity_diverse",
            "test_degraded_dependency_loss_and_unknown_never_amplify_authority",
            "test_present_and_unknown_hard_hazards_dominate_all_assurance",
            "test_irreversibility_escalates_assurance_and_scarcity_never_relaxes_floor",
            "test_fixture_suite_creates_no_public_or_runtime_surface",
        ):
            if token not in tests:
                fail(f"TextPCB S4 aggregate corpus missing test: {token}")
        workflow = text(".github/workflows/safety-governance.yml")
        for path in REQUIRED_S4_TESTS:
            if path not in workflow:
                fail(f"aggregate safety-governance workflow missing S4 corpus: {path}")
        for token in (
            "python scripts/check_safety_governance_contracts.py",
            "python scripts/check_release_contracts.py",
            "python scripts/check_s48_release_contracts.py",
            "python scripts/check_s49_release_contracts.py",
            "context='aasm/safety-governance'",
        ):
            if token not in workflow:
                fail(f"aggregate safety-governance workflow missing token: {token}")
        runtime = text("src/aasm/runtime_v56_foundation.py")
        package_root = text("src/aasm/__init__.py")
        for token in ("TextPCBSafetyFixture", "safety_governance_"):
            if token in runtime or token in package_root:
                fail(f"fixture-only S4.10 surface leaked into runtime/public root: {token}")
        print("S4.10 TextPCB fixture and aggregate safety-governance contracts: PASS")


    if __name__ == "__main__":
        main()
    ''',
)

write(
    "scripts/check_s410_release_contracts.py",
    r'''
    from __future__ import annotations

    from pathlib import Path
    import sys


    def fail(message: str) -> None:
        raise SystemExit(message)


    def text(root: Path, path: str) -> str:
        target = root / path
        if not target.exists():
            fail(f"missing S4.10 release-contract file: {path}")
        return target.read_text(encoding="utf-8")


    def require(root: Path, path: str, tokens: tuple[str, ...]) -> None:
        source = text(root, path)
        missing = [token for token in tokens if token not in source]
        if missing:
            fail(f"{path} missing S4.10 release tokens: {missing}")


    def main() -> int:
        root = Path(__file__).resolve().parents[1]
        for path in (
            "fixtures/textpcb/s4-safety-governance-fixtures.json",
            "schemas/textpcb-s4-safety-fixture.schema.json",
            "tests/test_textpcb_s4_safety_governance.py",
            "scripts/check_safety_governance_contracts.py",
            "docs/implementation/TEXTPCB_S4_SAFETY_GOVERNANCE_FIXTURES.md",
        ):
            text(root, path)
        require(
            root,
            ".github/workflows/safety-governance.yml",
            (
                "AASM S4 Aggregate Safety Governance Qualification",
                "tests/test_textpcb_s4_safety_governance.py",
                "context='aasm/safety-governance'",
            ),
        )
        require(
            root,
            ".github/workflows/engineering-s4.yml",
            (
                "check_safety_governance_contracts.py",
                "tests/test_textpcb_s4_safety_governance.py",
                "context='aasm/engineering-s4'",
            ),
        )
        require(
            root,
            ".github/workflows/v56.yml",
            (
                "Check S4.10 TextPCB fixtures and aggregate safety-governance contracts",
                "check_safety_governance_contracts.py",
                "tests/test_textpcb_s4_safety_governance.py",
                "check_s410_release_contracts.py",
                "context='aasm/v56'",
            ),
        )
        require(
            root,
            ".github/workflows/release.yml",
            (
                "aasm/safety-governance",
                "python scripts/check_s410_release_contracts.py",
            ),
        )
        sys.path.insert(0, str(root / "src"))
        import aasm

        contract = aasm.public_api_contract()
        if "textpcb_s4_fixtures" in contract or "safety_governance" in contract:
            fail("qualification-only S4.10 surface leaked into active public contract")
        if any(
            name.startswith(("textpcb_", "safety_governance_"))
            for name in aasm.SUPPORTED_ENGINE_METHODS
        ):
            fail("qualification-only S4.10 surface leaked into engine methods")
        print("S4.10 TextPCB fixture and aggregate safety-governance release contracts: PASS")
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
    ''',
)

write(
    ".github/workflows/safety-governance.yml",
    r'''
    name: AASM S4 Aggregate Safety Governance Qualification

    on:
      push:
        branches: [main]
      pull_request:
        branches: [main]

    concurrency:
      group: aasm-safety-governance-${{ github.ref }}
      cancel-in-progress: true

    permissions:
      contents: read
      statuses: write

    jobs:
      safety-governance:
        runs-on: ubuntu-24.04
        steps:
          - uses: actions/checkout@v7
          - uses: actions/setup-python@v7
            with:
              python-version: "3.13"
              cache: pip
          - name: Install AASM development dependencies
            run: python -m pip install -e '.[dev]'
          - name: Validate permanent fixture manifest and aggregate firewall
            run: |
              python -m json.tool fixtures/textpcb/s4-safety-governance-fixtures.json >/dev/null
              python -m json.tool schemas/textpcb-s4-safety-fixture.schema.json >/dev/null
              python scripts/check_safety_governance_contracts.py
          - name: Run every S4 foundation, public-adoption, adversarial, and TextPCB corpus
            run: |
              pytest -q \
                tests/test_quantity_foundation.py \
                tests/test_quantity_public.py \
                tests/test_rule_foundation.py \
                tests/test_rule_public.py \
                tests/test_semantic_projection_foundation.py \
                tests/test_semantic_projection_textpcb.py \
                tests/test_semantic_projection_adversarial.py \
                tests/test_semantic_projection_public.py \
                tests/test_uncertainty_scenario_trace_foundation.py \
                tests/test_uncertainty_scenario_trace_public.py \
                tests/test_degraded_operation_foundation.py \
                tests/test_degraded_operation_public.py \
                tests/test_risk_irreversibility_foundation.py \
                tests/test_obligation_phase_foundation.py \
                tests/test_safety_envelope_hybrid_state_foundation.py \
                tests/test_epistemic_debt_manual_override_foundation.py \
                tests/test_textpcb_s4_safety_governance.py
          - name: Recheck cumulative release and public-boundary contracts
            run: |
              python scripts/check_release_contracts.py
              python scripts/check_s48_release_contracts.py
              python scripts/check_s49_release_contracts.py
              python scripts/check_s410_release_contracts.py
          - name: Publish aggregate safety-governance qualification
            if: always()
            env:
              GH_TOKEN: ${{ github.token }}
              JOB_STATUS: ${{ job.status }}
            shell: bash
            run: |
              set -euo pipefail
              if [ "$JOB_STATUS" = success ]; then
                state=success
                description='S4 permanent TextPCB corpus and aggregate safety governance passed'
              else
                state=failure
                description='S4 aggregate safety governance failed'
              fi
              for attempt in 1 2 3 4 5; do
                if gh api "repos/$GITHUB_REPOSITORY/statuses/$GITHUB_SHA" \
                  -f state="$state" \
                  -f context='aasm/safety-governance' \
                  -f description="$description" \
                  -f target_url="https://github.com/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"; then
                  exit 0
                fi
                if [ "$attempt" -lt 5 ]; then sleep $((attempt * 2)); fi
              done
              exit 1
    ''',
)

# Compute the permanent manifest fingerprint using AASM's canonical semantic hash.
from aasm.semantic_result import semantic_fingerprint
manifest_path = ROOT / "fixtures/textpcb/s4-safety-governance-fixtures.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
payload = dict(manifest)
payload.pop("suite_fingerprint", None)
manifest["suite_fingerprint"] = semantic_fingerprint(payload)
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")

# Add S4.10 to cumulative engineering qualification.
replace_once(
    ".github/workflows/engineering-s4.yml",
    "            scripts/check_epistemic_debt_manual_override_contracts.py\n",
    "            scripts/check_epistemic_debt_manual_override_contracts.py \\\n            scripts/check_safety_governance_contracts.py\n",
)
replace_once(
    ".github/workflows/engineering-s4.yml",
    "          python -m json.tool schemas/manual-override-assessment.schema.json >/dev/null\n",
    "          python -m json.tool schemas/manual-override-assessment.schema.json >/dev/null\n          python -m json.tool schemas/textpcb-s4-safety-fixture.schema.json >/dev/null\n          python -m json.tool fixtures/textpcb/s4-safety-governance-fixtures.json >/dev/null\n",
)
replace_once(
    ".github/workflows/engineering-s4.yml",
    "      - name: Run cumulative S4 semantic corpus\n",
    "      - name: Check permanent TextPCB fixture and aggregate safety-governance contracts\n        run: python scripts/check_safety_governance_contracts.py\n      - name: Run cumulative S4 semantic corpus\n",
)
replace_once(
    ".github/workflows/engineering-s4.yml",
    "            tests/test_epistemic_debt_manual_override_foundation.py\n",
    "            tests/test_epistemic_debt_manual_override_foundation.py \\\n            tests/test_textpcb_s4_safety_governance.py\n",
)
replace_once(
    ".github/workflows/engineering-s4.yml",
    "description='S4 through active degraded 0.32.20 + risk + obligation phases + safety envelope + epistemic governance passed'",
    "description='S4 through active degraded 0.32.20 + all pre-admission foundations + TextPCB safety governance passed'",
)

# Add S4.10 to cumulative v0.56 qualification.
replace_once(
    ".github/workflows/v56.yml",
    "      - name: Validate cumulative development source contract\n",
    "      - name: Check S4.10 TextPCB fixtures and aggregate safety-governance contracts\n        run: |\n          python scripts/check_safety_governance_contracts.py\n          pytest -q tests/test_textpcb_s4_safety_governance.py\n\n      - name: Validate cumulative development source contract\n",
)
replace_once(
    ".github/workflows/v56.yml",
    "          python scripts/check_s49_release_contracts.py\n",
    "          python scripts/check_s49_release_contracts.py\n          python scripts/check_s410_release_contracts.py\n",
)
replace_once(
    ".github/workflows/v56.yml",
    "through Epistemic Debt/Manual Override pre-admission: PASS",
    "through aggregate S4 safety governance: PASS",
)
replace_once(
    ".github/workflows/v56.yml",
    "and S4.9 pre-admission passed'",
    "and aggregate S4 safety governance passed'",
)

# Require the aggregate gate for deliberate release.
replace_once(
    ".github/workflows/release.yml",
    "            aasm/engineering-epistemic-debt-manual-override \\\n            aasm/engineering-s4",
    "            aasm/engineering-epistemic-debt-manual-override \\\n            aasm/engineering-s4 \\\n            aasm/safety-governance",
)
replace_once(
    ".github/workflows/release.yml",
    "          python scripts/check_s49_release_contracts.py\n",
    "          python scripts/check_s49_release_contracts.py\n          python scripts/check_s410_release_contracts.py\n",
)

# Close S4 and advance the dependency seam to S5.1.
replace_once(
    "docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md",
    "## 4.10 TextPCB S4 fixtures\n\nPermanent fixture requirements include:",
    "## 4.10 TextPCB S4 fixtures\n\n**Status: PERMANENT CORPUS IMPLEMENTED; aggregate qualification active under `aasm/safety-governance`.**\n\nPermanent fixture requirements include:",
)
replace_once(
    "docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md",
    "**Next seam:** S4.10 permanent TextPCB fixtures and aggregate safety-governance qualification, then S5 governed refinement.",
    "**Next seam:** S5.1 governed Refinement Proposal/Loop foundation.",
)
replace_once(
    "docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md",
    "**Future aggregate safety gate:** `aasm/safety-governance`.",
    "**Aggregate safety gate:** `aasm/safety-governance` (permanent TextPCB corpus implemented; qualification active).",
)
append_once(
    "docs/implementation/GOVERNED_SEMANTIC_EVOLUTION_EXECUTION_LEDGER.md",
    "## S4.10 — Permanent TextPCB Corpus and Aggregate Safety Governance",
    r'''
    ## S4.10 — Permanent TextPCB Corpus and Aggregate Safety Governance

    - Closed, fingerprinted `aasm.textpcb.s4-safety-fixtures.v1` manifest implements all twelve normative S4.10 cases.
    - Independent `aasm/safety-governance` gate reruns every S4 foundation/public/adversarial corpus plus integrated TextPCB fixtures and release firewalls.
    - TextPCB remains a qualification consumer; no domain-specific runtime or engine surface was introduced.
    - S4 dependency chain is now implemented through the permanent aggregate corpus.
    - Next dependency seam: S5.1 governed Refinement Proposal/Loop foundation.
    ''',
)
append_once(
    "ROADMAP.md",
    "## Governed Semantic Evolution live status — S4 complete",
    r'''
    ## Governed Semantic Evolution live status — S4 complete

    S4.10 now provides the permanent, fingerprinted TextPCB stress corpus and independent `aasm/safety-governance` aggregate gate. All S4 foundations remain within their explicit claim ceilings. The next dependency-ordered implementation seam is S5.1 governed Refinement Proposal/Loop.
    ''',
)
replace_once(
    "README.md",
    "**Next unfinished boundary:** S4.10 — permanent TextPCB safety/engineering fixtures and aggregate safety-governance qualification",
    "**Next unfinished boundary:** S5.1 — governed Refinement Proposal/Loop with evaluator/proposer authority separation",
)

# Update the canonical tracked-file inventory.
permanent_paths = [
    ".github/workflows/safety-governance.yml",
    "fixtures/textpcb/s4-safety-governance-fixtures.json",
    "schemas/textpcb-s4-safety-fixture.schema.json",
    "tests/test_textpcb_s4_safety_governance.py",
    "scripts/check_safety_governance_contracts.py",
    "scripts/check_s410_release_contracts.py",
    "docs/implementation/TEXTPCB_S4_SAFETY_GOVERNANCE_FIXTURES.md",
]
anchors = {
    "src/aasm/obligation_phase.py",
    "scripts/check_obligation_phase_contracts.py",
    "tests/test_obligation_phase_foundation.py",
    "schemas/obligation-phase-assessment.schema.json",
    ".github/workflows/engineering-obligation-phase.yml",
}
check = subprocess.run(
    ["python", "scripts/release_manifest.py", "--check-file-list"],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
if check.returncode:
    candidates: list[tuple[int, Path, str]] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if not any(word in path.name.lower() for word in ("release", "manifest", "inventory")):
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        score = sum(anchor in source for anchor in anchors)
        if score >= 3:
            candidates.append((score, path, source))
    if not candidates:
        raise SystemExit("canonical tracked-file inventory source not found")
    _, inventory_path, source = max(candidates, key=lambda item: (item[0], len(item[2])))
    tree = ast.parse(source)
    matches: list[tuple[ast.List | ast.Tuple | ast.Set, list[str]]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            continue
        values: list[str] = []
        for element in node.elts:
            if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
                break
            values.append(element.value)
        else:
            if len(anchors.intersection(values)) >= 3:
                matches.append((node, values))
    if not matches:
        raise SystemExit(f"canonical literal tracked-file inventory not found in {inventory_path}")
    node, values = max(matches, key=lambda item: len(item[1]))
    additions = [value for value in permanent_paths if value not in values]
    lines = source.splitlines()
    close_index = node.end_lineno - 1
    sample = next(
        (
            line
            for line in reversed(lines[node.lineno - 1 : node.end_lineno - 1])
            if '"' in line or "'" in line
        ),
        lines[close_index],
    )
    indentation = re.match(r"\s*", sample).group(0)
    quote = '"' if '"' in sample else "'"
    comma = "," if sample.rstrip().endswith(",") else ""
    lines[close_index:close_index] = [
        f"{indentation}{quote}{value}{quote}{comma}" for value in additions
    ]
    inventory_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

print("S4.10 payload materialized")
