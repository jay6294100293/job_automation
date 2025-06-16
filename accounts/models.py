from django.db import models

# Create your models here.
# accounts/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import json


class UserProfile(models.Model):
    WORK_TYPE_CHOICES = [
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
        ('onsite', 'On-site'),
        ('flexible', 'Flexible'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    discord_user_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=255, blank=True)
    linkedin_url = models.URLField(max_length=500, blank=True)
    github_url = models.URLField(max_length=500, blank=True)
    portfolio_url = models.URLField(max_length=500, blank=True)

    # Professional Details
    years_experience = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(50)],
        null=True, blank=True
    )
    education = models.TextField(blank=True)
    current_job_title = models.CharField(max_length=255, blank=True)
    current_company = models.CharField(max_length=255, blank=True)
    key_skills = models.JSONField(default=list, blank=True)

    # Job Preferences
    preferred_salary_min = models.IntegerField(null=True, blank=True)
    preferred_salary_max = models.IntegerField(null=True, blank=True)
    work_type_preference = models.CharField(
        max_length=50,
        choices=WORK_TYPE_CHOICES,
        default='remote'
    )
    preferred_company_sizes = models.JSONField(default=list, blank=True)
    industries_of_interest = models.JSONField(default=list, blank=True)

    # Resume Management
    resume_file = models.FileField(upload_to='resumes/', null=True, blank=True)
    profile_completion_percentage = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - Profile"

    def calculate_completion_percentage(self):
        """Calculate profile completion percentage"""
        total_fields = 15
        completed_fields = 0

        # Check required fields
        if self.user.first_name: completed_fields += 1
        if self.user.last_name: completed_fields += 1
        if self.user.email: completed_fields += 1
        if self.phone: completed_fields += 1
        if self.location: completed_fields += 1
        if self.linkedin_url: completed_fields += 1
        if self.years_experience is not None: completed_fields += 1
        if self.education: completed_fields += 1
        if self.current_job_title: completed_fields += 1
        if self.key_skills: completed_fields += 1
        if self.preferred_salary_min: completed_fields += 1
        if self.preferred_salary_max: completed_fields += 1
        if self.work_type_preference: completed_fields += 1
        if self.industries_of_interest: completed_fields += 1
        if self.resume_file: completed_fields += 1

        percentage = int((completed_fields / total_fields) * 100)
        self.profile_completion_percentage = percentage
        self.save(update_fields=['profile_completion_percentage'])
        return percentage

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not kwargs.get('update_fields'):
            self.calculate_completion_percentage()