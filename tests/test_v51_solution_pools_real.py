import os

import pytest

from aasm.optimization import OptimizationConstraint, OptimizationModel, OptimizationVariable
from aasm.solution_pool_conformance import run_solution_pool_conformance
from aasm.solution_pools import EnumerationUnsupportedError, enumerate_native_binary_backend


pytestmark = pytest.mark.skipif(
    os.environ.get("AASM_REQUIRE_SOLUTION_POOL_BACKENDS") != "1",
    reason="real v0.51 enumeration backends run in the dedicated solution-pool workflow",
)


def test_real_cp_sat_and_highs_enumerate_exact_same_binary_set():
    report = run_solution_pool_conformance(real_backends=True)
    assert report["status"] == "PASS", report
    assert report["checks"]["real_cp_sat_exhausts"] is True
    assert report["checks"]["real_highs_exhausts"] is True
    assert report["checks"]["real_cross_backend_exact_solution_set"] is True


def test_native_enumerator_rejects_nonbinary_consistency_fixture():
    model = OptimizationModel(
        "integer-native-unsupported",
        (OptimizationVariable("x", "INTEGER", 0, 2),),
        (OptimizationConstraint("LINEAR", coefficients={"x": 1}, sense=">=", rhs=0),),
        family="CP_SAT",
    )
    with pytest.raises(EnumerationUnsupportedError):
        enumerate_native_binary_backend(model, "ortools-cp-sat")
