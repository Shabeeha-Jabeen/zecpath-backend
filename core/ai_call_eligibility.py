from core.tasks import trigger_ai_call_task
from datetime import datetime, time, timedelta
from django.utils import timezone
import uuid


from core.models import AICallLog
from core.models import Application, ATSScore


def check_ai_call_eligibility(application_id):
    """
    Check whether an application is eligible for an AI call.
    """

    try:
        application = Application.objects.select_related(
            "candidate__user",
            "job",
        ).get(id=application_id)
    except Application.DoesNotExist:
        return {
            "eligible": False,
            "reason": "Application not found.",
        }

    job = application.job

    # 1. Job must be open.
    if job.status != "OPEN":
        return {
            "eligible": False,
            "reason": "Job is not open.",
        }

    # 2. Job deadline must not have passed.
    if job.deadline < timezone.localdate():
        return {
            "eligible": False,
            "reason": "Job deadline has passed.",
        }

    # 3. Application must be shortlisted.
    if application.status != "SHORTLISTED":
        return {
            "eligible": False,
            "reason": "Application is not shortlisted.",
        }

    # 4. Candidate account must be active.
    if not application.candidate.user.is_active:
        return {
            "eligible": False,
            "reason": "Candidate account is inactive.",
        }
    if not application.candidate.is_available_for_ai_call:
        return {
            "eligible": False,
            "reason": "Candidate is not available for AI calls.",
        }
    # 5. ATS score must exist.
    try:
        ats_score = application.ats_score
    except ATSScore.DoesNotExist:
        return {
            "eligible": False,
            "reason": "ATS score not found.",
        }

    # 6. ATS score must meet the job's cutoff.
    if ats_score.match_percentage < job.ats_cutoff:
        return {
            "eligible": False,
            "reason": (
                f"ATS score {ats_score.match_percentage}% is below "
                f"the required cutoff {job.ats_cutoff}%."
            ),
        }

    return {
        "eligible": True,
        "reason": "Candidate is eligible for an AI call.",
        "application_id": application.id,
        "candidate_id": application.candidate_id,
        "job_id": job.id,
        "ats_score": ats_score.match_percentage,
    }



def is_ai_call_time_allowed():
    """
    Allow AI call scheduling between 9 AM and 6 PM IST.
    """
    current_time = timezone.localtime().time()

    start_time = time(9, 0)
    end_time = time(18, 0)

    return start_time <= current_time < end_time
def get_next_ai_call_time():
    """
    Return the next allowed AI call time: 9 AM to 6 PM.
    """
    now = timezone.localtime()
    start_time = time(9, 0)
    end_time = time(18, 0)

    if now.time() < start_time:
        next_date = now.date()
    elif now.time() >= end_time:
        next_date = now.date() + timedelta(days=1)
    else:
        return now

    next_datetime = datetime.combine(next_date, start_time)
    return timezone.make_aware(
        next_datetime,
        timezone.get_current_timezone(),
    )


def auto_trigger_ai_call(application_id):
    """
    Check eligibility, create a call log, and schedule the task.
    """
    result = check_ai_call_eligibility(application_id)

    if not result["eligible"]:
        return {
            "triggered": False,
            "reason": result["reason"],
        }

    scheduled_time = get_next_ai_call_time()
    task_id = str(uuid.uuid4())

    call_log = AICallLog.objects.create(
        application_id=result["application_id"],
        status="QUEUED",
        celery_task_id=task_id,
        scheduled_at=scheduled_time,
    )

    try:
        trigger_ai_call_task.apply_async(
            args=[
                result["candidate_id"],
                result["job_id"],
                result["application_id"],
            ],
            task_id=task_id,
            eta=scheduled_time,
        )
    except Exception as exc:
        call_log.status = "FAILED"
        call_log.error_message = str(exc)
        call_log.save(
            update_fields=[
                "status",
                "error_message",
                "updated_at",
            ]
        )
        return {
            "triggered": False,
            "reason": "Failed to schedule AI call task.",
            "error": str(exc),
            "call_log_id": call_log.id,
        }

    return {
        "triggered": True,
        "message": "AI call task scheduled successfully.",
        "task_id": task_id,
        "call_log_id": call_log.id,
        "application_id": result["application_id"],
        "scheduled_at": scheduled_time.isoformat(),
    }
