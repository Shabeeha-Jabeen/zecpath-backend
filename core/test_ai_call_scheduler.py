
from datetime import datetime
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from core.ai_call_eligibility import get_next_ai_call_time


class AICallSchedulerTests(SimpleTestCase):

    def test_before_call_window(self):
        fake_now = timezone.make_aware(
            datetime(2026, 10, 13, 8, 0),
            timezone.get_current_timezone(),
        )

        with patch(
            "core.ai_call_eligibility.timezone.localtime",
            return_value=fake_now,
        ):
            result = get_next_ai_call_time()

        self.assertEqual(result.hour, 9)
        self.assertEqual(result.day, 13)

    def test_during_call_window(self):
        fake_now = timezone.make_aware(
            datetime(2026, 10, 13, 12, 0),
            timezone.get_current_timezone(),
        )

        with patch(
            "core.ai_call_eligibility.timezone.localtime",
            return_value=fake_now,
        ):
            result = get_next_ai_call_time()

        self.assertEqual(result, fake_now)

    def test_after_call_window(self):
        fake_now = timezone.make_aware(
            datetime(2026, 10, 13, 19, 0),
            timezone.get_current_timezone(),
        )

        with patch(
            "core.ai_call_eligibility.timezone.localtime",
            return_value=fake_now,
        ):
            result = get_next_ai_call_time()

        self.assertEqual(result.hour, 9)
        self.assertEqual(result.day, 14)
