# jobs/models.py - Enhanced Universal Version
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class JobSearchConfig(models.Model):
    """Universal job search configuration that works for any industry"""

    REMOTE_PREFERENCES = [
        ('remote_only', 'Remote Only'),
        ('remote_preferred', 'Remote Preferred'),
        ('hybrid', 'Hybrid (Remote + Office)'),
        ('office_preferred', 'Office Preferred'),
        ('office_only', 'Office Only'),
        ('no_preference', 'No Preference'),
    ]

    # Basic Configuration
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    config_name = models.CharField(
        max_length=255,
        help_text="Descriptive name for this search configuration"
    )

    # Universal Job Categories (stored as JSON list)
    job_categories = models.JSONField(
        default=list,
        help_text="Job titles/roles as a list of strings"
    )

    # Universal Locations (stored as JSON list)
    target_locations = models.JSONField(
        default=list,
        help_text="Target locations as a list of strings"
    )

    # Work Preferences
    remote_preference = models.CharField(
        max_length=50,
        choices=REMOTE_PREFERENCES,
        default='no_preference'
    )

    # Universal Salary Configuration
    salary_min = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Minimum salary expectation"
    )
    salary_max = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Maximum salary expectation"
    )
    salary_currency = models.CharField(
        max_length=10,
        default='CAD',
        help_text="Currency for salary range"
    )

    # Enhanced Filtering Options
    required_keywords = models.JSONField(
        default=list,
        blank=True,
        help_text="Keywords that must be present in job postings"
    )
    excluded_keywords = models.JSONField(
        default=list,
        blank=True,
        help_text="Keywords that disqualify job postings"
    )
    excluded_companies = models.JSONField(
        default=list,
        blank=True,
        help_text="Companies to exclude from search"
    )

    # Company Preferences
    company_size_preference = models.JSONField(
        default=list,
        blank=True,
        help_text="Preferred company sizes"
    )

    # Automation Settings
    auto_follow_up_enabled = models.BooleanField(
        default=False,
        help_text="Enable automatic follow-up emails"
    )
    auto_apply_enabled = models.BooleanField(
        default=False,
        help_text="Enable automatic job applications (where possible)"
    )

    # Search Frequency
    search_frequency = models.CharField(
        max_length=20,
        choices=[
            ('manual', 'Manual Only'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ],
        default='manual'
    )

    # Status and Tracking
    is_active = models.BooleanField(default=True)
    last_search_date = models.DateTimeField(null=True, blank=True)
    total_jobs_found = models.IntegerField(default=0)
    total_applications_sent = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.config_name}"

    class Meta:
        unique_together = ['user', 'config_name']
        ordering = ['-updated_at']

    @property
    def job_categories_display(self):
        """Return job categories as a formatted string"""
        if self.job_categories:
            return ', '.join(self.job_categories[:3]) + (
                f' +{len(self.job_categories) - 3} more' if len(self.job_categories) > 3 else ''
            )
        return 'No categories set'

    @property
    def locations_display(self):
        """Return locations as a formatted string"""
        if self.target_locations:
            return ', '.join(self.target_locations[:3]) + (
                f' +{len(self.target_locations) - 3} more' if len(self.target_locations) > 3 else ''
            )
        return 'No locations set'

    @property
    def salary_display(self):
        """Return formatted salary range"""
        if self.salary_min or self.salary_max:
            min_sal = f"{self.salary_currency} {self.salary_min:,}" if self.salary_min else "No min"
            max_sal = f"{self.salary_currency} {self.salary_max:,}" if self.salary_max else "No max"
            return f"{min_sal} - {max_sal}"
        return "No salary range set"


class JobApplication(models.Model):
    """Enhanced universal job application tracking"""

    STATUS_CHOICES = [
        ('discovered', 'Discovered'),
        ('saved', 'Saved for Later'),
        ('applied', 'Applied'),
        ('application_viewed', 'Application Viewed'),
        ('phone_screening', 'Phone Screening'),
        ('technical_assessment', 'Technical Assessment'),
        ('first_interview', 'First Interview'),
        ('second_interview', 'Second Interview'),
        ('final_interview', 'Final Interview'),
        ('reference_check', 'Reference Check'),
        ('offer_pending', 'Offer Pending'),
        ('offer_received', 'Offer Received'),
        ('offer_accepted', 'Offer Accepted'),
        ('offer_declined', 'Offer Declined'),
        ('hired', 'Hired'),
        ('rejected_automated', 'Rejected (Automated)'),
        ('rejected_screening', 'Rejected (Screening)'),
        ('rejected_interview', 'Rejected (Interview)'),
        ('rejected_offer', 'Rejected (Offer Stage)'),
        ('withdrawn', 'Withdrawn'),
        ('ghosted', 'Ghosted'),
    ]

    URGENCY_LEVELS = [
        ('low', 'Low Priority'),
        ('medium', 'Medium Priority'),
        ('high', 'High Priority'),
        ('urgent', 'Urgent'),
        ('dream_job', 'Dream Job'),
    ]

    APPLICATION_SOURCES = [
        ('company_website', 'Company Website'),
        ('linkedin', 'LinkedIn'),
        ('indeed', 'Indeed'),
        ('glassdoor', 'Glassdoor'),
        ('monster', 'Monster'),
        ('ziprecruiter', 'ZipRecruiter'),
        ('stackoverflow', 'Stack Overflow Jobs'),
        ('angellist', 'AngelList'),
        ('remote_co', 'Remote.co'),
        ('we_work_remotely', 'We Work Remotely'),
        ('flexjobs', 'FlexJobs'),
        ('referral', 'Referral'),
        ('recruiter', 'Recruiter Contact'),
        ('job_fair', 'Job Fair'),
        ('cold_outreach', 'Cold Outreach'),
        ('other', 'Other'),
    ]

    # Basic Information
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    search_config = models.ForeignKey(
        JobSearchConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Job Details
    job_title = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    job_url = models.URLField(max_length=2000, blank=True)
    job_description = models.TextField(blank=True)

    # Location and Remote Options
    location = models.CharField(max_length=255, blank=True)
    remote_option = models.CharField(max_length=50, blank=True)
    work_schedule = models.CharField(max_length=100, blank=True)  # Full-time, Part-time, Contract, etc.

    # Salary Information
    salary_range = models.CharField(max_length=100, blank=True)
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)
    salary_currency = models.CharField(max_length=10, default='CAD')

    # Application Tracking
    application_status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='discovered'
    )
    application_source = models.CharField(
        max_length=50,
        choices=APPLICATION_SOURCES,
        default='company_website'
    )
    applied_date = models.DateTimeField(null=True, blank=True)
    application_deadline = models.DateField(null=True, blank=True)

    # Priority and Organization
    urgency_level = models.CharField(
        max_length=20,
        choices=URGENCY_LEVELS,
        default='medium'
    )
    notes = models.TextField(blank=True)
    personal_rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Personal rating 1-10"
    )

    # Follow-up Management
    last_follow_up_date = models.DateTimeField(null=True, blank=True)
    follow_up_count = models.IntegerField(default=0)
    next_follow_up_date = models.DateField(null=True, blank=True)
    follow_up_sequence_active = models.BooleanField(default=False)
    custom_follow_up_notes = models.TextField(blank=True)

    # Interview Process
    interview_scheduled_date = models.DateTimeField(null=True, blank=True)
    interview_type = models.CharField(
        max_length=50,
        choices=[
            ('phone', 'Phone Interview'),
            ('video', 'Video Interview'),
            ('in_person', 'In-Person Interview'),
            ('technical', 'Technical Interview'),
            ('panel', 'Panel Interview'),
            ('group', 'Group Interview'),
        ],
        blank=True
    )
    interview_notes = models.TextField(blank=True)

    # Offer Management
    offer_received = models.BooleanField(default=False)
    offer_amount = models.IntegerField(null=True, blank=True)
    offer_currency = models.CharField(max_length=10, default='CAD')
    offer_benefits = models.TextField(blank=True)
    offer_deadline = models.DateField(null=True, blank=True)

    # Rejection Tracking
    rejection_received = models.BooleanField(default=False)
    rejection_reason = models.CharField(max_length=255, blank=True)
    rejection_feedback = models.TextField(blank=True)

    # Company Analysis
    company_size = models.CharField(max_length=50, blank=True)
    company_industry = models.CharField(max_length=100, blank=True)
    company_rating = models.FloatField(null=True, blank=True)
    glassdoor_rating = models.FloatField(null=True, blank=True)
    company_culture_notes = models.TextField(blank=True)

    # Document Management
    documents_generated = models.BooleanField(default=False)
    documents_folder_path = models.CharField(max_length=500, blank=True)
    custom_resume_used = models.BooleanField(default=False)
    cover_letter_sent = models.BooleanField(default=False)

    # AI Analysis and Matching
    match_percentage = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    skills_match_analysis = models.TextField(blank=True)
    ai_recommendation_score = models.FloatField(null=True, blank=True)
    automated_application = models.BooleanField(default=False)

    # Contact Information
    hiring_manager_name = models.CharField(max_length=255, blank=True)
    hiring_manager_email = models.EmailField(blank=True)
    recruiter_name = models.CharField(max_length=255, blank=True)
    recruiter_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)

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
            models.Index(fields=['application_deadline']),
            models.Index(fields=['company_name']),
            models.Index(fields=['match_percentage']),
        ]

    def get_status_display_color(self):
        """Return Bootstrap color class for status"""
        status_colors = {
            'discovered': 'info',
            'saved': 'secondary',
            'applied': 'primary',
            'application_viewed': 'info',
            'phone_screening': 'warning',
            'technical_assessment': 'warning',
            'first_interview': 'warning',
            'second_interview': 'warning',
            'final_interview': 'warning',
            'reference_check': 'info',
            'offer_pending': 'success',
            'offer_received': 'success',
            'offer_accepted': 'success',
            'offer_declined': 'secondary',
            'hired': 'success',
            'rejected_automated': 'danger',
            'rejected_screening': 'danger',
            'rejected_interview': 'danger',
            'rejected_offer': 'danger',
            'withdrawn': 'dark',
            'ghosted': 'muted',
        }
        return status_colors.get(self.application_status, 'secondary')

    def get_urgency_color(self):
        """Return Bootstrap color class for urgency"""
        urgency_colors = {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger',
            'urgent': 'danger',
            'dream_job': 'info'
        }
        return urgency_colors.get(self.urgency_level, 'warning')

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

    @property
    def is_deadline_approaching(self):
        """Check if application deadline is approaching (within 3 days)"""
        if self.application_deadline:
            from django.utils import timezone
            days_until_deadline = (self.application_deadline - timezone.now().date()).days
            return days_until_deadline <= 3 and days_until_deadline >= 0
        return False

    @property
    def salary_display(self):
        """Return formatted salary information"""
        if self.salary_min or self.salary_max:
            min_sal = f"{self.salary_currency} {self.salary_min:,}" if self.salary_min else "No min"
            max_sal = f"{self.salary_currency} {self.salary_max:,}" if self.salary_max else "No max"
            return f"{min_sal} - {max_sal}"
        elif self.salary_range:
            return self.salary_range
        return "Salary not specified"

    @property
    def status_progress_percentage(self):
        """Calculate progress percentage based on status"""
        status_weights = {
            'discovered': 5,
            'saved': 10,
            'applied': 20,
            'application_viewed': 30,
            'phone_screening': 40,
            'technical_assessment': 50,
            'first_interview': 60,
            'second_interview': 70,
            'final_interview': 80,
            'reference_check': 85,
            'offer_pending': 90,
            'offer_received': 95,
            'offer_accepted': 100,
            'hired': 100,
            'rejected_automated': 0,
            'rejected_screening': 0,
            'rejected_interview': 0,
            'rejected_offer': 0,
            'withdrawn': 0,
            'ghosted': 0,
        }
        return status_weights.get(self.application_status, 0)