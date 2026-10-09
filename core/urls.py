from django.urls import path
from .views import (
    JobListAPI,
    JobCreateAPI,
    JobUpdateAPI,
    JobStatusAPI,
    UserTestAPI,
    UserRegistrationAPI,
    ApplicationCreateAPI,
    MyApplicationsAPI,
    CandidateProfileAPI,
    EmployerProfileAPI,
    ErrorTestAPI,
    FeaturedJobListAPI,
    LatestJobListAPI,
    ApplicationStatusHistoryAPI,
    ApplicationStatusUpdateAPI,
    EmployerJobListAPI,
    EmployerJobApplicationsAPI,
    EmployerDashboardAPI,
    SaveJobAPI,
    SavedJobListAPI,
    UnsaveJobAPI,
    CandidateInterviewStatusAPI,
    CandidateApplicationTimelineAPI,
    CandidateJobRecommendationAPI,
    EmployerApprovalAPI,
    UserBlockAPI,
    AdminJobListAPI,
    AdminJobDeleteAPI,
    PlatformStatsAPI,
    UserGrowthAPI,
    JobActivityAPI,
    AccountFlagListAPI,
    AccountFlagAPI,
    ResolveAccountFlagAPI,
    AdminAuditLogAPI,
    

    
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


urlpatterns = [
    path('jobs/', JobListAPI.as_view(), name='job-list'),
    path('jobs/create/', JobCreateAPI.as_view(), name='job-create'),
    path('test/', UserTestAPI.as_view(), name='test-api'),
    path('register/', UserRegistrationAPI.as_view(), name='user-register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path(
    'applications/create/',
    ApplicationCreateAPI.as_view(),
    name='application-create'
),
path('candidate/profile/', CandidateProfileAPI.as_view()),
path('employer/profile/', EmployerProfileAPI.as_view()),
path('error-test/', ErrorTestAPI.as_view(), name='error-test'),
path(
    'jobs/<int:pk>/',
    JobUpdateAPI.as_view(),
    name='job-update'
),
path(
    'jobs/<int:pk>/status/',
    JobStatusAPI.as_view(),
    name='job-status'
),
path(
    'jobs/featured/',
    FeaturedJobListAPI.as_view(),
    name='featured-jobs'
),
path(
    'jobs/latest/',
    LatestJobListAPI.as_view(),
    name='latest-jobs'
),
path(
    'applications/my/',
    MyApplicationsAPI.as_view(),
    name='my-applications'
),
path(
    'applications/<int:application_id>/history/',
    ApplicationStatusHistoryAPI.as_view(),
    name='application-status-history'
),
path(
    'applications/<int:application_id>/status/',
    ApplicationStatusUpdateAPI.as_view(),
    name='application-status-update'
),
path(
    'employer/jobs/',
    EmployerJobListAPI.as_view(),
    name='employer-job-list'
),
path(
    'employer/jobs/<int:job_id>/applications/',
    EmployerJobApplicationsAPI.as_view(),
    name='employer-job-applications'
),
path(
    'employer/dashboard/',
    EmployerDashboardAPI.as_view(),
    name='employer-dashboard'
),
path(
    'jobs/<int:job_id>/save/',
    SaveJobAPI.as_view(),
    name='save-job'
),
path('candidate/saved-jobs/',SavedJobListAPI.as_view(),name='saved-job-list'),
path(
    'jobs/<int:job_id>/unsave/',
    UnsaveJobAPI.as_view(),
    name='unsave-job'
),
path(
    'candidate/interviews/',
    CandidateInterviewStatusAPI.as_view(),
    name='candidate-interviews'
),
path(
    'candidate/applications/<int:application_id>/timeline/',
    CandidateApplicationTimelineAPI.as_view(),
    name='candidate-application-timeline'
),
path(
    'candidate/recommendations/',
    CandidateJobRecommendationAPI.as_view(),
    name='candidate-recommendations'
),
path(
    'admin/employers/<int:employer_id>/approval/',
    EmployerApprovalAPI.as_view(),
    name='admin-employer-approval'
),

path(
    'admin/users/<int:user_id>/block/',
    UserBlockAPI.as_view(),
    name='admin-user-block'
),

path(
    'admin/jobs/',
    AdminJobListAPI.as_view(),
    name='admin-job-list'
),

path(
    'admin/jobs/<int:job_id>/delete/',
    AdminJobDeleteAPI.as_view(),
    name='admin-job-delete'
),

path(
    'admin/stats/',
    PlatformStatsAPI.as_view(),
    name='admin-platform-stats'
),

path(
    'admin/user-growth/',
    UserGrowthAPI.as_view(),
    name='admin-user-growth'
),

path(
    'admin/job-activity/',
    JobActivityAPI.as_view(),
    name='admin-job-activity'
),

path(
    'admin/account-flags/',
    AccountFlagListAPI.as_view(),
    name='admin-account-flag-list'
),
path(
    'admin/account-flags/create/',
    AccountFlagAPI.as_view(),
    name='admin-account-flag-create'
),

path(
    'admin/account-flags/<int:flag_id>/resolve/',
    ResolveAccountFlagAPI.as_view(),
    name='admin-account-flag-resolve'
),

path('admin/audit-logs/',AdminAuditLogAPI.as_view(),name='admin-audit-logs'),
]