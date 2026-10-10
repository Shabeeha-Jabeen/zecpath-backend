
from celery import shared_task
from django.core.mail import send_mail
from core.models import EmailDeliveryLog


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
