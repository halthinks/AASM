# AASM Architecture

AASM separates concerns that are often collapsed into one LLM loop.

## 1. Machine state

The machine owns authoritative state. Agents and adapters observe state through provided views and return proposals or results. They do not directly mutate the lifecycle, calculus, profile binding, or effect state.

## 2. Algorithmic planning

Problem features are classified and mapped to useful operators such as graph traversal, backtracking, dynamic programming, shortest-path reasoning, capacity allocation, or an optional decision backend.

## 3. Formal decision and obligation calculus

AASM records named decisions, conditional obligations, locks, conflicts, causal explanations, learned constraints, fairness, backjumping, and search restart. This is durable machine state rather than conversational memory.

## 4. Domain-neutral profile packages

A package supplies use-case meaning through a versioned profile and independent adapter contracts. Profiles declare vocabulary, policies, evidence/artifact kinds, machine identity, migrations, and optional adapter bindings.

The package/profile layer is subordinate to the kernel:

```text
package proposes meaning and candidate outputs
              ↓
AASM validates identity, authority, evidence, constraints, and migration
              ↓
authoritative state changes through the existing event/reducer path
```

Profiles are immutable by ID, version, and fingerprint. A package revision becomes active only through explicit conformance and migration. Discovery never downloads packages or executes adapters automatically.

## 5. Execution

Agents, tools, humans, simulators, or services execute authorized work. The runtime is role-agnostic and does not require a fixed team topology.

## 6. Authority

Capability and authority are separate. A worker or adapter may be capable of proposing a model, explanation, or external action without being authorized to activate, commit, learn a hard constraint, migrate a profile, or cross an effect boundary.

## 7. Verification and provenance

Results become evidence or generic semantic-result envelopes. Observations are checked against evidence contracts and invariants before authoritative commitment. Material changes retain provenance and survive replay, restart, and fork.

## 8. Canonical adoption surface

AASM v0.25.2 defines one supported golden path over the existing event/reducer runtime. It does not add a second runtime, alternate reducer, duplicate persistence layer, or replacement authority mechanism.

The machine-readable source of truth is:

```python
from aasm import public_api_contract, validate_public_api_contract

contract = public_api_contract()
report = validate_public_api_contract()
```

The same contract is available through:

```bash
aasm adoption-contract
```

and:

```text
GET /adoption-contract
```

The contract identifies:

- supported top-level imports;
- supported `AASMEngine` methods;
- supported CLI commands;
- supported inspection surfaces;
- supported HTTP entry points;
- the runtime version and separate remote-protocol version;
- the compatibility expectations for supported, experimental, and internal surfaces.

“Supported” inside the pre-1.0 project means that a breaking change must be explicit in the changelog and accompanied by migration or deprecation guidance when practical. It does not declare the entire project API frozen.

Reference applications, Control Center work, operator runbooks, and external framework adapters must exercise this existing path. An adoption deliverable is incomplete if it works only through private snapshot mutation, direct database writes, or a parallel orchestration loop.

## Design boundary

AASM remains usable underneath different agent frameworks and domains. Provider-specific invocation, application UX, domain logic, package adapters, and tool implementations belong outside the core or behind explicit contracts.
