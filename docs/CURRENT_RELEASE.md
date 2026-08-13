# AASM v0.36.0 — Semantic Compiler SDK

v0.36.0 adds deterministic compiler interfaces over the v0.35 semantic problem model.

## Contracts

```text
aasm.semantic.source.v1   / 0.1.0
aasm.semantic.compiler.v1 / 0.1.0
aasm.semantic.problem.v1  / 0.1.0
```

## Compiler stages

```text
PARSE → RESOLVE → NORMALIZE → TYPE_CHECK → VALIDATE → FINGERPRINT → INSTANTIATE
```

## Delivered

- `DomainCompiler` and `InstanceCompiler` protocols;
- `RawProblemInput`, `EnvironmentSnapshot`, `CompilerDiagnostic`, and `CompileResult`;
- deterministic source normalization and instance-ID derivation;
- source name, JSON pointer, line, column, and UTF-8 byte-offset diagnostics;
- explicit missing input and capability reporting;
- deterministic compile audit trail;
- content-addressed cache with collision rejection;
- compiler declaration fixed to `PROPOSAL_ONLY`;
- admission boundary fixed to `AASM_EVENT_REDUCER_ONLY`;
- compile-and-admit through ordinary semantic Evidence events;
- compiler conformance with determinism, cache, diagnostics, authority, and event-admission checks;
- CLI compile, problem-check, conformance, contract, and compile-admit surfaces;
- bounded compiler-admission invariants in the trace TLC/SPIN model.

```text
package/runtime: 0.36.0
adoption:         aasm.adoption.v1 / 0.12.0
remote:           aasm.remote.v1 / 0.19.0
next:             v0.37.0 Reasoning Artifacts and Semantic Dependency Graph
```
