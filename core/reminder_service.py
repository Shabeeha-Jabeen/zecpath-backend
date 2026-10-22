from datetime import timedelta

from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from core.models import InterviewReminder


REMINDER_OFFSETS = {
    "24_HOURS": timedelta(hours=24),
    "1_HOUR": timedelta(hours=1),
}

MAX_RETRIES = 3


def create_reminders_for_interview(interview):
    """
    Create reminder records for a confirmed future interview.
    """

    if interview.status != "CONFIRMED":
        return []

    now = timezone.now()
    created_reminders = []

    for stage, offset in REMINDER_OFFSETS.items():
        scheduled_at = interview.scheduled_start - offset

        if scheduled_at <= now:
            continue

        reminder, created = InterviewReminder.objects.get_or_create(
            interview=interview,
            stage=stage,
            defaults={
                "scheduled_at": scheduled_at,
                "status": "PENDING",
            },
        )

        if created:
            created_reminders.append(reminder)

    return created_reminders

def cancel_pending_reminders(interview):
    return InterviewReminder.objects.filter(
        interview=interview,
        status="PENDING",
    ).update(status="CANCELLED")

def send_reminder_email(reminder):
    """
    Send a reminder email to the interview candidate.
    """

    interview = reminder.interview
    candidate = interview.application.candidate
    recipient_email = candidate.user.email

    if not recipient_email:
        raise ValueError("Candidate email address is missing.")

    subject = "Interview Reminder - ZecPath"

    message = (
        f"Hello {candidate.user.username},\n\n"
        "This is a reminder for your upcoming interview.\n\n"
        f"Job: {interview.application.job}\n"
        f"Start: {interview.scheduled_start}\n"
        f"End: {interview.scheduled_end}\n\n"
        "Please be available at the scheduled time.\n\n"
        "Regards,\nZecPath Team"
    )

    return send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [recipient_email],
        fail_silently=False,
    )


def process_due_reminders():
    """
    Process due reminders and retry failed attempts up to MAX_RETRIES.
    """

    now = timezone.now()

    reminders = InterviewReminder.objects.filter(
        status__in=["PENDING", "FAILED"],
        scheduled_at__lte=now,
        attempts__lt=MAX_RETRIES,
        interview__status="CONFIRMED",
    ).select_related(
        "interview__application__candidate__user",
        "interview__application__job",
    ).order_by("scheduled_at")

    results = {
        "processed": 0,
        "sent": 0,
        "failed": 0,
    }

    for reminder in reminders:
        results["processed"] += 1
        reminder.attempts += 1

        try:
            sent = send_reminder_email(reminder)

            if sent:
                reminder.status = "SENT"
                reminder.sent_at = timezone.now()
                reminder.last_error = ""
                results["sent"] += 1
            else:
                reminder.status = "FAILED"
                reminder.last_error = "Email backend did not send the message."
                results["failed"] += 1

        except Exception as exc:
            reminder.status = "FAILED"
            reminder.last_error = str(exc)
            results["failed"] += 1

        reminder.save(
            update_fields=[
                "status",
                "attempts",
                "sent_at",
                "last_error",
            ]
        )

    return results