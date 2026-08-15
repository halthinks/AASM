from aasm import (
    AASMEngine,
    CERTIFICATION_CONTRACT_VERSION,
    SII_CONTRACT_VERSION,
    __version__,
    governed_sii_contract,
    public_api_contract,
    run_certification,
    validate_public_api_contract,
)
from aasm.cli import build_parser
from aasm.runtime_v46 import AASMEngine as V46Engine
from aasm.runtime_v47 import AASMEngine as V47Engine
from aasm.runtime_v48 import AASMEngine as V48Engine
from aasm.runtime_v49 import AASMEngine as V49Engine
from aasm.runtime_v50 import AASMEngine as V50Engine
from aasm.runtime_v51 import AASMEngine as V51Engine
from aasm.runtime_v52 import AASMEngine as V52Engine
from aasm.runtime_v53 import AASMEngine as V53AuthorityEngine
from aasm.runtime_v53_learning import AASMEngine as V53Engine
from aasm.runtime_v54_full import AASMEngine as V54Engine


def test_v47_public_contract_remains_active_under_current_composition():
    assert __version__ == "0.54.0"
    assert AASMEngine is V54Engine
    assert issubclass(V54Engine, V53Engine)
    assert issubclass(V53Engine, V53AuthorityEngine)
    assert issubclass(V53AuthorityEngine, V52Engine)
    assert issubclass(V52Engine, V51Engine)
    assert issubclass(V51Engine, V50Engine)
    assert issubclass(V50Engine, V49Engine)
    assert issubclass(V49Engine, V48Engine)
    assert issubclass(V48Engine, V47Engine)
    assert issubclass(V47Engine, V46Engine)
    report = validate_public_api_contract()
    assert report["valid"], report
    contract = report["contract"]
    assert contract["contract_version"] == "0.30.0"
    assert contract["runtime_version"] == "0.54.0"
    assert contract["distribution"]["version"] == "0.54.0"
    assert contract["certification"]["contract_version"] == "0.2.0"
    assert contract["sii_governance"]["contract_version"] == "0.3.0"
    assert contract["sii_governance"]["authority_reward"] == "NEVER"
    assert CERTIFICATION_CONTRACT_VERSION == "0.2.0"
    assert SII_CONTRACT_VERSION == "0.3.0"


def test_current_sii_contract_is_governed_while_legacy_preview_surface_remains_compatible():
    contract = governed_sii_contract()
    assert contract["stability"] == "GOVERNED_ENFORCED"
    assert contract["measurement_identity_binding"] == "RESOLVED_FROM_DURABLE_PRINCIPAL_BINDING"
    assert contract["mandatory_verification"] == "NEVER_REDUCED_BY_SII"
    imports = public_api_contract()["supported_imports"]
    assert "create_sii" in imports
    assert "create_governed_sii" in imports


def test_sii_preview_certification_alias_now_runs_governed_graduation_and_passes():
    report = run_certification("sii-preview")
    assert report["status"] == "PASS", report
    assert report["target_count"] == 1
    target = report["targets"][0]
    assert target["target_id"] == "sii-preview"
    assert target["status"] == "PASS"
    checks = {row["check_id"]: row for row in target["checks"]}
    assert checks["measurement-principal-authority-binding"]["status"] == "PASS"
    assert checks["resource-lease-native-solver-enforcement"]["status"] == "PASS"
    assert checks["resource-lease-scheduler-enforcement"]["status"] == "PASS"
    assert checks["mandatory-verification-not-reduced"]["status"] == "PASS"


def test_full_v47_certification_includes_governed_sii_and_has_no_expected_preview_inconclusive():
    report = run_certification()
    assert report["status"] == "PASS", report
    assert report["status_counts"]["INCONCLUSIVE"] == 0
    assert {row["target_id"] for row in report["targets"]} == {"reference-domains", "solver-reuse", "truth-memory", "formal-verification", "sii-governance"}


def test_v47_cli_keeps_certify_and_adds_governed_sii_surfaces():
    help_text = build_parser().format_help()
    for command in ("certify", "sii-governance-contract", "sii-default-scoring-policy", "advanced-optimization-conformance"):
        assert command in help_text
