from django.core.management.base import BaseCommand

from core.reminder_service import process_due_reminders


class Command(BaseCommand):
    help = "Process due interview reminders"

    def handle(self, *args, **options):
        results = process_due_reminders()

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed: {results['processed']}, "
                f"Sent: {results['sent']}, "
                f"Failed: {results['failed']}"
            )
        )