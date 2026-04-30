import pytest
from utils.billing_client import (
    QuotaExceededError,
    check_analysis_quota,
    get_analysis_minutes_limit,
)


def test_free_plan_limit_is_240():
    assert get_analysis_minutes_limit("free") == 240


def test_paid_plans_are_unlimited():
    assert get_analysis_minutes_limit(plan="solo") is None
    assert get_analysis_minutes_limit(plan="team") is None
    assert get_analysis_minutes_limit(plan="unlimited") is None


def test_quota_passes_when_under_limit():
    check_analysis_quota(plan="free", used_minutes=200, incoming_minutes=30)


def test_quota_raises_when_exceeded():
    with pytest.raises(QuotaExceededError):
        check_analysis_quota(plan="free", used_minutes=230, incoming_minutes=20)


def test_quota_raises_when_exactly_at_limit():
    with pytest.raises(QuotaExceededError):
        check_analysis_quota(plan="free", used_minutes=240, incoming_minutes=1)


def test_quota_passes_for_unlimited_plan():
    check_analysis_quota(plan="solo", used_minutes=99999, incoming_minutes=100)
