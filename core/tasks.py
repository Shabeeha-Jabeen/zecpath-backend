from celery import shared_task
from django.core.mail import send_mail
from core.models import EmailDeliveryLog
from django.utils import timezone
from core.models import AICallLog

@shared_task
def send_email_notification(log_id):
    try:
        log = EmailDeliveryLog.objects.get(id=log_id)

        if log.status == "SENT":
            return "Email already sent."

        application = log.application

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
            log.status = "FAILED"
            log.error_message = "Unsupported email event."
            log.save(update_fields=["status", "error_message", "updated_at"])
            return "Unsupported email event."

        log.attempts += 1
        log.save(update_fields=["attempts", "updated_at"])

        send_mail(
            subject=log.subject,
            message=message,
            from_email=None,
            recipient_list=[log.recipient],
            fail_silently=False,
        )

        log.status = "SENT"
        log.error_message = ""
        log.save(update_fields=["status", "error_message", "updated_at"])

        return "Email sent successfully."

    except Exception as exc:
        if "log" in locals():
            log.status = "FAILED"
            log.error_message = str(exc)
            log.save(
                update_fields=["status", "error_message", "updated_at"]
            )
        raise

@shared_task
def test_background_task():
    return "ZecPath background task completed successfully!"


@shared_task
def process_resume_text_task(saved_file_path, filename):
    from pathlib import Path

    from core.resume_parser import (
        extract_resume_text,
        clean_resume_text,
        extract_resume_skills,
        extract_experience_years,
        extract_education,
    )

    path = Path(saved_file_path)

    try:
        with path.open("rb") as resume_file:
            # The parser checks file.name for its extension.
            # Use a small wrapper to provide the original filename.
            class ResumeFile:
                def __init__(self, file_obj, name):
                    self.file_obj = file_obj
                    self.name = name

                def read(self, *args, **kwargs):
                    return self.file_obj.read(*args, **kwargs)

                def seek(self, *args, **kwargs):
                    return self.file_obj.seek(*args, **kwargs)

                def tell(self):
                    return self.file_obj.tell()

            file_obj = ResumeFile(resume_file, filename)
            extracted_text = extract_resume_text(file_obj)

        cleaned_text = clean_resume_text(extracted_text)

        if not cleaned_text:
            return {
                "status": "FAILED",
                "message": "No readable text found in resume.",
            }

        return {
            "status": "SUCCESS",
            "filename": filename,
            "file_type": path.suffix.lower(),
            "extracted_text": extracted_text,
            "cleaned_text": cleaned_text,
            "character_count": len(cleaned_text),
            "skills": extract_resume_skills(cleaned_text),
            "experience_years": extract_experience_years(cleaned_text),
            "education": extract_education(cleaned_text),
        }

    except Exception:
        # Keep detailed error information in the worker log.
        raise

@shared_task(bind=True, max_retries=3)
def trigger_ai_call_task(self, candidate_id, job_id, application_id):
    from django.utils import timezone
    from core.models import AICallLog

    try:
        call_log = AICallLog.objects.get(
            application_id=application_id,
            celery_task_id=self.request.id,
        )
    except AICallLog.DoesNotExist:
        return {
            "status": "FAILED",
            "message": "AI call log not found.",
        }

    try:
        call_log.status = "IN_PROGRESS"
        call_log.started_at = timezone.now()
        call_log.save(
            update_fields=["status", "started_at", "updated_at"]
        )

        # Placeholder only: no real phone call is made here.
        result = {
            "status": "SUCCESS",
            "message": "AI call workflow placeholder completed.",
            "candidate_id": candidate_id,
            "job_id": job_id,
            "application_id": application_id,
        }

        call_log.status = "COMPLETED"
        call_log.completed_at = timezone.now()
        call_log.error_message = ""
        call_log.save(
            update_fields=[
                "status",
                "completed_at",
                "error_message",
                "updated_at",
            ]
        )
        return result

    except Exception as exc:
        call_log.status = "FAILED"
        call_log.error_message = str(exc)
        call_log.retry_count = self.request.retries + 1
        call_log.save(
            update_fields=[
                "status",
                "error_message",
                "retry_count",
                "updated_at",
            ]
        )

        raise self.retry(exc=exc, countdown=60)

@shared_task
def expire_deadline_jobs_task():
    from .models import Job

    today = timezone.localdate()

    expired_count = Job.objects.filter(
        status="OPEN",
        deadline__lt=today,
    ).update(status="EXPIRED")

    return {
        "status": "SUCCESS",
        "expired_jobs_count": expired_count,
        "checked_date": str(today),
    }
