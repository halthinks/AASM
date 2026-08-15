# AASM Governed Semantic Evolution — Source Lock Manifest

**Lock date:** 2026-08-15  
**Live baseline evaluated:** `e7322e0827009e094c849ca8a3b218534f41b924` (`v0.54.0`)  
**Purpose:** prevent implementation drift by fixing the exact source set, its precedence, and immutable hashes.

## Canonical implementation doctrine

1. `docs/architecture/GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md`
   - initial doctrine commit: `84891869c3fc0e53c97d98287318d2b1ed80db16`
2. `docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md`
   - initial roadmap commit: `b03ebb3b0f4f480eca1e0f85a5e3a5d5b91aba98`
3. `docs/implementation/GOVERNED_SEMANTIC_EVOLUTION_EXECUTION_LEDGER.md`
   - live status ledger; may advance status/evidence but may not delete source requirements.

The whitepaper defines architecture and invariants. The roadmap defines work packages, ordering, dependencies, and release claims. The execution ledger is the mutable progress projection over those locked requirements.

## Immutable supplied/research source fingerprints

| Source | SHA-256 |
|---|---|
| `Pasted markdown(1).md` — TextPCB AASM requirements | `59340a1620bc4be7b20c981fb6fb023c79e44862a35e84d7564ff86375efd560` |
| `Pasted markdown (2)(1).md` — TextPCB builder gap-closure work packages | `7e58621fcba1b90c70bf9da4f64913845cc6648b343095429f4d2992a3c1531c` |
| `AASM_TEXTPCB_CAD_PCB_DEEP_RESEARCH_AND_ARCHITECTURE.md` | `fa6e091524c6595724a983c72063136515cd6129362e7785aa156f6e9d07b23a` |
| `AASM_TEXTPCB_IMPLEMENTATION_ROADMAP_HANDOFF.md` | `51eb917f9d1525fc7371991097df4ff99fc2e464c593bc84a05cccfcd8dbd42e` |
| `AASM_SEMANTIC_PROBLEM_MODEL_WHITEPAPER(1).md` | `c34a52cab5765940981a75c33df078d2614d3c176e32b09766742abe2038f9ac` |
| `AASM_SEMANTIC_SOLVER_IMPLEMENTATION_HANDOFF(1).md` | `a3aa5bb28c1f1c7dee511b8a4bfc1bc8b8d36a384774a61a44159b3b28bbaba9` |
| `AASM_architecture_chat_transcript(1).md` | `1899a0fbbc3298d30ed3c6733e9e33f5e373cff749780d4c896af7c052fdee84` |
| `AASM_SOURCE_CHAT_6a78169c_FULL_TRANSCRIPT (1).md` | `155e9cb6de68718e0c52af0f88fe96a9232687595cc9d382cfd7c88ff949cad8` |
| `AASM_TextPCB_Research_Package.zip` | `cfa3f1b48837b47dc8a5def1cb8dcfb7554bc3366912c2954f9400e5905b504a` |
| `AASM_SEMANTIC_SOLVER_WHITEPAPER_AND_HANDOFF(1).zip` | `4b2db2084a8024b1bf9300262dc5da900314287385b6ca26b73190e8afa79570` |

## Source precedence

When sources appear to conflict:

1. **Released/live AASM code** determines what is already implemented and what released contracts must remain compatible.
2. **Locked semantic-problem / semantic-solver invariants** determine architecture boundaries: one truth path, proposal/commit separation, no alternate runtime truth, explicit admission, append-only provenance, deterministic/fail-closed authority.
3. **Locked TextPCB requirement sources** determine the capabilities the public AASM engine must expose so the separate TextPCB adapter can qualify.
4. **Locked AASM × TextPCB research** generalizes those requirements to CAD/PCB/CAE and external-machine control.
5. **Canonical governed-semantic-evolution whitepaper** reconciles the above against the current live baseline and is the implementation doctrine.
6. **Canonical roadmap** determines release ordering and acceptance gates.

A later implementation discovery may refine a mechanism, but it may not erase a locked product requirement. If a mechanism changes, update the whitepaper/roadmap with an explicit rationale and add a new source-lock entry; never silently reinterpret the old source.

## No-drift rules

- Never overwrite or mutate an immutable supplied-source snapshot under the same identity/hash.
- A changed source is a new source revision with a new hash and an explicit reconciliation note.
- Roadmap items are append-preserving: requirements may be split or refined, but not dropped without an explicit supersession record explaining where the requirement moved and why.
- “Implemented” means code plus acceptance/adversarial evidence; “released” additionally requires the declared release gate.
- New code must compose through existing AASM authority, Evidence, TaskLease, resource, effect, persistence, and replay paths rather than bypassing them.
- TextPCB remains outside the kernel. Generic AASM semantics are qualified by a TextPCB adapter/conformance corpus.
- Resource scarcity may alter strategy, not hard semantics or evidence requirements.
- A result bound to a superseded semantic or external-machine revision remains historical Evidence only unless applicability is independently re-established.

## Source-storage note

The original supplied files and the prior research package are retained under the hashes above as the immutable project source set. The readable, reconciled repository-native implementation references are the canonical whitepaper and roadmap. Builders must compare any reintroduced source copy against this manifest before treating it as the same source.
