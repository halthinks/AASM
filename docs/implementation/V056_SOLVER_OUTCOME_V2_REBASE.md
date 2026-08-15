# AASM v0.56 — Solver Outcome v2 Re-baseline

**Status:** ACTIVE IMPLEMENTATION NOTE  
**Baseline release:** `v0.55.0`  
**Baseline release SHA:** `dd9360858be8755a5639162a7d388d867c1b01e6`  
**Post-release ledger baseline:** `53ba1f7a7e653ecd3c4ce9ea912b4019a3835f78`

This note re-baselines work item **56.1 — Solver Outcome v2** after the immutable v0.55.0 release. It does not advance 56.2 or 56.3.

## Scope admitted for 56.1

56.1 owns only the provider-independent solver outcome/status contract and the minimum provider decoding needed to make that contract truthful:

- an authoritative normalized v2 status distinct from termination cause;
- independently validated incumbent state before any `*_WITH_INCUMBENT`, `SAT`, `OPTIMAL`, or feasible status is admitted;
- preserved objective, best bound, relative gap, raw provider status/code, diagnostics, and provider identity;
- explicit checked/unchecked certificate and evidence-grade axes;
- exact provider status-map rules with rule identity, eligibility declarations, and conservative unknown handling;
- one-way v2 -> legacy v1 coarse-status projection, explicitly marked lossy where information is collapsed;
- provider-native exact decoding for the currently qualified CaDiCaL/PySAT, OR-Tools CP-SAT, and HiGHS paths;
- durable normalization through existing AASM Evidence/event replay only.

## Explicit non-scope

The following remain **SOURCE_LOCKED / uncredited** in this tranche:

- 56.2 execution profiles and runtime provenance;
- 56.3 reproducibility certification;
- generalized learned-knowledge application;
- core/MUS pipeline integration;
- external-machine control, artifact lineage, and later engineering contracts.

Dormant pre-v0.55 provenance/reproducibility files remain ignored by the v0.55 test surface and are not evidence of v0.56 progress.

## Compatibility rule

`aasm.optimization.v1` remains the released compatibility contract. Its coarse status vocabulary is not replaced. Internal provider decoding may be hardened where the old implementation inferred status from text fragments, but the v1 public status vocabulary remains frozen.

For new v0.56 features, v2 is the detailed authoritative evidence object. `legacy_projection` is a derived compatibility view and never the source of v2 truth.

## Claim ceiling

Until the dedicated 56.1 gate passes real provider fixtures, the implementation remains a qualification candidate and the active root package remains released AASM v0.55.0.
