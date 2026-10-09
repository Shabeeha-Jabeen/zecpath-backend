from django.db.models import Q,Count
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny,IsAuthenticated
from .models import Application, Candidate, Employer, Job,ApplicationStatusHistory,SavedJob,User,AccountFlag,AdminAuditLog,ATSScore
from .permissions import IsCandidate, IsEmployer,IsPlatformAdmin
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models.functions import TruncMonth
from core.ats_scoring import calculate_ats_score
from .resume_parser import extract_resume_text,clean_resume_text,extract_resume_skills,extract_experience_years,extract_education
from pathlib import Path
from .serializers import (
    ApplicationSerializer,
    CandidateProfileSerializer,
    EmployerProfileSerializer,
    JobSerializer,
    UserRegistrationSerializer,
    ApplicationStatusHistorySerializer,
)
class JobListAPI(APIView):

    permission_classes = [AllowAny]

    def get(self, request):

        jobs = Job.objects.select_related('employer').filter(
            status='OPEN'
        ).order_by('-created_at')

        # Filter by role
        role = request.query_params.get('role')

        if role:
            jobs = jobs.filter(employer__user__role=role)

        # Filter by job type
        job_type = request.query_params.get('job_type')

        if job_type:
            jobs = jobs.filter(job_type=job_type)

        # Filter by deadline
        deadline = request.query_params.get('deadline')

        if deadline:
            jobs = jobs.filter(deadline=deadline)

        # Filter by status
        status = request.query_params.get('status')

        if status:
            jobs = jobs.filter(status=status)

        # Search by keyword
        search = request.query_params.get('search')

        if search:
            jobs = jobs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(skills__icontains=search) |
                Q(location__icontains=search)
    )
        # Filter by skills
        skills = request.query_params.get('skills')

        if skills:
            jobs = jobs.filter(
                skills__icontains=skills
    ) 
        # Filter by minimum experience
        min_experience = request.query_params.get('min_experience')

        if min_experience:
             jobs = jobs.filter(
                experience_required__gte=min_experience
    )

# Filter by maximum experience
        max_experience = request.query_params.get('max_experience')

        if max_experience:
            jobs = jobs.filter(
                experience_required__lte=max_experience
    )      
    # Filter by minimum salary
        min_salary = request.query_params.get('min_salary')

        if min_salary:
            jobs = jobs.filter(
                salary_min__gte=min_salary
    )

# Filter by maximum salary
        max_salary = request.query_params.get('max_salary')

        if max_salary:
            jobs = jobs.filter(
                salary_max__lte=max_salary
    )  
        # Filter by location
        location = request.query_params.get('location')

        if location:
            jobs = jobs.filter(
                location__icontains=location
    )           

        # Search by title
        title = request.query_params.get('title')

        if title:
            jobs = jobs.filter(title__icontains=title)

        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = 5

        page = paginator.paginate_queryset(jobs, request)

        serializer = JobSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)
class FeaturedJobListAPI(APIView):

    permission_classes = [AllowAny]

    def get(self, request):

        jobs = Job.objects.filter(
            status='OPEN',
            featured=True
        ).select_related(
            'employer'
        ).order_by('-created_at')

        serializer = JobSerializer(
            jobs,
            many=True
        )

        return Response(serializer.data)
class LatestJobListAPI(APIView):

    permission_classes = [AllowAny]

    def get(self, request):

        jobs = Job.objects.filter(
            status='OPEN'
        ).select_related(
            'employer'
        ).order_by('-created_at')

        paginator = PageNumberPagination()
        paginator.page_size = 5

        page = paginator.paginate_queryset(
            jobs,
            request
        )

        serializer = JobSerializer(
            page,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )
class JobCreateAPI(APIView):
    permission_classes = [IsEmployer]

    def post(self, request):
        serializer = JobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save(
            employer=request.user.employer_profile
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )
class JobUpdateAPI(APIView):
    permission_classes = [IsEmployer]

    def put(self, request, pk):
        try:
            job = Job.objects.get(pk=pk)
        except Job.DoesNotExist:
            return Response(
                {"detail": "Job not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if job.employer.user != request.user:
            return Response(
                {"detail": "You can only edit your own jobs."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = JobSerializer(
            job,
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)  
class JobStatusAPI(APIView):
    permission_classes = [IsEmployer]

    def patch(self, request, pk):
        try:
            job = Job.objects.get(pk=pk)
        except Job.DoesNotExist:
            return Response(
                {"detail": "Job not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if job.employer.user != request.user:
            return Response(
                {"detail": "You can only update your own jobs."},
                status=status.HTTP_403_FORBIDDEN
            )

        new_status = request.data.get("status")

        if new_status not in ["OPEN", "CLOSED", "EXPIRED"]:
            return Response(
                {
                    "detail": "Invalid status. Use OPEN, CLOSED, or EXPIRED."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        job.status = new_status
        job.save()

        return Response(
            {
                "message": "Job status updated successfully.",
                "status": job.status
            },
            status=status.HTTP_200_OK
        )   
class EmployerJobListAPI(APIView):
    permission_classes = [IsEmployer]

    def get(self, request):
        employer = request.user.employer_profile

        jobs = Job.objects.filter(
            employer=employer
        ).order_by('-created_at')

        serializer = JobSerializer(
            jobs,
            many=True
        )

        return Response(serializer.data)  
class EmployerJobApplicationsAPI(APIView):
    permission_classes = [IsEmployer]

    def get(self, request, job_id):
        employer = request.user.employer_profile

        try:
            job = Job.objects.get(
                id=job_id,
                employer=employer
            )
        except Job.DoesNotExist:
            return Response(
                {"detail": "Job not found or you do not own this job."},
                status=status.HTTP_404_NOT_FOUND
            )

        applications = Application.objects.filter(
            job=job
        ).select_related(
            'candidate__user'
        ).order_by('-applied_at')

        status_filter = request.query_params.get("status")

        if status_filter:
            applications = applications.filter(
                status=status_filter
            )
        search = request.query_params.get("search")

        if search:
            applications = applications.filter(
                Q(candidate__user__username__icontains=search) |
                Q(candidate__user__first_name__icontains=search) |
                Q(candidate__user__last_name__icontains=search) |
                Q(candidate__user__email__icontains=search)
        )

        serializer = ApplicationSerializer(
            applications,
            many=True
        )

        return Response(serializer.data)   
class EmployerDashboardAPI(APIView):
    permission_classes = [IsEmployer]

    def get(self, request):
        employer = request.user.employer_profile

        jobs = Job.objects.filter(
            employer=employer
        )

        applications = Application.objects.filter(
            job__employer=employer
        )

        total_jobs = jobs.count()
        open_jobs = jobs.filter(status="OPEN").count()
        closed_jobs = jobs.filter(status="CLOSED").count()

        total_applications = applications.count()

        applied_count = applications.filter(
            status="APPLIED"
        ).count()

        shortlisted_count = applications.filter(
            status="SHORTLISTED"
        ).count()

        interview_count = applications.filter(
            status="INTERVIEW_SCHEDULED"
        ).count()

        rejected_count = applications.filter(
            status="REJECTED"
        ).count()

        selected_count = applications.filter(
            status="SELECTED"
        ).count()

        if total_applications > 0:
            shortlist_ratio = round(
                (shortlisted_count / total_applications) * 100,
                2
            )
        else:
            shortlist_ratio = 0

        return Response({
            "total_jobs": total_jobs,
            "open_jobs": open_jobs,
            "closed_jobs": closed_jobs,
            "total_applications": total_applications,
            "applied": applied_count,
            "shortlisted": shortlisted_count,
            "interview_scheduled": interview_count,
            "rejected": rejected_count,
            "selected": selected_count,
            "shortlist_ratio": shortlist_ratio
        })          

class UserTestAPI(APIView):
    def get(self, request):
        return Response({
            "message": "API Working Successfully"
        })


class UserRegistrationAPI(APIView):

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        return Response(
            {
                "message": "User registered successfully",
                "user": {
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                }
            },
            status=status.HTTP_201_CREATED
        )
class ApplicationCreateAPI(APIView):
    permission_classes = [IsCandidate]

    def post(self, request):
        candidate = request.user.candidate_profile

        # Get job ID
        job_id = request.data.get("job")

        if not job_id:
            return Response(
                {"detail": "Job is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check whether job exists
        try:
            job = Job.objects.get(pk=job_id)
        except Job.DoesNotExist:
            return Response(
                {"detail": "Job not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check job status
        if job.status != "OPEN":
            return Response(
                {"detail": "You can only apply for open jobs."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check duplicate application
        already_applied = Application.objects.filter(
            candidate=candidate,
            job=job
        ).exists()

        if already_applied:
            return Response(
                {"detail": "You have already applied for this job."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check candidate resume
        if not candidate.resume:
            return Response(
                {"detail": "Please upload your resume before applying."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        application = serializer.save(
            candidate=candidate,
            status="APPLIED"
        )
        ApplicationStatusHistory.objects.create(
            application=application,
            status="APPLIED"
        )

        # Bind candidate's current resume to application
        application.resume_snapshot = candidate.resume
        application.save(update_fields=["resume_snapshot"])

        return Response(
            ApplicationSerializer(application).data,
            status=status.HTTP_201_CREATED
        )
class SaveJobAPI(APIView):
    permission_classes = [IsCandidate]

    def post(self, request, job_id):
        candidate = request.user.candidate_profile

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response(
                {"detail": "Job not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        saved_job, created = SavedJob.objects.get_or_create(
            candidate=candidate,
            job=job
        )

        if not created:
            return Response(
                {"detail": "Job already saved."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "message": "Job saved successfully.",
                "job_id": job.id
            },
            status=status.HTTP_201_CREATED
        )  
class SavedJobListAPI(APIView):
    permission_classes = [IsCandidate]

    def get(self, request):
        candidate = request.user.candidate_profile

        saved_jobs = SavedJob.objects.filter(
            candidate=candidate
        ).select_related(
            'job'
        ).order_by('-saved_at')

        serializer = JobSerializer(
            [saved.job for saved in saved_jobs],
            many=True
        )

        return Response(serializer.data)  
class UnsaveJobAPI(APIView):
    permission_classes = [IsCandidate]

    def delete(self, request, job_id):
        candidate = request.user.candidate_profile

        try:
            saved_job = SavedJob.objects.get(
                candidate=candidate,
                job_id=job_id
            )
        except SavedJob.DoesNotExist:
            return Response(
                {"detail": "Job is not saved."},
                status=status.HTTP_404_NOT_FOUND
            )

        saved_job.delete()

        return Response(
            {"message": "Job unsaved successfully."},
            status=status.HTTP_200_OK
        )        
class MyApplicationsAPI(APIView):
    permission_classes = [IsCandidate]

    def get(self, request):
        candidate = request.user.candidate_profile

        applications = Application.objects.filter(
            candidate=candidate
        ).select_related(
            'job'
        ).order_by('-applied_at')

        serializer = ApplicationSerializer(
            applications,
            many=True
        )

        return Response(serializer.data)
class CandidateInterviewStatusAPI(APIView):
    permission_classes = [IsCandidate]

    def get(self, request):
        candidate = request.user.candidate_profile

        applications = Application.objects.filter(
            candidate=candidate,
            status="INTERVIEW_SCHEDULED"
        ).select_related(
            'job'
        ).order_by('-updated_at')

        serializer = ApplicationSerializer(
            applications,
            many=True
        )

        return Response(serializer.data)    
class CandidateApplicationTimelineAPI(APIView):
    permission_classes = [IsCandidate]

    def get(self, request, application_id):
        candidate = request.user.candidate_profile

        try:
            application = Application.objects.get(
                id=application_id,
                candidate=candidate
            )
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        history = ApplicationStatusHistory.objects.filter(
            application=application
        ).order_by('changed_at')

        serializer = ApplicationStatusHistorySerializer(
            history,
            many=True
        )

        return Response(serializer.data)      
class ApplicationStatusHistoryAPI(APIView):
    permission_classes = [IsCandidate]

    def get(self, request, application_id):
        candidate = request.user.candidate_profile

        try:
            application = Application.objects.get(
                id=application_id,
                candidate=candidate
            )
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        history = ApplicationStatusHistory.objects.filter(
            application=application
        ).order_by('changed_at')

        serializer = ApplicationStatusHistorySerializer(
            history,
            many=True
        )

        return Response(serializer.data) 
class ApplicationStatusUpdateAPI(APIView):
    permission_classes = [IsEmployer]

    def patch(self, request, application_id):
        try:
            application = Application.objects.select_related(
                'job__employer'
            ).get(id=application_id)
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Ownership check
        if application.job.employer.user != request.user:
            return Response(
                {
                    "detail": (
                        "You can only update applications "
                        "for your own jobs."
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )

        new_status = request.data.get("status")

        allowed_statuses = [
            "APPLIED",
            "SHORTLISTED",
            "INTERVIEW_SCHEDULED",
            "REJECTED",
            "SELECTED",
        ]

        if new_status not in allowed_statuses:
            return Response(
                {
                    "detail": (
                        "Invalid status. Use APPLIED, SHORTLISTED, "
                        "INTERVIEW_SCHEDULED, REJECTED, or SELECTED."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Workflow transition rules
        allowed_transitions = {
            "APPLIED": ["SHORTLISTED", "REJECTED"],
            "SHORTLISTED": ["INTERVIEW_SCHEDULED", "REJECTED"],
            "INTERVIEW_SCHEDULED": ["SELECTED", "REJECTED"],
            "REJECTED": [],
            "SELECTED": [],
        }

        current_status = application.status

        if new_status not in allowed_transitions[current_status]:
            return Response(
                {
                    "detail": (
                        f"Invalid status transition: "
                        f"{current_status} → {new_status}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        application.status = new_status
        application.save()

        ApplicationStatusHistory.objects.create(
            application=application,
            status=new_status
        )

        return Response(
            {
                "message": "Application status updated successfully.",
                "application_id": application.id,
                "status": application.status
            },
            status=status.HTTP_200_OK
        )
class CandidateProfileAPI(APIView):
    permission_classes = [IsAuthenticated, IsCandidate]
    parser_classes = [MultiPartParser, FormParser]

    def get_profile(self, request):
        return Candidate.objects.get(user=request.user)

    def get(self, request):
        profile = self.get_profile(request)
        serializer = CandidateProfileSerializer(profile)

        return Response(serializer.data)

    def post(self, request):
        if Candidate.objects.filter(user=request.user).exists():
            return Response(
                {"detail": "Candidate profile already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CandidateProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    def put(self, request):
        profile = self.get_profile(request)

        serializer = CandidateProfileSerializer(
            profile,
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def delete(self, request):
        profile = self.get_profile(request)
        profile.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )
    
class EmployerProfileAPI(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = Employer.objects.get(user=request.user)
        serializer = EmployerProfileSerializer(profile)
        return Response(serializer.data)

    def put(self, request):
        profile = Employer.objects.get(user=request.user)

        serializer = EmployerProfileSerializer(
            profile,
            data=request.data
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)
              
class ErrorTestAPI(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        raise Exception("Test server error")
class CandidateJobRecommendationAPI(APIView):
    permission_classes = [IsCandidate]

    def get(self, request):
        candidate = request.user.candidate_profile

        if not candidate.skills:
            return Response([])

        candidate_skills = [
            skill.strip()
            for skill in candidate.skills.split(',')
            if skill.strip()
        ]

        jobs = Job.objects.filter(
            status="OPEN"
        ).select_related(
            'employer'
        )

        recommended_jobs = []

        for job in jobs:
            matched_skills = []

            for skill in candidate_skills:
                if skill.lower() in job.skills.lower():
                    matched_skills.append(skill)

            if matched_skills:
                recommended_jobs.append({
                    "job": JobSerializer(job).data,
                    "matched_skills": matched_skills
                })

        return Response(recommended_jobs)

class EmployerApprovalAPI(APIView):
    permission_classes = [IsPlatformAdmin]

    def patch(self, request, employer_id):
        try:
            employer = Employer.objects.get(id=employer_id)
        except Employer.DoesNotExist:
            return Response(
                {"detail": "Employer not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        is_verified = request.data.get("is_verified")

        if not isinstance(is_verified, bool):
            return Response(
                {"detail": "is_verified must be true or false."},
                status=status.HTTP_400_BAD_REQUEST
            )

        employer.is_verified = is_verified
        employer.save(update_fields=["is_verified", "updated_at"])
        AdminAuditLog.objects.create(
            admin=request.user,
            action="EMPLOYER_APPROVAL_UPDATED",
            details=(
                f"Employer ID {employer.id} verification "
                f"status changed to {employer.is_verified}."
            )
        )

        return Response(
            {
                "message": "Employer verification status updated.",
                "employer_id": employer.id,
                "is_verified": employer.is_verified
            },
            status=status.HTTP_200_OK
        )   


class UserBlockAPI(APIView):
    permission_classes = [IsPlatformAdmin]

    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        is_active = request.data.get("is_active")

        if not isinstance(is_active, bool):
            return Response(
                {"detail": "is_active must be true or false."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.is_staff or user.is_superuser:
            return Response(
                {"detail": "Staff and superuser accounts cannot be blocked through this API."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active = is_active
        user.save(update_fields=["is_active"])
        AdminAuditLog.objects.create(
            admin=request.user,
            action="USER_STATUS_UPDATED",
            details=f"User ID {user.id} is_active set to {user.is_active}."
        )

        return Response(
            {
                "message": "User status updated successfully.",
                "user_id": user.id,
                "is_active": user.is_active
            },
            status=status.HTTP_200_OK
        )     

class AdminJobListAPI(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        jobs = Job.objects.select_related(
            'employer'
        ).order_by('-created_at')

        serializer = JobSerializer(jobs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)    

class AdminJobDeleteAPI(APIView):
    permission_classes = [IsPlatformAdmin]

    def delete(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response(
                {"detail": "Job not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        deleted_job_id = job.id
        deleted_job_title = job.title

        job.delete()

        AdminAuditLog.objects.create(
            admin=request.user,
            action="JOB_POST_DELETED",
            details=(
                f"Job ID {deleted_job_id}, "
                f"title '{deleted_job_title}', was deleted."
            )
        )

        return Response(
            {
                "message": "Job post deleted successfully.",
                "job_id": deleted_job_id
            },
            status=status.HTTP_200_OK
        ) 

class PlatformStatsAPI(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        return Response(
            {
                "total_users": User.objects.count(),
                "total_candidates": Candidate.objects.count(),
                "total_employers": Employer.objects.count(),
                "total_jobs": Job.objects.count(),
                "open_jobs": Job.objects.filter(status="OPEN").count(),
                "closed_jobs": Job.objects.filter(status="CLOSED").count(),
            },
            status=status.HTTP_200_OK
        )   

class UserGrowthAPI(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        growth = (
            User.objects
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(user_count=Count("id"))
            .order_by("month")
        )

        return Response(
            list(growth),
            status=status.HTTP_200_OK
        )    

class JobActivityAPI(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        activity = (
            Job.objects
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(job_count=Count("id"))
            .order_by("month")
        )

        return Response(
            list(activity),
            status=status.HTTP_200_OK
        )   

class AccountFlagAPI(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        user_id = request.data.get("user_id")
        reason = request.data.get("reason", "").strip()

        if not user_id or not reason:
            return Response(
                {"detail": "user_id and reason are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            flagged_user = User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if flagged_user.id == request.user.id:
            return Response(
                {"detail": "You cannot flag your own account."},
                status=status.HTTP_400_BAD_REQUEST
            )

        flag = AccountFlag.objects.create(
            user=flagged_user,
            reason=reason,
            flagged_by=request.user
        )
        AdminAuditLog.objects.create(
        admin=request.user,
        action="ACCOUNT_FLAGGED",
        details=(
            f"User ID {flag.user_id} was flagged. "
            f"Flag ID: {flag.id}. Reason: {flag.reason}"
        )
    )

        return Response(
            {
                "message": "Account flagged successfully.",
                "flag_id": flag.id,
                "user_id": flag.user_id,
                "reason": flag.reason,
                "is_resolved": flag.is_resolved
            },
            status=status.HTTP_201_CREATED
        )

class AccountFlagListAPI(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        flags = AccountFlag.objects.select_related(
            "user", "flagged_by"
        ).order_by("-created_at")

        data = [
            {
                "flag_id": flag.id,
                "user_id": flag.user_id,
                "username": flag.user.username,
                "reason": flag.reason,
                "flagged_by": (
                    flag.flagged_by.username
                    if flag.flagged_by else None
                ),
                "is_resolved": flag.is_resolved,
                "created_at": flag.created_at
            }
            for flag in flags
        ]

        return Response(data, status=status.HTTP_200_OK)

class ResolveAccountFlagAPI(APIView):
    permission_classes = [IsPlatformAdmin]

    def patch(self, request, flag_id):
        try:
            flag = AccountFlag.objects.get(id=flag_id)
        except AccountFlag.DoesNotExist:
            return Response(
                {"detail": "Account flag not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        flag.is_resolved = True
        flag.save(update_fields=["is_resolved"])
        AdminAuditLog.objects.create(
            admin=request.user,
            action="ACCOUNT_FLAG_RESOLVED",
            details=(
                f"Account flag ID {flag.id} resolved "
                f"for User ID {flag.user_id}."
            )
        )

        return Response(
            {
                "message": "Account flag resolved successfully.",
                "flag_id": flag.id,
                "user_id": flag.user_id,
                "is_resolved": flag.is_resolved
            },
            status=status.HTTP_200_OK
        )    


class AdminAuditLogAPI(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        logs = AdminAuditLog.objects.select_related(
            "admin"
        ).order_by("-created_at")

        data = [
            {
                "id": log.id,
                "admin": log.admin.username if log.admin else None,
                "action": log.action,
                "details": log.details,
                "created_at": log.created_at
            }
            for log in logs
        ]

        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        action = request.data.get("action", "").strip()
        details = request.data.get("details", "").strip()

        if not action:
            return Response(
                {"detail": "action is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        log = AdminAuditLog.objects.create(
            admin=request.user,
            action=action,
            details=details
        )

        return Response(
            {
                "message": "Audit log created successfully.",
                "id": log.id,
                "action": log.action,
                "details": log.details
            },
            status=status.HTTP_201_CREATED
        )

class ResumeTextExtractionAPI(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        resume_file = request.FILES.get("resume")

        if not resume_file:
            return Response(
                {"detail": "Please upload a resume file."},
                status=status.HTTP_400_BAD_REQUEST
            )

        extension = Path(resume_file.name).suffix.lower()

        if extension not in [".pdf", ".docx"]:
            return Response(
                {"detail": "Only PDF and DOCX files are supported."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if resume_file.size > 5 * 1024 * 1024:
            return Response(
                {"detail": "File size must not exceed 5 MB."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            extracted_text = extract_resume_text(resume_file)
            cleaned_text = clean_resume_text(extracted_text)

        except Exception:
            return Response(
                {"detail": "Unable to process this file."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not cleaned_text:
            return Response(
                {
                    "detail": (
                        "No readable text found. "
                        "The PDF may require OCR."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

       
        return Response({
            "filename": resume_file.name,
            "file_type": extension,
            "extracted_text": extracted_text,
            "cleaned_text": cleaned_text,
            "character_count": len(cleaned_text),
            "skills": extract_resume_skills(cleaned_text),
            "experience_years": extract_experience_years(cleaned_text),
            "education": extract_education(cleaned_text),
        }, status=status.HTTP_200_OK)  
class ATSMatchPercentageAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        try:
            job = Job.objects.get(
                id=job_id,
                status="OPEN"
            )
        except Job.DoesNotExist:
            return Response(
                {"error": "Open job not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            candidate = request.user.candidate_profile
        except Candidate.DoesNotExist:
            return Response(
                {"error": "Candidate profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        result = calculate_ats_score(candidate, job)

        return Response({
            "job_id": job.id,
            "job_title": job.title,
            "candidate_id": candidate.id,
            **result
        }, status=status.HTTP_200_OK)   

class RankedCandidatesAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id, status="OPEN")
        except Job.DoesNotExist:
            return Response(
                {"error": "Open job not found"},
                status=404
            )

        applications = (
            Application.objects
            .filter(job=job)
            .select_related("candidate", "candidate__user")
        )

        ranked_candidates = []

        for application in applications:
            candidate = application.candidate
            score_data = calculate_ats_score(candidate, job)
            ATSScore.objects.update_or_create(
                application=application,
                defaults={
                    "match_percentage": score_data["match_percentage"],
                    "skills_score": (
                        score_data["skills_score"]
                        if score_data["skills_score"] is not None
                        else 0
                    ),
                    "experience_score": score_data["experience_score"],
                    "education_score": score_data["education_score"],
                    "matched_skills": score_data["matched_skills"],
                    "missing_skills": score_data["missing_skills"],
            }
        )

            ranked_candidates.append({
                "application_id": application.id,
                "candidate_id": candidate.id,
                "candidate_name": candidate.user.username,
                "application_status": application.status,
                **score_data,
            })

        ranked_candidates.sort(
            key=lambda item: item["match_percentage"],
            reverse=True
        )

        for rank, candidate_data in enumerate(
            ranked_candidates, start=1
        ):
            candidate_data["rank"] = rank

        return Response({
            "job_id": job.id,
            "job_title": job.title,
            "total_candidates": len(ranked_candidates),
            "ranked_candidates": ranked_candidates,
        })     