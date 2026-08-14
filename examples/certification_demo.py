from aasm import run_certification


report = run_certification()
print("core_status:", report["core_status"])
print("combined_status:", report["status"])
for target in report["targets"]:
    print(target["target_id"], target["status"])

# v0.43 core targets are expected to certify.  The combined report remains
# INCONCLUSIVE until the experimental v0.44 SII graduation gates are closed.
assert report["core_status"] == "PASS"
assert report["status"] == "INCONCLUSIVE"
