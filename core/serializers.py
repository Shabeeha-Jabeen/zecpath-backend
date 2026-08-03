from rest_framework import serializers
from .models import User, Job


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = '__all__'


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