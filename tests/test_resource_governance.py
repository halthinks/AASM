from datetime import datetime, timedelta, timezone

import pytest

from aasm.resource_governance import (
    CapacityWindowKind,
    MeasurementAuthority,
    ResourceCapacity,
    ResourceDemandEstimate,
    ResourceObservation,
)


def test_weekly_subscription_capacity_protects_reserve_and_settles_actual_use():
    reset = datetime(2026, 8, 18, tzinfo=timezone.utc)
    observation = ResourceObservation(
        resource_id="codex-weekly",
        observed_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
        source="provider_usage_surface",
        measurement_authority=MeasurementAuthority.OBSERVED,
        reported_capacity=100.0,
        reported_consumed=60.0,
        reported_remaining=40.0,
        confidence=0.95,
    )
    capacity = ResourceCapacity(
        resource_id="codex-weekly",
        resource_class="SUBSCRIPTION_ALLOWANCE",
        unit="percent",
        provider="openai",
        window_kind=CapacityWindowKind.FIXED,
        total=100.0,
        consumed=60.0,
        protected_reserve=20.0,
        resets_at=reset,
        latest_observation=observation,
    )

    assert capacity.allocatable == 20.0
    assert capacity.can_reserve(20.0)
    assert not capacity.can_reserve(20.01)

    capacity.reserve(10.0)
    assert capacity.committed == 10.0
    assert capacity.allocatable == 10.0

    capacity.settle(reserved_amount=10.0, actual_consumption=7.0)
    assert capacity.committed == 0.0
    assert capacity.consumed == 67.0
    assert capacity.allocatable == 13.0


def test_unknown_capacity_fails_closed_for_reservation():
    capacity = ResourceCapacity(
        resource_id="unknown-provider-quota",
        resource_class="SUBSCRIPTION_ALLOWANCE",
        unit="credits",
    )

    assert capacity.allocatable is None
    assert capacity.can_reserve(1.0) is False
    with pytest.raises(ValueError, match="insufficient allocatable capacity"):
        capacity.reserve(1.0)


def test_observation_keeps_epistemic_authority_explicit():
    observed = ResourceObservation(
        resource_id="quota",
        observed_at=datetime.now(timezone.utc),
        source="user_report",
        measurement_authority=MeasurementAuthority.DECLARED,
        reported_remaining=25.0,
        confidence=0.6,
    )
    authoritative = ResourceObservation(
        resource_id="quota",
        observed_at=datetime.now(timezone.utc),
        source="provider_api",
        measurement_authority=MeasurementAuthority.AUTHORITATIVE,
        reported_remaining=25.0,
    )

    assert observed.is_authoritative is False
    assert authoritative.is_authoritative is True


def test_resource_demand_estimate_supports_expected_and_upper_bound_use():
    estimate = ResourceDemandEstimate(
        resource_class="MODEL",
        resource_id="expert-model",
        amount=8.0,
        upper_bound=15.0,
        unit="provider_units",
        confidence=0.8,
    )

    assert estimate.amount == 8.0
    assert estimate.upper_bound == 15.0

    with pytest.raises(ValueError, match="upper_bound"):
        ResourceDemandEstimate(
            resource_class="MODEL",
            amount=8.0,
            upper_bound=7.0,
            unit="provider_units",
        )


def test_reset_horizon_is_explicit_and_timezone_safe():
    reset = datetime(2026, 8, 18, tzinfo=timezone.utc)
    now = reset - timedelta(hours=6)
    capacity = ResourceCapacity(
        resource_id="weekly",
        resource_class="SUBSCRIPTION_ALLOWANCE",
        unit="percent",
        window_kind=CapacityWindowKind.FIXED,
        total=100.0,
        resets_at=reset,
    )

    assert capacity.seconds_until_reset(now=now) == 6 * 60 * 60
