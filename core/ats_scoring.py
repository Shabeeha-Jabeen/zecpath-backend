from core.models import ATSScore, Application, ApplicationStatusHistory,EmailDeliveryLog
from django.conf import settings
from django.core.mail import send_mail
def normalize_items(value):
    """Convert comma/newline-separated text into normalized items."""
    return {
        item.strip().casefold()
        for item in value.replace("\n", ",").split(",")
        if item.strip()
    }


def calculate_ats_score(candidate, job):
    # 1. Skills score: 60%
    candidate_skills = normalize_items(candidate.skills)
    required_skills = normalize_items(job.skills)

    if required_skills:
        matched_skills = candidate_skills & required_skills
        skills_score = (
            len(matched_skills) / len(required_skills)
        ) * 100
    else:
        matched_skills = set()
        skills_score = None

    # 2. Experience score: 25%
    required_experience = job.experience_required

    if required_experience > 0:
        experience_score = min(
            candidate.experience / required_experience * 100,
            100
        )
    else:
        experience_score = 100

    # 3. Education score: 15%
    required_education = job.education_required.strip().casefold()
    candidate_education = candidate.education.strip().casefold()

    if required_education:
        education_score = (
            100
            if required_education in candidate_education
            else 0
        )
    else:
        education_score = None

    # Normalize weights when a criterion is not provided
    weighted_total = 0
    active_weight = 0

    if skills_score is not None:
        weighted_total += skills_score * 60
        active_weight += 60

    weighted_total += experience_score * 25
    active_weight += 25

    if education_score is not None:
        weighted_total += education_score * 15
        active_weight += 15

    match_percentage = round(weighted_total / active_weight, 2)

    return {
        "match_percentage": match_percentage,
        "skills_score": (
            round(skills_score, 2)
            if skills_score is not None else None
        ),
        "matched_skills": sorted(matched_skills),
        "missing_skills": sorted(required_skills - candidate_skills),
        "experience_score": round(experience_score, 2),
        "education_score": education_score,
    }


def auto_shortlist_application(application):
    try:
        ats_score = application.ats_score
    except ATSScore.DoesNotExist:
        return {
            "success": False,
            "message": "ATS score not found for this application.",
        }

    job = application.job
    cutoff = job.ats_cutoff
    score = ats_score.match_percentage

    if application.status in ["SHORTLISTED", "REJECTED", "SELECTED"]:
        return {
            "success": False,
            "message": "Application already has a final status.",
            "status": application.status,
        }

    if score >= cutoff:
        new_status = "SHORTLISTED"
    else:
        new_status = "REJECTED"

    old_status = application.status

    application.status = new_status
    application.save(update_fields=["status", "updated_at"])

    ApplicationStatusHistory.objects.create(
        application=application,
        status=new_status,
    )

    return {
        "success": True,
        "application_id": application.id,
        "previous_status": old_status,
        "new_status": new_status,
        "match_percentage": score,
        "cutoff": cutoff,
    }


def send_application_submitted_notification(application):
    candidate_email = application.candidate.user.email

    if not candidate_email:
        return {
            "success": False,
            "message": "Candidate email address not available.",
        }

    subject = "Application Submitted Successfully"
    message = (
        f"Hello {application.candidate.user.username},\n\n"
        f"Your application for '{application.job.title}' "
        "has been submitted successfully.\n\n"
        "Thank you for applying!"
    )

    log = EmailDeliveryLog.objects.create(
        application=application,
        event="APPLICATION_SUBMITTED",
        recipient=candidate_email,
        subject=subject,
        status="PENDING",
    )

    log.attempts += 1

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=None,
            recipient_list=[candidate_email],
            fail_silently=False,
        )

        log.status = "SENT"
        log.error_message = ""
        log.save(update_fields=[
            "status", "attempts", "error_message", "updated_at"
        ])

        return {
            "success": True,
            "message": "Application confirmation sent.",
            "log_id": log.id,
        }

    except Exception as exc:
        log.status = "FAILED"
        log.error_message = str(exc)
        log.save(update_fields=[
            "status", "attempts", "error_message", "updated_at"
        ])

        return {
            "success": False,
            "message": "Email sending failed.",
            "log_id": log.id,
        }

def send_application_status_notification(application):
    candidate_email = application.candidate.user.email
    status = application.status

    if status == "SHORTLISTED":
        event = "SHORTLISTED"
        subject = "Application Shortlisted"
        message = (
            f"Congratulations! Your application for "
            f"{application.job.title} has been shortlisted."
        )
    elif status == "REJECTED":
        event = "REJECTED"
        subject = "Application Status Update"
        message = (
            f"Your application for {application.job.title} "
            f"was not shortlisted at this stage."
        )
    else:
        return {
            "success": False,
            "message": "No notification configured for this status.",
        }

    if not candidate_email:
        return {
            "success": False,
            "message": "Candidate email address not available.",
        }
    
    existing_log = EmailDeliveryLog.objects.filter(
        application=application,
        event=event,
        status="SENT",
    ).first()

    if existing_log:
        return {
            "success": True,
            "message": "Notification already sent for this event.",
            "log_id": existing_log.id,
        }

    log = EmailDeliveryLog.objects.create(
        application=application,
        event=event,
        recipient=candidate_email,
        subject=subject,
        status="PENDING",
        attempts=1,
    )

    log.attempts += 1

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=None,
            recipient_list=[candidate_email],
            fail_silently=False,
        )

        log.status = "SENT"
        log.error_message = ""
        log.save(update_fields=[
            "status", "attempts", "error_message", "updated_at"
        ])

        return {
            "success": True,
            "message": "Notification sent successfully.",
            "recipient": candidate_email,
            "status": status,
            "log_id": log.id,
        }

    except Exception as exc:
        log.status = "FAILED"
        log.error_message = str(exc)
        log.save(update_fields=[
            "status", "attempts", "error_message", "updated_at"
        ])

        return {
            "success": False,
            "message": "Notification sending failed.",
            "log_id": log.id,
        }

def batch_process_applications():
    applications = Application.objects.filter(status="APPLIED")

    results = []

    for application in applications:
        try:
            application.ats_score
        except ATSScore.DoesNotExist:
            results.append({
                "application_id": application.id,
                "success": False,
                "message": "ATS score not found.",
            })
            continue

        result = auto_shortlist_application(application)

        if result["success"]:
            try:
                result["notification"] = (
                    send_application_status_notification(application)
                )
            except Exception:
                result["notification"] = {
                    "success": False,
                    "message": "Notification could not be sent.",
                }

        results.append(result)

    return {
        "total_processed": len(results),
        "results": results,
    }

def retry_failed_email_notifications(max_attempts=3):
    failed_logs = EmailDeliveryLog.objects.filter(
        status="FAILED",
        attempts__lt=max_attempts,
    )

    results = []

    for log in failed_logs:
        log.attempts += 1

        application = log.application
        candidate_email = log.recipient

        if log.event == "APPLICATION_SUBMITTED":
            message = (
                f"Hello {application.candidate.user.username},\n\n"
                f"Your application for '{application.job.title}' "
                "has been submitted successfully.\n\n"
                "Thank you for applying!"
            )
        elif log.event == "SHORTLISTED":
            message = (
                f"Congratulations! Your application for "
                f"{application.job.title} has been shortlisted."
            )
        elif log.event == "REJECTED":
            message = (
                f"Your application for {application.job.title} "
                "was not shortlisted at this stage."
            )
        else:
            results.append({
                "log_id": log.id,
                "success": False,
                "message": "Unsupported email event.",
            })
            continue

        try:
            send_mail(
                subject=log.subject,
                message=message,
                from_email=None,
                recipient_list=[candidate_email],
                fail_silently=False,
            )

            log.status = "SENT"
            log.error_message = ""

            results.append({
                "log_id": log.id,
                "success": True,
                "message": "Retry successful.",
            })

        except Exception as exc:
            log.status = "FAILED"
            log.error_message = str(exc)

            results.append({
                "log_id": log.id,
                "success": False,
                "message": "Retry failed.",
            })

        finally:
            log.save(update_fields=[
                "status",
                "attempts",
                "error_message",
                "updated_at",
            ])

    return {
        "total_retried": len(results),
        "results": results,
    }
