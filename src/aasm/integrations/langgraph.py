from __future__ import annotations

"""Thin LangGraph adapter for the canonical AASM runtime.

The adapter intentionally does not own graph state, routing, or checkpoints.
LangGraph continues to execute the graph; AASM records durable authority,
obligations, evidence, effects, conflicts, and recovery underneath it.
"""

import inspect
from typing import Any, Callable, Mapping

from ._langgraph_binding import LangGraphBindingMixin
from ._langgraph_conflict import LangGraphConflictMixin
from ._langgraph_types import (
    LANGGRAPH_ADAPTER_ID, LANGGRAPH_ADAPTER_VERSION,
    _NODE_ENTERED, _NODE_FAILED, _NODE_SUCCEEDED, _ROUTE_RECORDED,
    LangGraphBinding, LangGraphNodePolicy, LangGraphRecoveryAction,
    LangGraphRecoveryResult, LangGraphRunKey, _command_projection,
    _configurable, _fingerprint, _json_safe, _preserve_node_metadata, _stable_id,
)


class LangGraphAdapter(LangGraphConflictMixin, LangGraphBindingMixin):
    """Translate LangGraph lifecycle signals into the canonical AASM runtime."""

    @staticmethod
    def _call_node(
        node: Callable[..., Any],
        state: Any,
        *,
        config: Mapping[str, Any] | None,
        runtime: Any | None,
        extra: Mapping[str, Any],
    ) -> Any:
        signature = inspect.signature(node)
        parameters = signature.parameters
        accepts_kwargs = any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values())
        kwargs = dict(extra)
        if "config" in parameters or accepts_kwargs:
            kwargs["config"] = config
        if "runtime" in parameters or accepts_kwargs:
            kwargs["runtime"] = runtime
        return node(state, **kwargs)

    def _invocation_identity(
        self,
        engine: Any,
        binding: LangGraphBinding,
        node_name: str,
        state: Any,
        config: Mapping[str, Any] | None,
    ) -> tuple[str, str]:
        configurable = _configurable(config)
        state_fingerprint = _fingerprint(state)
        invocation_id = _stable_id(
            "lgcall",
            binding.run_key.to_dict(),
            node_name,
            configurable.get("checkpoint_id"),
            configurable.get("checkpoint_ns"),
            state_fingerprint,
        )
        return invocation_id, state_fingerprint

    def _begin_node(
        self,
        engine: Any,
        binding: LangGraphBinding,
        node_name: str,
        policy: LangGraphNodePolicy,
        state: Any,
        config: Mapping[str, Any] | None,
    ) -> tuple[str, str]:
        invocation_id, state_fingerprint = self._invocation_identity(
            engine, binding, node_name, state, config
        )
        obligation_id = _stable_id("obligation", invocation_id)
        existing = engine.calculus_report()["obligations"].get(obligation_id)
        if existing is None:
            self.record_obligation(
                engine,
                obligation_id=obligation_id,
                statement=policy.statement or f"Execute LangGraph node {node_name}",
                required_evidence_types=policy.required_evidence_types,
                mandatory=policy.mandatory,
                persistent=policy.persistent,
                scope={
                    "node_name": node_name,
                    "invocation_id": invocation_id,
                    "binding_fingerprint": binding.run_key.fingerprint,
                },
            )
            engine.enable_obligation(obligation_id, reason="LangGraph node obligation enabled")
            engine.set_obligation_status(
                obligation_id,
                "IN_PROGRESS",
                reason="LangGraph node execution entered",
            )
        engine.emit(
            _NODE_ENTERED,
            engine.state_value,
            engine.state_value,
            f"LangGraph node {node_name} entered",
            data={
                "node_name": node_name,
                "invocation_id": invocation_id,
                "obligation_id": obligation_id,
                "state_fingerprint": state_fingerprint,
                "configurable": _json_safe(_configurable(config)),
            },
        )
        return invocation_id, obligation_id

    def _finish_node(
        self,
        engine: Any,
        binding: LangGraphBinding,
        node_name: str,
        invocation_id: str,
        obligation_id: str,
        policy: LangGraphNodePolicy,
        state: Any,
        output: Any,
    ) -> None:
        command = _command_projection(output)
        output_projection = _json_safe(output)
        output_fingerprint = _fingerprint(output_projection)
        evidence = self.record_evidence(
            engine,
            kind="observation",
            statement=f"LangGraph node {node_name} completed",
            source=f"langgraph:{node_name}",
            evidence_type="langgraph_node_output",
            evidence_id=_stable_id("evidence", invocation_id, "output"),
            metadata={
                "node_name": node_name,
                "invocation_id": invocation_id,
                "output_fingerprint": output_fingerprint,
                "output": output_projection,
            },
        )
        current = engine.calculus_report()["obligations"][obligation_id]
        if current.get("status") not in {"VERIFIED", "COMMITTED"}:
            engine.set_obligation_status(
                obligation_id,
                "VERIFYING",
                evidence_ids=[evidence.evidence_id],
                reason="LangGraph node output entered verification",
            )
            engine.set_obligation_status(
                obligation_id,
                "VERIFIED",
                evidence_ids=[evidence.evidence_id],
                reason="LangGraph node output evidence verified",
            )
            engine.set_obligation_status(
                obligation_id,
                "COMMITTED",
                evidence_ids=[evidence.evidence_id],
                reason="LangGraph node obligation committed",
            )
        if policy.evidence_mapper is not None:
            for index, raw in enumerate(policy.evidence_mapper(state, output) or []):
                payload = dict(raw)
                self.record_evidence(
                    engine,
                    kind=str(payload.pop("kind", "observation")),
                    statement=str(payload.pop("statement")),
                    source=str(payload.pop("source", f"langgraph:{node_name}")),
                    evidence_type=str(payload.pop("evidence_type", "langgraph_mapped")),
                    evidence_id=payload.pop("evidence_id", None),
                    metadata={"mapper_index": index, **dict(payload.pop("metadata", {}))},
                    confidence=payload.pop("confidence", 1.0),
                    **payload,
                )
        if policy.decision_mapper is not None:
            for raw in policy.decision_mapper(state, output) or []:
                payload = dict(raw)
                self.record_decision(engine, **payload)
        if command is not None and command.get("goto") not in (None, (), [], ""):
            engine.emit(
                _ROUTE_RECORDED,
                engine.state_value,
                engine.state_value,
                f"LangGraph node {node_name} returned dynamic route",
                data={
                    "node_name": node_name,
                    "invocation_id": invocation_id,
                    "goto": command.get("goto"),
                    "command_fingerprint": _fingerprint(command),
                },
            )
        engine.emit(
            _NODE_SUCCEEDED,
            engine.state_value,
            engine.state_value,
            f"LangGraph node {node_name} succeeded",
            evidence=[evidence.evidence_id],
            data={
                "node_name": node_name,
                "invocation_id": invocation_id,
                "obligation_id": obligation_id,
                "output_fingerprint": output_fingerprint,
                "command": command,
            },
        )

    def _fail_node(
        self,
        engine: Any,
        node_name: str,
        invocation_id: str,
        obligation_id: str,
        exc: BaseException,
    ) -> None:
        evidence = self.record_evidence(
            engine,
            kind="contradiction",
            statement=f"LangGraph node {node_name} failed: {type(exc).__name__}: {exc}",
            source=f"langgraph:{node_name}",
            evidence_type="langgraph_node_failure",
            evidence_id=_stable_id("evidence", invocation_id, "failure"),
            metadata={
                "node_name": node_name,
                "invocation_id": invocation_id,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            },
        )
        current = engine.calculus_report()["obligations"][obligation_id]
        if current.get("status") not in {
            "BLOCKED",
            "REJECTED",
            "SUPERSEDED",
            "IMPOSSIBLE",
        }:
            engine.set_obligation_status(
                obligation_id,
                "BLOCKED",
                evidence_ids=[evidence.evidence_id],
                reason="LangGraph node failure blocked its AASM obligation",
            )
        engine.emit(
            _NODE_FAILED,
            engine.state_value,
            engine.state_value,
            f"LangGraph node {node_name} failed",
            evidence=[evidence.evidence_id],
            data={
                "node_name": node_name,
                "invocation_id": invocation_id,
                "obligation_id": obligation_id,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            },
        )

    def wrap_node(
        self,
        node_name: str,
        node: Callable[..., Any],
        *,
        policy: LangGraphNodePolicy | None = None,
        goal: str = "LangGraph run governed by AASM",
    ) -> Callable[..., Any]:
        """Wrap a node without changing its state update or Command result."""

        selected_policy = policy or LangGraphNodePolicy()
        if inspect.iscoroutinefunction(node):

            async def async_wrapped(
                state: Any,
                config=None,
                runtime: Any | None = None,
                **kwargs: Any,
            ) -> Any:
                engine, binding = self.bind(config, goal=goal)
                invocation_id, obligation_id = self._begin_node(
                    engine, binding, node_name, selected_policy, state, config
                )
                try:
                    result = self._call_node(
                        node, state, config=config, runtime=runtime, extra=kwargs
                    )
                    if inspect.isawaitable(result):
                        result = await result
                except BaseException as exc:
                    self._fail_node(engine, node_name, invocation_id, obligation_id, exc)
                    raise
                self._finish_node(
                    engine,
                    binding,
                    node_name,
                    invocation_id,
                    obligation_id,
                    selected_policy,
                    state,
                    result,
                )
                return result

            return _preserve_node_metadata(async_wrapped, node)

        def wrapped(
            state: Any,
            config=None,
            runtime: Any | None = None,
            **kwargs: Any,
        ) -> Any:
            engine, binding = self.bind(config, goal=goal)
            invocation_id, obligation_id = self._begin_node(
                engine, binding, node_name, selected_policy, state, config
            )
            try:
                result = self._call_node(
                    node, state, config=config, runtime=runtime, extra=kwargs
                )
                if inspect.isawaitable(result):
                    raise TypeError(
                        "synchronous LangGraph node returned an awaitable; define the node with async def"
                    )
            except BaseException as exc:
                self._fail_node(engine, node_name, invocation_id, obligation_id, exc)
                raise
            self._finish_node(
                engine,
                binding,
                node_name,
                invocation_id,
                obligation_id,
                selected_policy,
                state,
                result,
            )
            return result

        return _preserve_node_metadata(wrapped, node)


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
