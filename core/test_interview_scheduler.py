from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from core.models import (
    User,
    Candidate,
    Employer,
    Job,
    Application,
    AvailabilitySlot,
    InterviewSchedule,
    InterviewReminder,
)
from core.interview_scheduler import (
    get_available_slots,
    schedule_interview,
    reschedule_interview,
)


class InterviewSchedulerServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="scheduler_candidate",
            email="candidate@example.com",
            password="TestPassword123!",
            role="CANDIDATE",
        )
        self.candidate = self.user.candidate_profile
        self.candidate.phone = "9876543210"
        self.candidate.address = "Kozhikode"
        self.candidate.skills = "Python, Django"
        self.candidate.save()

        self.employer_user = User.objects.create_user(
            username="scheduler_employer",
            email="employer@example.com",
            password="TestPassword123!",
            role="EMPLOYER",
        )
        self.employer = self.employer_user.employer_profile
        self.employer.company_name = "Test Company"
        self.employer.company_email = "company@example.com"
        self.employer.company_phone = "9876543211"
        self.employer.location = "Kozhikode"
        self.employer.description = "Test employer"
        self.employer.save()

        self.job = Job.objects.create(
            employer=self.employer,
            title="Python Developer",
            description="Django development role",
            location="Kozhikode",
            job_type="Full-time",
            experience_required=0,
            deadline=timezone.localdate() + timedelta(days=30),
        )
        self.application = Application.objects.create(
            candidate=self.candidate,
            job=self.job,
            cover_letter="I am interested in this Python role.",
        )

        start = timezone.now() + timedelta(days=3)
        start = start.replace(minute=0, second=0, microsecond=0)

        self.slot = AvailabilitySlot.objects.create(
            role="PYTHON",
            start_time=start,
            end_time=start + timedelta(hours=1),
            is_available=True,
        )
        self.new_slot = AvailabilitySlot.objects.create(
            role="PYTHON",
            start_time=start + timedelta(days=1),
            end_time=start + timedelta(days=1, hours=1),
            is_available=True,
        )

    @patch("core.interview_scheduler.create_reminders_for_interview")
    @patch("core.interview_scheduler.send_interview_confirmation_email")
    def test_schedule_interview_success(
        self, mock_email, mock_reminders
    ):
        mock_email.return_value = {"success": True}

        result = schedule_interview(
            self.application.id, self.slot.id
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "CONFIRMED")
        self.assertTrue(result["confirmation_email_sent"])
        self.assertTrue(
            InterviewSchedule.objects.filter(
                availability_slot=self.slot,
                status="CONFIRMED",
            ).exists()
        )
        mock_email.assert_called_once()
        mock_reminders.assert_called_once()

    def test_schedule_rejects_missing_application(self):
        result = schedule_interview(999999, self.slot.id)

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Application not found.")

    def test_schedule_rejects_missing_slot(self):
        result = schedule_interview(
            self.application.id, 999999
        )

        self.assertFalse(result["success"])
        self.assertEqual(
            result["message"], "Availability slot not found."
        )

    def test_schedule_rejects_unavailable_slot(self):
        self.slot.is_available = False
        self.slot.save(update_fields=["is_available"])

        result = schedule_interview(
            self.application.id, self.slot.id
        )

        self.assertFalse(result["success"])
        self.assertEqual(
            result["message"], "This slot is not available."
        )

    @patch("core.interview_scheduler.create_reminders_for_interview")
    @patch("core.interview_scheduler.send_interview_confirmation_email")
    def test_schedule_rejects_already_booked_slot(
        self, mock_email, mock_reminders
    ):
        mock_email.return_value = {"success": True}

        first = schedule_interview(
            self.application.id, self.slot.id
        )
        second = schedule_interview(
            self.application.id, self.slot.id
        )

        self.assertTrue(first["success"])
        self.assertFalse(second["success"])
        mock_email.assert_called_once()
        mock_reminders.assert_called_once()

    def test_available_slots_excludes_booked_slots(self):
        available_before = list(get_available_slots("PYTHON"))
        self.assertIn(self.slot, available_before)

        InterviewSchedule.objects.create(
            application=self.application,
            availability_slot=self.slot,
            scheduled_start=self.slot.start_time,
            scheduled_end=self.slot.end_time,
            status="CONFIRMED",
        )

        available_after = list(get_available_slots("PYTHON"))
        self.assertNotIn(self.slot, available_after)
        self.assertIn(self.new_slot, available_after)

    @patch("core.interview_scheduler.create_reminders_for_interview")
    @patch("core.interview_scheduler.send_interview_confirmation_email")
    def test_reschedule_interview_success(
        self, mock_email, mock_reminders
    ):
        old_schedule = InterviewSchedule.objects.create(
            application=self.application,
            availability_slot=self.slot,
            scheduled_start=self.slot.start_time,
            scheduled_end=self.slot.end_time,
            status="CONFIRMED",
        )
        mock_email.return_value = {"success": True}

        result = reschedule_interview(
            old_schedule.id, self.new_slot.id
        )

        self.assertTrue(result["success"])
        old_schedule.refresh_from_db()
        self.assertEqual(old_schedule.status, "CANCELLED")
        self.assertTrue(
            InterviewSchedule.objects.filter(
                availability_slot=self.new_slot,
                status="CONFIRMED",
            ).exists()
        )
        mock_email.assert_called_once()
        mock_reminders.assert_called_once()

    def test_reschedule_rejects_missing_schedule(self):
        result = reschedule_interview(999999, self.new_slot.id)

        self.assertFalse(result["success"])
        self.assertEqual(
            result["message"], "Interview schedule not found."
        )

    def test_reschedule_rejects_same_slot(self):
        old_schedule = InterviewSchedule.objects.create(
            application=self.application,
            availability_slot=self.slot,
            scheduled_start=self.slot.start_time,
            scheduled_end=self.slot.end_time,
            status="CONFIRMED",
        )

        result = reschedule_interview(
            old_schedule.id, self.slot.id
        )

        self.assertFalse(result["success"])
        self.assertEqual(
            result["message"], "Please select a different slot."
        )

    def test_cancelled_interview_cannot_be_rescheduled(self):
        old_schedule = InterviewSchedule.objects.create(
            application=self.application,
            availability_slot=self.slot,
            scheduled_start=self.slot.start_time,
            scheduled_end=self.slot.end_time,
            status="CANCELLED",
        )

        result = reschedule_interview(
            old_schedule.id, self.new_slot.id
        )

        self.assertFalse(result["success"])
        self.assertEqual(
            result["message"],
            "Cancelled interview cannot be rescheduled.",
        )

    @patch("core.interview_scheduler.create_reminders_for_interview")
    @patch("core.interview_scheduler.send_interview_confirmation_email")
    def test_reschedule_email_failure_does_not_create_reminders(
        self, mock_email, mock_reminders
    ):
        old_schedule = InterviewSchedule.objects.create(
            application=self.application,
            availability_slot=self.slot,
            scheduled_start=self.slot.start_time,
            scheduled_end=self.slot.end_time,
            status="CONFIRMED",
        )
        mock_email.return_value = {
            "success": False,
            "message": "Email could not be sent.",
        }

        result = reschedule_interview(
            old_schedule.id, self.new_slot.id
        )

        self.assertTrue(result["success"])
        mock_email.assert_called_once()
        mock_reminders.assert_not_called()
