"""Tests for subscription quota manager.

Covers the key bug fix: users who just purchased Pro+ should NOT immediately
see "quota used up" – their usage must be reset to 0 upon activation.
"""

import pytest
from datetime import datetime, timezone

from quota_manager import (
    QuotaConfig,
    QuotaExceededError,
    QuotaManager,
    Subscription,
    SubscriptionTier,
)


# ---------------------------------------------------------------------------
# QuotaConfig
# ---------------------------------------------------------------------------

class TestQuotaConfig:
    def test_free_tier_limit(self):
        config = QuotaConfig.for_tier(SubscriptionTier.FREE)
        assert config.monthly_limit == 100

    def test_pro_plus_tier_limit(self):
        config = QuotaConfig.for_tier(SubscriptionTier.PRO_PLUS)
        assert config.monthly_limit == 10_000


# ---------------------------------------------------------------------------
# Subscription model
# ---------------------------------------------------------------------------

class TestSubscription:
    def _make(self, tier=SubscriptionTier.PRO_PLUS, usage=0) -> Subscription:
        now = datetime.now(tz=timezone.utc)
        return Subscription(
            user_id="u1",
            tier=tier,
            activated_at=now,
            current_period_start=now,
            usage=usage,
        )

    def test_remaining_quota_full(self):
        sub = self._make(usage=0)
        assert sub.remaining_quota == 10_000

    def test_remaining_quota_partial(self):
        sub = self._make(usage=1_000)
        assert sub.remaining_quota == 9_000

    def test_remaining_quota_never_negative(self):
        sub = self._make(usage=99_999)
        assert sub.remaining_quota == 0

    def test_is_quota_exceeded_false(self):
        sub = self._make(usage=9_999)
        assert not sub.is_quota_exceeded

    def test_is_quota_exceeded_true(self):
        sub = self._make(usage=10_000)
        assert sub.is_quota_exceeded


# ---------------------------------------------------------------------------
# QuotaManager – core bug fix
# ---------------------------------------------------------------------------

class TestQuotaManagerActivation:
    """
    Regression tests for the bug: "just bought Pro+ but immediately see
    quota used up."

    Root cause: the usage counter was not reset when a subscription was
    activated/upgraded. The fix resets usage to 0 on every activation.
    """

    def test_new_pro_plus_starts_with_zero_usage(self):
        manager = QuotaManager()
        sub = manager.activate_subscription("user1", SubscriptionTier.PRO_PLUS)
        assert sub.usage == 0

    def test_new_pro_plus_has_full_quota_available(self):
        manager = QuotaManager()
        manager.activate_subscription("user1", SubscriptionTier.PRO_PLUS)
        assert manager.check_quota("user1") is True

    def test_upgrade_from_free_resets_usage(self):
        """
        A user who exhausted their Free quota and then upgrades to Pro+
        must NOT immediately see "quota used up" on the Pro+ plan.
        """
        manager = QuotaManager()

        # Exhaust the free quota
        manager.activate_subscription("user1", SubscriptionTier.FREE)
        free_sub = manager.get_subscription("user1")
        free_sub.usage = free_sub.quota_config.monthly_limit  # exhaust quota

        # Confirm quota is exceeded on free tier
        assert not manager.check_quota("user1")

        # User upgrades to Pro+
        manager.activate_subscription("user1", SubscriptionTier.PRO_PLUS)

        # After upgrade, quota must no longer be exceeded
        assert manager.check_quota("user1") is True
        pro_sub = manager.get_subscription("user1")
        assert pro_sub.usage == 0

    def test_new_subscription_has_pro_plus_limit(self):
        manager = QuotaManager()
        manager.activate_subscription("user1", SubscriptionTier.PRO_PLUS)
        sub = manager.get_subscription("user1")
        assert sub.quota_config.monthly_limit == 10_000

    def test_activation_stores_correct_tier(self):
        manager = QuotaManager()
        manager.activate_subscription("user1", SubscriptionTier.PRO_PLUS)
        sub = manager.get_subscription("user1")
        assert sub.tier == SubscriptionTier.PRO_PLUS


# ---------------------------------------------------------------------------
# QuotaManager – record_usage
# ---------------------------------------------------------------------------

class TestQuotaManagerUsage:
    def test_record_usage_increments_counter(self):
        manager = QuotaManager()
        manager.activate_subscription("user1", SubscriptionTier.PRO_PLUS)
        manager.record_usage("user1", amount=5)
        sub = manager.get_subscription("user1")
        assert sub.usage == 5

    def test_record_usage_raises_when_quota_exceeded(self):
        manager = QuotaManager()
        manager.activate_subscription("user1", SubscriptionTier.FREE)
        sub = manager.get_subscription("user1")
        sub.usage = sub.quota_config.monthly_limit  # exhaust

        with pytest.raises(QuotaExceededError):
            manager.record_usage("user1")

    def test_record_usage_raises_for_unknown_user(self):
        manager = QuotaManager()
        with pytest.raises(ValueError, match="No subscription found"):
            manager.record_usage("unknown_user")

    def test_check_quota_raises_for_unknown_user(self):
        manager = QuotaManager()
        with pytest.raises(ValueError, match="No subscription found"):
            manager.check_quota("unknown_user")


# ---------------------------------------------------------------------------
# QuotaManager – period reset
# ---------------------------------------------------------------------------

class TestQuotaManagerPeriodReset:
    def test_reset_period_usage_clears_counter(self):
        manager = QuotaManager()
        manager.activate_subscription("user1", SubscriptionTier.PRO_PLUS)
        sub = manager.get_subscription("user1")
        sub.usage = 5_000

        manager.reset_period_usage("user1")

        assert sub.usage == 0

    def test_reset_period_updates_period_start(self):
        manager = QuotaManager()
        manager.activate_subscription("user1", SubscriptionTier.PRO_PLUS)
        sub = manager.get_subscription("user1")
        old_start = sub.current_period_start

        manager.reset_period_usage("user1")

        assert sub.current_period_start >= old_start
