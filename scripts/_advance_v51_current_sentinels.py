from pathlib import Path

FILES = [
    "tests/test_v32_trace_conformance.py",
    "tests/test_v37_reasoning.py",
    "tests/test_v38_semantic_dependencies.py",
    "tests/test_v39_typed_capabilities.py",
    "tests/test_v40_hierarchical_memory.py",
    "tests/test_v42_reference_domains.py",
    "tests/test_v44_optimization.py",
    "tests/test_v45_public.py",
    "tests/test_v46_public.py",
    "tests/test_v47_public.py",
    "tests/test_v48_public.py",
    "tests/test_v49_rc_real.py",
]

for name in FILES:
    p = Path(name)
    text = p.read_text()
    if "0.50.0" not in text:
        raise SystemExit(f"{name}: expected current-public 0.50.0 sentinel")
    text = text.replace("0.50.0", "0.51.0")
    text = text.replace("0.26.0", "0.27.0")
    text = text.replace("under_v50", "under_v51")
    text = text.replace("under v50", "under v51")
    text = text.replace("under_v50_composition", "under_v51_composition")
    text = text.replace("v0.50 here", "v0.51 here")
    p.write_text(text)

for name in ("tests/test_v47_public.py", "tests/test_v48_public.py"):
    p = Path(name)
    text = p.read_text()
    import_anchor = "from aasm.runtime_v50 import AASMEngine as V50Engine\n"
    if import_anchor not in text:
        raise SystemExit(f"{name}: missing V50 import anchor")
    text = text.replace(import_anchor, import_anchor + "from aasm.runtime_v51 import AASMEngine as V51Engine\n", 1)
    if "assert AASMEngine is V50Engine" not in text:
        raise SystemExit(f"{name}: missing active-engine identity anchor")
    text = text.replace(
        "assert AASMEngine is V50Engine\n    assert issubclass(V50Engine, V49Engine)",
        "assert AASMEngine is V51Engine\n    assert issubclass(V51Engine, V50Engine)\n    assert issubclass(V50Engine, V49Engine)",
        1,
    )
    p.write_text(text)
