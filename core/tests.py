from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from datetime import date, timedelta
from rest_framework import status
from .models import User, Candidate, Employer, Job, Application
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
    
