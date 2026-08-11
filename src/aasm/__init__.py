from copy import deepcopy as _deepcopy

__version__ = "0.28.1"
REMOTE_PROTOCOL_NAME = "aasm.remote.v1"
REMOTE_PROTOCOL_VERSION = "0.19.0"

from .runtime_v25 import AASMEngine, default_profile_registry
from .model import MachineState, ProblemSpec, TaskEnvelope, Proposal, Result, CapabilitySet
from .agents import AASMAgent, FunctionAgent
from .authority import SingleControllerAuthority, AutonomousAuthority, QuorumAuthority, HierarchicalAuthority
from .effects import EffectSpec, EffectRecord, EffectStatus, RetryPolicy, EffectExecutionError, EffectUnknownOutcome
from .definitions import MachineDefinition, default_machine_definition
from .model_check import ModelCheckIssue, ModelCheckReport, check_machine
from .persistence import MemoryStore, SQLiteStore, PostgresStore
from .workers import WorkerRecord, WorkerStatus, TaskLease, LeaseStatus, QuotaPolicy
from .model_routing import ModelProfile, ModelRouteRequest, ModelRouteResult, ModelStrengthRouter
from .adaptive_routing import ModelOutcomeRecord, ModelPerformance, ModelOutcomeLedger, AdaptiveRouteResult, AdaptiveModelRouter
from .collaboration import CollaborationPolicy, CollaborationCandidate, CollaborationAnalysis, CollaborationPlanner
from .change_impact import ChangeKind, ChangeSignal, ImpactAnalysis, ChangeImpactAnalyzer
from .checkpoint_triggers import CheckpointTriggerPolicy, CheckpointTrigger, CheckpointTriggerEngine
from .fleet_control import FleetControlPolicy
from .execution_telemetry import TelemetryKind, TelemetryPolicy, ExecutionTelemetryRecord, ExecutionTelemetryLedger
from .provisioning import ProvisioningAction, ProvisioningRequest, ProvisioningPlan, ProvisioningAdapter, FunctionProvisioningAdapter, ProvisioningRegistry
from .provider_adapters import CommandProvisioningAdapter, KubernetesScaleAdapter, subprocess_runner
from .artifact_backends import ArtifactBackend, ArtifactBackendRegistry, MemoryArtifactBackend, LocalDirectoryArtifactBackend
from .execution_controls import WorkerControlAction, WorkerControlRecord
from .mission_control import MissionStatus, MissionControlAction, MissionPauseMode, MissionControlRecord, ForkRequest
from .pagination import CursorError, page_records
from .supervisor_adapters import LocalProcessSupervisorAdapter, DockerComposeScaleAdapter, load_runtime_registries
from .team_protocol import TeamRole, PlannerDirective, TeamMember, BuilderOutput, VerifierReport, PlannerDecision, PlannerBuilderVerifierPolicy
from .pbv_orchestrator import PBVCycleResult, PBVCoordinator
from .remote import AASMRemoteClient, RemoteProtocolError
from .worker_loop import RemoteWorkerLoop
from .economics import CallPurpose, ModelPricing, ModelUsageRecord, ReviewGatePolicy, EconomicsLedger
from .governance import GovernanceAction, GovernanceBudgetPolicy, GovernanceContext, GovernanceDecision, GovernanceEconomicsController
from .openai_executor import OpenAIResponsesExecutor, OpenAIExecutionResult, OpenAIExecutorError
from .codex_executor import CodexCLIExecutor, CodexExecutionResult, CodexExecutorError
from .executor_orchestration import ExecutorAdapter, ExecutorBinding, ExecutorRegistry, ExecutionContract, ExecutionOrchestrator, OrchestrationResult, OrchestratedRemoteWorker
from .codex_policy import CodexGovernancePolicy
from .codex_telemetry import CodexTelemetryImport, import_otel_events, import_otel_jsonl
from .calculus import (
    DecisionLiteral, DecisionRecord, ObligationRecord, LockRecord, ConflictRecord,
    ExplanationRecord, LearnedConstraint, FairnessPolicy, RecoveryDecision,
    default_calculus_state, condition_holds, project_constraint, compute_backjump,
    assert_calculus_invariants,
)
from .profile_packages import (
    PROFILE_CONTRACT, PROFILE_ENTRY_POINT_GROUP, AdapterBinding,
    ProfileEvolutionPolicy, ProfileMigration, AASMProfile, AASMPackageManifest,
    ProfileBinding, ProfileEvolutionProposal, ProfileRegistry, bare_profile,
    evolve_profile,
)
from .research_profile import (
    ResearchProfileRegistry, research_package, research_profile,
)
from .domain_adapters import (
    DecisionRequest, CandidateModel, CandidateValidationReport, DomainContext,
    ValidationContext, ExplanationContext, ExplanationCandidate,
    CertificationContext, ConstraintCertificate, DecisionBackend,
    ObligationAdapter, SemanticValidator, ConflictExplainer, ConstraintCertifier,
    load_adapter, validate_adapter_object, determinism_probe,
)
from .semantic_result import (
    SEMANTIC_CLASSIFICATIONS, ProducerRef, SemanticResultEnvelope,
    validate_semantic_result,
)
from .profile_conformance import (
    ConformanceIssue, ConformanceReport, ProfileConformanceKit,
    assert_profile_conformant,
)
from .decision_backends import (
    BackendCapabilities, BackendBudget, BackendUsage, BackendDiagnostic,
    CandidateExplanation, CandidateBatch, CandidateLifecycleRecord,
    FiniteDomainDecisionBackend, HumanDecisionBackend, CallbackDecisionBackend,
    PortfolioDecisionBackend, DecisionBackendRegistry, default_backend_registry,
    route_backend,
)
from .assurance import (
    AssurancePolicy, CertificateRecord, CertificateVerification, HistoryIssue,
    HistoryCheckReport, ProjectionCertificateVerifier, DetachedDigestVerifier,
    default_assurance_policy, normalize_assurance_state,
    hard_constraint_certification_issues, assert_hard_constraint_certification,
    projection_payload, check_history,
)
from .conflict_minimization import (
    ConflictMinimizationResult, ConflictOracle, minimize_conflict_core,
)
from .observability import (
    ObservableGraph, decision_graph, obligation_graph, evidence_graph,
    causal_graph, conflict_timeline, fairness_debt, event_timeline,
    package_history, observability_report,
)
from .research_demo import (
    CORPUS_ID, REFERENCE_RESULT_ID, ResearchDemoResult,
    load_research_corpus, run_research_synthesis_demo, verify_research_corpus,
)
from .demo_stack import (
    DEFAULT_STATE_PATH, DEFAULT_WORKER_RESOURCE_ID,
    bootstrap_stack, complete_stack, fresh_stack, read_stack_state,
    run_worker_cycle, select_stack_machine, stack_status, verify_stack,
)
from .operator_runbooks import (
    RUNBOOK_DEFINITIONS, OperatorRunbookResult, execute_operator_runbook,
    list_operator_runbooks, run_history_diagnosis, run_human_approval,
    run_learned_no_good, run_lease_loss_recovery, run_replay_fork,
    run_requirement_change, run_unknown_effect,
)
from .graph import PlanNode, PlanEdge, PlanGraph
from .evidence import EvidenceRecord, EvidenceLedger
from .resources import ResourceRecord, TaskDemand, Assignment, ScheduleResult
from .scheduler import CapabilityScheduler

SUPPORTED_PUBLIC_IMPORTS = [
    "__version__",
    "AASMEngine",
    "ProblemSpec",
    "MachineState",
    "DecisionRecord",
    "ObligationRecord",
    "EvidenceRecord",
    "ConflictRecord",
    "ExplanationRecord",
    "RecoveryDecision",
    "CandidateModel",
    "BackendBudget",
    "AssurancePolicy",
    "CertificateRecord",
    "MemoryStore",
    "SQLiteStore",
    "PostgresStore",
    "research_profile",
    "research_package",
    "verify_research_corpus",
    "run_research_synthesis_demo",
    "bootstrap_stack",
    "fresh_stack",
    "complete_stack",
    "stack_status",
    "verify_stack",
    "OperatorRunbookResult",
    "list_operator_runbooks",
    "execute_operator_runbook",
]

SUPPORTED_ENGINE_METHODS = [
    "register_decision",
    "activate_decision",
    "register_obligation",
    "enable_obligation",
    "set_obligation_status",
    "add_evidence",
    "raise_conflict",
    "register_explanation",
    "learn_constraint",
    "register_projection_certificate",
    "verify_projection_certificate",
    "promote_constraint_hard",
    "generate_candidate_batch",
    "select_candidate",
    "activate_candidate",
    "inspect_machine",
    "check_durable_history",
    "backjump_conflict",
    "restart_search",
    "replay",
    "fork",
]

SUPPORTED_CLI_COMMANDS = [
    "adoption-contract",
    "demo",
    "stack",
    "runbook",
    "serve",
    "inspect",
    "history-check",
    "candidate-generate",
    "candidate-select",
    "candidate-activate",
    "assurance",
]

SUPPORTED_INSPECTION_SURFACES = [
    "summary",
    "decisions",
    "obligations",
    "evidence",
    "causal",
    "conflicts",
    "fairness",
    "packages",
    "candidates",
    "assurance",
    "calculus",
    "profile",
]

PUBLIC_API_CONTRACT = {
    "contract_id": "aasm.adoption.v1",
    "schema_version": 1,
    "contract_version": "0.4.0",
    "runtime_version": __version__,
    "project_status": "EXPERIMENTAL",
    "remote_protocol": {
        "name": REMOTE_PROTOCOL_NAME,
        "version": REMOTE_PROTOCOL_VERSION,
    },
    "support_policy": {
        "SUPPORTED": (
            "Documented golden-path surface. Breaking changes require an explicit "
            "changelog entry and migration or deprecation guidance when practical."
        ),
        "EXPERIMENTAL": (
            "Available for evaluation but may change between pre-1.0 releases."
        ),
        "INTERNAL": "No compatibility promise; applications should not depend on it.",
    },
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
    "supported_http_endpoints": [
        "/",
        "/ui",
        "/health",
        "/adoption-contract",
        "/demo-stack",
        "/v1/machines/{machine_id}/inspect/{surface}",
        "/v1/machines/{machine_id}/history-check",
        "/v1/machines/{machine_id}/workers/register",
        "/v1/machines/{machine_id}/claim-next",
        "/v1/machines/{machine_id}/leases/{lease_id}/complete",
    ],
    "reference_application": {
        "id": "research-synthesis",
        "profile_id": "aasm.research-synthesis",
        "corpus_id": CORPUS_ID,
        "offline": True,
        "entry_points": [
            "aasm demo --scenario research-synthesis",
            "run_research_synthesis_demo()",
        ],
    },
    "local_stack": {
        "id": "aasm-local",
        "entry_point": "docker compose up --build",
        "control_center": "http://localhost:8787/",
        "store": "PostgreSQL 17",
        "default_workers": 1,
        "optional_workers": 1,
        "external_credentials_required": False,
        "maintenance_entry_point": "docker compose run --rm stackctl",
        "reset_semantics": "create a fresh canonical machine and retain prior history",
    },
    "distribution": {
        "package": "aasm-runtime",
        "version": __version__,
        "release_workflow": ".github/workflows/release.yml",
        "release_history": "release-history.json",
        "checksums": "SHA256SUMS.txt",
        "historical_report": "historical-release-report.json",
        "reproducible_builds": True,
        "historical_release_policy": "REPORT_ONLY",
        "github_release_assets": [
            "wheel",
            "source distribution",
            "checksums",
            "manifest",
            "historical release report",
        ],
        "pypi_trusted_publishing": True,
        "pypi_status": "EXTERNAL_TRUSTED_PUBLISHER_BINDING_REQUIRED",
    },
    "operator_runbooks": sorted(RUNBOOK_DEFINITIONS),
    "golden_path": [
        "create machine",
        "register decisions and obligations",
        "record evidence",
        "raise and explain conflicts",
        "learn soft constraints and certify hard knowledge",
        "activate complete candidates atomically",
        "inject selective steering through the existing change-impact path",
        "operate workers through registration, heartbeat, claim, lease, telemetry, and completion",
        "execute tested operator recovery drills",
        "inspect, replay, backjump, restart, or fork",
    ],
    "implementation_rule": (
        "Reference applications, adapters, Control Center work, local-stack "
        "services, distribution tooling, and operator runbooks must use the "
        "existing event/reducer runtime and public surface rather than create a "
        "parallel authority or persistence path."
    ),
}


def public_api_contract() -> dict:
    """Return the machine-readable canonical adoption surface."""

    return _deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract() -> dict:
    """Verify that every supported import, engine method, and runbook still exists."""

    errors: list[str] = []
    missing_imports = [name for name in SUPPORTED_PUBLIC_IMPORTS if name not in globals()]
    missing_methods = [
        name for name in SUPPORTED_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))
    ]
    if missing_imports:
        errors.append(f"missing supported imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing supported AASMEngine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("public API contract runtime_version does not match __version__")
    if PUBLIC_API_CONTRACT.get("remote_protocol") != {
        "name": REMOTE_PROTOCOL_NAME,
        "version": REMOTE_PROTOCOL_VERSION,
    }:
        errors.append("public API contract remote protocol does not match package constants")
    if sorted(PUBLIC_API_CONTRACT.get("operator_runbooks") or []) != sorted(
        RUNBOOK_DEFINITIONS
    ):
        errors.append("public API contract operator runbooks do not match the registry")
    corpus = verify_research_corpus()
    if not corpus["valid"]:
        errors.append("packaged research reference corpus failed verification")
    return {
        "valid": not errors,
        "errors": errors,
        "contract": public_api_contract(),
    }


__all__ = ["__version__", *[name for name in globals() if not name.startswith("_")]]
