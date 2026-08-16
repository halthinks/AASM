from __future__ import annotations

from .effects import EffectStatus
from .external_machine import MachineStateObservation
from .external_machine_transition import MachineTransitionIntent


class MachinePostconditionExecutionCorrelationMixin:
    """PR-2C guard: terminal effect semantics first, then exact execution correlation."""

    def verify_machine_transition_postconditions(
        self,
        transition_id: str,
        *,
        achieved_state_claim_ids,
        machine_observation_ids,
        verifier_principal_id: str,
        at_time: float = 0.0,
        metadata=None,
        reason: str = "machine transition postconditions verified",
    ):
        transition_row = self.machine_transition_report(transition_id)
        transition = MachineTransitionIntent.from_dict(transition_row["transition"])
        effect = self.store.load_effect(self.snapshot.machine_id, transition.effect_id)
        if effect.status == EffectStatus.UNKNOWN.value:
            raise ValueError(
                "machine transition effect is UNKNOWN; use existing effect reconciliation before postcondition verification"
            )
        if effect.status != EffectStatus.SUCCEEDED.value:
            raise ValueError(
                f"machine transition effect must be SUCCEEDED before postcondition verification, got {effect.status}"
            )
        execution_id = str(effect.execution_id or "").strip()
        if not execution_id:
            raise ValueError(
                "SUCCEEDED machine transition effect has no execution_id; postcondition observation cannot be correlated"
            )
        observation_ids = tuple(
            sorted({str(value).strip() for value in machine_observation_ids if str(value).strip()})
        )
        if not observation_ids:
            raise ValueError("postcondition verification requires at least one machine state observation")
        for observation_id in observation_ids:
            row = self.machine_state_observation_report(observation_id)
            observation = MachineStateObservation.from_dict(row["observation"])
            if observation.correlation_id != execution_id:
                raise ValueError(
                    "postcondition machine observation correlation_id must equal existing effect execution_id"
                )
        return super().verify_machine_transition_postconditions(
            transition_id,
            achieved_state_claim_ids=achieved_state_claim_ids,
            machine_observation_ids=observation_ids,
            verifier_principal_id=verifier_principal_id,
            at_time=at_time,
            metadata=metadata,
            reason=reason,
        )


__all__ = ["MachinePostconditionExecutionCorrelationMixin"]
