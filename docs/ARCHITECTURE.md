# AASM Architecture

AASM separates five concerns that are often collapsed into one LLM loop.

## 1. Machine state

The machine owns the authoritative state. Agents observe state through provided views and return proposals/results. They should not directly mutate the machine lifecycle.

## 2. Algorithmic planning

Problem features are classified and mapped to useful operators such as graph traversal, backtracking, dynamic programming, shortest-path reasoning, or capacity allocation.

## 3. Execution

Agents, tools, humans, or services execute authorized work. The runtime is role-agnostic and does not require a fixed team topology.

## 4. Authority

Capability and authority are separate. A worker may be capable of making a change without being authorized to commit that change to authoritative state.

## 5. Verification and provenance

Results become observations. Observations can be checked against evidence and invariants before state is committed. Important transitions emit provenance events.

## Design boundary

AASM should remain usable underneath many different agent frameworks. Provider-specific model invocation, application UX, domain-specific logic, and tool implementations generally belong outside the core or in adapters.
