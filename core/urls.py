from .views import JobListAPI, JobCreateAPI, UserTestAPI, UserRegistrationAPI
from django.urls import path
from .views import (
    JobListAPI,
    JobCreateAPI,
    UserTestAPI,
    UserRegistrationAPI
)

urlpatterns = [
    path('jobs/', JobListAPI.as_view(), name='job-list'),
    path('jobs/create/', JobCreateAPI.as_view(), name='job-create'),
    path('test/', UserTestAPI.as_view(), name='test-api'),
    path('register/', UserRegistrationAPI.as_view(), name='user-register'),
]