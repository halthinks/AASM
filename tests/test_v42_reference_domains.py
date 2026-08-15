import pytest

from aasm import __version__, validate_public_api_contract
from aasm.cli import build_parser
from aasm.reference_domains import (
    REFERENCE_DOMAIN_IDS,
    reference_domain_contract,
    run_reference_domain_stress,
)


def test_v42_public_and_cli_surfaces_are_active():
    assert __version__ == "0.53.0"
    report = validate_public_api_contract()
    assert report["valid"] is True, report
    assert report["contract"]["contract_version"] == "0.29.0"
    assert report["contract"]["reference_domains"]["contract_id"] == "aasm.reference-domains.v1"
    help_text = build_parser().format_help()
    assert "reference-domain-contract" in help_text
    assert "reference-domain-stress" in help_text


def test_reference_domain_contract_is_offline_and_kernel_neutral():
    contract = reference_domain_contract()
    assert contract["contract_id"] == "aasm.reference-domains.v1"
    assert contract["authority"] == "REFERENCE_HARNESS_ONLY"
    assert contract["kernel_changes"] == "NONE"
    assert contract["network_required"] is False
    assert contract["model_key_required"] is False
    assert tuple(contract["domains"]) == REFERENCE_DOMAIN_IDS


@pytest.mark.parametrize("domain_id", REFERENCE_DOMAIN_IDS)
def test_each_reference_domain_exercises_its_boundaries(domain_id):
    report = run_reference_domain_stress(domain_id)
    assert report["domain_count"] == 1
    assert report["passed"] is True, report
    assert report["checks_total"] == report["checks_passed"]
    assert report["domains"][0]["domain_id"] == domain_id
    assert report["domains"][0]["passed"] is True


def test_full_reference_domain_stress_suite_passes_all_domains():
    report = run_reference_domain_stress()
    assert report["passed"] is True, report
    assert report["domain_count"] == len(REFERENCE_DOMAIN_IDS)
    assert report["checks_total"] == report["checks_passed"]
    assert [row["domain_id"] for row in report["domains"]] == list(REFERENCE_DOMAIN_IDS)


def test_unknown_reference_domain_is_rejected():
    with pytest.raises(ValueError, match="unknown reference domain"):
        run_reference_domain_stress("not-a-domain")
