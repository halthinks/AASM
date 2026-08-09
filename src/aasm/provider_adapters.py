from __future__ import annotations

from dataclasses import dataclass
import json
import subprocess
from typing import Any, Callable

from .provisioning import ProvisioningAction, ProvisioningRequest


CommandRunner = Callable[[list[str]], tuple[int, str, str]]


def subprocess_runner(argv: list[str]) -> tuple[int, str, str]:
    completed = subprocess.run(argv, capture_output=True, text=True, check=False)
    return completed.returncode, completed.stdout, completed.stderr


@dataclass
class CommandProvisioningAdapter:
    """Explicit command adapter for already-authorized provisioning effects.

    Command construction is supplied by the caller; AASM never executes a shell
    string and never adds implicit credentials/network access.
    """

    builder: Callable[[ProvisioningRequest], list[str]]
    runner: CommandRunner = subprocess_runner

    def apply(self, request: ProvisioningRequest, idempotency_key: str) -> dict[str, Any]:
        argv = list(self.builder(request))
        if not argv or any(not isinstance(value, str) or not value for value in argv):
            raise ValueError("provisioning command builder returned invalid argv")
        code, stdout, stderr = self.runner(argv)
        if code != 0:
            raise RuntimeError(
                f"provisioning command failed ({code}): {stderr.strip() or stdout.strip()}"
            )
        return {
            "argv": argv,
            "exit_code": code,
            "stdout": stdout[-20000:],
            "stderr": stderr[-20000:],
            "idempotency_key": idempotency_key,
        }


@dataclass
class KubernetesScaleAdapter:
    """Scale one Kubernetes workload through kubectl.

    The request metadata must name `workload` and may set `kind` (deployment by
    default) and `namespace`. PROVISION/DRAIN are interpreted as desired replica
    deltas relative to the current replica count read from the API. The adapter
    is only invoked after the enclosing AASM effect is authorized.

    Replica scaling cannot prove which logical AASM worker was terminated. A
    DRAIN result therefore declares `drain_scope=replica-count` and does not
    claim targeted logical worker IDs.
    """

    kubectl: str = "kubectl"
    runner: CommandRunner = subprocess_runner

    def _base(self, request: ProvisioningRequest):
        metadata = request.metadata or {}
        workload = str(metadata.get("workload") or "").strip()
        if not workload:
            raise ValueError("Kubernetes provisioning requires metadata.workload")
        kind = str(metadata.get("kind") or "deployment").strip()
        namespace = str(metadata.get("namespace") or "default").strip()
        return kind, workload, namespace

    def _current_replicas(self, kind: str, workload: str, namespace: str) -> int:
        argv = [self.kubectl, "-n", namespace, "get", kind, workload, "-o", "json"]
        code, stdout, stderr = self.runner(argv)
        if code != 0:
            raise RuntimeError(
                f"kubectl get failed ({code}): {stderr.strip() or stdout.strip()}"
            )
        payload = json.loads(stdout or "{}")
        return int(((payload.get("spec") or {}).get("replicas")) or 0)

    def apply(self, request: ProvisioningRequest, idempotency_key: str) -> dict[str, Any]:
        kind, workload, namespace = self._base(request)
        current = self._current_replicas(kind, workload, namespace)
        if request.action == ProvisioningAction.PROVISION:
            desired = current + request.count
        elif request.action == ProvisioningAction.DRAIN:
            desired = max(0, current - request.count)
        else:
            raise ValueError(
                f"Unsupported Kubernetes provisioning action: {request.action}"
            )
        argv = [
            self.kubectl,
            "-n",
            namespace,
            "scale",
            kind,
            workload,
            f"--replicas={desired}",
        ]
        code, stdout, stderr = self.runner(argv)
        if code != 0:
            raise RuntimeError(
                f"kubectl scale failed ({code}): {stderr.strip() or stdout.strip()}"
            )
        return {
            "kind": kind,
            "workload": workload,
            "namespace": namespace,
            "previous_replicas": current,
            "desired_replicas": desired,
            "drain_scope": (
                "replica-count"
                if request.action == ProvisioningAction.DRAIN
                else None
            ),
            "stdout": stdout[-20000:],
            "stderr": stderr[-20000:],
            "idempotency_key": idempotency_key,
        }
