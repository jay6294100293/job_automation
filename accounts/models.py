
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


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

    email_processing_enabled = models.BooleanField(default=False)
    forwarding_email = models.CharField(max_length=255, blank=True)
    dedicated_email_enabled = models.BooleanField(default=False)
    interview_detection_enabled = models.BooleanField(default=True)
    email_consent_date = models.DateTimeField(null=True, blank=True)

    # Email processing statistics
    total_emails_processed = models.IntegerField(default=0)
    jobs_found_via_email = models.IntegerField(default=0)
    interviews_detected = models.IntegerField(default=0)
    last_email_processed = models.DateTimeField(null=True, blank=True)

    # Email preferences
    email_job_alerts = models.BooleanField(default=True)
    email_interview_reminders = models.BooleanField(default=True)
    email_weekly_summary = models.BooleanField(default=True)

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # ... all your existing fields ...

    # ADD THESE EXTENSION-SPECIFIC FIELDS:

    # Extension Settings
    extension_notifications = models.BooleanField(
        default=True,
        help_text="Enable notifications from browser extension"
    )
    extension_auto_save = models.BooleanField(
        default=False,
        help_text="Automatically save jobs when visiting job pages"
    )
    extension_extraction_level = models.CharField(
        max_length=20,
        choices=[
            ('fast', 'Fast (Basic info)'),
            ('standard', 'Standard (Recommended)'),
            ('comprehensive', 'Comprehensive (All details)')
        ],
        default='standard',
        help_text="Job extraction detail level"
    )
    extension_theme = models.CharField(
        max_length=20,
        choices=[
            ('light', 'Light'),
            ('dark', 'Dark'),
            ('auto', 'Auto (System)')
        ],
        default='auto',
        help_text="Extension theme preference"
    )

    # Extension Usage Tracking
    extension_first_used = models.DateTimeField(
        null=True, blank=True,
        help_text="When user first used the extension"
    )
    extension_last_used = models.DateTimeField(
        null=True, blank=True,
        help_text="When user last used the extension"
    )
    extension_jobs_saved = models.IntegerField(
        default=0,
        help_text="Total jobs saved through extension"
    )
    extension_version = models.CharField(
        max_length=20,
        blank=True,
        help_text="Last known extension version"
    )

    def update_extension_usage(self):
        """Update extension usage tracking"""
        now = timezone.now()

        if not self.extension_first_used:
            self.extension_first_used = now

        self.extension_last_used = now
        self.save()

    def increment_extension_jobs(self):
        """Increment the count of jobs saved through extension"""
        self.extension_jobs_saved += 1
        self.update_extension_usage()

    @property
    def extension_active(self):
        """Check if user has used extension recently"""
        if not self.extension_last_used:
            return False

        # Consider active if used within last 30 days
        return (timezone.now() - self.extension_last_used).days <= 30

    @property
    def extension_statistics(self):
        """Get extension usage statistics"""
        total_jobs = self.user.jobapplication_set.count()
        extension_jobs = self.user.jobapplication_set.filter(
            source_platform='extension'
        ).count()

        return {
            'total_jobs_saved': self.extension_jobs_saved,
            'extension_jobs_count': extension_jobs,
            'total_jobs_count': total_jobs,
            'extension_percentage': (extension_jobs / total_jobs * 100) if total_jobs > 0 else 0,
            'first_used': self.extension_first_used,
            'last_used': self.extension_last_used,
            'is_active': self.extension_active
        }

    def generate_unique_forwarding_email(self):
        """Generate unique forwarding email address"""
        return f"jobs-{self.user.username}-{self.id}@jobautomation.me"

    def update_email_stats(self, jobs_found=0, interviews_detected=0):
        """Update email processing statistics"""
        self.total_emails_processed += 1
        self.jobs_found_via_email += jobs_found
        self.interviews_detected += interviews_detected
        self.last_email_processed = timezone.now()
        self.save()

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


class ExtensionActivity(models.Model):
    """Track extension usage and activities"""

    ACTIVITY_TYPES = [
        ('login', 'Login'),
        ('job_save', 'Job Saved'),
        ('job_extract', 'Job Extracted'),
        ('settings_update', 'Settings Updated'),
        ('error', 'Error Occurred'),
        ('page_visit', 'Page Visit'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Activity details
    page_url = models.URLField(blank=True, help_text="URL where activity occurred")
    job_title = models.CharField(max_length=200, blank=True)
    company_name = models.CharField(max_length=100, blank=True)
    site_detected = models.CharField(max_length=50, blank=True)
    extraction_confidence = models.FloatField(null=True, blank=True)

    # Technical details
    extension_version = models.CharField(max_length=20, blank=True)
    user_agent = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'activity_type']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} at {self.timestamp}"

    @classmethod
    def log_activity(cls, user, activity_type, **kwargs):
        """Helper method to log extension activity"""
        return cls.objects.create(
            user=user,
            activity_type=activity_type,
            **kwargs
        )


# ADD THIS MODEL for extension error tracking
class ExtensionError(models.Model):
    """Track extension errors for debugging"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Error details
    error_type = models.CharField(max_length=100)
    error_message = models.TextField()
    stack_trace = models.TextField(blank=True)

    # Context
    page_url = models.URLField(blank=True)
    site_detected = models.CharField(max_length=50, blank=True)
    extension_version = models.CharField(max_length=20, blank=True)
    browser_info = models.TextField(blank=True)

    # Status
    resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Extension Error: {self.error_type} at {self.timestamp}"
