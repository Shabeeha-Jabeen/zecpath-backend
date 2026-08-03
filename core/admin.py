from django.contrib import admin
from .models import User, Employer, Candidate, Job, Application


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "username",
        "role",
        "phone",
        "is_active",
        "is_verified",
    )
    list_filter = ("role", "is_active", "is_verified")
    search_fields = ("email", "username", "phone")


@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display = ("company_name", "company_email", "company_phone", "location")
    search_fields = ("company_name", "company_email")


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "experience")
    search_fields = ("user__email", "phone")


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "employer", "location", "deadline")
    search_fields = ("title", "location")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("candidate", "job", "status", "applied_at")
    list_filter = ("status",)