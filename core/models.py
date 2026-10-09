from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES=[
        ('ADMIN','Admin'),
        ('EMPLOYER','Employer'),
        ('CANDIDATE','Candidate'),
    ]
    email=models.EmailField(unique=True)
    phone=models.CharField(max_length=15,blank=True)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email



class Candidate (models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE,related_name='candidate_profile')
    phone=models.CharField(max_length=15)
    address=models.TextField()
    skills=models.TextField()
    education=models.TextField(blank=True)
    experience=models.PositiveIntegerField(default=0)
    expected_salary=models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    resume=models.FileField(upload_to='resumes/',blank=True,null=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.user.username


class Employer(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE,related_name='employer_profile')
    company_name=models.CharField(max_length=200)
    company_email=models.EmailField()
    company_phone=models.CharField(max_length=15)
    website=models.URLField(blank=True,null=True)
    domain=models.CharField(max_length=200,blank=True)
    company_size=models.PositiveIntegerField(null=True,blank=True)
    location=models.CharField(max_length=200)
    description=models.TextField()
    is_verified=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name

class Job(models.Model):
    employer = models.ForeignKey(
        Employer,
        on_delete=models.CASCADE,
        related_name='jobs'
    )
    title = models.CharField(
    max_length=200,
    db_index=True
    )

    description = models.TextField()
    skills = models.TextField(blank=True)
    education_required = models.CharField(
    max_length=100,
    blank=True
    )

    salary_min = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    null=True,
    blank=True
    )

    salary_max = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    null=True,
    blank=True
    )

    location = models.CharField(
    max_length=200,
    db_index=True
    )
    
    job_type = models.CharField(max_length=50)

    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
        ('EXPIRED', 'Expired'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='OPEN'
    )
    featured = models.BooleanField(default=False)
    experience_required = models.PositiveIntegerField()
    deadline = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [
            models.Index(
                fields=['status', '-created_at']
            ),
        ]
    def __str__(self):
        return self.title


class Application(models.Model):
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='applications'
    )

    # Resume snapshot at the time of application
    resume_snapshot = models.FileField(
        upload_to='application_resumes/',
        blank=True,
        null=True
    )

    cover_letter = models.TextField()

    STATUS_CHOICES = [
        ('APPLIED', 'Applied'),
        ('SHORTLISTED', 'Shortlisted'),
        ('INTERVIEW_SCHEDULED', 'Interview Scheduled'),
        ('REJECTED', 'Rejected'),
        ('SELECTED', 'Selected'),
]

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='APPLIED'
    )

    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.candidate.user.username} - {self.job.title}"
class ApplicationStatusHistory(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='status_history'
    )

    status = models.CharField(max_length=50)

    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.application.id} - {self.status}" 
class SavedJob(models.Model):
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name='saved_jobs'
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='saved_by'
    )
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['candidate', 'job'],
                name='unique_candidate_saved_job'
            )
        ]
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.candidate.user.username} - {self.job.title}"       

class AccountFlag(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='flags'
    )
    reason = models.TextField()
    flagged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_account_flags'
    )
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Flag for {self.user.username}"  

class AdminAuditLog(models.Model):
    admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=100)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} - {self.created_at}"      

class ATSScore(models.Model):
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="ats_score"
    )

    match_percentage = models.FloatField(default=0)
    skills_score = models.FloatField(default=0)
    experience_score = models.FloatField(default=0)
    education_score = models.FloatField(null=True, blank=True)

    matched_skills = models.JSONField(default=list, blank=True)
    missing_skills = models.JSONField(default=list, blank=True)

    calculated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"Application {self.application.id} "
            f"- ATS Match {self.match_percentage}%"
        )    