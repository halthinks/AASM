import io
import json
from contextlib import redirect_stdout

from aasm import public_v51
from aasm.cli_v51 import build_parser, main
from aasm.runtime_v50 import AASMEngine as V50Engine
from aasm.runtime_v51 import AASMEngine as V51Engine


def test_v51_public_contract_is_valid_before_activation():
    assert public_v51.__version__ == "0.51.0"
    assert public_v51.AASMEngine is V51Engine
    assert issubclass(V51Engine, V50Engine)
    report = public_v51.validate_public_api_contract()
    assert report["valid"], report
    contract = report["contract"]
    assert contract["contract_version"] == "0.27.0"
    assert contract["runtime_version"] == "0.51.0"
    assert contract["solution_pool"]["contract_id"] == "aasm.optimization.solution-pool.v1"
    assert contract["enumeration"]["contract_id"] == "aasm.optimization.enumeration.v1"
    assert contract["solution_pool"]["complete_requires_independent_exhaustion_certificate"] is True
    assert contract["solution_pool"]["bounded_or_native_pool_implies_completeness"] is False


def test_v51_cli_contract_surfaces_emit_clean_json():
    help_text = build_parser().format_help()
    for command in ("solution-pool-contract", "enumeration-contract", "solution-pool-conformance"):
        assert command in help_text
    for argv in (["solution-pool-contract"], ["enumeration-contract"], ["solution-pool-conformance"]):
        stream = io.StringIO()
        with redirect_stdout(stream):
            main(argv)
        json.loads(stream.getvalue())
