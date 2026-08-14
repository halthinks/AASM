from pathlib import Path

p = Path("scripts/check_release_contracts.py")
text = p.read_text()
old = '        "SOLVER_PROOF_CONTRACT_ID", "PROOF_CERTIFIED",\n'
new = '        "SOLVER_PROOF_CONTRACT_ID",\n'
if text.count(old) != 1:
    raise SystemExit(f"expected one invalid inherited-proof token requirement, found {text.count(old)}")
p.write_text(text.replace(old, new, 1))
