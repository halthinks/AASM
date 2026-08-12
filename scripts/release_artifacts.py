from __future__ import annotations

"""Public release-artifact CLI and compatibility import surface."""

from pathlib import Path
import sys

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from release_artifacts_core import *  # noqa: F401,F403,E402
from release_artifacts_github import *  # noqa: F401,F403,E402
from release_artifacts_cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
