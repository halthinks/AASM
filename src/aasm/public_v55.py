from __future__ import annotations

from copy import deepcopy

from . import public_v54 as _v54

for _name in dir(_v54):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v54, _name)

from ._runtime_v55_formulation import (
    FORMULATION_RUNTIME_CONTRACT_ID,
    FORMULATION_RUNTIME_CONTRACT_VERSION,
    FORMULATION_RUNTIME_STABILITY,
    formulation_runtime_contract,
)
from ._runtime_v55_semantic_evolution import (
    SEMANTIC_EVOLUTION_RUNTIME_CONTRACT_ID,
    SEMANTIC_EVOLUTION_RUNTIME_CONTRACT_VERSION,
    SEMANTIC_EVOLUTION_RUNTIME_STABILITY,
    semantic_evolution_runtime_contract,
)
from .continuous_ir import (
    CONTINUOUS_ASSIGNMENT_CONTRACT_ID,
    CONTINUOUS_MODEL_CONTRACT_ID,
    CONTINUOUS_PROVIDER_BINDING_CONTRACT_ID,
    CONTINUOUS_VALIDATION_CONTRACT_ID,
    NUMERIC_TOLERANCE_CONTRACT_ID,
    ContinuousAssignment,
    ContinuousModel,
    ContinuousProviderBinding,
    ContinuousValidationReport,
    ContinuousVariable,
    LinearExpression,
    NumericTolerancePolicy,
    QuadraticConstraint,
    QuadraticExpression,
    QuadraticObjective,
    QuadraticTerm,
    SecondOrderConeConstraint,
    bind_continuous_provider,
    canonical_decimal,
    continuous_ir_contract,
    validate_continuous_assignment,
)
from .decision_vector_ir import (
    DECISION_VECTOR_COMPILATION_CONTRACT_ID,
    DECISION_VECTOR_CONTRACT_ID,
    DecisionHardFloor,
    DecisionObjective,
    DecisionVectorCompilation,
    GovernedDecisionVector,
    compile_linear_decision_vector,
    decision_vector_contract,
    evaluate_hard_floors,
)
from .discrete_ir import (
    CARDINALITY_LINEARIZATION_ID,
    DISCRETE_BOOLEAN_MODEL_CONTRACT_ID,
    DISCRETE_LINEARIZATION_CONTRACT_ID,
    DISCRETE_LOWERING_CERTIFICATE_CONTRACT_ID,
    PSEUDO_BOOLEAN_LINEARIZATION_ID,
    CardinalityConstraint,
    DiscreteBooleanModel,
    DiscreteConstraintMapping,
    DiscreteLinearization,
    DiscreteLoweringCertificate,
    PseudoBooleanConstraint,
    WeightedBooleanLiteral,
    discrete_ir_contract,
    lower_discrete_boolean_model,
    verify_discrete_boolean_linearization,
)
from .formulation_execution import (
    FORMULATION_EXECUTION_BINDING_CONTRACT_ID,
    FormulationExecutionBinding,
    bind_formulation_execution_request,
    formulation_execution_contract,
    validate_formulation_governance_chain,
)
from .model_features import (
    MODEL_ADMISSION_CONTRACT_ID,
    MODEL_FEATURE_SET_CONTRACT_ID,
    PROVIDER_CAPABILITY_MANIFEST_CONTRACT_ID,
    ModelAdmissionReport,
    ModelFeatureRequirement,
    ModelFeatureSet,
    ProviderCapabilityManifest,
    ProviderFeatureSupport,
    evaluate_model_admission,
    model_feature_contract,
)
from .runtime_v55 import AASMEngine
from .scheduling_ir import (
    SCHEDULING_ASSIGNMENT_CONTRACT_ID,
    SCHEDULING_MODEL_CONTRACT_ID,
    SCHEDULING_PROVIDER_BINDING_CONTRACT_ID,
    SCHEDULING_VALIDATION_CONTRACT_ID,
    CumulativeResourceConstraint,
    NoOverlapConstraint,
    PrecedenceConstraint,
    SchedulingAssignment,
    SchedulingModel,
    SchedulingProviderBinding,
    SchedulingTask,
    SchedulingValidationReport,
    bind_scheduling_provider,
    scheduling_ir_contract,
    validate_scheduling_assignment,
)
from .semantic_archive import (
    SEMANTIC_ARCHIVE_CONTRACT_ID,
    SEMANTIC_ARCHIVE_VERIFICATION_CONTRACT_ID,
    SemanticEvolutionArchive,
    build_semantic_evolution_archive,
    semantic_archive_contract,
    verify_semantic_evolution_archive,
)
from .semantic_evolution import (
    EXTERNAL_REFERENCE_CONTRACT_ID,
    PROBLEM_DELTA_CONTRACT_ID,
    PROBLEM_REVISION_CONTRACT_ID,
    ExternalReference,
    ProblemDelta,
    ProblemRevision,
    semantic_evolution_contract,
    validate_revision_transition,
)
from .solver_formulation import (
    SOLVER_FORMULATION_CERTIFICATE_CONTRACT_ID,
    SOLVER_FORMULATION_CONTRACT_ID,
    FormulationExternalReferenceBinding,
    FormulationObjectMapping,
    SolverFormulation,
    SolverFormulationCertificate,
    formulation_from_v54_translation,
    solver_formulation_contract,
    verify_solver_formulation_identity,
)


__version__ = "0.55.0"
PUBLIC_RELEASE_STABILITY = "ACTIVE_DEVELOPMENT"
REMOTE_PROTOCOL_NAME = _v54.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _v54.REMOTE_PROTOCOL_VERSION

_NEW_ENGINE_METHODS = [
    "semantic_evolution_runtime_contract_report",
    "semantic_evolution_report",
    "register_initial_problem_revision",
    "commit_problem_revision_transition",
    "resume_problem_revision_impacts",
    "require_usable_problem_revision",
    "formulation_runtime_contract_report",
    "register_solver_formulation",
    "prepare_registered_formulation_request",
    "formulation_report",
]

_NEW_IMPORTS = [
    "EXTERNAL_REFERENCE_CONTRACT_ID",
    "PROBLEM_REVISION_CONTRACT_ID",
    "PROBLEM_DELTA_CONTRACT_ID",
    "ExternalReference",
    "ProblemRevision",
    "ProblemDelta",
    "validate_revision_transition",
    "semantic_evolution_contract",
    "SEMANTIC_EVOLUTION_RUNTIME_CONTRACT_ID",
    "SEMANTIC_EVOLUTION_RUNTIME_CONTRACT_VERSION",
    "SEMANTIC_EVOLUTION_RUNTIME_STABILITY",
    "semantic_evolution_runtime_contract",
    "MODEL_FEATURE_SET_CONTRACT_ID",
    "PROVIDER_CAPABILITY_MANIFEST_CONTRACT_ID",
    "MODEL_ADMISSION_CONTRACT_ID",
    "ModelFeatureRequirement",
    "ModelFeatureSet",
    "ProviderFeatureSupport",
    "ProviderCapabilityManifest",
    "ModelAdmissionReport",
    "evaluate_model_admission",
    "model_feature_contract",
    "SOLVER_FORMULATION_CONTRACT_ID",
    "SOLVER_FORMULATION_CERTIFICATE_CONTRACT_ID",
    "FormulationObjectMapping",
    "FormulationExternalReferenceBinding",
    "SolverFormulation",
    "SolverFormulationCertificate",
    "formulation_from_v54_translation",
    "verify_solver_formulation_identity",
    "solver_formulation_contract",
    "FORMULATION_EXECUTION_BINDING_CONTRACT_ID",
    "FormulationExecutionBinding",
    "validate_formulation_governance_chain",
    "bind_formulation_execution_request",
    "formulation_execution_contract",
    "FORMULATION_RUNTIME_CONTRACT_ID",
    "FORMULATION_RUNTIME_CONTRACT_VERSION",
    "FORMULATION_RUNTIME_STABILITY",
    "formulation_runtime_contract",
    "DISCRETE_BOOLEAN_MODEL_CONTRACT_ID",
    "DISCRETE_LINEARIZATION_CONTRACT_ID",
    "DISCRETE_LOWERING_CERTIFICATE_CONTRACT_ID",
    "PSEUDO_BOOLEAN_LINEARIZATION_ID",
    "CARDINALITY_LINEARIZATION_ID",
    "WeightedBooleanLiteral",
    "PseudoBooleanConstraint",
    "CardinalityConstraint",
    "DiscreteBooleanModel",
    "DiscreteConstraintMapping",
    "DiscreteLinearization",
    "DiscreteLoweringCertificate",
    "lower_discrete_boolean_model",
    "verify_discrete_boolean_linearization",
    "discrete_ir_contract",
    "SCHEDULING_MODEL_CONTRACT_ID",
    "SCHEDULING_ASSIGNMENT_CONTRACT_ID",
    "SCHEDULING_VALIDATION_CONTRACT_ID",
    "SCHEDULING_PROVIDER_BINDING_CONTRACT_ID",
    "SchedulingTask",
    "PrecedenceConstraint",
    "NoOverlapConstraint",
    "CumulativeResourceConstraint",
    "SchedulingModel",
    "SchedulingAssignment",
    "SchedulingValidationReport",
    "SchedulingProviderBinding",
    "validate_scheduling_assignment",
    "bind_scheduling_provider",
    "scheduling_ir_contract",
    "CONTINUOUS_MODEL_CONTRACT_ID",
    "CONTINUOUS_ASSIGNMENT_CONTRACT_ID",
    "CONTINUOUS_VALIDATION_CONTRACT_ID",
    "CONTINUOUS_PROVIDER_BINDING_CONTRACT_ID",
    "NUMERIC_TOLERANCE_CONTRACT_ID",
    "NumericTolerancePolicy",
    "ContinuousVariable",
    "LinearExpression",
    "QuadraticTerm",
    "QuadraticExpression",
    "QuadraticConstraint",
    "SecondOrderConeConstraint",
    "QuadraticObjective",
    "ContinuousModel",
    "ContinuousAssignment",
    "ContinuousValidationReport",
    "ContinuousProviderBinding",
    "canonical_decimal",
    "validate_continuous_assignment",
    "bind_continuous_provider",
    "continuous_ir_contract",
    "DECISION_VECTOR_CONTRACT_ID",
    "DECISION_VECTOR_COMPILATION_CONTRACT_ID",
    "DecisionHardFloor",
    "DecisionObjective",
    "GovernedDecisionVector",
    "DecisionVectorCompilation",
    "compile_linear_decision_vector",
    "evaluate_hard_floors",
    "decision_vector_contract",
    "SEMANTIC_ARCHIVE_CONTRACT_ID",
    "SEMANTIC_ARCHIVE_VERIFICATION_CONTRACT_ID",
    "SemanticEvolutionArchive",
    "build_semantic_evolution_archive",
    "verify_semantic_evolution_archive",
    "semantic_archive_contract",
]

SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*getattr(_v54, "SUPPORTED_ENGINE_METHODS", []), *_NEW_ENGINE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(getattr(_v54, "SUPPORTED_CLI_COMMANDS", []))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([
    *getattr(_v54, "SUPPORTED_INSPECTION_SURFACES", []),
    "semantic-evolution",
    "solver-formulation",
]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_v54, "SUPPORTED_PUBLIC_IMPORTS", []), *_NEW_IMPORTS]))

PUBLIC_API_CONTRACT = deepcopy(_v54.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.31.0",
    "runtime_version": __version__,
    "release_stability": PUBLIC_RELEASE_STABILITY,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["semantic_evolution"] = {
    **semantic_evolution_contract(),
    "runtime": semantic_evolution_runtime_contract(),
}
PUBLIC_API_CONTRACT["model_features"] = model_feature_contract()
PUBLIC_API_CONTRACT["solver_formulation"] = {
    **solver_formulation_contract(),
    "execution": formulation_execution_contract(),
    "runtime": formulation_runtime_contract(),
}
PUBLIC_API_CONTRACT["discrete_ir"] = discrete_ir_contract()
PUBLIC_API_CONTRACT["scheduling_ir"] = scheduling_ir_contract()
PUBLIC_API_CONTRACT["continuous_ir"] = continuous_ir_contract()
PUBLIC_API_CONTRACT["decision_vector"] = decision_vector_contract()
PUBLIC_API_CONTRACT["semantic_archive"] = semantic_archive_contract()
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _v54.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.54: {error}" for error in parent["errors"])
    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing v0.55 imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing v0.55 engine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("v0.55 runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.31.0":
        errors.append("v0.55 adoption contract mismatch")
    if PUBLIC_RELEASE_STABILITY != "ACTIVE_DEVELOPMENT":
        errors.append("v0.55 active release stability mismatch")
    if PUBLIC_API_CONTRACT.get("semantic_evolution", {}).get("truth_authority") != "EXISTING_AASM_ADMISSION_PATH_ONLY":
        errors.append("semantic evolution authority boundary mismatch")
    if PUBLIC_API_CONTRACT.get("solver_formulation", {}).get("truth_authority") != "NONE":
        errors.append("solver formulation authority boundary mismatch")
    if PUBLIC_API_CONTRACT.get("discrete_ir", {}).get("approximation") != "NOT_SUPPORTED_BY_THIS_CONTRACT":
        errors.append("discrete IR approximation boundary mismatch")
    if PUBLIC_API_CONTRACT.get("scheduling_ir", {}).get("execution_adapter") != "NOT_CLAIMED_BY_THIS_FOUNDATION":
        errors.append("scheduling execution claim ceiling mismatch")
    if PUBLIC_API_CONTRACT.get("continuous_ir", {}).get("optimality_proof") != "NOT_CLAIMED_BY_ASSIGNMENT_VALIDATION":
        errors.append("continuous optimality claim ceiling mismatch")
    if PUBLIC_API_CONTRACT.get("decision_vector", {}).get("scalarization") != "NONE":
        errors.append("decision vector scalarization boundary mismatch")
    if PUBLIC_API_CONTRACT.get("semantic_archive", {}).get("replay_uses_persisted_snapshot") is not False:
        errors.append("semantic archive replay boundary mismatch")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__
