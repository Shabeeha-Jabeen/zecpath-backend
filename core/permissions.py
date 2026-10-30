
from django.utils import timezone
from rest_framework.permissions import BasePermission

from .models import UserSubscription


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "ADMIN"
        )


class IsEmployer(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "EMPLOYER"
        )


class IsCandidate(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "CANDIDATE"
        )


class IsPlatformAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and user.role == "ADMIN"
            and user.is_staff
        )


def get_active_subscription(user):
    """Return the user's latest currently active subscription."""
    now = timezone.now()

    return (
        UserSubscription.objects
        .filter(
            user=user,
            status="ACTIVE",
            plan__is_active=True,
        )
        .filter(
            models_Q_end_date(now)
        )
        .select_related("plan")
        .order_by("-created_at")
        .first()
    )


def models_Q_end_date(now):
    from django.db.models import Q

    return Q(end_date__isnull=True) | Q(end_date__gt=now)


def user_has_feature(user, feature_name):
    """Check whether the active subscription includes a feature."""
    subscription = get_active_subscription(user)

    if subscription is None:
        return False

    return bool(subscription.plan.features.get(feature_name, False))


class HasRecruiterAnalyticsAccess(BasePermission):
    """Allow recruiters with PRO or ENTERPRISE subscriptions."""

    message = (
        "An active PRO or ENTERPRISE subscription is required "
        "to access recruiter analytics."
    )

    def has_permission(self, request, view):
        user = request.user

        if not (
            user
            and user.is_authenticated
            and user.role == "EMPLOYER"
        ):
            return False

        subscription = get_active_subscription(user)

        return (
            subscription is not None
            and subscription.plan.name in ("PRO", "ENTERPRISE")
        )


class HasAIAnalyticsAccess(BasePermission):
    """Allow recruiters with an active ENTERPRISE subscription."""

    message = (
        "An active ENTERPRISE subscription is required "
        "to access AI analytics."
    )

    def has_permission(self, request, view):
        user = request.user

        if not (
            user
            and user.is_authenticated
            and user.role == "EMPLOYER"
        ):
            return False

        subscription = get_active_subscription(user)

        return (
            subscription is not None
            and subscription.plan.name == "ENTERPRISE"
        )
