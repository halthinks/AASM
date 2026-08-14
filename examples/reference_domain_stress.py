from __future__ import annotations

import json

from aasm.reference_domains import run_reference_domain_stress


if __name__ == "__main__":
    print(json.dumps(run_reference_domain_stress(), indent=2, sort_keys=True))
