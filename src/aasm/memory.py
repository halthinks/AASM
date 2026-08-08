from __future__ import annotations
from copy import deepcopy
import hashlib, json, time


class DPMemory:
    def __init__(self, initial=None):
        self._cache = deepcopy(initial or {})

    @staticmethod
    def signature(problem_class: str, inputs, constraints=None):
        raw = json.dumps(
            {"class": problem_class, "inputs": inputs, "constraints": constraints or {}},
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode()
        return hashlib.sha256(raw).hexdigest()

    def put(self, key, value, *, scope=None, proof=None, metadata=None, created_at=None):
        record = {
            "value": deepcopy(value),
            "scope": deepcopy(scope or {}),
            "proof": list(proof or []),
            "metadata": deepcopy(metadata or {}),
            "created_at": float(created_at if created_at is not None else time.time()),
            "valid": True,
        }
        self._cache[key] = record
        return deepcopy(record)

    def get_record(self, key):
        item = self._cache.get(key)
        return None if item is None else deepcopy(item)

    def get(self, key, *, scope=None):
        item = self._cache.get(key)
        if not item or not item.get("valid", False):
            return None
        required = item.get("scope", {})
        if scope is not None and any(scope.get(k) != v for k, v in required.items()):
            return None
        return deepcopy(item.get("value"))

    def invalidate(self, key, reason="", *, invalidated_at=None):
        if key not in self._cache:
            raise KeyError(key)
        self._cache[key]["valid"] = False
        self._cache[key]["invalidated_reason"] = reason
        self._cache[key]["invalidated_at"] = float(invalidated_at if invalidated_at is not None else time.time())
        return deepcopy(self._cache[key])

    def dump(self):
        return deepcopy(self._cache)
