from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

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
    is_available_for_ai_call = models.BooleanField(default=True)
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
    ats_cutoff = models.FloatField(default=70.0)
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

class AICallLog(models.Model):
    STATUS_CHOICES = [
        ("QUEUED", "Queued"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    application = models.ForeignKey(
        "Application",
        on_delete=models.CASCADE,
        related_name="ai_call_logs",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="QUEUED",
    )
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
    )
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    retry_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"AI Call - Application {self.application_id} "
            f"({self.status})"
        )

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

class EmailDeliveryLog(models.Model):
    EVENT_CHOICES = [
        ("APPLICATION_SUBMITTED", "Application Submitted"),
        ("SHORTLISTED", "Shortlisted"),
        ("REJECTED", "Rejected"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SENT", "Sent"),
        ("FAILED", "Failed"),
    ]

    application = models.ForeignKey(
        "Application",
        on_delete=models.CASCADE,
        related_name="email_logs",
    )
    event = models.CharField(
        max_length=30,
        choices=EVENT_CHOICES,
    )
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="PENDING",
    )
    error_message = models.TextField(blank=True)
    attempts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.event} - {self.status} - {self.recipient}"

class AIInterviewSession(models.Model):
    STATUS_CHOICES = [
        ("CREATED", "Created"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    application = models.ForeignKey(
        "Application",
        on_delete=models.CASCADE,
        related_name="ai_interview_sessions",
    )
    call_log = models.ForeignKey(
        "AICallLog",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interview_sessions",
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_ai_sessions",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="CREATED",
    )
    transcript_text = models.TextField(blank=True)
    transcript_json = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Interview Session {self.id} - {self.status}"


class AIQuestion(models.Model):
    session = models.ForeignKey(
        AIInterviewSession,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    question_text = models.TextField()
    order = models.PositiveIntegerField(default=1)
    asked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Question {self.order} - Session {self.session_id}"

class QuestionTemplate(models.Model):
    CATEGORY_CHOICES = [
        ("INTRODUCTION", "Introduction"),
        ("EXPERIENCE", "Experience"),
        ("SKILLS", "Skills"),
        ("AVAILABILITY", "Availability"),
        ("SALARY", "Salary"),
    ]

    ROLE_CHOICES = [
        ("ALL", "All Roles"),
        ("PYTHON_DEVELOPER", "Python Developer"),
        ("DJANGO_DEVELOPER", "Django Developer"),
        ("BACKEND_DEVELOPER", "Backend Developer"),
    ]

    question_text = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
    )
    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default="ALL",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "id"]

    def __str__(self):
        return f"{self.category} - {self.question_text[:50]}"


class JobQuestionMapping(models.Model):
    job = models.ForeignKey(
        "Job",
        on_delete=models.CASCADE,
        related_name="question_mappings",
    )
    question_template = models.ForeignKey(
        QuestionTemplate,
        on_delete=models.CASCADE,
        related_name="job_mappings",
    )
    order = models.PositiveIntegerField(default=1)
    is_required = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["job", "question_template"],
                name="unique_job_question_template",
            )
        ]

    def __str__(self):
        return f"{self.job.title} - Question {self.order}"
    


class AIAnswer(models.Model):
    question = models.OneToOneField(
        AIQuestion,
        on_delete=models.CASCADE,
        related_name="answer"
    )
    answer_text = models.TextField(blank=True)
    transcript_text = models.TextField(blank=True)
    structured_data = models.JSONField(default=dict, blank=True)

    # Day 37: Answer evaluation fields
    confidence_score = models.FloatField(
        null=True,
        blank=True
    )
    ai_annotations = models.JSONField(
        default=dict,
        blank=True
    )
    relevance_score = models.FloatField(
        default=0,
    )
    completeness_score = models.FloatField(
        default=0,
    )
    keyword_score = models.FloatField(
        default=0,
    )
    total_score = models.FloatField(
        default=0,
    )

    answered_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Answer for Question {self.question_id}"

class CallLog(models.Model):
    session = models.ForeignKey(
        AIInterviewSession,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    call_log = models.ForeignKey(
        "AICallLog",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_call_audit_logs",
    )
    event_type = models.CharField(max_length=100)
    reason = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} - {self.created_at}"

class AvailabilitySlot(models.Model):
    ROLE_CHOICES = [
        ("ALL", "All Roles"),
        ("PYTHON", "Python Developer"),
        ("DJANGO", "Django Developer"),
        ("FULLSTACK", "Full Stack Developer"),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="ALL",
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.role}: {self.start_time} - {self.end_time}"


class InterviewSchedule(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("CONFIRMED", "Confirmed"),
        ("CANCELLED", "Cancelled"),
    ]

    application = models.ForeignKey(
        "Application",
        on_delete=models.CASCADE,
        related_name="interview_schedules",
    )
    availability_slot = models.ForeignKey(
        AvailabilitySlot,
        on_delete=models.PROTECT,
        related_name="interview_schedules",
    )
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )
    confirmation_email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["availability_slot"],
                condition=~models.Q(status="CANCELLED"),
                name="unique_active_interview_per_slot",
            ),
        ]

    def __str__(self):
        return f"Interview {self.id} - {self.status}"
   
class InterviewReminder(models.Model):
    STAGE_CHOICES = [
        ("24_HOURS", "24 Hours Before"),
        ("1_HOUR", "1 Hour Before"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SENT", "Sent"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
    ]

    interview = models.ForeignKey(
        "core.InterviewSchedule",
        on_delete=models.CASCADE,
        related_name="reminders",
    )
    stage = models.CharField(
        max_length=20,
        choices=STAGE_CHOICES,
    )
    scheduled_at = models.DateTimeField()
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="PENDING",
    )
    attempts = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["interview", "stage"],
                name="unique_reminder_per_interview_stage",
            )
        ]
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"{self.interview_id} - {self.stage} - {self.status}"