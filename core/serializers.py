from rest_framework import serializers
from .models import User, Job, Application,Candidate,Employer, ApplicationStatusHistory


class JobSerializer(serializers.ModelSerializer):

    class Meta:
        model = Job
        fields = '__all__'
        read_only_fields = ['employer', 'created_at']


class UserRegistrationSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password',
            'phone',
            'role',
        ]

    def validate_role(self, value):
        allowed_roles = ['ADMIN', 'EMPLOYER', 'CANDIDATE']

        if value not in allowed_roles:
            raise serializers.ValidationError(
                "Invalid role. Choose Admin, Employer, or Candidate."
            )

        return value

    def create(self, validated_data):
        password = validated_data.pop('password')

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        return user
class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = '__all__'
        read_only_fields = [
            'candidate',
            'resume_snapshot',
            'status',
            'applied_at',
            'updated_at',
        ]
class ApplicationStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationStatusHistory
        fields = [
            'id',
            'application',
            'status',
            'changed_at',
        ]
        read_only_fields = [
            'id',
            'application',
            'status',
            'changed_at',
        ]

class CandidateProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = Candidate
        fields = [
            'id',
            'phone',
            'address',
            'skills',
            'education',
            'experience',
            'expected_salary',
            'resume',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_resume(self, file):
        if file is None:
            return file

        allowed_extensions = ['pdf', 'doc', 'docx']
        extension = file.name.split('.')[-1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only PDF, DOC, and DOCX files are allowed."
            )

        # Maximum file size = 5 MB
        max_size = 5 * 1024 * 1024

        if file.size > max_size:
            raise serializers.ValidationError(
                "Resume file size must not exceed 5 MB."
            )

        return file
    def update(self, instance, validated_data):
        old_resume = instance.resume

        new_resume = validated_data.get('resume')

        if new_resume and old_resume:
            old_resume.delete(save=False)

        return super().update(instance, validated_data)


class EmployerProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = Employer
        fields = [
            'id',
            'company_name',
            'company_email',
            'company_phone',
            'website',
            'domain',
            'company_size',
            'location',
            'description',
            'is_verified',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'is_verified',
            'created_at',
            'updated_at',
        ]