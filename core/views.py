from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Job
from .serializers import JobSerializer, UserRegistrationSerializer


class JobListAPI(APIView):
    def get(self, request):
        jobs = Job.objects.all()
        serializer = JobSerializer(jobs, many=True)
        return Response(serializer.data)


class JobCreateAPI(APIView):
    def post(self, request):
        serializer = JobSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors)


class UserTestAPI(APIView):
    def get(self, request):
        return Response({
            "message": "API Working Successfully"
        })


class UserRegistrationAPI(APIView):
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            return Response({
                "message": "User registered successfully",
                "user": {
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                }
            }, status=201)

        return Response(serializer.errors, status=400)