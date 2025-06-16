
# api/serializers.py
from rest_framework import serializers
from jobs.models import JobApplication, JobSearchConfig
from followups.models import FollowUpHistory, FollowUpTemplate
from accounts.models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'id', 'full_name', 'email', 'phone', 'location',
            'linkedin_url', 'github_url', 'portfolio_url',
            'years_experience', 'education', 'current_job_title',
            'current_company', 'key_skills', 'preferred_salary_min',
            'preferred_salary_max', 'work_type_preference',
            'preferred_company_sizes', 'industries_of_interest',
            'profile_completion_percentage'
        ]


class JobSearchConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobSearchConfig
        fields = [
            'id', 'config_name', 'job_categories', 'target_locations',
            'remote_preference', 'salary_min', 'salary_max',
            'company_size_preference', 'auto_follow_up_enabled',
            'is_active', 'last_search_date'
        ]


class JobApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = [
            'id', 'job_title', 'company_name', 'job_url',
            'job_description', 'salary_range', 'location',
            'remote_option', 'application_status', 'applied_date',
            'last_follow_up_date', 'follow_up_count',
            'next_follow_up_date', 'urgency_level',
            'company_rating', 'glassdoor_rating',
            'documents_generated', 'match_percentage',
            'created_at', 'updated_at'
        ]


class FollowUpTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUpTemplate
        fields = [
            'id', 'template_name', 'template_type',
            'subject_template', 'body_template',
            'days_after_application', 'is_default',
            'success_rate', 'times_used', 'responses_received'
        ]


class FollowUpHistorySerializer(serializers.ModelSerializer):
    application_title = serializers.CharField(source='application.job_title', read_only=True)
    company_name = serializers.CharField(source='application.company_name', read_only=True)
    template_name = serializers.CharField(source='template.template_name', read_only=True)

    class Meta:
        model = FollowUpHistory
        fields = [
            'id', 'application_title', 'company_name',
            'template_name', 'sent_date', 'subject',
            'response_received', 'response_date',
            'response_type', 'notes'
        ]