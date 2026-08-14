from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text()
    if old not in text:
        raise SystemExit(f"{path}: replacement anchor missing: {old[:120]!r}")
    p.write_text(text.replace(old, new, 1))


# Release workflow: v0.50 requires the dedicated proof gate too.
replace_once(
    ".github/workflows/release.yml",
    "for context in aasm/ci-summary aasm/formal-assurance aasm/semantic-solver-rc; do",
    "for context in aasm/ci-summary aasm/formal-assurance aasm/semantic-solver-rc aasm/proof-claims; do",
)

# Release source contracts: promote v0.50 while preserving v0.49 as parent.
p = Path("scripts/check_release_contracts.py")
text = p.read_text()
text = text.replace('if version != "0.49.0":', 'if version != "0.50.0":', 1)
start = text.index("    # Current v0.49 public surface.")
end = text.index("    # Preserve v0.48 cross-run authority boundaries.")
current = '''    # Current v0.50 public surface and proof-carrying solver claim boundary.
    require(root / "src/aasm/__init__.py", ["public_v50"])
    require(root / "src/aasm/cli.py", ["cli_v50"])
    require(root / "src/aasm/public_v50.py", [
        '__version__ = "0.50.0"', '"contract_version": "0.26.0"', "runtime_v50",
        'PUBLIC_RELEASE_STABILITY = "ACTIVE_DEVELOPMENT"',
        "SOLVER_PROOF_CONTRACT_ID", "SOLVER_PROOF_CONTRACT_VERSION",
        '"solver_status_is_proof_grade"', '"proof_certified_requires_independent_checker"',
        '"certificate_authority"', '"truth_authority"',
    ])
    require(root / "src/aasm/runtime_v50.py", ["ProofClaimRuntimeMixin", "V49Engine"])
    require(root / "src/aasm/_runtime_v50_proof.py", [
        "solver_proof_contract_report", "solver_proof_claim_report", "certify_optimization_claim",
        '"authority": "EVIDENCE_ONLY"', 'snapshot.evidence.get("records", [])',
    ])
    require(root / "src/aasm/proof_claims.py", [
        'SOLVER_PROOF_CONTRACT_ID = "aasm.solver.proof-certificate.v1"',
        'SOLVER_PROOF_CONTRACT_VERSION = "0.1.0"',
        'SOLVER_PROOF_STABILITY = "EXPERIMENTAL_ENFORCED"',
        '"solver_status_is_proof_grade": False',
        '"proof_certified_requires_independent_checker": True',
        '"exact_problem_binding_required": True',
        '"exact_model_binding_required": True',
        '"exact_result_binding_required": True',
        '"certificate_authority": "EVIDENCE_ONLY"',
        '"truth_authority": "EXISTING_AASM_POLICY_ONLY"',
        "ProofUnsupportedError", "build_finite_domain_proof", "verify_finite_domain_proof",
        "finite-domain proof budget exceeded", "negative solver claim is false",
        "OPTIMAL solver claim is false", "proof checker must be independent of the solver provider",
    ])
    require(root / "src/aasm/proof_claim_conformance.py", [
        "run_solver_proof_conformance", "unsat_is_proof_certified", "optimal_is_proof_certified",
        "false_optimality_never_certifies", "positive_claim_does_not_fake_proof", "replay_exact",
    ])
    require(root / "src/aasm/cli_v50.py", ["solver-proof-contract", "solver-proof-conformance"])

    # v0.49 remains a frozen parent contract.
    require(root / "src/aasm/public_v49.py", [
        '__version__ = "0.49.0"', '"contract_version": "0.25.0"', "runtime_v49",
        "SEMANTIC_SOLVER_RC_CONTRACT_VERSION", "RELEASE_CANDIDATE",
        "THIN_V48_COMPOSITION_NO_NEW_KERNEL", "AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE",
        "AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS",
        "NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE",
    ])
    require(root / "src/aasm/runtime_v49.py", ["SemanticSolverRCRuntimeMixin", "V48Engine"])
    require(root / "src/aasm/_runtime_v49_rc.py", [
        "semantic_solver_rc_contract_report", "semantic_solver_rc_freeze_manifest", "semantic_solver_rc_upgrade_report",
        "semantic_solver_rc_cross_backend_report", "semantic_solver_rc_benchmark_report",
        "semantic_solver_rc_claim_audit", "semantic_solver_rc_certify",
    ])
    require(root / "src/aasm/semantic_solver_rc.py", [
        'SEMANTIC_SOLVER_RC_CONTRACT_ID = "aasm.semantic.solver.rc.v1"',
        'SEMANTIC_SOLVER_RC_CONTRACT_VERSION = "0.1.0"',
        'SEMANTIC_SOLVER_RC_STABILITY = "RELEASE_CANDIDATE"',
        '"runtime_extension": "THIN_V48_COMPOSITION_NO_NEW_KERNEL"',
        '"cross_backend_rule": "AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE"',
        '"native_solver_claim": "AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS"',
        '"claim_policy": "NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE"',
    ])
    require(root / "src/aasm/cli_v49.py", ["semantic-solver-rc-contract", "semantic-solver-rc-certify"])

'''
text = text[:start] + current + text[end:]

docs_start = text.index("    # Public release/docs claims must agree with the RC contract and actual gates.")
docs_end = text.index('    extras = project["optional-dependencies"]')
docs = '''    # Public release/docs claims must agree with v0.50 and the open-ended roadmap.
    require(root / "README.md", [
        "Current release — v0.50.0", "Proof-Carrying Solver Claims",
        "aasm.adoption.v1 / 0.26.0", "aasm.solver.proof-certificate.v1 / 0.1.0",
        "SOLVER STATUS != PROOF GRADE", "PROOF_CERTIFIED", "SOLVER_VALIDATED",
        "aasm/proof-claims", "v0.51", "Governed Solution Pools & Complete Enumeration",
        "Apache License, Version 2.0", "LICENSE_POLICY.md", "no presumed v1.0",
    ])
    require(root / "ROADMAP.md", [
        "v0.50.0 / Proof-Carrying Solver Claims", "v0.50.0 Proof-Carrying Solver Claims — Current",
        "v0.51.0", "Governed Solution Pools & Complete Enumeration",
        "v0.52.0", "Lexicographic Multi-Objective & Pareto Solving",
        "v0.53.0", "Durable Cross-Run Solver Learning",
        "v0.54.0", "Certified Cross-Solver Exchange & Deterministic Portfolio Racing",
        "v0.55.0", "Extended Mathematical IR", "v0.56.0", "Stress Corpus",
        "v0.57.0", "Semantic Solver RC2 / Contract Review", "No Presumed v1.0",
        "v0.50–v0.57 closes the currently identified semantic-solver gap cluster. It does not close AASM.",
    ])
    forbid(root / "README.md", ["v0.50 Post-RC Stabilization", "v0.50.0 — Post-RC Stabilization"])
    forbid(root / "ROADMAP.md", ["v0.50.0 — Post-RC Stabilization"])
    require(root / "CHANGELOG.md", ["[0.50.0]", "Proof-Carrying Solver Claims", "[0.49.0]", "Semantic Solver Release Candidate"])
    require(root / "docs/CURRENT_RELEASE.md", [
        "AASM v0.50.0", "runtime_v50", "0.26.0", "aasm.solver.proof-certificate.v1 / 0.1.0",
        "aasm/proof-claims", "Apache-2.0",
    ])
    require(root / "docs/PROOF_CARRYING_SOLVER_CLAIMS.md", [
        "SOLVER STATUS != PROOF GRADE", "UNSUPPORTED != FAIL", "PROOF_CERTIFIED",
        "aasm.checker.finite-domain-exhaustive.v1", "EXISTING_AASM_POLICY_ONLY",
    ])
    require(root / "docs/RELEASE_0.50.md", [
        "AASM v0.50.0", "0.26.0", "aasm.solver.proof-certificate.v1 / 0.1.0",
        "PROOF_CERTIFIED", "SOLVER_VALIDATED", "aasm/proof-claims", "Apache-2.0",
    ])
    require(root / "docs/RELEASE_0.49.md", ["AASM v0.49.0", "0.25.0", "RELEASE_CANDIDATE", "aasm/semantic-solver-rc", "Apache-2.0"])
    require(root / "docs/RELEASE_0.48.1.md", ["Project-Wide Apache-2.0 Policy Correction", "LICENSE_POLICY.md", "prior AASM versions", "MIT permissions remain valid"])
    require(root / "docs/RELEASE_0.47.1.md", ["Project-wide relicensing declaration", "also offered under Apache-2.0", "MIT-only", "LICENSE_POLICY.md"])

    require(root / "tests/test_v50_proof_claims.py", ["PROOF_CERTIFIED", "false_optimality_fails", "tampered_artifact", "replays"])
    require(root / "tests/test_v50_proof_claim_limits.py", ["UNSUPPORTED", "budget_exhaustion"])
    require(root / "tests/test_v50_public.py", ["0.50.0", "0.26.0", "solver-proof-contract", "solver-proof-conformance"])
    require(root / "tests/test_v49_rc.py", ["0.49.0", "0.25.0", "v41_memo_preserved", "v47_sii_policy_preserved", "v48_foreign_authority_still_not_inherited"])
    require(root / ".github/workflows/proof-claims.yml", ["Proof Claims", "test_v50_public.py", "solver-proof-conformance", "aasm/proof-claims"])
    require(root / ".github/workflows/rc.yml", ["Semantic Solver RC", "AASM_REQUIRE_RC_BACKENDS", "semantic-solver-rc-certify --real", "aasm/semantic-solver-rc"])
    require(root / ".github/workflows/release.yml", [
        "aasm/ci-summary", "aasm/formal-assurance", "aasm/semantic-solver-rc", "aasm/proof-claims",
        "Require exact main commit and all release gates",
    ])
    require(root / ".github/workflows/cross-run.yml", ["Cross-Run Knowledge", "test_v48_cross_run_knowledge.py", "test_v48_cross_run_sii_mapping.py"])
    require(root / ".github/workflows/optimization.yml", ["AASM_REQUIRE_OPTIMIZATION_BACKENDS", "AASM_REQUIRE_MODELING_BACKENDS", "AASM_REQUIRE_ADVANCED_BACKENDS", "AASM_REQUIRE_SII_BACKENDS", "test_v47_sii_real.py"])
    for name in ("solver-claim.schema.json", "solver-proof-artifact.schema.json", "solver-claim-certificate.schema.json"):
        require(root / "schemas" / name, ['"$schema"', "2020-12"])

'''
text = text[:docs_start] + docs + text[docs_end:]
text = text.replace('print("v0.49.0 release contracts: PASS")', 'print("v0.50.0 release contracts: PASS")', 1)
text = text.replace(
    'root / "docs/RELEASE_0.47.1.md", root / "docs/RELEASE_0.48.1.md", root / "docs/RELEASE_0.49.md",',
    'root / "docs/RELEASE_0.47.1.md", root / "docs/RELEASE_0.48.1.md", root / "docs/RELEASE_0.49.md", root / "docs/RELEASE_0.50.md",',
    1,
)
p.write_text(text)

# README current-release identity and proof surface.
p = Path("README.md")
text = p.read_text()
text = text.replace("## Current release — v0.49.0", "## Current release — v0.50.0", 1)
text = text.replace("**Semantic Solver Release Candidate**", "**Proof-Carrying Solver Claims**", 1)
text = text.replace("**Next release:** v0.50.0 — Proof-Carrying Solver Claims", "**Next release:** v0.51.0 — Governed Solution Pools & Complete Enumeration", 1)
text = text.replace(
    "v0.49 does not add another execution kernel. It freezes and certifies the architecture assembled through v0.48: deterministic replay, typed authority, formal verification, governed memory, certified reuse, native optimization, SII resource economics, cross-run knowledge, and project-wide Apache-2.0 licensing.",
    "v0.50 adds proof-carrying solver claims as a thin layer over the v0.49 release-candidate runtime. Solver status remains Evidence; only an independent passing checker can label an exact-bound claim `PROOF_CERTIFIED`, and that certificate still does not become policy or truth authority.",
    1,
)
text = text.replace(
    "package / public surface: 0.49.0\naasm.adoption.v1 / 0.25.0\naasm.semantic.solver.rc.v1 / 0.1.0",
    "package / public surface: 0.50.0\naasm.adoption.v1 / 0.26.0\naasm.solver.proof-certificate.v1 / 0.1.0\naasm.semantic.solver.rc.v1 / 0.1.0",
    1,
)
proof_section = '''## v0.50 — Proof-Carrying Solver Claims

The governing distinction is:

```text
SOLVER STATUS != PROOF GRADE
SOLVER_VALIDATED = ordinary independently validated solver Evidence
PROOF_CERTIFIED  = exact-bound claim + proof artifact + independent checker PASS
```

The v0.50 contract is `aasm.solver.proof-certificate.v1 / 0.1.0`. Its first checker, `aasm.checker.finite-domain-exhaustive.v1 / 0.1.0`, exhaustively verifies bounded Boolean/integer `UNSAT`, `INFEASIBLE`, and `OPTIMAL` claims. Continuous domains, unsupported claim kinds, and proof spaces beyond the configured finite-domain budget remain explicitly `UNSUPPORTED`; they are never mislabeled as failed proofs or silently promoted.

Claims, proof artifacts, and certificates are durable through the existing AASM Evidence/event history. A passing certificate has `certificate_authority = EVIDENCE_ONLY` and `truth_authority = EXISTING_AASM_POLICY_ONLY`.

```text
proof failure       -> no PROOF_CERTIFIED
proof unsupported   -> no PROOF_CERTIFIED
solver self-check   -> no PROOF_CERTIFIED
independent PASS    -> PROOF_CERTIFIED Evidence only
```

Public CLI:

```bash
aasm solver-proof-contract
aasm solver-proof-conformance
```

See `docs/PROOF_CARRYING_SOLVER_CLAIMS.md` for exact scope and non-claims.

'''
text = text.replace("## v0.49 — Semantic Solver Release Candidate\n", proof_section + "## v0.49 — Semantic Solver Release Candidate\n", 1)
text = text.replace(
    "- **Semantic Solver RC** upgrade, cross-backend, benchmark, claim-audit, public CLI, and full real certification;",
    "- **Semantic Solver RC** upgrade, cross-backend, benchmark, claim-audit, public CLI, and full real certification;\n- **Proof Claims** exact binding, proof applicability, adversarial rejection, public CLI, replay, and conformance;",
    1,
)
text = text.replace(
    "- **v0.49 Semantic Solver Release Candidate — current ✅**\n- **v0.50 Proof-Carrying Solver Claims — next**\n- v0.51 Governed Solution Pools & Complete Enumeration",
    "- v0.49 Semantic Solver Release Candidate ✅\n- **v0.50 Proof-Carrying Solver Claims — current ✅**\n- **v0.51 Governed Solution Pools & Complete Enumeration — next**",
    1,
)
text = text.replace(
    "See [ROADMAP.md](ROADMAP.md), [docs/CURRENT_RELEASE.md](docs/CURRENT_RELEASE.md), [docs/SEMANTIC_SOLVER_RELEASE_CANDIDATE.md](docs/SEMANTIC_SOLVER_RELEASE_CANDIDATE.md), [docs/RELEASE_0.49.md](docs/RELEASE_0.49.md), and [LICENSE_POLICY.md](LICENSE_POLICY.md).",
    "See [ROADMAP.md](ROADMAP.md), [docs/CURRENT_RELEASE.md](docs/CURRENT_RELEASE.md), [docs/PROOF_CARRYING_SOLVER_CLAIMS.md](docs/PROOF_CARRYING_SOLVER_CLAIMS.md), [docs/RELEASE_0.50.md](docs/RELEASE_0.50.md), [docs/SEMANTIC_SOLVER_RELEASE_CANDIDATE.md](docs/SEMANTIC_SOLVER_RELEASE_CANDIDATE.md), and [LICENSE_POLICY.md](LICENSE_POLICY.md).",
    1,
)
p.write_text(text)

# Roadmap: v0.50 is delivered/current; v0.51 is next. No v1 assumption changes.
p = Path("ROADMAP.md")
text = p.read_text()
text = text.replace("AASM is currently **v0.49.0 / Semantic Solver Release Candidate**.", "AASM is currently **v0.50.0 / Proof-Carrying Solver Claims**.", 1)
text = text.replace("- **v0.49.0 Semantic Solver Release Candidate — Current**", "- v0.49.0 Semantic Solver Release Candidate\n- **v0.50.0 Proof-Carrying Solver Claims — Current**", 1)
text = text.replace(
    "## v0.50.0 — Proof-Carrying Solver Claims\n\nPrimary contract target:",
    '''## v0.50.0 — Proof-Carrying Solver Claims

**Status: Delivered/current.**

Delivered in v0.50:

1. `aasm.solver.proof-certificate.v1 / 0.1.0` with `EXPERIMENTAL_ENFORCED` stability;
2. public adoption contract `aasm.adoption.v1 / 0.26.0`;
3. thin `ProofClaimRuntimeMixin + runtime_v49.AASMEngine` composition with no new scheduler, reducer, solver kernel, memory store, or truth authority;
4. `SolverClaim`, `SolverProofArtifact`, and `SolverClaimCertificate` exact-bound objects;
5. explicit `SOLVER_VALIDATED` versus `PROOF_CERTIFIED` levels;
6. mandatory independent-checker requirement for `PROOF_CERTIFIED`;
7. exact problem/formulation/model/result fingerprint binding;
8. AASM-owned `aasm.checker.finite-domain-exhaustive.v1 / 0.1.0` checker for bounded Boolean/integer claims;
9. exhaustive certification of supported `UNSAT`, `INFEASIBLE`, and `OPTIMAL` claims;
10. deterministic proof trace digest and independent reconstruction/recheck;
11. `UNSUPPORTED != FAIL`: continuous, uncovered, or over-budget proof modes never masquerade as failed claims;
12. false optimality and false negative claims fail closed without a proof certificate;
13. proof artifacts/certificates persisted through the existing Evidence/event history and exact replay;
14. certificate authority fixed at `EVIDENCE_ONLY`, with truth authority remaining `EXISTING_AASM_POLICY_ONLY`;
15. JSON Schema 2020-12 contracts for claims, proof artifacts, and certificates;
16. bounded TLA+ and Promela/SPIN proof-certification invariants;
17. public CLI contract/conformance commands;
18. dedicated exact-head `aasm/proof-claims` gate with applicability and adversarial tests;
19. release workflow hardened to require the proof-claims gate before publishing v0.50.

**Next planned implementation release: v0.51.0 — Governed Solution Pools & Complete Enumeration.**

Primary contract target:''',
    1,
)
p.write_text(text)

# Changelog.
p = Path("CHANGELOG.md")
text = p.read_text()
entry = '''## [0.50.0] - 2026-08-14

### Proof-Carrying Solver Claims

- advanced the package/public surface to `0.50.0` and `aasm.adoption.v1` to `0.26.0`;
- added `aasm.solver.proof-certificate.v1 / 0.1.0` with `EXPERIMENTAL_ENFORCED` stability;
- added `SolverClaim`, `SolverProofArtifact`, and `SolverClaimCertificate` with exact problem/formulation/model/result bindings;
- separates `SOLVER_VALIDATED` from `PROOF_CERTIFIED`; solver status alone is never proof grade;
- requires an independent passing checker before any claim can become `PROOF_CERTIFIED`;
- added AASM-owned exhaustive finite-domain certification for bounded Boolean/integer `UNSAT`, `INFEASIBLE`, and `OPTIMAL` claims;
- added deterministic proof trace digests and independent proof reconstruction/recheck;
- distinguishes unsupported proof scope/budget from a contradicted claim (`UNSUPPORTED != FAIL`);
- rejects forged/tampered proof artifacts, false optimality, self-checking, unsupported continuous models, and over-budget exhaustive spaces;
- persists proof claims/artifacts/certificates through the existing Evidence/event history with exact replay;
- keeps proof certificates `EVIDENCE_ONLY`; AASM policy remains the only truth/state authority;
- added JSON schemas, public API/CLI, proof conformance, dedicated `aasm/proof-claims` CI, and bounded TLA+/SPIN assurance;
- hardened release publication to require CI + Formal Assurance + Semantic Solver RC + Proof Claims on the exact current `main` SHA;
- preserved project-wide Apache-2.0 policy and all v0.49/v0.48/v0.47 authority, solver, memory, reuse, SII, and cross-run boundaries.

'''
if "## [0.50.0]" not in text:
    text = text.replace("# Changelog\n\n", "# Changelog\n\n" + entry, 1)
p.write_text(text)

Path("docs/CURRENT_RELEASE.md").write_text('''# AASM v0.50.0 — Proof-Carrying Solver Claims

AASM v0.50 adds proof-grade solver-claim certification over the v0.49 Semantic Solver RC runtime without adding another scheduler, reducer, memory store, solver kernel, or authority plane.

Runtime composition:

```text
ProofClaimRuntimeMixin + runtime_v49.AASMEngine
```

## Contracts

```text
package/public surface: 0.50.0
aasm.adoption.v1 / 0.26.0
aasm.solver.proof-certificate.v1 / 0.1.0
proof stability: EXPERIMENTAL_ENFORCED
aasm.semantic.solver.rc.v1 / 0.1.0
aasm.knowledge.cross-run.v1 / 0.1.0
aasm.sii.v1 / 0.3.0
aasm.optimization.advanced.v1 / 0.1.0
aasm.optimization.v1 / 0.1.0
aasm.optimization.convex.v1 / 0.1.0
aasm.remote.v1 / 0.19.0
license: Apache-2.0 project-wide declaration
```

## Proof boundary

```text
SOLVER STATUS != PROOF GRADE
SOLVER_VALIDATED != PROOF_CERTIFIED
```

`PROOF_CERTIFIED` requires exact problem/formulation/model/result binding, an independent checker, and PASS. The initial checker `aasm.checker.finite-domain-exhaustive.v1 / 0.1.0` exhaustively certifies supported bounded Boolean/integer `UNSAT`, `INFEASIBLE`, and `OPTIMAL` claims.

Continuous variables, unsupported claim families, and proof spaces beyond the configured finite-domain budget are `UNSUPPORTED`, not proof failures. Contradicted claims are `FAIL`. Neither can produce `PROOF_CERTIFIED`.

## Durability and authority

Claims, proof artifacts, and certificates are recorded through the existing Evidence/event history and must replay exactly.

```text
certificate_authority = EVIDENCE_ONLY
truth_authority       = EXISTING_AASM_POLICY_ONLY
```

A proof certificate strengthens Evidence; it does not directly authorize truth or canonical state.

## Required release gates

```text
aasm/ci-summary
aasm/formal-assurance
aasm/semantic-solver-rc
aasm/proof-claims
```

All must be `success` on the exact current `main` SHA before release publication.

## Release identity

```text
package/public surface: 0.50.0
runtime: runtime_v50.AASMEngine
parent runtime: runtime_v49.AASMEngine
adoption: aasm.adoption.v1 / 0.26.0
proof claims: aasm.solver.proof-certificate.v1 / 0.1.0
license: Apache-2.0 project-wide declaration
```

See `docs/PROOF_CARRYING_SOLVER_CLAIMS.md`, `docs/RELEASE_0.50.md`, `docs/SEMANTIC_SOLVER_RELEASE_CANDIDATE.md`, and `LICENSE_POLICY.md`.
''')

Path("docs/RELEASE_0.50.md").write_text('''# AASM v0.50.0 — Proof-Carrying Solver Claims

v0.50 establishes a proof-carrying claim layer over the v0.49 Semantic Solver RC while preserving the existing AASM authority boundary.

```text
package/public surface: 0.50.0
aasm.adoption.v1 / 0.26.0
aasm.solver.proof-certificate.v1 / 0.1.0
stability: EXPERIMENTAL_ENFORCED
license: Apache-2.0 project-wide declaration
```

## What is new

- exact-bound `SolverClaim`, `SolverProofArtifact`, and `SolverClaimCertificate` objects;
- `SOLVER_VALIDATED` versus `PROOF_CERTIFIED` verification levels;
- `PROOF_CERTIFIED` requires an independent checker and PASS;
- `aasm.checker.finite-domain-exhaustive.v1 / 0.1.0` exhaustively certifies bounded Boolean/integer `UNSAT`, `INFEASIBLE`, and `OPTIMAL` claims;
- deterministic trace digests and independent reconstruction/recheck;
- proof applicability is explicit: unsupported continuous domains, uncovered claim kinds, and over-budget exhaustive spaces remain `UNSUPPORTED` rather than being misreported as proof failures;
- false optimality/negative claims fail closed and never create a certificate;
- durable proof records reuse AASM's existing Evidence/event history and exact replay;
- JSON Schema 2020-12 claim/artifact/certificate contracts;
- bounded TLA+ and Promela/SPIN invariants for independence, binding, PASS, failure/unsupported exclusion, and policy-only truth authorization;
- public `solver-proof-contract` and `solver-proof-conformance` CLI;
- dedicated exact-head `aasm/proof-claims` release gate.

## Authority law

```text
PROOF_CERTIFIED = independently checked Evidence
PROOF_CERTIFIED != POLICY AUTHORITY
certificate_authority = EVIDENCE_ONLY
truth_authority = EXISTING_AASM_POLICY_ONLY
```

## Deliberate limits

v0.50 does not claim native proof-object support for every backend or mathematical family. DRAT/LRAT-style SAT proofs, MILP proof formats, dual certificates, unboundedness rays, and theorem-prover-native proof transport require future dedicated checker/gate work before receiving proof-grade labels.

## Release gates

The exact release commit must have all of:

```text
aasm/ci-summary
aasm/formal-assurance
aasm/semantic-solver-rc
aasm/proof-claims
```

at `success`. Release artifacts remain reproducible, clean-install tested, historically audited, and remotely byte-verified before publication succeeds.
''')
