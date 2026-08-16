from aasm import (
    AASMEngine,
    CROSS_RUN_KNOWLEDGE_CONTRACT_VERSION,
    __version__,
    cross_run_knowledge_contract,
    public_api_contract,
    run_cross_run_knowledge_conformance,
    validate_public_api_contract,
)
from aasm.cli import build_parser
from aasm.runtime_v47 import AASMEngine as V47Engine
from aasm.runtime_v48 import AASMEngine as V48Engine
from aasm.runtime_v49 import AASMEngine as V49Engine
from aasm.runtime_v50 import AASMEngine as V50Engine
from aasm.runtime_v51 import AASMEngine as V51Engine
from aasm.runtime_v52 import AASMEngine as V52Engine
from aasm.runtime_v53 import AASMEngine as V53AuthorityEngine
from aasm.runtime_v53_learning import AASMEngine as V53Engine
from aasm.runtime_v54_full import AASMEngine as V54Engine
from aasm.runtime_v55 import AASMEngine as V55Engine
from aasm.runtime_v56 import AASMEngine as V56Engine


def test_v48_public_contract_remains_active_under_v55_composition():
    assert __version__ == "0.56.0"
    assert AASMEngine is V56Engine
    assert issubclass(V56Engine, V55Engine)
    assert issubclass(V55Engine, V54Engine)
    assert issubclass(V54Engine, V53Engine)
    assert issubclass(V53Engine, V53AuthorityEngine)
    assert issubclass(V53AuthorityEngine, V52Engine)
    assert issubclass(V52Engine, V51Engine)
    assert issubclass(V51Engine, V50Engine)
    assert issubclass(V50Engine, V49Engine)
    assert issubclass(V49Engine, V48Engine)
    assert issubclass(V48Engine, V47Engine)
    report = validate_public_api_contract()
    assert report["valid"], report
    contract = report["contract"]
    assert contract["contract_version"] == "0.32.0"
    assert contract["runtime_version"] == "0.56.0"
    assert contract["distribution"]["version"] == "0.56.0"
    assert contract["sii_governance"]["contract_version"] == "0.3.0"
    assert contract["certification"]["contract_version"] == "0.2.0"
    assert contract["cross_run_knowledge"]["contract_version"] == "0.1.0"
    assert CROSS_RUN_KNOWLEDGE_CONTRACT_VERSION == "0.1.0"


def test_cross_run_contract_keeps_receiving_authority_and_reuse_boundaries():
    contract = cross_run_knowledge_contract()
    assert contract["source_authority"] == "PROVENANCE_ONLY_NEVER_INHERITED"
    assert contract["receiving_admission"] == "POLICY_OR_CONTROLLER_REQUIRED"
    assert contract["semantic_materialization"] == "LOCAL_AUTHORIZED_REASONING_REQUIRED"
    assert contract["reuse"] == "EXISTING_V41_REUSE_CERTIFICATE_REQUIRED"
    assert contract["sii_reputation"] == "ACCOUNTING_ONLY_NEVER_AUTHORITY_OR_RESOURCE_ENTITLEMENT"


def test_cross_run_conformance_and_cli_are_public():
    conformance = run_cross_run_knowledge_conformance()
    assert conformance["status"] == "PASS", conformance
    assert all(conformance["checks"].values())
    help_text = build_parser().format_help()
    assert "cross-run-knowledge-contract" in help_text
    assert "cross-run-knowledge-conformance" in help_text
    imports = public_api_contract()["supported_imports"]
    assert "CrossRunKnowledgeEnvelope" in imports
    assert "CrossRunAdmissionCertificate" in imports
