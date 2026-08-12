"""Optional framework integration adapters.

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

__all__ = [
    "LANGGRAPH_ADAPTER_ID",
    "LANGGRAPH_ADAPTER_VERSION",
    "LangGraphAdapter",
    "LangGraphBinding",
    "LangGraphNodePolicy",
    "LangGraphRecoveryAction",
    "LangGraphRecoveryResult",
    "LangGraphRunKey",
]
