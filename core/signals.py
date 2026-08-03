from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Employer, Candidate


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):

    if created:

        if instance.role == "EMPLOYER":
            Employer.objects.create(
                user=instance,
                company_name="",
                company_email=instance.email,
                company_phone="",
                location="",
                description=""
            )

        elif instance.role == "CANDIDATE":
            Candidate.objects.create(
                user=instance,
                phone="",
                address="",
                skills="",
                experience=0
            )