from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
from typing import Any, Callable

from .artifact_backends import ArtifactBackendRegistry, LocalDirectoryArtifactBackend, MemoryArtifactBackend
from .provider_adapters import KubernetesScaleAdapter, subprocess_runner
from .provisioning import ProvisioningAction, ProvisioningRegistry, ProvisioningRequest


SpawnFn = Callable[[list[str], str | None, dict[str, str]], int]
TerminateFn = Callable[[int, float], bool]
CommandRunner = Callable[[list[str]], tuple[int, str, str]]


def _default_spawn(argv: list[str], cwd: str | None, env: dict[str, str]) -> int:
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return int(process.pid)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _default_terminate(pid: int, timeout: float) -> bool:
    pid = int(pid)
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    except Exception:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return True
    deadline = time.time() + max(0.0, float(timeout))
    while time.time() < deadline:
        if not _pid_alive(pid):
            return True
        time.sleep(0.05)
    try:
        os.killpg(pid, signal.SIGKILL)
    except Exception:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            return True
    return not _pid_alive(pid)


def _validate_argv(argv: list[str]) -> list[str]:
    argv = list(argv)
    if not argv or any(not isinstance(value, str) or not value for value in argv):
        raise ValueError("supervisor argv must be a non-empty list of non-empty strings")
    return argv


def _render_argv(argv: list[str], values: dict[str, str]) -> list[str]:
    rendered = []
    for item in _validate_argv(argv):
        try:
            rendered.append(item.format_map(values))
        except KeyError as exc:
            raise ValueError(f"unknown supervisor argv placeholder: {exc.args[0]}") from exc
    return _validate_argv(rendered)


@dataclass
class LocalProcessSupervisorAdapter:
    """Starts and drains local worker processes without invoking a shell.

    The adapter persists a small PID/idempotency ledger. Request metadata may
    provide `argv`, `cwd`, `env`, and `worker_id_prefix`; argv supports the
    placeholders `{worker_id}`, `{resource_id}`, and `{request_id}`.
    """

    state_dir: str | Path
    default_argv: list[str] = field(default_factory=list)
    workspace_root: str | Path | None = None
    base_env: dict[str, str] = field(default_factory=dict)
    spawn: SpawnFn = _default_spawn
    terminate: TerminateFn = _default_terminate
    terminate_timeout: float = 10.0

    def __post_init__(self):
        self.state_dir = Path(self.state_dir).expanduser().resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_root = None if self.workspace_root is None else Path(self.workspace_root).expanduser().resolve()
        if self.workspace_root is not None:
            self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.default_argv = list(self.default_argv)
        self._lock = threading.RLock()
        self._state_path = self.state_dir / "local-process-supervisor.json"

    def _load(self):
        if not self._state_path.exists():
            return {"version": 1, "next_index": 0, "workers": {}, "idempotency": {}}
        payload = json.loads(self._state_path.read_text(encoding="utf-8"))
        payload.setdefault("version", 1)
        payload.setdefault("next_index", 0)
        payload.setdefault("workers", {})
        payload.setdefault("idempotency", {})
        return payload

    def _save(self, payload):
        temp = self._state_path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temp, self._state_path)

    def _cwd(self, value: str | None):
        if value is None:
            return str(self.workspace_root) if self.workspace_root is not None else None
        path = Path(value).expanduser().resolve()
        if self.workspace_root is not None and path != self.workspace_root and self.workspace_root not in path.parents:
            raise ValueError("local supervisor cwd escaped workspace_root")
        return str(path)

    def apply(self, request: ProvisioningRequest, idempotency_key: str) -> dict[str, Any]:
        with self._lock:
            state = self._load()
            existing = state["idempotency"].get(idempotency_key)
            if existing is not None:
                return deepcopy(existing)

            if request.action == ProvisioningAction.PROVISION:
                raw_argv = list((request.metadata or {}).get("argv") or self.default_argv)
                _validate_argv(raw_argv)
                prefix = str((request.metadata or {}).get("worker_id_prefix") or request.resource_id).strip()
                if not prefix:
                    raise ValueError("worker_id_prefix resolved to an empty string")
                cwd = self._cwd((request.metadata or {}).get("cwd"))
                explicit_env = dict(self.base_env)
                explicit_env.update({str(k): str(v) for k, v in ((request.metadata or {}).get("env") or {}).items()})
                created = []
                for _ in range(request.count):
                    state["next_index"] = int(state.get("next_index", 0)) + 1
                    worker_id = f"{prefix}-{state['next_index']:04d}"
                    values = {
                        "worker_id": worker_id,
                        "resource_id": request.resource_id,
                        "request_id": request.request_id,
                    }
                    argv = _render_argv(raw_argv, values)
                    env = dict(os.environ)
                    env.update(explicit_env)
                    env.update({
                        "AASM_WORKER_ID": worker_id,
                        "AASM_RESOURCE_ID": request.resource_id,
                        "AASM_PROVISION_REQUEST_ID": request.request_id,
                    })
                    pid = int(self.spawn(argv, cwd, env))
                    row = {
                        "worker_id": worker_id,
                        "resource_id": request.resource_id,
                        "pid": pid,
                        "argv": argv,
                        "cwd": cwd,
                        "request_id": request.request_id,
                        "started_at": time.time(),
                    }
                    state["workers"][worker_id] = row
                    created.append(row)
                result = {
                    "provider": request.provider,
                    "action": request.action,
                    "created": created,
                    "idempotency_key": idempotency_key,
                }
            elif request.action == ProvisioningAction.DRAIN:
                matching = [
                    row for row in state["workers"].values()
                    if row.get("resource_id") == request.resource_id
                ]
                by_id = {row["worker_id"]: row for row in matching}
                targets = list(request.target_worker_ids)
                if not targets:
                    targets = [row["worker_id"] for row in sorted(matching, key=lambda row: (row.get("started_at", 0), row["worker_id"]))[: request.count]]
                unknown = sorted(set(targets) - set(by_id))
                if unknown:
                    raise KeyError(f"unknown local supervisor worker IDs: {unknown}")
                drained = []
                for worker_id in targets[: request.count]:
                    row = by_id[worker_id]
                    stopped = bool(self.terminate(int(row["pid"]), float(self.terminate_timeout)))
                    drained.append({**row, "stopped": stopped})
                    if stopped:
                        state["workers"].pop(worker_id, None)
                result = {
                    "provider": request.provider,
                    "action": request.action,
                    "drained": drained,
                    "drained_worker_ids": [row["worker_id"] for row in drained if row.get("stopped")],
                    "drain_scope": "targeted",
                    "idempotency_key": idempotency_key,
                }
            else:
                raise ValueError(f"unsupported local supervisor action: {request.action}")

            state["idempotency"][idempotency_key] = deepcopy(result)
            self._save(state)
            return deepcopy(result)


@dataclass
class DockerComposeScaleAdapter:
    """Scales one Docker Compose service using explicit argv only."""

    docker: str = "docker"
    default_service: str | None = None
    default_compose_file: str | None = None
    default_project_directory: str | None = None
    default_project_name: str | None = None
    runner: CommandRunner = subprocess_runner

    def _base(self, request: ProvisioningRequest):
        metadata = request.metadata or {}
        service = str(metadata.get("service") or self.default_service or "").strip()
        if not service:
            raise ValueError("Docker Compose provisioning requires metadata.service or default_service")
        compose_file = metadata.get("compose_file") or self.default_compose_file
        project_directory = metadata.get("project_directory") or self.default_project_directory
        project_name = metadata.get("project_name") or self.default_project_name
        argv = [self.docker, "compose"]
        if compose_file:
            argv.extend(["-f", str(compose_file)])
        if project_directory:
            argv.extend(["--project-directory", str(project_directory)])
        if project_name:
            argv.extend(["-p", str(project_name)])
        return argv, service

    def apply(self, request: ProvisioningRequest, idempotency_key: str) -> dict[str, Any]:
        base, service = self._base(request)
        code, stdout, stderr = self.runner(base + ["ps", "-q", service])
        if code != 0:
            raise RuntimeError(f"docker compose ps failed ({code}): {stderr.strip() or stdout.strip()}")
        current = len([line for line in stdout.splitlines() if line.strip()])
        if request.action == ProvisioningAction.PROVISION:
            desired = current + request.count
        elif request.action == ProvisioningAction.DRAIN:
            desired = max(0, current - request.count)
        else:
            raise ValueError(f"unsupported Docker Compose action: {request.action}")
        argv = base + ["up", "-d", "--scale", f"{service}={desired}", service]
        code, stdout, stderr = self.runner(argv)
        if code != 0:
            raise RuntimeError(f"docker compose scale failed ({code}): {stderr.strip() or stdout.strip()}")
        return {
            "service": service,
            "previous_replicas": current,
            "desired_replicas": desired,
            "drain_scope": "replica-count" if request.action == ProvisioningAction.DRAIN else None,
            "argv": argv,
            "stdout": stdout[-20000:],
            "stderr": stderr[-20000:],
            "idempotency_key": idempotency_key,
        }


def load_runtime_registries(path: str | Path):
    """Build provider/artifact registries from a JSON operator configuration."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    provisioners = ProvisioningRegistry()
    artifacts = ArtifactBackendRegistry()

    for raw in payload.get("provisioners", []) or []:
        name = str(raw["name"])
        kind = str(raw["kind"])
        if kind == "kubernetes":
            adapter = KubernetesScaleAdapter(kubectl=str(raw.get("kubectl") or "kubectl"))
        elif kind == "local-process":
            adapter = LocalProcessSupervisorAdapter(
                state_dir=raw["state_dir"],
                default_argv=list(raw.get("argv") or []),
                workspace_root=raw.get("workspace_root"),
                base_env={str(k): str(v) for k, v in (raw.get("env") or {}).items()},
                terminate_timeout=float(raw.get("terminate_timeout", 10.0)),
            )
        elif kind == "docker-compose":
            adapter = DockerComposeScaleAdapter(
                docker=str(raw.get("docker") or "docker"),
                default_service=raw.get("service"),
                default_compose_file=raw.get("compose_file"),
                default_project_directory=raw.get("project_directory"),
                default_project_name=raw.get("project_name"),
            )
        else:
            raise ValueError(f"unknown provisioner kind: {kind}")
        provisioners.register(name, adapter)

    for raw in payload.get("artifacts", []) or []:
        name = str(raw["name"])
        kind = str(raw["kind"])
        if kind == "memory":
            backend = MemoryArtifactBackend(name)
        elif kind == "local-directory":
            backend = LocalDirectoryArtifactBackend(raw["root"], name)
        else:
            raise ValueError(f"unknown artifact backend kind: {kind}")
        artifacts.register(name, backend)

    return provisioners, artifacts
