from __future__ import annotations

from dataclasses import dataclass
import hashlib
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Sequence

from .typed_protocol import _sha256_text
from .formal_models import (
    FormalVerificationPolicy, FormalVerificationRequest, FormalVerificationResult,
    SolverIdentity, canonicalize_solver_status, parse_smt_status, parse_vampire_status,
)


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str
    elapsed_ms: int


Runner = Callable[[Sequence[str], str, int, str], ProcessResult]


def _default_runner(argv: Sequence[str], stdin_text: str, timeout_ms: int, mode: str) -> ProcessResult:
    start = time.monotonic()
    if mode == "file":
        with tempfile.TemporaryDirectory(prefix="aasm-formal-") as directory:
            source = Path(directory) / "Main.lean"
            source.write_text(stdin_text, encoding="utf-8")
            try:
                completed = subprocess.run([*argv, str(source)], text=True, capture_output=True, timeout=timeout_ms / 1000.0, check=False)
            except subprocess.TimeoutExpired as exc:
                return ProcessResult(124, exc.stdout or "", exc.stderr or "", int((time.monotonic() - start) * 1000))
    else:
        try:
            completed = subprocess.run(list(argv), input=stdin_text, text=True, capture_output=True, timeout=timeout_ms / 1000.0, check=False)
        except subprocess.TimeoutExpired as exc:
            return ProcessResult(124, exc.stdout or "", exc.stderr or "", int((time.monotonic() - start) * 1000))
    return ProcessResult(completed.returncode, completed.stdout or "", completed.stderr or "", int((time.monotonic() - start) * 1000))


@dataclass
class ExecutableFormalWorker:
    provider_id: str
    executable: str
    version: str = "unknown"
    container_digest: str = ""
    extra_args: tuple[str, ...] = ()
    runner: Runner = _default_runner

    def _argv_and_mode(self, request: FormalVerificationRequest) -> tuple[tuple[str, ...], str]:
        provider = self.provider_id.lower()
        if provider == "z3":
            if request.formal_statement.logic != "smtlib2": raise ValueError("Z3 worker requires smtlib2")
            return (self.executable, "-in", "-smt2", *self.extra_args), "stdin"
        if provider == "cvc5":
            if request.formal_statement.logic != "smtlib2": raise ValueError("cvc5 worker requires smtlib2")
            return (self.executable, "--lang=smt2", *self.extra_args), "stdin"
        if provider == "vampire":
            if request.formal_statement.logic != "tptp": raise ValueError("Vampire worker requires tptp")
            return (self.executable, "--input_syntax", "tptp", *self.extra_args), "stdin"
        if provider in {"lean", "lean4"}:
            if request.formal_statement.logic != "lean4": raise ValueError("Lean worker requires lean4")
            return (self.executable, *self.extra_args), "file"
        raise ValueError(f"unsupported formal provider: {self.provider_id}")

    def _binary_sha(self) -> str:
        resolved = shutil.which(self.executable)
        if not resolved: return ""
        try: return hashlib.sha256(Path(resolved).read_bytes()).hexdigest()
        except OSError: return ""

    def run(self, request: FormalVerificationRequest) -> FormalVerificationResult:
        argv, mode = self._argv_and_mode(request)
        process = self.runner(argv, request.formal_statement.canonical_source, int(request.timeout_ms), mode)
        stdout, stderr = process.stdout or "", process.stderr or ""
        raw_hash = _sha256_text(stdout + "\n--stderr--\n" + stderr)
        if process.returncode == 124:
            raw_status, canonical = "timeout", "TIMEOUT"
        elif self.provider_id.lower() == "vampire":
            raw_status = parse_vampire_status(stdout + "\n" + stderr); canonical = canonicalize_solver_status(request.formal_statement.query_mode, "vampire", raw_status, returncode=process.returncode)
        elif self.provider_id.lower() in {"z3", "cvc5"}:
            raw_status = parse_smt_status(stdout); canonical = canonicalize_solver_status(request.formal_statement.query_mode, self.provider_id, raw_status, returncode=process.returncode)
        else:
            raw_status = "Accepted" if process.returncode == 0 else "Rejected"; canonical = canonicalize_solver_status(request.formal_statement.query_mode, "lean4", raw_status, returncode=process.returncode)
        if process.returncode not in {0, 124} and self.provider_id.lower() not in {"lean", "lean4"}: canonical = "ERROR"
        strength = "TRUSTED_KERNEL" if self.provider_id.lower() in {"lean", "lean4"} and canonical == "PROVED" else "SOLVER_VERDICT"
        identity = SolverIdentity(self.provider_id, self.version, self._binary_sha(), self.container_digest, tuple(argv))
        return FormalVerificationResult(request.request_id, request.fingerprint, request.formal_statement.fingerprint, canonical, identity, raw_status, process.elapsed_ms, strength, diagnostics=tuple(line for line in stderr.splitlines() if line.strip()), raw_output_sha256=raw_hash)


def aggregate_formal_results(policy: FormalVerificationPolicy, results: Sequence[FormalVerificationResult]) -> dict[str, Any]:
    if not results: return {"status": "INCONCLUSIVE", "reason": "no_results", "verification_strength": None}
    if len({r.request_id for r in results}) != 1 or len({r.request_fingerprint for r in results}) != 1 or len({r.formal_statement_fingerprint for r in results}) != 1:
        raise ValueError("formal result aggregation requires one exact request and formal statement")
    conclusive = [r for r in results if r.canonical_status in {"PROVED", "COUNTERMODEL", "DISPROVED", "SAT", "UNSAT"}]
    if policy.solver_identity_required:
        unidentified = [r.result_id for r in conclusive if r.solver.version in {"", "unknown"} or not (r.solver.binary_sha256 or r.solver.container_digest)]
        if unidentified: return {"status": "INCONCLUSIVE", "reason": "solver_identity_required", "verification_strength": None, "unidentified_result_ids": sorted(unidentified)}
    providers, statuses = {r.solver.solver_id for r in conclusive}, {r.canonical_status for r in conclusive}
    if len(statuses) > 1: return {"status": "INCONCLUSIVE", "reason": "solver_disagreement", "verification_strength": None, "disagreement_policy": policy.disagreement_policy, "statuses": sorted(statuses)}
    if len(providers) < policy.required_independent_results: return {"status": "INCONCLUSIVE", "reason": "insufficient_independent_results", "verification_strength": None}
    if policy.certificate_required and not any(r.certificate_checked for r in conclusive): return {"status": "INCONCLUSIVE", "reason": "certificate_required", "verification_strength": None}
    if policy.trusted_kernel_required and not any(r.verification_strength == "TRUSTED_KERNEL" for r in conclusive): return {"status": "INCONCLUSIVE", "reason": "trusted_kernel_required", "verification_strength": None}
    if not conclusive: return {"status": "INCONCLUSIVE", "reason": "no_conclusive_result", "verification_strength": None}
    if any(r.verification_strength == "TRUSTED_KERNEL" for r in conclusive): strength = "TRUSTED_KERNEL"
    elif any(r.certificate_checked for r in conclusive): strength = "CHECKED_CERTIFICATE"
    elif len(providers) >= 2: strength = "MULTI_SOLVER_AGREEMENT"
    else: strength = conclusive[0].verification_strength
    return {"status": conclusive[0].canonical_status, "reason": "policy_satisfied", "verification_strength": strength, "providers": sorted(providers), "result_ids": sorted(r.result_id for r in conclusive), "solver_voting": "NOT_USED"}


__all__ = ["ProcessResult", "ExecutableFormalWorker", "aggregate_formal_results"]
