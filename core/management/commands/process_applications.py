
from django.core.management.base import BaseCommand
from core.ats_scoring import batch_process_applications


class Command(BaseCommand):
    help = "Process pending job applications in batch"

    def handle(self, *args, **options):
        result = batch_process_applications()

        self.stdout.write(
            self.style.SUCCESS(
                f"Total processed: {result['total_processed']}"
            )
        )

        for item in result["results"]:
            self.stdout.write(str(item))
