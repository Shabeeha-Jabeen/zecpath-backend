
from datetime import timedelta
from core.models import User
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch
from core.models import AICallLog
from core.tasks import trigger_ai_call_task
from core.models import (
    Candidate,
    Employer,
    Job,
    Application,
    ATSScore,
)
from core.ai_call_eligibility import check_ai_call_eligibility, auto_trigger_ai_call


class AICallEligibilityTests(TestCase):

    
    def setUp(self):
        self.user = User.objects.create_user(
            username="eligibility_candidate",
            email="candidate@example.com",
            password="testpass123",
            is_active=True,
        )

        self.candidate = Candidate.objects.create(
            user=self.user,
            phone="9876543210",
            address="Test Address",
            skills="Python, Django, SQL",
            education="Bachelor",
            experience=1,
            is_available_for_ai_call=True,
        )

        employer_user = User.objects.create_user(
            username="eligibility_employer",
            email="employer@example.com",
            password="testpass123",
        )

        self.employer = Employer.objects.create(
            user=employer_user,
            company_name="Test Company",
            company_email="test@example.com",
            company_phone="9876543211",
            location="Kerala",
            description="Test employer",
        )   

        self.job = Job.objects.create(
            employer=self.employer,
            title="Python Developer",
            description="Django backend role",
            skills="Python, Django, SQL",
            location="Kerala",
            job_type="Full-time",
            experience_required=1,
            deadline=timezone.localdate() + timedelta(days=7),
            status="OPEN",
            ats_cutoff=70,
        )

        self.application = Application.objects.create(
            candidate=self.candidate,
            job=self.job,
            cover_letter="I am interested in this role.",
            status="SHORTLISTED",
        )

        self.ats_score = ATSScore.objects.create(
            application=self.application,
            match_percentage=85,
            skills_score=100,
            experience_score=100,
            education_score=100,
        )


    def test_shortlisted_candidate_with_good_score_is_eligible(self):
        result = check_ai_call_eligibility(self.application.id)

        self.assertTrue(result["eligible"])
        self.assertEqual(result["application_id"], self.application.id)

    def test_candidate_below_ats_cutoff_is_not_eligible(self):
        self.ats_score.match_percentage = 50
        self.ats_score.save()

        result = check_ai_call_eligibility(self.application.id)

        self.assertFalse(result["eligible"])
        self.assertIn("below", result["reason"])

    def test_application_not_shortlisted_is_not_eligible(self):
        self.application.status = "APPLIED"
        self.application.save()

        result = check_ai_call_eligibility(self.application.id)

        self.assertFalse(result["eligible"])
        self.assertIn("not shortlisted", result["reason"].lower())

    def test_inactive_candidate_is_not_eligible(self):
        self.user.is_active = False
        self.user.save()

        result = check_ai_call_eligibility(self.application.id)

        self.assertFalse(result["eligible"])
        self.assertIn("inactive", result["reason"].lower())

    def test_candidate_unavailable_for_ai_call_is_not_eligible(self):
        self.candidate.is_available_for_ai_call = False
        self.candidate.save()

        result = check_ai_call_eligibility(self.application.id)

        self.assertFalse(result["eligible"])
        self.assertIn("not available", result["reason"].lower())

    def test_closed_job_is_not_eligible(self):
        self.job.status = "CLOSED"
        self.job.save()

        result = check_ai_call_eligibility(self.application.id)

        self.assertFalse(result["eligible"])
        self.assertIn("not open", result["reason"].lower())

    def test_missing_application_is_not_eligible(self):
        result = check_ai_call_eligibility(999999)

        self.assertFalse(result["eligible"])
        self.assertIn("not found", result["reason"].lower())

    @patch("core.ai_call_eligibility.trigger_ai_call_task.apply_async")
    def test_auto_trigger_schedules_eligible_application(self, mock_apply_async):
        result = auto_trigger_ai_call(self.application.id)

        self.assertTrue(result["triggered"])
        self.assertIn("task_id", result)
        self.assertTrue(
            AICallLog.objects.filter(
                application=self.application,
                status="QUEUED",
            ).exists()
        )
        mock_apply_async.assert_called_once()

    @patch("core.ai_call_eligibility.trigger_ai_call_task.apply_async")
    def test_auto_trigger_does_not_schedule_ineligible_application(
        self, mock_apply_async
    ):
        self.application.status = "APPLIED"
        self.application.save()

        result = auto_trigger_ai_call(self.application.id)

        self.assertFalse(result["triggered"])
        mock_apply_async.assert_not_called()

    
   
    @patch("core.tasks.AICallLog.objects.get")
    def test_ai_call_task_updates_status_to_completed(self, mock_get):
        from types import SimpleNamespace

        call_log = SimpleNamespace(
            status="QUEUED",
            started_at=None,
            completed_at=None,
            error_message="",
            retry_count=0,
            save=lambda **kwargs: None,
        )
        mock_get.return_value = call_log

        result = trigger_ai_call_task.apply(
            args=(1, 1, self.application.id),
            task_id="test-task-id",
        ).get()

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(call_log.status, "COMPLETED")
        self.assertIsNotNone(call_log.started_at)
        self.assertIsNotNone(call_log.completed_at)



    def test_ai_call_log_has_status_tracking_fields(self):
        field_names = {
            field.name for field in AICallLog._meta.get_fields()
        }

        self.assertIn("status", field_names)
        self.assertIn("started_at", field_names)
        self.assertIn("completed_at", field_names)
        self.assertIn("retry_count", field_names)
        self.assertIn("error_message", field_names)
