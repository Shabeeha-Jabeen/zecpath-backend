
from unittest.mock import patch

from django.test import TestCase

from core.models import (
    User,
    Candidate,
    Employer,
    Job,
    Application,
    AICallLog,
)
from core.tasks import trigger_ai_call_task


class AICallStatusTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="ai_call_test_candidate",
            email="ai_call_candidate_test@example.com",
            password="test-password-123",
        )

        self.candidate = Candidate.objects.create(
            user=self.user,
            phone="9876543210",
            address="Test Address",
            skills="Python, Django",
            education="Bachelor",
            experience=1,
        )

        self.employer_user = User.objects.create_user(
            username="ai_call_test_employer",
            email="ai_call_employer_test@example.com",
            password="test-password-123",
        )

        self.employer = Employer.objects.create(
            user=self.employer_user,
            company_name="Test Company",
            company_email="test@example.com",
            company_phone="9876543211",
            location="Kochi",
            description="Test employer for AI call status tests",
        )

        self.job = Job.objects.create(
            employer=self.employer,
            title="AI Call Test Job",
            description="Testing AI call status",
            skills="Python",
            experience_required=0,
            deadline="2027-12-31",
        )

        self.application = Application.objects.create(
            candidate=self.candidate,
            job=self.job,
            status="SHORTLISTED",
        )

        self.task_id = "ai-call-test-task-001"

        self.call_log = AICallLog.objects.create(
            application=self.application,
            status="QUEUED",
            celery_task_id=self.task_id,
        )

    def test_successful_call_status(self):
        result = trigger_ai_call_task.apply(
            args=[
                self.candidate.id,
                self.job.id,
                self.application.id,
            ],
            task_id=self.task_id,
        ).get()

        self.call_log.refresh_from_db()

        self.assertEqual(self.call_log.status, "COMPLETED")
        self.assertIsNotNone(self.call_log.started_at)
        self.assertIsNotNone(self.call_log.completed_at)
        self.assertEqual(result["status"], "SUCCESS")

    def test_missing_call_log(self):
        result = trigger_ai_call_task.apply(
            args=[
                self.candidate.id,
                self.job.id,
                self.application.id,
            ],
            task_id="missing-task-id",
        ).get()

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(
            result["message"],
            "AI call log not found.",
        )

    
    @patch.object(
        trigger_ai_call_task,
        "retry",
        side_effect=RuntimeError("Retry requested"),
    )
    def test_failure_updates_status_and_retry_count(self, mock_retry):
        with patch(
            "core.tasks.AICallLog.objects.get",
            return_value=self.call_log,
        ):
            # Make the first save (IN_PROGRESS) succeed, then
            # simulate a failure when the task processes the call.
            with patch.object(
                self.call_log,
                "save",
                side_effect=[
                    None,
                    Exception("Simulated failure"),
                    None,
                ],
            ):
                with self.assertRaises(RuntimeError):
                    trigger_ai_call_task.apply(
                        args=[
                            self.candidate.id,
                            self.job.id,
                            self.application.id,
                        ],
                        task_id=self.task_id,
                    ).get()

        self.assertEqual(self.call_log.status, "FAILED")
        self.assertEqual(self.call_log.retry_count, 1)
        self.assertIn(
            "Simulated failure",
            self.call_log.error_message,
        )
        mock_retry.assert_called_once()
