import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zecpath.settings")

app = Celery("zecpath")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.beat_schedule = {
    "expire-deadline-jobs-daily": {
        "task": "core.tasks.expire_deadline_jobs_task",
        "schedule": crontab(minute=0, hour=3),
    },
    
    "process-interview-reminders-every-minute": {
        "task": "core.tasks.process_interview_reminders_task",
        "schedule": crontab(minute="*"),
    },

}

