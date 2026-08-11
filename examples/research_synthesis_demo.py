from __future__ import annotations

import argparse
import json
from pathlib import Path

from aasm import SQLiteStore, run_research_synthesis_demo


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the deterministic, offline AASM research-synthesis hero stack."
    )
    parser.add_argument("--db", default="research-demo.db")
    parser.add_argument("--mode", choices=["setup", "complete"], default="complete")
    parser.add_argument("--output-dir", default="research-output")
    args = parser.parse_args()

    store = SQLiteStore(args.db)
    try:
        result = run_research_synthesis_demo(
            store=store,
            mode=args.mode,
            output_dir=Path(args.output_dir),
        )
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True, default=str))
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
