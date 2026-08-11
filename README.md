<div align="center">

# AASM

## Algorithmic Agent State Machine

**A durable control system for agents, tools, models, humans, and real work.**

AASM keeps the official state of a job outside the language model. Models can propose what to do; AASM decides what is legal, records what happened, preserves evidence, and recovers from bad assumptions without discarding unrelated work.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Formal Assurance](https://github.com/halthinks/AASM/actions/workflows/formal.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/formal.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-v0.28.1%20experimental-orange)](ROADMAP.md)

[Run the full stack](#one-command-start) · [Install](#install-aasm) · [Operator runbooks](#operator-runbooks) · [Why AASM?](WHY_AASM.md) · [Roadmap](ROADMAP.md)

</div>

---

## Current release

**v0.28.1 — Distribution Release Hardening**

| Item | Current state |
|---|---|
| **Package/runtime** | **v0.28.1** |
| **Project status** | Experimental / pre-1.0 |
| **Current milestone** | **Distribution Release Hardening** |
| **Prior capability release** | **v0.28.0 — Distribution and Operator Readiness** |
| **One-command application** | PostgreSQL + runtime + Control Center + worker + Research Synthesis Hero Stack |
| **Next release** | **v0.29.0 — Thin LangGraph Adapter** |
| **Remote compatibility protocol** | `aasm.remote.v1 / 0.19.0` |

v0.28.1 does not add a second runtime. It hardens the distribution boundary around the working v0.28.0 implementation:

- build dependencies are exact and declared;
- two clean builds must produce byte-identical wheel and source-distribution files;
- a release is attempted only for an explicit dispatch or a package-version change;
- an existing release is never overwritten or repaired in place;
- the remote tag, asset set, byte sizes, and SHA-256 digests are read back and verified;
- historical tags are inspected and reported without making old-tag permissions release-critical.

The package version and wire-protocol version are intentionally separate. AASM v0.28.1 can evolve while compatible remote clients continue to use `aasm.remote.v1 / 0.19.0`.

> **Models propose. AASM decides what may become durable state.**

---

# One-command start

The easiest way to understand AASM is to run the complete local application:

```bash
git clone https://github.com/halthinks/AASM.git
cd AASM
docker compose up --build
```

Open:

```text
http://localhost:8787/
```

The stack starts PostgreSQL 17, the existing AASM HTTP runtime, the existing Control Center, a deterministic remote worker, a live setup machine, and a completed reference trajectory. It requires no model key, paid API, external literature service, or host PostgreSQL installation.

Useful commands:

```bash
# Show machines, workers, and leases
docker compose run --rm stackctl status

# Create a fresh live machine without deleting previous history
docker compose run --rm stackctl fresh

# Verify the completed machine by full replay
docker compose run --rm stackctl verify --selection completed

# Run the complete readiness check
docker compose run --rm stackctl check

# Stop while preserving PostgreSQL data
docker compose down
```

See [One-Command Local Full Stack](docs/LOCAL_FULL_STACK.md).

---

# Install AASM

## Immutable GitHub release wheel

Every maintained release builds twice, inspects its contents, clean-installs the wheel, records SHA-256 values, publishes once, and verifies the exact remote assets.

For v0.28.1:

```bash
pip install \
  https://github.com/halthinks/AASM/releases/download/v0.28.1/aasm_runtime-0.28.1-py3-none-any.whl
```

Verify the installed package:

```bash
aasm adoption-contract
aasm runbook history-diagnosis
```

The release contains:

```text
aasm_runtime-0.28.1-py3-none-any.whl
aasm_runtime-0.28.1.tar.gz
historical-release-report.json
SHA256SUMS.txt
release-manifest.json
```

`historical-release-report.json` records each maintained pre-automation tag as `VERIFIED`, `PENDING_OWNER_PUBLICATION`, or `MISMATCH`. Missing historical tags are visible but do not invalidate a correctly built current release. A real tag/commit mismatch does.

## PyPI

The package name is `aasm-runtime`, and the primary PyPI command is:

```bash
pip install aasm-runtime
```

The repository contains a credential-free PyPI Trusted Publisher workflow. Actual PyPI publication begins only after the external PyPI project/publisher binding is configured and the repository gate `AASM_PUBLISH_PYPI` is enabled. Until that one-time external binding is active, use the immutable GitHub release wheel above.

## Contributor install

```bash
git clone https://github.com/halthinks/AASM.git
cd AASM
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS or Linux
source .venv/bin/activate

pip install -e '.[dev]'
pytest -q
```

---

# What problem does AASM solve?

A capable agent can still:

- forget an earlier decision;
- repeat a failed approach;
- hide an unfinished requirement;
- edit the latest symptom instead of the causal decision;
- report success without the required evidence;
- lose useful knowledge during restart;
- duplicate an external effect whose prior outcome is unknown.

A conversation is not a reliable control plane. AASM gives the work an official, replayable machine state.

Imagine an agent building a service:

1. It chooses PostgreSQL.
2. Work relevant only to SQLite becomes conditionally hidden, not deleted.
3. An integration test contradicts the selected schema.
4. AASM links the evidence to the responsible decisions.
5. It backjumps to the causal decision rather than randomly changing the newest files.
6. Unrelated valid work stays intact.
7. The failed combination becomes certified blocking knowledge and cannot silently recur.

AASM is not a language model. It is the deterministic runtime around models, tools, workers, and people.

---

# The three things to remember

## Decisions

A decision is a named choice or assumption:

```text
database = postgres
schema = v2
synthesis.causal_model = retrieval_only
```

AASM records which decisions are active, what they depend on, why they changed, and which work they authorize.

## Obligations

An obligation is work that must eventually receive a terminal disposition:

```text
run the compatibility test
collect the missing measurement
resolve contradictory evidence
publish the required artifact
```

Mandatory work cannot quietly disappear because the current plan makes it inconvenient.

## Evidence

Evidence is the durable reason a claim, decision, conflict, or completion is accepted. It can come from tests, tools, humans, simulations, sensors, or external systems.

AASM records provenance. It does not manufacture truth.

---

# How a run works

```text
Goal
  ↓
Candidate decisions are proposed
  ↓
AASM checks authority, dependencies, constraints, and fairness
  ↓
A complete candidate is activated atomically
  ↓
Authorized work runs
  ↓
Evidence is collected
  ↓
Success is committed, or a conflict is explained
  ↓
Repair, causal backjump, or knowledge-preserving restart
```

A model, heuristic, person, or solver may propose a candidate. Only the AASM kernel can make it durable.

This keeps the architecture faithful to its AVATAR/labelled-splitting inspiration: conditional components may be activated or locked reversibly, conflicts become durable blocking information, fairness keeps obligations from remaining hidden forever, and restart discards speculation rather than verified knowledge.

---

# Operator runbooks

v0.28.0 — Distribution and Operator Readiness turned operational claims into executable drills. v0.28.1 preserves those seven procedures and hardens how their package is released.

List them:

```bash
aasm runbook list
```

Run any drill in memory:

```bash
aasm runbook lease-loss
aasm runbook requirement-change
aasm runbook learned-no-good
aasm runbook human-approval
aasm runbook replay-fork
aasm runbook unknown-effect
aasm runbook history-diagnosis
```

Persist a drill to SQLite or PostgreSQL:

```bash
aasm runbook lease-loss --store operator-drills.db
```

| Runbook | Proves |
|---|---|
| `lease-loss` | stale ownership expires and the same task is reclaimed under a new lease |
| `requirement-change` | only the affected plan region pauses; unrelated completed work remains |
| `learned-no-good` | a conflict becomes independently verified blocking knowledge |
| `human-approval` | insufficient approval is denied and quorum authorization is durable |
| `replay-fork` | source history verifies, replay is exact, and the fork records lineage |
| `unknown-effect` | unsafe retry is blocked until the external outcome is explicitly reconciled |
| `history-diagnosis` | a corrupted copy yields concrete issue codes without modifying canonical history |

Start at [Operator Runbooks](docs/runbooks/README.md).

---

# Research Synthesis Hero Stack

The bundled offline application demonstrates:

```text
initial interpretation
→ explicit obligations and evidence
→ validated contradiction
→ certified learned no-good
→ non-chronological backjump
→ unrelated work preserved
→ mid-run requirement injection
→ conditional lock restoration
→ corrected synthesis
→ claim-level provenance
→ exact full-history replay
```

Run it without Docker:

```bash
aasm demo \
  --scenario research-synthesis \
  --mode complete \
  --db research-demo.db \
  --output-dir research-output
```

Read [Why AASM?](WHY_AASM.md) and [Research Synthesis Hero Stack](docs/RESEARCH_SYNTHESIS_DEMO.md).

---

# Canonical adoption surface

AASM exposes one machine-readable supported path over the existing runtime:

```python
from aasm import public_api_contract, validate_public_api_contract

contract = public_api_contract()
assert validate_public_api_contract()["valid"]
```

CLI:

```bash
aasm adoption-contract
```

HTTP:

```text
GET /adoption-contract
```

Reference applications, adapters, local-stack services, release tooling, Control Center additions, and runbooks must use the existing event/reducer runtime. Direct snapshot mutation, private database writes, and parallel authority paths are not accepted adoption mechanisms.

---

# Major capabilities

| Capability | What it gives you |
|---|---|
| Durable state and replay | Reconstruct a run from events instead of trusting a transcript |
| Legal transitions | Explicit rules for what the machine may do next |
| Decision / Obligation / Evidence calculus | Durable choices, unfinished work, provenance, and truth maintenance |
| Conditional locks | Hide model-irrelevant work without deleting it |
| Conflict learning | Evidence-backed explanations and reusable no-goods |
| Causal backjumping | Revisit the responsible decision while preserving unrelated work |
| Restart without amnesia | Discard speculation while retaining evidence and learned knowledge |
| Certificate-gated hard knowledge | Require independent verification before a constraint becomes hard |
| Atomic candidate activation | Commit an entire candidate model or none of it |
| Distributed workers | Registration, heartbeat, leases, expiry, reclaim, quotas, and stale-result rejection |
| Controlled effects | Authorization, idempotency, ownership, UNKNOWN outcomes, and reconciliation |
| Observability | Decision, Obligation, Evidence, causal graphs, timelines, and fairness debt |
| Release integrity | Byte-identical double build, clean-wheel test, exact hashes, no overwrite, and remote asset verification |

---

# Compatibility and correctness boundary

AASM is pre-1.0 experimental software. The supported public imports, engine methods, CLI commands, inspection surfaces, HTTP endpoints, and operator runbooks are declared by `aasm.adoption.v1`.

AASM strengthens legality, durability, replay, provenance, and machine-level assurance. It does not prove that a scientific model is physically correct, a sensor was calibrated, a human report was honest, or an external service told the truth.

See [Compatibility Policy](docs/COMPATIBILITY.md), [Formal Assurance](docs/FORMAL_ASSURANCE.md), and [Release Process](docs/RELEASE_PROCESS.md).

---

# Next phases

The execution plan is maintained in [ROADMAP.md](ROADMAP.md). The next release is **v0.29.0 — Thin LangGraph Adapter**, followed by adapter conformance, hierarchical decision scopes, runtime/formal trace conformance, signed provenance, and distributed recovery certification. Each phase has an explicit user outcome, implementation boundary, and exit gate.

---

# Documentation

| Start here when you are… | Read |
|---|---|
| Trying AASM | This README and [Local Full Stack](docs/LOCAL_FULL_STACK.md) |
| Evaluating why it is different | [Why AASM?](WHY_AASM.md) |
| Operating the system | [Operator Runbooks](docs/runbooks/README.md) |
| Integrating an application | [Architecture](docs/ARCHITECTURE.md) and `aasm adoption-contract` |
| Reviewing correctness | [Formal Assurance](docs/FORMAL_ASSURANCE.md) and [`formal/`](formal/) |
| Publishing a release | [Release Process](docs/RELEASE_PROCESS.md) |
| Depending on public APIs | [Compatibility Policy](docs/COMPATIBILITY.md) |

[Roadmap](ROADMAP.md) · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Support](SUPPORT.md)

## License

MIT — see [LICENSE](LICENSE).
