"""Optional framework integration adapters and conformance tools.

Integrations translate framework lifecycle signals into the supported AASM
adoption surface. They never replace the authoritative event/reducer runtime.
"""

from .langgraph import (
    LANGGRAPH_ADAPTER_ID,
    LANGGRAPH_ADAPTER_VERSION,
    LangGraphAdapter,
    LangGraphBinding,
    LangGraphNodePolicy,
    LangGraphRecoveryAction,
    LangGraphRecoveryResult,
    LangGraphRunKey,
)
from .conformance import (
    ADAPTER_CONFORMANCE_ID,
    ADAPTER_CONFORMANCE_VERSION,
    CONFORMANCE_SCENARIOS,
    ConformanceStatus,
    AdapterCapabilityDeclaration,
    AdapterScenarioOutcome,
    ConformanceFinding,
    ConformanceScenarioResult,
    AdapterConformanceReport,
    AdapterConformanceDriver,
    AuditedStore,
    AdapterConformanceContext,
    AdapterConformanceKit,
    conformance_contract,
)
from .langgraph_conformance import (
    LANGGRAPH_CONFORMANCE_DRIVER_ID,
    LANGGRAPH_CONFORMANCE_DRIVER_VERSION,
    LangGraphConformanceDriver,
)
from .conformance_registry import (
    BUILTIN_CONFORMANCE_DRIVERS,
    list_conformance_drivers,
    get_conformance_driver,
    run_adapter_conformance,
)

__all__ = [
    "LANGGRAPH_ADAPTER_ID",
    "LANGGRAPH_ADAPTER_VERSION",
    "LangGraphAdapter",
    "LangGraphBinding",
    "LangGraphNodePolicy",
    "LangGraphRecoveryAction",
    "LangGraphRecoveryResult",
    "LangGraphRunKey",
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
    "LANGGRAPH_CONFORMANCE_DRIVER_ID",
    "LANGGRAPH_CONFORMANCE_DRIVER_VERSION",
    "LangGraphConformanceDriver",
    "BUILTIN_CONFORMANCE_DRIVERS",
    "list_conformance_drivers",
    "get_conformance_driver",
    "run_adapter_conformance",
]
