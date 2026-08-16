from __future__ import annotations

from copy import deepcopy

from .physical_authority import AUTHORITY_LEASE_CONTRACT_ID, AuthorityLease
from .physical_preemption import AuthorityPreemption, AUTHORITY_PREEMPTION_CONTRACT_ID
from .semantic_result import semantic_fingerprint


_AUTHORITY_LEASE_REVOCATION_RECORD = "AUTHORITY_LEASE_REVOCATION"


class PhysicalPreemptionRecoveryGuardMixin:
    """Repair a preemption whose semantic Evidence was durable before lease-revocation Evidence."""

    def preempt_authority_lease(
        self,
        lease_id: str,
        *,
        authority_lease_fingerprint: str,
        authority_epoch: int,
        actor_principal_id: str,
        at_time: float,
        reason_code: str,
        evidence_ids=(),
        reason: str = "authority lease semantically preempted",
    ):
        control = self._require_valid_physical_control_fencing_projection()
        matching = None
        for row in control["preemptions"].values():
            document = row["preemption"]
            if document["authority_lease_id"] == str(lease_id):
                matching = row
                break
        if matching is not None:
            item = AuthorityPreemption.from_dict(matching["preemption"])
            exact = (
                item.authority_lease_fingerprint == str(authority_lease_fingerprint)
                and item.authority_epoch == int(authority_epoch)
                and item.preemptor_principal_id == actor_principal_id
                and item.preempted_at == float(at_time)
                and item.reason_code == str(reason_code)
            )
            if not exact:
                raise ValueError(f"authority lease already has a non-identical preemption: {lease_id}")
            physical = self._require_valid_physical_authority_projection()
            revocation_row = physical["revocations"].get(str(lease_id))
            repaired = False
            revocation_evidence_id = None
            if revocation_row is None:
                lease_row = physical["leases"].get(str(lease_id))
                if lease_row is None:
                    raise RuntimeError(f"preemption references missing authority lease during repair: {lease_id}")
                lease = AuthorityLease.from_dict(lease_row["lease"])
                if lease.fingerprint != item.authority_lease_fingerprint or lease.epoch != item.authority_epoch:
                    raise RuntimeError("durable preemption no longer matches authority lease during repair")
                document = {
                    "contract_id": AUTHORITY_LEASE_CONTRACT_ID,
                    "contract_version": lease.contract_version,
                    "lease_id": lease.lease_id,
                    "lease_fingerprint": lease.fingerprint,
                    "domain_id": lease.domain_id,
                    "epoch": lease.epoch,
                    "revocation_generation": lease.revocation_generation + 1,
                    "revoked_by_principal_id": item.preemptor_principal_id,
                    "revoked_at": item.preempted_at,
                    "reason": f"PREEMPTION:{item.reason_code}",
                }
                revocation_evidence_id = self._record_physical_authority_document(
                    record_type=_AUTHORITY_LEASE_REVOCATION_RECORD,
                    object_id=lease.lease_id,
                    object_fingerprint=semantic_fingerprint(document),
                    document=document,
                    source=AUTHORITY_PREEMPTION_CONTRACT_ID,
                    derived_from=tuple(sorted(set((
                        *map(str, evidence_ids),
                        str(matching["evidence_id"]),
                        str(lease_row["evidence_id"]),
                    )))),
                    reason="repaired canonical lease revocation after durable preemption",
                )
                repaired = True
            else:
                revocation_evidence_id = revocation_row["evidence_id"]
            return {
                **deepcopy(matching),
                "already_preempted": True,
                "lease_revocation_evidence_id": revocation_evidence_id,
                "lease_revocation_repaired": repaired,
                "effect_authority_granted": False,
                "required_next_epoch": item.required_next_epoch,
            }
        return super().preempt_authority_lease(
            lease_id,
            authority_lease_fingerprint=authority_lease_fingerprint,
            authority_epoch=authority_epoch,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
            reason_code=reason_code,
            evidence_ids=evidence_ids,
            reason=reason,
        )


__all__ = ["PhysicalPreemptionRecoveryGuardMixin"]
