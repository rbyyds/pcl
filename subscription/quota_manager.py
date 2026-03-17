"""
Subscription Quota Manager

Handles quota initialization and validation for subscription tiers.

Bug fix: Users who just purchased Pro+ were immediately shown "quota used up"
because the quota was not properly reset/initialized when a new subscription
was activated. This module ensures that on subscription activation (including
upgrades), the current period usage is reset and the new quota limits apply.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class SubscriptionTier(Enum):
    FREE = "free"
    PRO_PLUS = "pro_plus"


@dataclass
class QuotaConfig:
    """Quota limits per subscription tier."""
    tier: SubscriptionTier
    monthly_limit: int

    @classmethod
    def for_tier(cls, tier: SubscriptionTier) -> "QuotaConfig":
        limits = {
            SubscriptionTier.FREE: 100,
            SubscriptionTier.PRO_PLUS: 10_000,
        }
        return cls(tier=tier, monthly_limit=limits[tier])


@dataclass
class Subscription:
    """Represents a user's active subscription."""
    user_id: str
    tier: SubscriptionTier
    activated_at: datetime
    current_period_start: datetime
    usage: int = 0

    @property
    def quota_config(self) -> QuotaConfig:
        return QuotaConfig.for_tier(self.tier)

    @property
    def remaining_quota(self) -> int:
        return max(0, self.quota_config.monthly_limit - self.usage)

    @property
    def is_quota_exceeded(self) -> bool:
        return self.usage >= self.quota_config.monthly_limit


class QuotaManager:
    """
    Manages subscription quotas for users.

    Key fix: When a subscription is activated or upgraded (e.g., to Pro+),
    the usage counter is reset to 0 for the new billing period, preventing
    the scenario where users who just purchased Pro+ immediately see
    "quota used up" due to leftover usage from their previous tier.
    """

    def __init__(self) -> None:
        self._subscriptions: dict[str, Subscription] = {}

    def activate_subscription(
        self,
        user_id: str,
        tier: SubscriptionTier,
        activated_at: Optional[datetime] = None,
    ) -> Subscription:
        """
        Activate or upgrade a subscription for a user.

        On activation, the usage is reset to 0 so that the user benefits from
        their new quota immediately without being affected by prior usage from
        a different tier or period.
        """
        now = activated_at or datetime.now(tz=timezone.utc)
        subscription = Subscription(
            user_id=user_id,
            tier=tier,
            activated_at=now,
            current_period_start=now,
            usage=0,  # Reset usage on new subscription/upgrade
        )
        self._subscriptions[user_id] = subscription
        return subscription

    def get_subscription(self, user_id: str) -> Optional[Subscription]:
        """Return the active subscription for a user, or None if not found.

        Use :meth:`check_quota` or :meth:`record_usage` when you need an
        error raised for missing subscriptions instead of a None return.
        """
        return self._subscriptions.get(user_id)

    def check_quota(self, user_id: str) -> bool:
        """
        Return True if the user has remaining quota, False if exhausted.

        Raises ValueError if no subscription is found for the user.
        """
        subscription = self._subscriptions.get(user_id)
        if subscription is None:
            raise ValueError(f"No subscription found for user '{user_id}'")
        return not subscription.is_quota_exceeded

    def record_usage(self, user_id: str, amount: int = 1) -> None:
        """
        Record usage for a user.

        Raises ValueError if no subscription exists.
        Raises QuotaExceededError if the user's quota is already exhausted.
        """
        subscription = self._subscriptions.get(user_id)
        if subscription is None:
            raise ValueError(f"No subscription found for user '{user_id}'")
        if subscription.is_quota_exceeded:
            raise QuotaExceededError(
                user_id=user_id,
                tier=subscription.tier,
                limit=subscription.quota_config.monthly_limit,
            )
        subscription.usage += amount

    def reset_period_usage(self, user_id: str) -> None:
        """Reset the usage counter at the start of a new billing period."""
        subscription = self._subscriptions.get(user_id)
        if subscription is None:
            raise ValueError(f"No subscription found for user '{user_id}'")
        subscription.usage = 0
        subscription.current_period_start = datetime.now(tz=timezone.utc)


class QuotaExceededError(Exception):
    """Raised when a user attempts to use more than their allowed quota."""

    def __init__(
        self,
        user_id: str,
        tier: SubscriptionTier,
        limit: int,
    ) -> None:
        self.user_id = user_id
        self.tier = tier
        self.limit = limit
        super().__init__(
            f"Quota exceeded for user '{user_id}' on tier '{tier.value}' "
            f"(limit: {limit})"
        )
