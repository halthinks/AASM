from aasm.conflict_minimization import minimize_conflict_core


class ContainsOracle:
    def __init__(self, required):
        self.required = set(required)

    def conflicts(self, literals):
        values = {row["name"] for row in literals}
        return self.required <= values


def test_original_must_reproduce_conflict():
    oracle = ContainsOracle({"missing"})
    try:
        minimize_conflict_core("c", "e", [{"name": "a"}], oracle)
    except ValueError as exc:
        assert "does not reproduce" in str(exc)
    else:
        raise AssertionError("non-conflicting input was accepted")


def test_exact_mode_finds_empty_root_conflict():
    class RootOracle:
        def conflicts(self, literals):
            return True

    result = minimize_conflict_core(
        "c",
        "e",
        [{"name": "a"}, {"name": "b"}],
        RootOracle(),
        mode="EXACT_BOUNDED",
        max_calls=10,
    )
    assert result.minimized_literals == []
    assert result.minimality == "PROVEN_MINIMAL"
    assert result.metadata["root_conflict"] is True


def test_duplicate_literals_are_canonicalized():
    oracle = ContainsOracle({"a"})
    result = minimize_conflict_core(
        "c",
        "e",
        [{"name": "a"}, {"name": "a"}, {"name": "b"}],
        oracle,
        mode="GREEDY_IRREDUCIBLE",
        max_calls=10,
    )
    assert result.minimized_literals == [{"name": "a"}]
    assert result.metadata["duplicate_count"] == 1


def test_exact_budget_at_natural_boundary_is_complete():
    oracle = ContainsOracle({"a"})
    result = minimize_conflict_core(
        "c",
        "e",
        [{"name": "a"}],
        oracle,
        mode="EXACT_BOUNDED",
        max_calls=2,
    )
    assert result.oracle_calls == 2
    assert result.exhausted is True
    assert result.minimality == "PROVEN_MINIMAL"
