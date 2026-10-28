
from datetime import timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import (
    Employer,
    Candidate,
    Job,
    Application,
    AIInterviewSession,
    AIQuestion,
    AIAnswer,
    AICallLog,
)
from .ai_conversation import (
    save_transcript,
    save_question_and_answer,
    create_call_audit_log,
)


class AIConversationTest(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="conversation_test_user",
            email="employer_test@example.com",
            password="testpass123",
        )

        self.employer = Employer.objects.create(
            user=self.user,
            company_name="Test Company",
            company_email="test@example.com",
            company_phone="9876543210",
            location="Kochi",
            description="Test employer",
        )

        self.candidate_user = User.objects.create_user(
            username="conversation_candidate",
            email="candidate_test@example.com",
            password="testpass123",
        )

        self.candidate = Candidate.objects.create(
            user=self.candidate_user,
            phone="9876501234",
            address="Kochi",
            skills="Python, Django",
            education="Bachelor's degree",
        )

        self.job = Job.objects.create(
            employer=self.employer,
            title="Python Developer",
            description="Django developer role",
            skills="Python, Django",
            location="Kochi",
            job_type="FULL_TIME",
            experience_required=0,
            deadline=timezone.now() + timedelta(days=30),
        )

        self.application = Application.objects.create(
            candidate=self.candidate,
            job=self.job,
        )

        self.call_log = AICallLog.objects.create(
            application=self.application,
            status="QUEUED",
        )

        self.session = AIInterviewSession.objects.create(
            application=self.application,
            call_log=self.call_log,
            triggered_by=self.user,
        )

    def test_save_transcript(self):
        session = save_transcript(
            self.session.id,
            "Tell me about yourself. I am a Python developer.",
            {"language": "en", "segments": []},
        )

        session.refresh_from_db()

        self.assertIn("Python developer", session.transcript_text)
        self.assertEqual(session.transcript_json["language"], "en")

    def test_save_question_and_answer(self):
        question, answer = save_question_and_answer(
            self.session.id,
            "What is Django?",
            "Django is a Python web framework.",
            order=1,
            structured_data={"topic": "Django"},
        )

        self.assertEqual(AIQuestion.objects.count(), 1)
        self.assertEqual(AIAnswer.objects.count(), 1)
        self.assertEqual(answer.question_id, question.id)
        self.assertEqual(answer.structured_data["topic"], "Django")

    def test_create_audit_log(self):
        from .models import CallLog

        log = create_call_audit_log(
            event_type="AI_CALL_TRIGGERED",
            triggered_by=self.user,
            session=self.session,
            call_log=self.call_log,
            reason="Candidate met eligibility requirements",
            details={"source": "test"},
        )

        self.assertEqual(log.triggered_by, self.user)
        self.assertEqual(log.event_type, "AI_CALL_TRIGGERED")
        self.assertEqual(log.details["source"], "test")

    def test_transcript_is_encrypted_in_database(self):
        from django.db import connection

        original = "Sensitive transcript for encryption test"

        self.session.transcript_text = original
        self.session.save(update_fields=["transcript_text"])

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT transcript_text FROM core_aiinterviewsession WHERE id = %s",
                [self.session.id],
            )
            raw_value = cursor.fetchone()[0]

        self.assertNotEqual(raw_value, original)
        self.assertTrue(raw_value.startswith("enc:v1:"))

        self.session.refresh_from_db()
        self.assertEqual(self.session.transcript_text, original)
