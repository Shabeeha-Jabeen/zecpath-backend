from django.db import IntegrityError
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from core.reminder_service import create_reminders_for_interview,cancel_pending_reminders

from core.models import (
    Application,
    AvailabilitySlot,
    InterviewSchedule,
)


def get_available_slots(role=None):
    """
    Return future availability slots that are still available
    and have no active interview booking.
    """
    now = timezone.now()

    slots = AvailabilitySlot.objects.filter(
        is_available=True,
        start_time__gte=now,
    ).order_by("start_time")

    if role and role != "ALL":
        slots = slots.filter(role__in=[role, "ALL"])

    booked_slot_ids = InterviewSchedule.objects.exclude(
        status="CANCELLED"
    ).values_list("availability_slot_id", flat=True)

    return slots.exclude(id__in=booked_slot_ids)


@transaction.atomic
def schedule_interview(application_id, slot_id):
    now = timezone.now()

    try:
        application = Application.objects.get(id=application_id)
    except Application.DoesNotExist:
        return {
            "success": False,
            "message": "Application not found.",
        }

    try:
        slot = AvailabilitySlot.objects.select_for_update().get(
            id=slot_id
        )
    except AvailabilitySlot.DoesNotExist:
        return {
            "success": False,
            "message": "Availability slot not found.",
        }

    if not slot.is_available:
        return {
            "success": False,
            "message": "This slot is not available.",
        }

    if slot.start_time <= now:
        return {
            "success": False,
            "message": "Interview slot must be in the future.",
        }

    if slot.end_time <= slot.start_time:
        return {
            "success": False,
            "message": "Invalid slot time range.",
        }

    # Check whether another active interview overlaps this time.
    conflict = InterviewSchedule.objects.filter(
        scheduled_start__lt=slot.end_time,
        scheduled_end__gt=slot.start_time,
    ).exclude(status="CANCELLED").exists()

    if conflict:
        return {
            "success": False,
            "message": "This time overlaps with another booked interview.",
        }

    try:
        with transaction.atomic():
            schedule = InterviewSchedule.objects.create(
                application=application,
                availability_slot=slot,
                scheduled_start=slot.start_time,
                scheduled_end=slot.end_time,
                status="CONFIRMED",
            )
    except IntegrityError:
        return {
            "success": False,
            "message": "This slot has already been booked.",
        }

    email_result = send_interview_confirmation_email(schedule)

    if email_result.get("success"):
        schedule.confirmation_email_sent = True
        schedule.save(update_fields=["confirmation_email_sent"])
    create_reminders_for_interview(schedule)

    return {
        "success": True,
        "schedule_id": schedule.id,
        "application_id": application.id,
        "slot_id": slot.id,
        "scheduled_start": schedule.scheduled_start.isoformat(),
        "scheduled_end": schedule.scheduled_end.isoformat(),
        "status": schedule.status,
        "confirmation_email_sent": schedule.confirmation_email_sent,
    }
def send_interview_confirmation_email(schedule):
    candidate = schedule.application.candidate
    recipient_email = candidate.user.email

    if not recipient_email:
        return {
            "success": False,
            "message": "Candidate email address is missing.",
        }

    subject = "Interview Scheduled - ZecPath"

    message = (
        f"Hello {candidate.user.username},\n\n"
        "Your interview has been scheduled successfully.\n\n"
        f"Job: {schedule.application.job}\n"
        f"Start: {schedule.scheduled_start}\n"
        f"End: {schedule.scheduled_end}\n"
        f"Status: {schedule.status}\n\n"
        "Please be available at the scheduled time.\n\n"
        "Regards,\nZecPath Team"
    )

    sent = send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [recipient_email],
        fail_silently=False,
    )

    if sent:
        return {
            "success": True,
            "message": "Interview confirmation email sent.",
        }

    return {
        "success": False,
        "message": "Email could not be sent.",
    }
@transaction.atomic
def reschedule_interview(schedule_id, new_slot_id):
    try:
        old_schedule = InterviewSchedule.objects.select_for_update().get(
            id=schedule_id
        )
    except InterviewSchedule.DoesNotExist:
        return {
            "success": False,
            "message": "Interview schedule not found.",
        }

    if old_schedule.status == "CANCELLED":
        return {
            "success": False,
            "message": "Cancelled interview cannot be rescheduled.",
        }

    if old_schedule.availability_slot_id == new_slot_id:
        return {
            "success": False,
            "message": "Please select a different slot.",
        }

    try:
        new_slot = AvailabilitySlot.objects.select_for_update().get(
            id=new_slot_id
        )
    except AvailabilitySlot.DoesNotExist:
        return {
            "success": False,
            "message": "New availability slot not found.",
        }

    now = timezone.now()

    if not new_slot.is_available:
        return {
            "success": False,
            "message": "New slot is not available.",
        }

    if new_slot.start_time <= now:
        return {
            "success": False,
            "message": "New slot must be in the future.",
        }

    if new_slot.end_time <= new_slot.start_time:
        return {
            "success": False,
            "message": "Invalid new slot time range.",
        }

    conflict = InterviewSchedule.objects.filter(
        scheduled_start__lt=new_slot.end_time,
        scheduled_end__gt=new_slot.start_time,
    ).exclude(
        status="CANCELLED"
    ).exclude(
        id=old_schedule.id
    ).exists()

    if conflict:
        return {
            "success": False,
            "message": "New slot is already booked.",
        }

    try:
        with transaction.atomic():
            old_schedule.status = "CANCELLED"
            old_schedule.save(update_fields=["status"])
            cancel_pending_reminders(old_schedule)
            new_schedule = InterviewSchedule.objects.create(
                application=old_schedule.application,
                availability_slot=new_slot,
                scheduled_start=new_slot.start_time,
                scheduled_end=new_slot.end_time,
                status="CONFIRMED",
            )
    except IntegrityError:
        return {
            "success": False,
            "message": "New slot has already been booked.",
        }

    email_result = send_interview_confirmation_email(new_schedule)

    if email_result.get("success"):
        new_schedule.confirmation_email_sent = True
        new_schedule.save(update_fields=["confirmation_email_sent"])
        create_reminders_for_interview(new_schedule)
    return {
        "success": True,
        "old_schedule_id": old_schedule.id,
        "new_schedule_id": new_schedule.id,
        "new_slot_id": new_slot.id,
        "status": new_schedule.status,
        "confirmation_email_sent": new_schedule.confirmation_email_sent,
        "message": "Interview rescheduled successfully.",
    }