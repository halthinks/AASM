from __future__ import annotations

"""Types and deterministic projections for the thin LangGraph adapter."""

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
import hashlib
import inspect
import json
from typing import Any, Awaitable, Callable, Mapping, MutableMapping, Sequence

from ..calculus import ConflictRecord, DecisionRecord, ExplanationRecord, ObligationRecord
from ..effects import EffectRecord, EffectSpec
from ..evidence import EvidenceRecord
from ..model import ProblemSpec
from ..persistence import MemoryStore


LANGGRAPH_ADAPTER_ID = "aasm.langgraph.v1"
LANGGRAPH_ADAPTER_VERSION = "0.1.0"
_BIND_EVENT = "langgraph_run_bound"
_NODE_ENTERED = "langgraph_node_entered"
_NODE_SUCCEEDED = "langgraph_node_succeeded"
_NODE_FAILED = "langgraph_node_failed"
_ROUTE_RECORDED = "langgraph_route_recorded"
_RECOVERY_RECORDED = "langgraph_recovery_recorded"
_EFFECT_AUTHORIZED = "langgraph_effect_authorized"


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    """Return a deterministic JSON-safe representation without executing code."""

    if depth > 6:
        return {"type": type(value).__name__, "repr": repr(value)[:500]}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return {"type": "bytes", "sha256": hashlib.sha256(value).hexdigest(), "bytes": len(value)}
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe(item, depth=depth + 1)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_json_safe(item, depth=depth + 1) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_json_safe(item, depth=depth + 1) for item in value), key=repr)
    if is_dataclass(value):
        return _json_safe(asdict(value), depth=depth + 1)
    if hasattr(value, "model_dump") and callable(value.model_dump):
        try:
            return _json_safe(value.model_dump(mode="json"), depth=depth + 1)
        except Exception:
            pass
    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            return _json_safe(value.to_dict(), depth=depth + 1)
        except Exception:
            pass
    command = _command_projection(value)
    if command is not None:
        return command
    return {"type": type(value).__name__, "repr": repr(value)[:1000]}


def _canonical(value: Any) -> str:
    return json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _stable_id(prefix: str, *parts: Any, length: int = 24) -> str:
    digest = _fingerprint(list(parts))[:length]
    return f"{prefix}_{digest}"


def _command_projection(value: Any) -> dict[str, Any] | None:
    """Project a LangGraph Command without importing LangGraph."""

    if type(value).__name__ != "Command":
        return None
    keys = ("graph", "update", "resume", "goto")
    if not any(hasattr(value, key) for key in keys):
        return None
    return {
        "type": "Command",
        **{key: _json_safe(getattr(value, key, None), depth=1) for key in keys},
    }


def _configurable(config: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if config is None:
        return {}
    raw = config.get("configurable", {})
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise TypeError("LangGraph config['configurable'] must be a mapping")
    return raw


def _preserve_node_metadata(wrapper: Callable[..., Any], node: Callable[..., Any]) -> Callable[..., Any]:
    """Preserve human-facing metadata without hiding the adapter signature.

    LangGraph decides whether to inject ``config`` and ``runtime`` by inspecting
    the callable signature. ``functools.wraps`` installs ``__wrapped__`` and
    would make inspection see the original node instead of the adapter hook.
    """

    for attribute in ("__name__", "__qualname__", "__doc__", "__module__"):
        if hasattr(node, attribute):
            setattr(wrapper, attribute, getattr(node, attribute))
    setattr(wrapper, "__aasm_wrapped_node__", node)
    return wrapper


@dataclass(frozen=True)
class LangGraphRunKey:
    namespace: str
    thread_id: str
    run_id: str | None = None
    binding_scope: str = "THREAD"

    def __post_init__(self) -> None:
        scope = self.binding_scope.upper()
        object.__setattr__(self, "binding_scope", scope)
        if not self.namespace.strip():
            raise ValueError("namespace is required")
        if not self.thread_id.strip():
            raise ValueError("LangGraph config requires configurable.thread_id")
        if scope not in {"THREAD", "RUN"}:
            raise ValueError("binding_scope must be THREAD or RUN")
        if scope == "RUN" and not self.run_id:
            raise ValueError("RUN binding_scope requires a run_id")

    @classmethod
    def from_config(
        cls,
        config: Mapping[str, Any] | None,
        *,
        namespace: str,
        binding_scope: str = "THREAD",
        run_id: str | None = None,
    ) -> "LangGraphRunKey":
        configurable = _configurable(config)
        thread_id = configurable.get("thread_id")
        selected_run_id = run_id
        if selected_run_id is None:
            selected_run_id = configurable.get("run_id")
        if selected_run_id is None and config is not None:
            selected_run_id = config.get("run_id")
        return cls(
            namespace=str(namespace),
            thread_id=str(thread_id or ""),
            run_id=None if selected_run_id is None else str(selected_run_id),
            binding_scope=binding_scope,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.to_dict())

    @property
    def machine_id(self) -> str:
        identity: dict[str, Any] = {
            "adapter_id": LANGGRAPH_ADAPTER_ID,
            "namespace": self.namespace,
            "thread_id": self.thread_id,
            "binding_scope": self.binding_scope,
        }
        if self.binding_scope == "RUN":
            identity["run_id"] = self.run_id
        return "lg_" + _fingerprint(identity)[:28]


@dataclass(frozen=True)
class LangGraphBinding:
    machine_id: str
    run_key: LangGraphRunKey
    created: bool
    source: str = "configurable.thread_id"

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": LANGGRAPH_ADAPTER_ID,
            "adapter_version": LANGGRAPH_ADAPTER_VERSION,
            "machine_id": self.machine_id,
            "created": self.created,
            "source": self.source,
            "run_key": self.run_key.to_dict(),
            "binding_fingerprint": self.run_key.fingerprint,
            "langgraph_checkpoint_is_authority": False,
            "aasm_event_history_is_authority": True,
        }


class LangGraphRecoveryAction(str, Enum):
    CONTINUE = "CONTINUE"
    REPAIR = "REPAIR"
    BACKJUMP = "BACKJUMP"
    PAUSE = "PAUSE"
    RESTART = "RESTART"
    FORK = "FORK"


@dataclass
class LangGraphRecoveryResult:
    action: str
    machine_id: str
    reason: str
    conflict_id: str | None = None
    target: str | None = None
    update: dict[str, Any] = field(default_factory=dict)
    fork_machine_id: str | None = None
    aasm_result: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.action = LangGraphRecoveryAction(self.action).value
        if not self.reason:
            raise ValueError("recovery reason is required")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_langgraph_command(self) -> Any:
        """Convert a directive to a real LangGraph Command when appropriate.

        PAUSE is intentionally not converted: LangGraph pause/resume must use
        its own interrupt mechanism in node code, while AASM records why the
        pause is authoritative.
        """

        if self.action == LangGraphRecoveryAction.PAUSE.value:
            raise ValueError(
                "PAUSE must be implemented with LangGraph interrupt(); "
                "AASM records the durable reason but does not replace checkpoint control"
            )
        try:
            from langgraph.types import Command
        except ImportError as exc:  # pragma: no cover - exercised in optional job
            raise RuntimeError(
                "LangGraph is not installed; install aasm-runtime[langgraph]"
            ) from exc
        goto = self.target or ()
        return Command(update=dict(self.update), goto=goto)


@dataclass
class LangGraphNodePolicy:
    statement: str | None = None
    mandatory: bool = True
    persistent: bool = True
    required_evidence_types: list[str] = field(default_factory=lambda: ["langgraph_node_output"])
    decision_mapper: Callable[[Any, Any], Sequence[Mapping[str, Any]]] | None = None
    evidence_mapper: Callable[[Any, Any], Sequence[Mapping[str, Any]]] | None = None

