from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol
import re


class ArtifactBackend(Protocol):
    def put_text(self, namespace: str, name: str, text: str) -> str: ...
    def get_text(self, ref: str) -> str: ...


_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def _safe(value: str) -> str:
    value = _SAFE.sub("_", str(value)).strip("._")
    return value or "artifact"


class MemoryArtifactBackend:
    def __init__(self, name: str = "memory"):
        self.name = name
        self._data: dict[str, str] = {}

    def put_text(self, namespace: str, name: str, text: str) -> str:
        raw = str(text)
        digest = sha256(raw.encode("utf-8")).hexdigest()[:16]
        ref = f"artifact+memory://{_safe(namespace)}/{_safe(name)}-{digest}"
        self._data[ref] = raw
        return ref

    def get_text(self, ref: str) -> str:
        if ref not in self._data:
            raise KeyError(ref)
        return self._data[ref]


class LocalDirectoryArtifactBackend:
    """Stores text artifacts below one configured root and returns stable refs."""

    def __init__(self, root: str | Path, name: str = "local"):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.name = _safe(name)

    def put_text(self, namespace: str, name: str, text: str) -> str:
        raw = str(text)
        ns = _safe(namespace)
        stem = _safe(name)
        digest = sha256(raw.encode("utf-8")).hexdigest()[:16]
        directory = (self.root / ns).resolve()
        if self.root not in directory.parents and directory != self.root:
            raise ValueError("artifact namespace escaped configured root")
        directory.mkdir(parents=True, exist_ok=True)
        path = (directory / f"{stem}-{digest}.txt").resolve()
        if self.root not in path.parents:
            raise ValueError("artifact path escaped configured root")
        if not path.exists():
            path.write_text(raw, encoding="utf-8")
        return f"artifact+file://{self.name}/{ns}/{path.name}"

    def get_text(self, ref: str) -> str:
        prefix = f"artifact+file://{self.name}/"
        if not ref.startswith(prefix):
            raise ValueError(f"artifact ref is not owned by backend {self.name}")
        relative = ref[len(prefix):]
        parts = relative.split("/", 1)
        if len(parts) != 2:
            raise ValueError("invalid artifact ref")
        path = (self.root / _safe(parts[0]) / _safe(parts[1])).resolve()
        if self.root not in path.parents:
            raise ValueError("artifact path escaped configured root")
        return path.read_text(encoding="utf-8")


@dataclass
class ArtifactBackendBinding:
    name: str
    backend: ArtifactBackend


class ArtifactBackendRegistry:
    def __init__(self):
        self._backends: dict[str, ArtifactBackend] = {}

    def register(self, name: str, backend: ArtifactBackend):
        key = _safe(name)
        if key in self._backends:
            raise ValueError(f"Artifact backend already registered: {key}")
        self._backends[key] = backend
        return backend

    def get(self, name: str):
        key = _safe(name)
        if key not in self._backends:
            raise KeyError(f"Unknown artifact backend: {key}")
        return self._backends[key]

    def names(self):
        return sorted(self._backends)
