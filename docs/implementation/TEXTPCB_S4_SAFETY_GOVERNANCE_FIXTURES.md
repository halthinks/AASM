# TextPCB S4 Permanent Safety-Governance Fixture Corpus

**Status:** permanent aggregate qualification corpus  
**Fixture contract:** `aasm.textpcb.s4-safety-fixtures.v1`  
**Required context:** `aasm/safety-governance`  
**Runtime admission:** none; qualification only

## Purpose

The S4 foundations are intentionally narrow and separately gated. S4.10 proves that their boundaries compose without allowing information, solver results, resource pressure, degraded state, human intervention, or representation changes to acquire authority or weaken hard semantics.

The fixture manifest under `fixtures/textpcb/` is closed-schema, fingerprinted, and permanent. It names twelve required failure and composition cases covering Quantity, Rule, Projection, Scenario, Degraded Operation, Risk/Irreversibility, Obligation Phases, Safety Envelope/Hybrid State, Epistemic Debt, and Manual Override.

## Required cases

1. Dimensional mismatch fails before solving or verification.
2. Trace width, clearance, and manufacturing limits remain typed and exact.
3. DRC/ERC hard floors dominate preferences.
4. Controlled waiver provenance remains review-only and append-only.
5. Thermal, power, and signal contexts remain explicit distinct scenarios.
6. Tolerance and quantization are conservative at safety boundaries.
7. Production alternatives may be projection-equivalent while exact identities remain diverse.
8. Degraded dependency loss never amplifies capability or authority.
9. UNKNOWN degraded state fails closed to no new effects.
10. Present and unknown hard hazards dominate optimization.
11. Irreversible or unknown operations escalate assurance monotonically.
12. Provider, solver, time, and resource scarcity cannot relax hard hazard or evidence floors.

## Aggregate gate

`aasm/safety-governance` independently runs:

- the fixture manifest/schema/source firewall;
- the integrated TextPCB fixture tests;
- every dedicated S4 foundation and public-adoption test corpus from Quantity through S4.9;
- cumulative release/public-boundary checks.

The gate creates no new runtime contract and exposes no TextPCB-specific engine methods. TextPCB is the permanent stress corpus; the semantics remain domain-neutral AASM contracts.
