import logging

from core.models import AdminAuditLog

logger = logging.getLogger("core")


def record_audit(
    action,
    details="",
    user=None,
):
    """
    Record a user, admin, or AI-related action
    in the audit table.
    """
    try:
        AdminAuditLog.objects.create(
            admin=user,
            actor=user,
            action=action,
            details=details,
        )

        logger.info(
            "Audit event recorded: action=%s actor_id=%s",
            action,
            getattr(user, "id", None),
        )

    except Exception:
        logger.exception(
            "Failed to record audit event: action=%s",
            action,
        )