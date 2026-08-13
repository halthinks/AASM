from copy import deepcopy
from . import _public_v39 as _v39
for _name in dir(_v39):
    if not _name.startswith("_"): globals()[_name]=getattr(_v39,_name)
from .hierarchical_memory import *
from .memory_operations import *
from .memory_conformance import run_hierarchical_memory_conformance
from .reuse_model import *
from .reuse_certificate import *
from .reuse_validation import validate_reuse_candidate
from .reuse_index import HotReuseIndex
from .reuse_metrics import ReuseMetrics
from .reuse_policy import ReusePolicy
from .solver_loop import *
from .solver_types import SolverStepRequest,SolverStepResult
from .runtime_v41 import AASMEngine

__version__="0.41.0"
REMOTE_PROTOCOL_NAME=_v39.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION=_v39.REMOTE_PROTOCOL_VERSION

_MEMORY_METHODS=["hierarchical_memory_contract_report","hierarchical_memory_report","propose_memory_operation","propose_memory_forget","authorize_memory_operation","commit_memory_operation","admit_memory_index","reasoning_frontier","context_projection","record_context_projection"]
_REUSE_METHODS=["reuse_contract_report","canonical_reuse_ref","register_reuse_candidate","lookup_reuse","commit_reuse_certificate","reuse_report","record_reuse_metrics","solver_loop_contract_report","solver_step"]
SUPPORTED_ENGINE_METHODS=list(dict.fromkeys([*getattr(_v39,"SUPPORTED_ENGINE_METHODS",[]),*_MEMORY_METHODS,*_REUSE_METHODS]))
SUPPORTED_CLI_COMMANDS=list(dict.fromkeys([*getattr(_v39,"SUPPORTED_CLI_COMMANDS",[]),"hierarchical-memory-contract","memory-report","reasoning-frontier","context-project","reuse-contract","reuse-report","reuse-candidate-add","reuse-lookup","reuse-metrics-record","solver-loop-contract","solver-step"]))
SUPPORTED_INSPECTION_SURFACES=list(dict.fromkeys([*getattr(_v39,"SUPPORTED_INSPECTION_SURFACES",[]),"hierarchical-memory","reasoning-frontier","context-projection","reuse","reuse-report","reuse-contract","solver-loop","solver-loop-contract"]))
SUPPORTED_PUBLIC_IMPORTS=list(dict.fromkeys([*getattr(_v39,"SUPPORTED_PUBLIC_IMPORTS",[]),"MemoryObject","MemoryTombstone","MemoryIndexEntry","ContextProjectionRequest","hierarchical_memory_contract","ReuseRequest","ReuseCandidate","ReuseCertificate","ReuseValidation","ReuseMetrics","ReusePolicy","HotReuseIndex","reuse_contract","validate_reuse_candidate","SolverStepRequest","SolverStepResult","solver_loop_contract"]))
PUBLIC_API_CONTRACT=deepcopy(_v39.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({"contract_version":"0.17.0","runtime_version":__version__,"supported_imports":SUPPORTED_PUBLIC_IMPORTS,"supported_engine_methods":SUPPORTED_ENGINE_METHODS,"supported_cli_commands":SUPPORTED_CLI_COMMANDS,"supported_inspection_surfaces":SUPPORTED_INSPECTION_SURFACES})
PUBLIC_API_CONTRACT["hierarchical_memory"]=hierarchical_memory_contract()
PUBLIC_API_CONTRACT["reuse"]=reuse_contract()
PUBLIC_API_CONTRACT["solver_loop"]=solver_loop_contract()
PUBLIC_API_CONTRACT["distribution"]["version"]=__version__

def public_api_contract(): return deepcopy(PUBLIC_API_CONTRACT)
def validate_public_api_contract():
    errors=list(_v39.validate_public_api_contract().get("errors",[]))
    for name in _MEMORY_METHODS+_REUSE_METHODS:
        if not callable(getattr(AASMEngine,name,None)): errors.append(f"missing engine method: {name}")
    if PUBLIC_API_CONTRACT["contract_version"]!="0.17.0": errors.append("adoption contract mismatch")
    if PUBLIC_API_CONTRACT["reuse"].get("authority")!="INDEX_AND_VALIDATE_ONLY": errors.append("reuse authority mismatch")
    if PUBLIC_API_CONTRACT["reuse"].get("cache_deletion_semantics")!="PERFORMANCE_ONLY": errors.append("reuse cache deletion mismatch")
    return {"valid":not errors,"errors":errors,"contract":public_api_contract()}

from . import demo_stack as _demo_stack
_demo_stack.AASMEngine=AASMEngine
_demo_stack._runtime_version=lambda:__version__
