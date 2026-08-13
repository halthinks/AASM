from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .evidence import EvidenceRecord
from .resources import ResourceRecord
from .workers import WorkerRecord
from .typed_capabilities import CAPABILITY_ABI_CONTRACT_ID, CapabilityContract, CapabilityProvider, capability_abi_contract, default_formal_capability_contracts, default_formal_providers, formal_verification_contract, pattern_document
from ._runtime_v39_typed import _records, _document


class CapabilityABIRuntimeMixin:
    def capability_report(self, capability_id: str | None = None) -> dict[str, Any]:
        contracts, providers = {}, {}
        for row in _records(self.snapshot, "capability_contract"):
            contract = CapabilityContract.from_dict(_document(row)); contracts[contract.capability_id] = {"contract": contract.to_dict(), "evidence_id": row["evidence_id"], "authority_id": (row.get("metadata") or {}).get("authority_id"), "authority_class": (row.get("metadata") or {}).get("authority_class")}
        for row in _records(self.snapshot, "capability_provider"):
            provider = CapabilityProvider.from_dict(_document(row)); providers[provider.provider_id] = {"provider": provider.to_dict(), "evidence_id": row["evidence_id"], "authority_id": (row.get("metadata") or {}).get("authority_id"), "authority_class": (row.get("metadata") or {}).get("authority_class")}
        if capability_id is not None:
            if capability_id not in contracts: raise KeyError(capability_id)
            return {"contract": capability_abi_contract(), "capability": deepcopy(contracts[capability_id]), "providers": {k: v for k, v in providers.items() if v["provider"]["capability_id"] == capability_id}}
        return {"contract": capability_abi_contract(), "capabilities": contracts, "providers": providers}

    def _validate_provider_contract(self, provider: CapabilityProvider) -> CapabilityContract:
        contract = CapabilityContract.from_dict(self.capability_report(provider.capability_id)["capability"]["contract"])
        if contract.version != provider.capability_version: raise ValueError("capability provider version does not match admitted capability contract")
        if not set(provider.supported_logics).issubset(set(contract.supported_logics)): raise ValueError("provider advertises logic not supported by capability")
        if not set(provider.query_modes).issubset(set(contract.query_modes)): raise ValueError("provider advertises query mode not supported by capability")
        return contract

    def register_capability_contract(self, contract: CapabilityContract | Mapping[str, Any], *, authority_id: str, authority_class: str, reason: str = "capability contract admitted") -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}: raise PermissionError("capability contract admission requires POLICY or CONTROLLER authority")
        if not authority_id: raise ValueError("authority_id is required")
        contract = contract if isinstance(contract, CapabilityContract) else CapabilityContract.from_dict(contract); existing = self.capability_report()["capabilities"]
        if contract.capability_id in existing:
            prior = CapabilityContract.from_dict(existing[contract.capability_id]["contract"])
            if prior.fingerprint != contract.fingerprint: raise ValueError(f"capability ID collision: {contract.capability_id}")
            return {"contract": capability_abi_contract(), **existing[contract.capability_id], "already_admitted": True}
        stored = self.add_evidence(EvidenceRecord(kind="capability_contract", statement=pattern_document(contract), source=CAPABILITY_ABI_CONTRACT_ID, metadata={"capability_record_type": "CONTRACT", "capability_abi_contract_id": CAPABILITY_ABI_CONTRACT_ID, "capability_id": contract.capability_id, "capability_version": contract.version, "capability_fingerprint": contract.fingerprint, "authority_id": authority_id, "authority_class": authority_class}), reason=reason)
        return {"contract": capability_abi_contract(), "capability": contract.to_dict(), "evidence_id": stored.evidence_id, "already_admitted": False}

    def register_capability_provider(self, provider: CapabilityProvider | Mapping[str, Any], *, authority_id: str, authority_class: str, reason: str = "capability provider admitted") -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}: raise PermissionError("capability provider admission requires POLICY or CONTROLLER authority")
        if not authority_id: raise ValueError("authority_id is required")
        provider = provider if isinstance(provider, CapabilityProvider) else CapabilityProvider.from_dict(provider)
        self._validate_provider_contract(provider)
        resource = next((row for row in self.list_resources() if row.get("resource_id") == provider.resource_id), None)
        if resource is None: raise KeyError(f"unknown capability resource: {provider.resource_id}")
        if not {provider.capability_token, provider.provider_token}.issubset(set(resource.get("capabilities", []))): raise ValueError("capability provider resource is missing capability/provider tokens")
        existing = self.capability_report()["providers"]
        if provider.provider_id in existing:
            prior = CapabilityProvider.from_dict(existing[provider.provider_id]["provider"])
            if prior.fingerprint != provider.fingerprint: raise ValueError(f"capability provider ID collision: {provider.provider_id}")
            return {"contract": capability_abi_contract(), **existing[provider.provider_id], "already_admitted": True}
        stored = self.add_evidence(EvidenceRecord(kind="capability_provider", statement=pattern_document(provider), source=CAPABILITY_ABI_CONTRACT_ID, metadata={"capability_record_type": "PROVIDER", "capability_abi_contract_id": CAPABILITY_ABI_CONTRACT_ID, "provider_id": provider.provider_id, "provider_fingerprint": provider.fingerprint, "capability_id": provider.capability_id, "resource_id": provider.resource_id, "authority_id": authority_id, "authority_class": authority_class}), reason=reason)
        return {"contract": capability_abi_contract(), "provider": provider.to_dict(), "evidence_id": stored.evidence_id, "already_admitted": False}

    def register_formal_resource(self, provider: CapabilityProvider | Mapping[str, Any], *, capacity: float = 1.0, reliability: float = 1.0, metadata: Mapping[str, Any] | None = None, reason: str = "formal verification resource registered") -> dict[str, Any]:
        provider = provider if isinstance(provider, CapabilityProvider) else CapabilityProvider.from_dict(provider)
        contract = self._validate_provider_contract(provider)
        if contract.capability_type != "VERIFIER": raise ValueError("formal provider runtime requires a VERIFIER capability")
        required_tokens = {provider.capability_token, provider.provider_token}
        existing = next((row for row in self.list_resources() if row.get("resource_id") == provider.resource_id), None)
        if existing is not None:
            if existing.get("kind") != "formal-verifier": raise ValueError("existing formal provider resource has incompatible kind")
            if not required_tokens.issubset(set(existing.get("capabilities", []))): raise ValueError("existing formal provider resource is missing capability/provider tokens")
            return existing
        return self.register_resource(ResourceRecord(resource_id=provider.resource_id, kind="formal-verifier", capabilities=sorted(required_tokens), capacity=capacity, reliability=reliability, metadata={"provider_id": provider.provider_id, "implementation": provider.implementation, **deepcopy(dict(metadata or {}))}), reason=reason)

    def formal_capability_blueprint(self) -> dict[str, Any]:
        return {"contract": capability_abi_contract(), "formal_verification": formal_verification_contract(), "capabilities": [row.to_dict() for row in default_formal_capability_contracts()], "providers": [row.to_dict() for row in default_formal_providers()], "registration": "EXPLICIT_POLICY_ADMISSION_REQUIRED", "execution": "EXISTING_RESOURCE_WORKER_LEASE_BOUNDARY"}

    def install_default_formal_capability_contracts(self, *, authority_id: str, authority_class: str, reason: str = "default formal capability contracts admitted") -> dict[str, Any]:
        return {"contract": capability_abi_contract(), "installed": [self.register_capability_contract(contract, authority_id=authority_id, authority_class=authority_class, reason=reason) for contract in default_formal_capability_contracts()]}

    def register_formal_provider_runtime(self, provider: CapabilityProvider | Mapping[str, Any], *, authority_id: str, authority_class: str, worker_id: str | None = None, capacity: float = 1.0, reliability: float = 1.0, heartbeat_timeout: float = 60.0, reason: str = "formal provider runtime admitted") -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}: raise PermissionError("formal provider runtime admission requires POLICY or CONTROLLER authority")
        if not authority_id: raise ValueError("authority_id is required")
        provider = provider if isinstance(provider, CapabilityProvider) else CapabilityProvider.from_dict(provider)
        contract = self._validate_provider_contract(provider)
        if contract.capability_type != "VERIFIER": raise ValueError("formal provider runtime requires a VERIFIER capability")
        worker_identity = worker_id or f"worker-{provider.provider_id}"
        existing_resource = next((row for row in self.list_resources() if row.get("resource_id") == provider.resource_id), None)
        if existing_resource is not None:
            required_tokens = {provider.capability_token, provider.provider_token}
            if existing_resource.get("kind") != "formal-verifier" or not required_tokens.issubset(set(existing_resource.get("capabilities", []))):
                raise ValueError("existing resource is incompatible with formal provider contract")
        existing_worker = next((row for row in self.list_workers() if row.get("worker_id") == worker_identity), None)
        if existing_worker is not None and existing_worker.get("resource_id") != provider.resource_id:
            raise ValueError("existing worker is bound to a different resource")
        existing_provider = self.capability_report()["providers"].get(provider.provider_id)
        if existing_provider is not None:
            prior = CapabilityProvider.from_dict(existing_provider["provider"])
            if prior.fingerprint != provider.fingerprint: raise ValueError(f"capability provider ID collision: {provider.provider_id}")
        resource = self.register_formal_resource(provider, capacity=capacity, reliability=reliability, reason=reason)
        worker = existing_worker
        if worker is None: worker = self.register_worker(WorkerRecord(worker_id=worker_identity, resource_id=provider.resource_id, heartbeat_timeout=heartbeat_timeout, metadata={"formal_provider_id": provider.provider_id}), reason=reason)
        admitted = self.register_capability_provider(provider, authority_id=authority_id, authority_class=authority_class, reason=reason)
        return {"contract": capability_abi_contract(), "resource": resource, "worker": worker, "provider": admitted}
