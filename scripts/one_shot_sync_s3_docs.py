from __future__ import annotations

from pathlib import Path
import re

HEAD = "6b107268cd4190357bf45b3bfd1385410a0d82cf"
ADOPTION = "0.32.15"
CONTEXTS = "27"


def load(path: str) -> tuple[Path, str]:
    p = Path(path)
    return p, p.read_text(encoding="utf-8")


def save(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8")


def replace_exact(text: str, old: str, new: str, label: str, *, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{label}: expected {expected}, found {count}")
    print(label)
    return text.replace(old, new)


def replace_at_least(text: str, old: str, new: str, label: str, *, minimum: int = 1) -> str:
    count = text.count(old)
    if count < minimum:
        raise SystemExit(f"{label}: expected >= {minimum}, found {count}")
    print(f"{label}: {count}")
    return text.replace(old, new)


def replace_line(text: str, prefix: str, replacement: str, label: str) -> str:
    lines = text.splitlines()
    hits = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    if len(hits) != 1:
        raise SystemExit(f"{label}: expected one line, found {len(hits)}")
    lines[hits[0]] = replacement
    print(label)
    return "\n".join(lines) + "\n"


def replace_section(text: str, start: str, end: str, replacement: str, label: str) -> str:
    a = text.find(start)
    b = text.find(end, a + len(start)) if a >= 0 else -1
    if a < 0 or b < 0:
        raise SystemExit(f"{label}: section anchors missing")
    print(label)
    return text[:a] + replacement.rstrip() + "\n\n" + text[b:]


def sync_readme() -> None:
    p, t = load("README.md")
    t = replace_at_least(t, "aasm.adoption.v1 / 0.32.7", f"aasm.adoption.v1 / {ADOPTION}", "README adoption")
    t = replace_line(t, "**Qualified development boundary:**", "**Qualified development boundary:** PR-1 + PR-2 + complete PR-3 / PHY-01 + S3 through artifact revision lineage and entity evolution  ", "README qualified boundary")
    t = replace_line(t, "**Next unfinished boundary:**", "**Next unfinished boundary:** S4 — Engineering + Safety Semantics (quantity/unit/tolerance foundation first)  ", "README next boundary")
    t = replace_at_least(t, "9425fbdd22f664f3a2cb5db73dcf45c5b77a0673", HEAD, "README qualified head")
    old_summary = "The latest immutable published release remains **v0.56.0**. Development on `main` has advanced materially beyond that published boundary without pretending the development target is already released. The active `0.56.1` candidate now combines execution provenance, explicit state/fact authority, external-machine supervision, postcondition verification, exclusive authority leases, bounded effect capabilities, stale-command fencing, semantic preemption, and crash-safe preemption recovery."
    new_summary = "The latest immutable published release remains **v0.56.0**. Development on `main` has advanced materially beyond that published boundary without pretending the development target is already released. The active `0.56.1` candidate now combines execution provenance, explicit state/fact authority, external-machine supervision, postcondition verification, complete physical-effect authority integration, observation epistemics, backend-independent artifact revision lineage, and governed entity evolution with ambiguity-safe reuse fencing."
    t = replace_exact(t, old_summary, new_summary, "README development summary")
    old_block = "PR-3H status:\n  NOT IMPLEMENTED\n  must integrate with existing authorize_effect / execute_effect\n  must recheck capability/lease/epoch/revocation/bounds at effect boundaries\n  must not create a second authority evaluator, dispatcher, ownership model, or effect lifecycle"
    new_block = "PR-3H physical-effect integration:\n  GATED\n  reuses existing authorize_effect / execute_effect\n  rechecks capability/lease/epoch/revocation/bounds at effect boundaries\n  creates no second authority evaluator, dispatcher, ownership model, or effect lifecycle\n\nS3 artifact + entity lineage:\n  aasm.artifact.revision.v1\n  aasm.artifact-lineage.runtime.v1\n  aasm.entity.evolution.v1\n  aasm.entity-evolution.runtime.v1\n  artifact existence/generation != authoritative acceptance\n  AMBIGUOUS entity mapping blocks hard automatic reuse"
    t = replace_exact(t, old_block, new_block, "README contract block")
    replacement = """### PR-3H — implemented and gated

PR-3H now connects the qualified authority-domain/lease/capability/fencing semantics to the **existing** Effect authorization and execution boundaries. Both boundaries recheck live lease identity/fingerprint/epoch, capability identity/fingerprint, effective revocation generation, holder, operation/bounds, workspace/scope/subject, and applicable problem/external revision. Earlier capability-use Evidence is never a reusable bearer token.

The inherited `effect.authorize`, resources/Worker/TaskLease, Effect ownership, dispatch, `UNKNOWN`, and reconciliation paths remain authoritative; no parallel authority evaluator, scheduler, dispatcher, Effect store, ownership primitive, or reconciliation path was introduced.

### S3 — artifact revision lineage + entity evolution

Artifact revisions now have backend-independent immutable identity over content/semantic hashes and exact provenance, exact parent ID+fingerprint lineage, and a separate storage-binding fingerprint for non-semantic `artifact_ref` locators. Registration/replay uses existing Evidence and does not imply artifact acceptance or create a current-artifact truth pointer.

Entity evolution now records `UNCHANGED | MODIFIED | GENERATED | SPLIT | MERGED | REPLACED | DELETED | AMBIGUOUS` relationships over exact artifact-revision-bound representations. `AMBIGUOUS` mappings remain durable and block hard automatic reuse. There is no hidden current-entity state table and no authority minting."""
    t = replace_section(t, "### PR-3H — next active implementation boundary", "## v0.56 — Truthful Solver Outcomes", replacement, "README PR3H/S3 section")
    save(p, t)


def sync_roadmap() -> None:
    p, t = load("ROADMAP.md")
    t = replace_line(t, "**Current active adoption contract:**", f"**Current active adoption contract:** `aasm.adoption.v1 / {ADOPTION}`  ", "ROADMAP adoption")
    t = replace_line(t, "**Qualified development boundary:**", "**Qualified development boundary:** PR-1, PR-2, complete PR-3 / PHY-01, plus complete S3 state conflict, causality/freshness, identity/calibration/trust, execution environment, observation epistemics, artifact revision lineage, and entity evolution  ", "ROADMAP qualified boundary")
    t = replace_line(t, "**Exact S3 observation-epistemics qualification head:**", f"**Exact qualified S3 code boundary before documentation-only synchronization:** `{HEAD}` — all {CONTEXTS} current custom qualification contexts green  ", "ROADMAP exact boundary")
    t = replace_line(t, "**Immediate unfinished boundary:**", "**Immediate unfinished boundary:** **S4 / Engineering + Safety Semantics — quantity/unit/tolerance semantics first**", "ROADMAP next boundary")
    t = replace_exact(t, "verification/refinement loops, and eventually a portable deterministic kernel that can be implemented", "verification/refinement loops, and a portable deterministic kernel that can be implemented", "ROADMAP portability wording")
    observation = "- **S3 observation lifecycle/fusion:** append-only `RAW -> NORMALIZED -> CALIBRATED -> DERIVED -> VALIDATED` processing lineage plus fusion/disposition Evidence; exact source fingerprints, explicit calibration/environment/freshness references, no stage skips, no consensus voting, and no authority/admission by a `VALIDATED` label."
    addition = observation + "\n- **S3 artifact revision lineage:** backend-independent immutable revision identity over content/semantic hashes and provenance, exact parent ID+fingerprint lineage, separate storage-binding fingerprint, Evidence-backed replay, and no hidden current-artifact or acceptance authority.\n- **S3 entity evolution:** exact predecessor/successor representation binding across `UNCHANGED | MODIFIED | GENERATED | SPLIT | MERGED | REPLACED | DELETED | AMBIGUOUS`; ambiguity is durable and fail-closed for hard automatic reuse; no current-entity truth table or authority minting."
    t = replace_exact(t, observation, addition, "ROADMAP S3 bullets")
    t = replace_exact(t, "        |       artifact revision/entity evolution -------------- NEXT", "        |       artifact revision/entity evolution -------------- GATED", "ROADMAP lineage graph")
    t = replace_exact(t, "U4  Reality identity + time + artifact lineage + observation epistemics ---- ACTIVE", "U4/S3 Reality identity + time + artifact lineage + observation epistemics -- GATED", "ROADMAP U4 status")
    save(p, t)


def sync_canonical_roadmap() -> None:
    p, t = load("docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md")
    t = replace_line(t, "**Current adoption contract:**", f"**Current adoption contract:** `aasm.adoption.v1 / {ADOPTION}`  ", "canonical adoption")
    t = replace_line(t, "**Current exact qualified development boundary:**", f"**Current exact qualified code boundary before documentation-only synchronization:** `{HEAD}` — all {CONTEXTS} current custom qualification contexts green  ", "canonical exact boundary")
    t = replace_at_least(t, "Exact qualified boundary: `55a8da1f6937d97439a6e2103a55d1b6f6d0f4fd`, adoption `0.32.13`, all 25 current custom qualification contexts green.", f"Exact qualified code boundary before documentation-only synchronization: `{HEAD}`, adoption `{ADOPTION}`, all {CONTEXTS} current custom qualification contexts green.", "canonical S3 baseline")
    anchor = "- `aasm.observation.processing.runtime.v1`."
    expanded = "- `aasm.observation.processing.runtime.v1`;\n- `aasm.artifact.revision.v1` + `aasm.artifact-lineage.runtime.v1`;\n- `aasm.entity.evolution.v1` + `aasm.entity-evolution.runtime.v1`."
    t = replace_exact(t, anchor, expanded, "canonical S3 contracts")
    t = replace_exact(t, "  |      +-- artifact revision/entity evolution ------------- NEXT", "  |      +-- artifact revision/entity evolution ------------- DONE", "canonical lineage graph")
    t = replace_exact(t, "**Status: NEXT under the separate cumulative `aasm/artifact-lineage` gate.**", "**Status: GATED under `aasm/artifact-lineage` and inherited by cumulative `aasm/v56`.**", "artifact lineage status")
    t = replace_exact(t, "**Status: NEXT after/with artifact revision lineage under `aasm/artifact-lineage`.**", "**Status: GATED under the independent `aasm/entity-evolution` gate and inherited by cumulative `aasm/v56`.**", "entity evolution status")
    old_art = "Failed/generated artifacts may remain Evidence without becoming current authoritative artifacts. Artifact existence or successful generation is not authoritative acceptance. AASM must not introduce a hidden current-artifact/project-truth table."
    new_art = "The landed runtime records immutable revision documents through existing Evidence/event replay, verifies payload and semantic-projection hashes, exact parent IDs and parent fingerprints, ProblemRevision/external-source bindings, producer/machine/effect provenance, and active Evidence dependencies. Revision identity is backend-independent; `artifact_ref` is a non-semantic storage locator with a separate storage-binding fingerprint. Failed/generated artifacts may remain Evidence without becoming current authoritative artifacts. Artifact existence or successful generation is not authoritative acceptance. No hidden current-artifact/project-truth table, parallel artifact registry, truth table, or authority evaluator is introduced."
    t = replace_exact(t, old_art, new_art, "artifact lineage semantics")
    old_entity = "Hard reusable knowledge fails closed across `AMBIGUOUS` mapping. Evolution records preserve exact predecessor/successor identities and provenance; they do not silently rewrite historical entity identity."
    new_entity = "The landed runtime binds every predecessor/successor representation to an exact qualified artifact revision ID+fingerprint, validates workspace/scope and artifact-lineage ancestry, requires active supporting Evidence, reconstructs history by deterministic replay, and rejects forged fingerprints, unrelated lineages, and non-descendant successors. Hard reusable knowledge fails closed across `AMBIGUOUS` mapping. Evolution records preserve exact predecessor/successor identities and provenance; they do not silently rewrite historical entity identity or create a current-entity truth pointer."
    t = replace_exact(t, old_entity, new_entity, "entity evolution semantics")
    old_gates = "**Gates:** `aasm/physical-evidence`, `aasm/identity-calibration-trust`, `aasm/execution-environment`, `aasm/observation-epistemics`, `aasm/artifact-lineage`."
    new_gates = "**Gates:** `aasm/physical-evidence`, `aasm/identity-calibration-trust`, `aasm/execution-environment`, `aasm/observation-epistemics`, `aasm/artifact-lineage`, `aasm/entity-evolution`; all inherited by cumulative `aasm/v56`."
    t = replace_exact(t, old_gates, new_gates, "canonical S3 gates")
    save(p, t)


def sync_ledger() -> None:
    p, t = load("docs/implementation/GOVERNED_SEMANTIC_EVOLUTION_EXECUTION_LEDGER.md")
    t = replace_line(t, "**Current adoption contract:**", f"**Current adoption contract:** `aasm.adoption.v1 / {ADOPTION}`", "ledger adoption")
    t = replace_line(t, "**Current exact qualified development boundary:**", f"**Current exact qualified code boundary before documentation-only synchronization:** `{HEAD}` — all {CONTEXTS} current custom qualification contexts green", "ledger exact boundary")
    row57_3 = f"| 57.3 | `external-machine-supervision` | Artifact revision lineage | GATED | immutable CAD/PCB/CAE/physical outputs | `aasm.artifact.revision.v1`; `artifact_lineage.py`; `artifact_lineage_runtime.py`; schema; active public surface | 55.1; 57.1; S3-01–04 | exact head `{HEAD}`; `aasm/artifact-lineage` + cumulative `aasm/v56`; content/semantic hash tamper, exact-parent, stale source revision/reference, producer/machine/effect mismatch, unsupported format/schema, storage-rebinding, Evidence invalidation, SQLite replay | artifact existence/generation/success is Evidence only; no authoritative acceptance, current artifact pointer, parallel registry/truth/authority evaluator | preserve; S3 entity evolution qualified on top |"
    row57_4 = f"| 57.4 | `external-machine-supervision` | Entity evolution | GATED | persistent semantic identity across topology/tool/world-model changes | `aasm.entity.evolution.v1`; `entity_evolution.py`; `entity_evolution_runtime.py`; schema; active public adoption `{ADOPTION}` | 57.3 | exact head `{HEAD}`; `aasm/entity-evolution` + cumulative `aasm/v56`; MODIFIED/SPLIT/MERGED/AMBIGUOUS, forged artifact fingerprints, unrelated/non-descendant lineages, inactive Evidence, envelope tamper, SQLite replay | exact predecessor/successor provenance only; `AMBIGUOUS` blocks hard automatic reuse; no entity authority/current-state table | preserve; S3 complete, next S4 engineering + safety semantics |"
    t = replace_line(t, "| 57.3 |", row57_3, "ledger 57.3")
    t = replace_line(t, "| 57.4 |", row57_4, "ledger 57.4")
    lines = t.splitlines()
    for prefix, old_tail, new_tail, label in (
        ("| 57.2 |", "preserve; next external-reality dependency is artifact/entity lineage", "preserve; artifact/entity lineage now qualified; next external-reality dependency is S4 engineering/safety semantics", "ledger 57.2 pointer"),
        ("| S3-04 |", "preserve; next boundary artifact/entity lineage", "preserve; artifact/entity lineage now qualified; next boundary S4", "ledger S3-04 pointer"),
    ):
        hits = [i for i, line in enumerate(lines) if line.startswith(prefix)]
        if len(hits) != 1 or old_tail not in lines[hits[0]]:
            raise SystemExit(f"{label}: anchor drift")
        lines[hits[0]] = lines[hits[0]].replace(old_tail, new_tail)
        print(label)
    save(p, "\n".join(lines) + "\n")


def sync_current_release() -> None:
    p, t = load("docs/CURRENT_RELEASE.md")
    t = replace_line(t, "**Current development target on `main`:**", "**Current development target on `main`:** 0.56.1 — Execution Profiles + Runtime Provenance + Governed External Reality + Physical Authority + S3 Artifact/Entity Lineage  ", "CURRENT_RELEASE target")
    t = replace_at_least(t, "aasm.adoption.v1 / 0.32.7", f"aasm.adoption.v1 / {ADOPTION}", "CURRENT_RELEASE adoption")
    t = replace_line(t, "**Current qualified physical-control boundary:**", "**Current qualified development boundary:** complete PR-3 / PHY-01 + S3 through artifact revision lineage and entity evolution  ", "CURRENT_RELEASE boundary")
    t = replace_line(t, "**Next unfinished boundary:**", "**Next unfinished boundary:** S4 — Engineering + Safety Semantics (quantity/unit/tolerance foundation first)", "CURRENT_RELEASE next")
    t = replace_at_least(t, "9425fbdd22f664f3a2cb5db73dcf45c5b77a0673", HEAD, "CURRENT_RELEASE head")
    replacement = """### PR-3H — implemented and gated

PR-3H integrates lease/capability/epoch/revocation/bounds checks into the **existing** `authorize_effect` / `execute_effect` path and rechecks live authority at both boundaries. It creates no second authority evaluator, scheduler, Effect dispatcher, ownership model, reconciliation path, or Effect truth store. The existing v0.54 Effect lifecycle remains authoritative.

### S3 — reality evidence, artifact lineage, and entity evolution

S3 is now gated through the observation/identity/calibration/trust/environment/fusion layers plus `aasm.artifact.revision.v1` / `aasm.artifact-lineage.runtime.v1` and `aasm.entity.evolution.v1` / `aasm.entity-evolution.runtime.v1`. Artifact revision identity is backend-independent and replayed through existing Evidence; storage binding is separate. Artifact existence or successful generation never implies authoritative acceptance. Entity evolution binds exact predecessor/successor artifact revision fingerprints and records split/merge/replacement/ambiguity without rewriting history. `AMBIGUOUS` mappings fail closed for hard automatic reuse. Neither subsystem creates a hidden current artifact/entity truth table or effect/fact authority."""
    t = replace_section(t, "### PR-3H — not yet implemented", "## Exact-head qualification", replacement, "CURRENT_RELEASE PR3H/S3")
    old_phrase = f"qualified the active `0.56.1 / {ADOPTION}` candidate with all required direct contexts green, including:"
    new_phrase = f"qualified the active `0.56.1 / {ADOPTION}` candidate with all {CONTEXTS} current custom commit-status contexts green, including:"
    t = replace_exact(t, old_phrase, new_phrase, "CURRENT_RELEASE context count")
    anchor = "- `aasm/physical-preemption-recovery`\n"
    extras = "- `aasm/physical-effect-integration`\n- `aasm/identity-calibration-trust`\n- `aasm/execution-environment`\n- `aasm/observation-epistemics`\n- `aasm/artifact-lineage`\n- `aasm/entity-evolution`\n- `aasm/physical-evidence`\n"
    t = replace_exact(t, anchor, anchor + extras, "CURRENT_RELEASE contexts")
    save(p, t)


def sync_candidate_release_note() -> None:
    p, t = load("docs/RELEASE_0.56.1.md")
    t = replace_at_least(t, "aasm.adoption.v1 / 0.32.7", f"aasm.adoption.v1 / {ADOPTION}", "0.56.1 adoption")
    t = replace_line(t, "**Active milestones:**", "**Active milestones:** solver provenance, authoritative state, external-machine supervision, complete physical authority/effect integration, S3 observation epistemics, artifact revision lineage, entity evolution  ", "0.56.1 milestones")
    t = replace_line(t, "**PR-3 boundary:**", "**Qualified boundary:** complete PR-3 / PHY-01 and S3 through artifact revision lineage + entity evolution; next architecture boundary is S4 Engineering + Safety Semantics", "0.56.1 boundary")
    t = replace_exact(t, "Across PR-1 through PR-3G:", "Across PR-1 through complete PR-3 and S3:", "0.56.1 no-parallel scope")
    replacement = """## PR-3H and S3 lineage are qualified

PR-3H now rechecks current AuthorityLease/EffectCapability identity, epoch, revocation generation, holder, operation/bounds, scope/subject, and problem/external revision at the actual inherited Effect authorization and execution boundaries. Earlier capability-use Evidence remains audit evidence only and cannot act as a bearer authorization token.

S3 additionally qualifies explicit causal/freshness/identity/calibration/trust/environment/observation-processing evidence, backend-independent artifact revision lineage, and exact entity evolution. Artifact existence/generation does not create authoritative acceptance; entity `AMBIGUOUS` mappings block hard automatic reuse. Both use existing Evidence/event replay and create no parallel truth/authority/current-state plane.

## Current claim ceilings

The candidate still does not claim:

- quantity/unit interpretation for capability numeric bounds;
- tolerance-aware postcondition verification with dimensional semantics;
- hybrid continuous/discrete safety envelopes;
- universal cross-domain physical-unit inference;
- automatic artifact or entity truth/acceptance by existence, recency, agreement, or generation success.

These are explicit S4 and later integration boundaries."""
    t = replace_section(t, "## PR-3H remains deliberately unimplemented", "## Qualification contexts", replacement, "0.56.1 PR3H/S3")
    anchor = "aasm/physical-preemption-recovery\n"
    extras = "aasm/physical-effect-integration\naasm/identity-calibration-trust\naasm/execution-environment\naasm/observation-epistemics\naasm/artifact-lineage\naasm/entity-evolution\naasm/physical-evidence\naasm/ci-summary\n"
    t = replace_exact(t, anchor, anchor + extras, "0.56.1 contexts")
    save(p, t)


def main() -> None:
    sync_readme()
    sync_roadmap()
    sync_canonical_roadmap()
    sync_ledger()
    sync_current_release()
    sync_candidate_release_note()
    print("S3 documentation synchronization: PASS")


if __name__ == "__main__":
    main()
