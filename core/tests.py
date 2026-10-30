from django.test import TestCase
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from unittest.mock import patch
from django.utils import timezone
from datetime import date, timedelta
from rest_framework import status
from .models import (
    User,
    Candidate,
    Employer,
    Job,
    Application,
    AvailabilitySlot,
    InterviewSchedule,
    InterviewReminder,
    SubscriptionPlan,
    UserSubscription,
    PaymentTransaction,
    BillingHistory,
)
from core.ai_question_engine import (
    get_questions_for_job,
    get_follow_up_question,
)
class JobListAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_job_list_api_returns_success(self):
        response = self.client.get("/api/jobs/")

        self.assertEqual(response.status_code, 200)

    def test_job_list_api_returns_json(self):
        response = self.client.get("/api/jobs/")

        self.assertEqual(response["Content-Type"].split(";")[0],
                         "application/json")

class AuthenticationAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_login_rejects_invalid_credentials(self):
        response = self.client.post(
            "/api/login/",
            {
                "username": "invalid_test_user",
                "password": "WrongPassword123!"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 401)
        
    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_AUTHENTICATION_CLASSES": [
                "rest_framework_simplejwt.authentication.JWTAuthentication",
            ],
            "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
            "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
            "PAGE_SIZE": 5,
            "DEFAULT_THROTTLE_CLASSES": [
                "rest_framework.throttling.ScopedRateThrottle",
            ],
            "DEFAULT_THROTTLE_RATES": {
                "login": "5/minute",
            },
        }
    )
    def test_login_throttle_returns_429_after_limit(self):
        cache.clear()
        try:
            responses = []

            for _ in range(6):
                response = self.client.post(
                    "/api/login/",
                    {
                        "username": "invalid_test_user",
                        "password": "WrongPassword123!",
                    },
                    format="json",
                )
                responses.append(response.status_code)

            self.assertEqual(responses[:5], [401] * 5)
            self.assertEqual(responses[5], 429)
        finally:
            cache.clear()


class ApplicationSecurityTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_user_cannot_submit_application(self):
        response = self.client.post(
            "/api/applications/create/",
            {},
            format="json"
        )

        self.assertIn(response.status_code, [401, 403])




class ApplicationFlowTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.candidate_user = User.objects.create_user(
            username="candidate_test",
            email="candidate_test@example.com",
            password="TestPass123!",
            role="CANDIDATE",
        )

        self.candidate = Candidate.objects.get(
            user=self.candidate_user
        )

        self.candidate.phone = "9876543210"
        self.candidate.address = "Kozhikode"
        self.candidate.skills = "Python, Django"
        self.candidate.save()
        self.employer_user = User.objects.create_user(
            username="employer_test",
            email="employer_test@example.com",
            password="TestPass123!",
            role="EMPLOYER",
        )

        self.employer = Employer.objects.get(
            user=self.employer_user
        )

        self.employer.company_name = "Test Company"
        self.employer.company_email = "company@example.com"
        self.employer.company_phone = "9876543211"
        self.employer.location = "Kozhikode"
        self.employer.description = "Test company"
        self.employer.save()
        self.job = Job.objects.create(
            employer=self.employer,
            title="Python Developer",
            description="Django backend development",
            skills="Python, Django",
            location="Kozhikode",
            job_type="Full-time",
            experience_required=0,
            deadline=date.today() + timedelta(days=30),
        )

    def test_candidate_and_job_are_created(self):
        self.assertEqual(self.candidate.user.role, "CANDIDATE")
        self.assertEqual(self.job.employer, self.employer)

    def test_application_model_links_candidate_and_job(self):
        application = Application.objects.create(
            candidate=self.candidate,
            job=self.job,
            cover_letter="I am interested in this role.",
        )

        self.assertEqual(application.candidate, self.candidate)
        self.assertEqual(application.job, self.job)
        self.assertEqual(application.status, "APPLIED")
    
    def test_employer_cannot_submit_application(self):
        self.client.force_authenticate(user=self.employer_user)

        response = self.client.post(
            "/api/applications/create/",
            {"job": self.job.id, "cover_letter": "Test application"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
    
    def test_duplicate_application_is_rejected(self):
        Application.objects.create(
            candidate=self.candidate,
            job=self.job,
            cover_letter="First application",
        )

        self.client.force_authenticate(user=self.candidate_user)

        response = self.client.post(
            "/api/applications/create/",
            {
                "job": self.job.id,
                "cover_letter": "Duplicate application",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
    

class AIQuestionEngineTests(TestCase):

    def test_invalid_job(self):
        result = get_questions_for_job(9999)

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Job not found.")

    def test_follow_up_for_python(self):
        result = get_follow_up_question("I know Python")

        self.assertEqual(result["category"], "SKILLS")
        self.assertIn("Django", result["question_text"])

    def test_follow_up_for_beginner(self):
        result = get_follow_up_question("I am a beginner")

        self.assertEqual(result["category"], "EXPERIENCE")

    def test_follow_up_for_empty_answer(self):
        result = get_follow_up_question("")

        self.assertEqual(result["category"], "SKILLS")


class InterviewReminderAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user1 = User.objects.create_user(
            username="reminder_candidate1",
            email="reminder1@example.com",
            password="TestPass123!",
            role="CANDIDATE",
        )
        self.candidate1 = Candidate.objects.get(user=self.user1)
        self.candidate1.phone = "9876543210"
        self.candidate1.address = "Kozhikode"
        self.candidate1.skills = "Python"
        self.candidate1.save()

        self.user2 = User.objects.create_user(
            username="reminder_candidate2",
            email="reminder2@example.com",
            password="TestPass123!",
            role="CANDIDATE",
        )
        self.candidate2 = Candidate.objects.get(user=self.user2)
        self.candidate2.phone = "9876543211"
        self.candidate2.address = "Malappuram"
        self.candidate2.skills = "Django"
        self.candidate2.save()

        employer_user = User.objects.create_user(
            username="reminder_employer",
            email="reminder_employer@example.com",
            password="TestPass123!",
            role="EMPLOYER",
        )
        employer = Employer.objects.get(user=employer_user)
        employer.company_name = "Reminder Test Company"
        employer.company_email = "company@example.com"
        employer.company_phone = "9876543212"
        employer.location = "Kozhikode"
        employer.description = "Test company"
        employer.save()

        self.job = Job.objects.create(
            employer=employer,
            title="Python Developer",
            description="Test job",
            skills="Python",
            location="Kozhikode",
            job_type="Full-time",
            experience_required=0,
            deadline=date.today() + timedelta(days=30),
        )

        self.application1 = Application.objects.create(
            candidate=self.candidate1,
            job=self.job,
            cover_letter="Candidate one",
        )
        self.application2 = Application.objects.create(
            candidate=self.candidate2,
            job=self.job,
            cover_letter="Candidate two",
        )

        start = timezone.now() + timedelta(days=2)
        slot1 = AvailabilitySlot.objects.create(
            start_time=start,
            end_time=start + timedelta(hours=1),
        )
        slot2 = AvailabilitySlot.objects.create(
            start_time=start + timedelta(days=1),
            end_time=start + timedelta(days=1, hours=1),
        )

        interview1 = InterviewSchedule.objects.create(
            application=self.application1,
            availability_slot=slot1,
            scheduled_start=slot1.start_time,
            scheduled_end=slot1.end_time,
            status="CONFIRMED",
        )
        interview2 = InterviewSchedule.objects.create(
            application=self.application2,
            availability_slot=slot2,
            scheduled_start=slot2.start_time,
            scheduled_end=slot2.end_time,
            status="CONFIRMED",
        )

        self.reminder1 = InterviewReminder.objects.create(
            interview=interview1,
            stage="24_HOURS",
            scheduled_at=start - timedelta(hours=24),
            status="PENDING",
        )
        InterviewReminder.objects.create(
            interview=interview2,
            stage="24_HOURS",
            scheduled_at=start + timedelta(days=1) - timedelta(hours=24),
            status="SENT",
            attempts=1,
            sent_at=timezone.now(),
        )

    def test_unauthenticated_user_cannot_access_reminders(self):
        response = self.client.get("/api/interview/reminders/")
        self.assertIn(response.status_code, [401, 403])

    def test_candidate_only_sees_own_reminders(self):
        self.client.force_authenticate(user=self.user1)

        response = self.client.get("/api/interview/reminders/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.reminder1.id)
        self.assertEqual(response.data[0]["status"], "PENDING")
        self.assertEqual(response.data[0]["attempts"], 0)

class InterviewReminderTaskTests(TestCase):
    @patch("core.reminder_service.process_due_reminders")
    def test_reminder_task_calls_processing_service(self, mock_process):
        mock_process.return_value = {
            "processed": 2,
            "sent": 1,
            "failed": 1,
        }

        from core.tasks import process_interview_reminders_task

        result = process_interview_reminders_task.apply(
            throw=True
        ).get()

        self.assertEqual(result["processed"], 2)
        self.assertEqual(result["sent"], 1)
        self.assertEqual(result["failed"], 1)
        mock_process.assert_called_once_with()
class SubscriptionAccessTest(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="testemployer",
            email="employer@test.com",
            password="testpass123",
            role="EMPLOYER"
        )

        self.employer = Employer.objects.get(user=self.user)

        self.free_plan = SubscriptionPlan.objects.create(
            name="FREE",
            description="Free plan",
            price=0,
            currency="INR",
            billing_period="MONTHLY",
            job_post_limit=2,
            features={
                "job_posting": True,
                "recruiter_analytics": False,
                "ai_analytics": False,
            },
        )

        self.pro_plan = SubscriptionPlan.objects.create(
            name="PRO",
            description="Pro plan",
            price=999,
            currency="INR",
            billing_period="MONTHLY",
            job_post_limit=None,
            features={
                "job_posting": True,
                "recruiter_analytics": True,
                "ai_analytics": False,
            },
        )
        self.enterprise_plan = SubscriptionPlan.objects.create(
            name="ENTERPRISE",
            description="Enterprise plan",
            price=4999,
            currency="INR",
            billing_period="MONTHLY",
            job_post_limit=None,
            features={
                "job_posting": True,
                "recruiter_analytics": True,
                "ai_analytics": True,
            },
        )

    def test_free_plan_job_limit(self):
        UserSubscription.objects.create(
            user=self.user,
            plan=self.free_plan,
            status="ACTIVE"
        )

        self.client.force_authenticate(user=self.user)

        job_data = {
            "description": "Python Django Developer",
            "skills": "Python, Django",
            "education_required": "Degree",
            "location": "Kochi",
            "job_type": "Full Time",
            "experience_required": 1,
            "deadline": (date.today() + timedelta(days=30)).isoformat()
        }

        # First job
        response1 = self.client.post(
            "/api/jobs/create/",
            {**job_data, "title": "Python Developer 1"},
            format="json"
        )

        self.assertEqual(
            response1.status_code,
            status.HTTP_201_CREATED
        )

        # Second job
        response2 = self.client.post(
            "/api/jobs/create/",
            {**job_data, "title": "Python Developer 2"},
            format="json"
        )

        self.assertEqual(
            response2.status_code,
            status.HTTP_201_CREATED
        )

        # Third job should be blocked
        response3 = self.client.post(
            "/api/jobs/create/",
            {**job_data, "title": "Python Developer 3"},
            format="json"
        )

        self.assertEqual(
            response3.status_code,
            status.HTTP_403_FORBIDDEN
        )
    def test_pro_plan_unlimited_job_posting(self):
        UserSubscription.objects.create(
            user=self.user,
            plan=self.pro_plan,
            status="ACTIVE"
        )

        self.client.force_authenticate(user=self.user)

        job_data = {
            "description": "Python Django Developer",
            "skills": "Python, Django",
            "education_required": "Degree",
            "location": "Kochi",
            "job_type": "Full Time",
            "experience_required": 1,
            "deadline": (date.today() + timedelta(days=30)).isoformat()
        }

        for number in range(1, 6):
            response = self.client.post(
                "/api/jobs/create/",
                {
                    **job_data,
                    "title": f"Python Developer {number}"
                },
                format="json"
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED
            )    
    def test_free_plan_cannot_access_recruiter_analytics(self):
        UserSubscription.objects.create(
            user=self.user,
            plan=self.free_plan,
            status="ACTIVE"
        )

        self.client.force_authenticate(user=self.user)

        endpoints = [
            "/api/analytics/funnel/",
            "/api/analytics/jobs/",
            "/api/analytics/monthly/",
            "/api/analytics/roles/",
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)

            self.assertEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN,
                msg=f"FREE user should not access {endpoint}"
            )

    def test_pro_can_access_recruiter_analytics(self):
        UserSubscription.objects.create(
            user=self.user,
            plan=self.pro_plan,
            status="ACTIVE"
        )

        self.client.force_authenticate(user=self.user)

        endpoints = [
            "/api/analytics/funnel/",
            "/api/analytics/jobs/",
            "/api/analytics/monthly/",
            "/api/analytics/roles/",
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)

            self.assertNotEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN,
                msg=f"PRO user should have permission for {endpoint}"
            )        
    def test_free_and_pro_cannot_access_candidate_report(self):
        for plan in [self.free_plan, self.pro_plan]:
            UserSubscription.objects.create(
                user=self.user,
                plan=plan,
                status="ACTIVE"
            )

            self.client.force_authenticate(user=self.user)

            response = self.client.get(
                "/api/applications/1/report/"
            )

            self.assertEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN
            )

            UserSubscription.objects.filter(
                user=self.user
            ).delete()

    def test_enterprise_can_access_candidate_report(self):
    # Create an Enterprise subscription
        UserSubscription.objects.create(
            user=self.user,
            plan=self.enterprise_plan,
            status="ACTIVE"
        )

    # Create candidate user
        candidate_user = User.objects.create_user(
            username="report_candidate",
            email="report_candidate@test.com",
            password="TestPass123!",
            role="CANDIDATE"
        )

        candidate = Candidate.objects.get(user=candidate_user)
        candidate.phone = "9876543210"
        candidate.address = "Kozhikode"
        candidate.skills = "Python, Django, SQL"
        candidate.save()

    # Create job
        job = Job.objects.create(
            employer=self.employer,
            title="Python Django Developer",
            description="Python backend developer required",
            skills="Python, Django",
            location="Kozhikode",
            job_type="FULL_TIME",
            experience_required=0,
            deadline="2026-12-31"
        )

    # Create application
        application = Application.objects.create(
            candidate=candidate,
            job=job,
            cover_letter="I am interested in this position."
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            f"/api/applications/{application.id}/report/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)