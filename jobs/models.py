# jobs/models.py
from django.db import models
from django.contrib.auth.models import User
from accounts.models import UserProfile


class JobSearchConfig(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    config_name = models.CharField(max_length=255)
    job_categories = models.JSONField(default=list)
    target_locations = models.JSONField(default=list)
    remote_preference = models.CharField(max_length=50, default='remote')
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)
    company_size_preference = models.JSONField(default=list)
    auto_follow_up_enabled = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_search_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.config_name}"

    class Meta:
        unique_together = ['user', 'config_name']


class JobApplication(models.Model):
    STATUS_CHOICES = [
        ('found', 'Found'),
        ('applied', 'Applied'),
        ('responded', 'Responded'),
        ('interview', 'Interview Scheduled'),
        ('offer', 'Offer Received'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]

    URGENCY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    search_config = models.ForeignKey(JobSearchConfig, on_delete=models.SET_NULL, null=True)

    # Job Details
    job_title = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    job_url = models.URLField(max_length=2000, blank=True)
    job_description = models.TextField(blank=True)
    salary_range = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=255, blank=True)
    remote_option = models.CharField(max_length=50, blank=True)

    # Application Status
    application_status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='found'
    )
    applied_date = models.DateTimeField(null=True, blank=True)

    # Follow-up Management
    last_follow_up_date = models.DateTimeField(null=True, blank=True)
    follow_up_count = models.IntegerField(default=0)
    next_follow_up_date = models.DateField(null=True, blank=True)
    follow_up_sequence_active = models.BooleanField(default=False)

    # NEW FIELDS - Previously Missing
    urgency_level = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        default='medium'
    )
    notes = models.TextField(blank=True)

    # Interview and Offer Management
    interview_scheduled_date = models.DateTimeField(null=True, blank=True)
    offer_received = models.BooleanField(default=False)
    offer_amount = models.IntegerField(null=True, blank=True)

    # Rejection Tracking
    rejection_received = models.BooleanField(default=False)
    rejection_reason = models.CharField(max_length=255, blank=True)

    # Company and Job Analysis
    company_rating = models.FloatField(null=True, blank=True)
    glassdoor_rating = models.FloatField(null=True, blank=True)
    match_percentage = models.IntegerField(null=True, blank=True)

    # Document Management
    documents_generated = models.BooleanField(default=False)
    documents_folder_path = models.CharField(max_length=500, blank=True)

    # AI Analysis
    skills_match_analysis = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.job_title} at {self.company_name} - {self.user.username}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'application_status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['urgency_level']),
            models.Index(fields=['next_follow_up_date']),
        ]

    def get_status_display_color(self):
        """Return Bootstrap color class for status"""
        colors = {
            'found': 'secondary',
            'applied': 'primary',
            'responded': 'success',
            'interview': 'warning',
            'offer': 'info',
            'hired': 'success',
            'rejected': 'danger',
            'withdrawn': 'dark'
        }
        return colors.get(self.application_status, 'secondary')

    def get_urgency_color(self):
        """Return Bootstrap color class for urgency"""
        colors = {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger',
            'urgent': 'danger'
        }
        return colors.get(self.urgency_level, 'warning')

    @property
    def days_since_application(self):
        """Calculate days since application was found/applied"""
        if self.applied_date:
            from django.utils import timezone
            return (timezone.now().date() - self.applied_date.date()).days
        elif self.created_at:
            from django.utils import timezone
            return (timezone.now().date() - self.created_at.date()).days
        return 0

    @property
    def is_follow_up_due(self):
        """Check if follow-up is due"""
        if self.next_follow_up_date:
            from django.utils import timezone
            return timezone.now().date() >= self.next_follow_up_date
        return False

# from django.db import models
#
# # Create your models here.
# from django.db import models
# from django.contrib.auth.models import User
# from accounts.models import UserProfile
#
#
# class JobSearchConfig(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     config_name = models.CharField(max_length=255)
#     job_categories = models.JSONField(default=list)
#     target_locations = models.JSONField(default=list)
#     remote_preference = models.CharField(max_length=50, default='remote')
#     salary_min = models.IntegerField(null=True, blank=True)
#     salary_max = models.IntegerField(null=True, blank=True)
#     company_size_preference = models.JSONField(default=list)
#     auto_follow_up_enabled = models.BooleanField(default=False)
#     is_active = models.BooleanField(default=True)
#     last_search_date = models.DateTimeField(null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     def __str__(self):
#         return f"{self.user.username} - {self.config_name}"
#
#     class Meta:
#         unique_together = ['user', 'config_name']
#
#
# class JobApplication(models.Model):
#     STATUS_CHOICES = [
#         ('found', 'Found'),
#         ('applied', 'Applied'),
#         ('responded', 'Responded'),
#         ('interview', 'Interview Scheduled'),
#         ('offer', 'Offer Received'),
#         ('hired', 'Hired'),
#         ('rejected', 'Rejected'),
#         ('withdrawn', 'Withdrawn'),
#     ]
#
#     URGENCY_CHOICES = [
#         ('low', 'Low'),
#         ('medium', 'Medium'),
#         ('high', 'High'),
#         ('urgent', 'Urgent'),
#     ]
#
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     search_config = models.ForeignKey(JobSearchConfig, on_delete=models.SET_NULL, null=True)
#
#     # Job Details
#     job_title = models.CharField(max_length=255)
#     company_name = models.CharField(max_length=255)
#     job_url = models.URLField(max_length=2000, blank=True)
#     job_description = models.TextField(blank=True)
#     salary_range = models.CharField(max_length=100, blank=True)
#     location = models.CharField(max_length=255, blank=True)
#     remote_option = models.CharField(max_length=50, blank=True)
#
#     # Application Status
#     application_status = models.CharField(
#         max_length=50,
#         choices=STATUS_CHOICES,
#         default='found'
#     )
#     applied_date = models.DateTimeField(null=True, blank=True)
#
#     # Follow-up Management
#     last_follow_up_date = models.DateTimeField(null=True, blank=True)
#     follow_up_count = models.IntegerField(default=0)
#     next_follow_up_date = models.DateField(null=True, blank=True)
#     follow_up_sequence_active = models.BooleanField(default=False)
#
#     # Interview & Offer
#     interview_scheduled_date = models.DateTimeField(null=True, blank=True)
#     offer_received = models.BooleanField(default=False)
#     offer_amount = models.IntegerField(null=True, blank=True)
#     rejection_received = models.BooleanField(default=False)
#     rejection_reason = models.CharField(max_length=255, blank=True)
#
#     # Additional Info
#     notes = models.TextField(blank=True)
#     urgency_level = models.CharField(
#         max_length=20,
#         choices=URGENCY_CHOICES,
#         default='medium'
#     )
#     company_rating = models.DecimalField(
#         max_digits=3, decimal_places=1, null=True, blank=True
#     )
#     glassdoor_rating = models.DecimalField(
#         max_digits=3, decimal_places=1, null=True, blank=True
#     )
#
#     # Document Generation
#     documents_generated = models.BooleanField(default=False)
#     documents_folder_path = models.CharField(max_length=500, blank=True)
#
#     # AI Analysis
#     match_percentage = models.IntegerField(null=True, blank=True)
#     skills_match_analysis = models.TextField(blank=True)
#
#     # Timestamps
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     def __str__(self):
#         return f"{self.job_title} at {self.company_name}"
#
#     class Meta:
#         ordering = ['-created_at']