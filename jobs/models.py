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
    employment_type = models.CharField(
        max_length=50,
        choices=[
            ('full_time', 'Full-time'),
            ('part_time', 'Part-time'),
            ('contract', 'Contract'),
            ('temporary', 'Temporary'),
            ('internship', 'Internship'),
            ('volunteer', 'Volunteer'),
            ('freelance', 'Freelance'),
            ('seasonal', 'Seasonal'),
            ('apprenticeship', 'Apprenticeship'),
        ],
        blank=True,
        null=True,
        help_text="Type of employment (full-time, part-time, contract, etc.)"
    )

    experience_level = models.CharField(
        max_length=50,
        choices=[
            ('entry_level', 'Entry Level'),
            ('junior', 'Junior (1-2 years)'),
            ('mid_level', 'Mid Level (3-5 years)'),
            ('senior', 'Senior (5-8 years)'),
            ('lead', 'Lead (8-12 years)'),
            ('principal', 'Principal (12+ years)'),
            ('executive', 'Executive'),
            ('director', 'Director'),
            ('manager', 'Manager'),
            ('intern', 'Intern'),
            ('associate', 'Associate'),
        ],
        blank=True,
        null=True,
        help_text="Required experience level for the position"
    )

    remote_type = models.CharField(
        max_length=50,
        choices=[
            ('onsite', 'On-site'),
            ('remote', 'Remote'),
            ('hybrid', 'Hybrid'),
            ('flexible', 'Flexible'),
            ('travel_required', 'Travel Required'),
            ('relocate_required', 'Relocation Required'),
        ],
        blank=True,
        null=True,
        help_text="Work arrangement type (remote, hybrid, on-site, etc.)"
    )
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

    source_platform = models.CharField(max_length=50, default='manual')
    # Values: 'manual', 'extension', 'rss', 'email_forward', 'email_auto'


    match_score = models.FloatField(default=0.0,
                                    validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])

    # Email-specific fields
    email_thread_id = models.CharField(max_length=255, blank=True)
    original_email_subject = models.CharField(max_length=500, blank=True)
    original_email_sender = models.CharField(max_length=255, blank=True)

    # Interview detection fields
    interview_date = models.DateTimeField(null=True, blank=True)
    interviewer_name = models.CharField(max_length=255, blank=True)
    interviewer_email = models.CharField(max_length=255, blank=True)
    interview_location = models.TextField(blank=True)

    calendar_event_id = models.CharField(max_length=255, blank=True)

    # Company research fields (auto-populated)
    company_website = models.URLField(blank=True)
    company_size = models.CharField(max_length=50, blank=True)

    company_description = models.TextField(blank=True)

    # Processing metadata
    processing_confidence = models.FloatField(default=0.0)
    needs_manual_review = models.BooleanField(default=False)
    ai_extraction_notes = models.TextField(blank=True)

    # Chrome Extension Integration Fields (ADD THESE)
    saved_from_extension = models.BooleanField(default=False, help_text="Job saved via Chrome extension")
    extraction_confidence = models.FloatField(default=0.0, help_text="Confidence in data extraction (0-1)")
    extraction_method = models.CharField(max_length=100, blank=True, help_text="Method used to extract job data")

    # Additional Metadata for Extension
    page_title = models.CharField(max_length=500, blank=True, help_text="Original page title")
    user_agent = models.CharField(max_length=500, blank=True, help_text="Browser user agent")
    discovered_at = models.DateTimeField(auto_now_add=True, help_text="When job was first discovered")

    # Auto-discovery fields
    auto_discovered = models.BooleanField(default=False, help_text="Job auto-discovered by system")
    overall_match_score = models.FloatField(default=0.0, help_text="Overall match score (0-100)")
    skill_match_score = models.FloatField(default=0.0, help_text="Skill alignment score")
    experience_match_score = models.FloatField(default=0.0, help_text="Experience level match")
    location_match_score = models.FloatField(default=0.0, help_text="Location preference match")
    salary_match_score = models.FloatField(default=0.0, help_text="Salary expectation match")
    culture_match_score = models.FloatField(default=0.0, help_text="Company culture fit")
    growth_potential_score = models.FloatField(default=0.0, help_text="Career growth potential")
    risk_assessment_score = models.FloatField(default=0.0, help_text="Job security and stability")

    # Detailed Analysis Results
    matched_skills = models.JSONField(default=list, help_text="Skills that match user profile")
    missing_skills = models.JSONField(default=list, help_text="Required skills user lacks")
    red_flags = models.JSONField(default=list, help_text="Potential concerns or issues")
    green_flags = models.JSONField(default=list, help_text="Positive indicators")

    # AI Recommendation System
    recommendation_level = models.CharField(
        max_length=50,
        choices=[
            ('highly_recommended', 'Highly Recommended'),
            ('recommended', 'Recommended'),
            ('consider', 'Consider'),
            ('not_recommended', 'Not Recommended')
        ],
        default='consider'
    )
    ai_reasoning = models.TextField(blank=True, help_text="AI explanation for scoring")
    confidence_score = models.FloatField(default=0.0, help_text="AI confidence in analysis")

    # Job Approval System
    approval_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Review'),
            ('approved', 'Approved for Documents'),
            ('rejected', 'Rejected'),
            ('applied', 'Applied')
        ],
        default='pending'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # Add this method to your JobApplication model
    def calculate_ai_score(self):
        """Calculate overall score from individual dimension scores"""
        scores = [
            self.skill_match_score,
            self.experience_match_score,
            self.location_match_score,
            self.salary_match_score,
            self.culture_match_score,
            self.growth_potential_score,
            self.risk_assessment_score
        ]
        # Weighted average (skills and experience are more important)
        weights = [0.25, 0.20, 0.15, 0.15, 0.10, 0.10, 0.05]
        self.overall_match_score = sum(score * weight for score, weight in zip(scores, weights))

        # Set recommendation level based on score
        if self.overall_match_score >= 85:
            self.recommendation_level = 'highly_recommended'
        elif self.overall_match_score >= 70:
            self.recommendation_level = 'recommended'
        elif self.overall_match_score >= 50:
            self.recommendation_level = 'consider'
        else:
            self.recommendation_level = 'not_recommended'


    def __str__(self):
        parts = [f"{self.job_title} at {self.company_name}"]
        if self.employment_type:
            parts.append(f"({self.get_employment_type_display()})")
        if self.remote_type:
            parts.append(f"[{self.get_remote_type_display()}]")
        return " ".join(parts)

    def get_employment_type_display_with_icon(self):
        """Return employment type with icon"""
        icons = {
            'full_time': '💼',
            'part_time': '⏰',
            'contract': '📋',
            'temporary': '⚡',
            'internship': '🎓',
            'volunteer': '🤝',
            'freelance': '💻',
            'seasonal': '🌟',
            'apprenticeship': '🔧',
        }
        if self.employment_type:
            return f"{icons.get(self.employment_type, '💼')} {self.get_employment_type_display()}"
        return ''

    def get_experience_level_display_with_icon(self):
        """Return experience level with icon"""
        icons = {
            'entry_level': '🌱',
            'junior': '🔰',
            'mid_level': '⭐',
            'senior': '🏆',
            'lead': '👑',
            'principal': '💎',
            'executive': '🎯',
            'director': '🎪',
            'manager': '📊',
            'intern': '📚',
            'associate': '🔹',
        }
        if self.experience_level:
            return f"{icons.get(self.experience_level, '⭐')} {self.get_experience_level_display()}"
        return ''

    def get_remote_type_display_with_icon(self):
        """Return remote type with icon"""
        icons = {
            'onsite': '🏢',
            'remote': '🏠',
            'hybrid': '🔄',
            'flexible': '🌍',
            'travel_required': '✈️',
            'relocate_required': '📦',
        }
        if self.remote_type:
            return f"{icons.get(self.remote_type, '🏢')} {self.get_remote_type_display()}"
        return ''
    # Helper method for extension
    def to_extension_dict(self):
        """Convert to dictionary format for extension responses"""
        return {
            'id': self.id,
            'job_title': self.job_title,
            'company_name': self.company_name,
            'location': self.location,
            'job_url': self.job_url,
            'source_platform': self.source_platform,
            'application_status': self.application_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'saved_from_extension': self.saved_from_extension,
            'extraction_confidence': self.extraction_confidence,
        }

    def get_source_icon(self):
        """Return icon for job source"""
        icons = {
            'manual': '✋',
            'extension': '🔗',
            'email_forward': '📬',
            'email_auto': '📧',
            'rss': '📰'
        }
        return icons.get(self.source_platform, '❓')

    def get_source_badge_class(self):
        """Return CSS class for source badge"""
        classes = {
            'manual': 'bg-secondary',
            'extension': 'bg-primary',
            'email_forward': 'bg-info',
            'email_auto': 'bg-success',
            'rss': 'bg-warning'
        }
        return classes.get(self.source_platform, 'bg-light')

    def __str__(self):
        return f"{self.job_title} at {self.company_name} - {self.user.username}"

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'job_title', 'company_name']
        indexes = [
            models.Index(fields=['user', 'application_status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['urgency_level']),
            models.Index(fields=['next_follow_up_date']),
            models.Index(fields=['application_deadline']),
            models.Index(fields=['company_name']),
            models.Index(fields=['match_percentage']),
            models.Index(fields=['employment_type']),
            models.Index(fields=['experience_level']),
            models.Index(fields=['remote_type']),
            models.Index(fields=['employment_type', 'experience_level']),
            models.Index(fields=['remote_type', 'employment_type']),
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


from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class EmailProcessingLog(models.Model):
    """Track all email processing for debugging and analytics"""

    EMAIL_TYPES = [
        ('job_alert', 'Job Alert'),
        ('interview_invite', 'Interview Invitation'),
        ('application_response', 'Application Response'),
        ('rejection', 'Rejection'),
        ('follow_up', 'Follow-up'),
        ('other', 'Other')
    ]

    PROCESSING_RESULTS = [
        ('success', 'Successfully Processed'),
        ('failed', 'Processing Failed'),
        ('manual_review', 'Requires Manual Review'),
        ('ignored', 'Ignored/Filtered Out')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email_subject = models.CharField(max_length=500)
    email_sender = models.CharField(max_length=255)
    email_received_date = models.DateTimeField()
    email_body_preview = models.TextField(max_length=1000)

    # Processing details
    email_type = models.CharField(max_length=50, choices=EMAIL_TYPES)
    processing_result = models.CharField(max_length=50, choices=PROCESSING_RESULTS)
    confidence_score = models.FloatField(default=0.0,
                                         validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])

    # Extracted data
    extracted_data = models.JSONField(default=dict)
    ai_response = models.TextField(blank=True)

    # Linked records
    created_application = models.ForeignKey('JobApplication', null=True, blank=True,
                                            on_delete=models.SET_NULL)

    # Processing metadata
    processing_time = models.FloatField(default=0.0)  # seconds
    ai_tokens_used = models.IntegerField(default=0)
    ai_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)

    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'email_type', 'created_at']),
            models.Index(fields=['processing_result', 'created_at']),
            models.Index(fields=['user', 'processing_result']),
            models.Index(fields=['email_type', 'processing_result'])
        ]

    def __str__(self):
        return f"{self.email_subject[:50]}... - {self.get_processing_result_display()}"

    def get_confidence_color(self):
        """Return Bootstrap color class based on confidence score"""
        if self.confidence_score >= 80:
            return 'success'
        elif self.confidence_score >= 60:
            return 'warning'
        else:
            return 'danger'

    def get_processing_icon(self):
        """Return icon based on processing result"""
        icons = {
            'success': '✅',
            'failed': '❌',
            'manual_review': '⏳',
            'ignored': '🚫'
        }
        return icons.get(self.processing_result, '❓')

    def get_email_type_icon(self):
        """Return icon based on email type"""
        icons = {
            'job_alert': '💼',
            'interview_invite': '📅',
            'application_response': '📧',
            'rejection': '❌',
            'follow_up': '🔄',
            'other': '📨'
        }
        return icons.get(self.email_type, '📧')

    def mark_for_reprocessing(self):
        """Mark email for reprocessing"""
        self.processing_result = 'manual_review'
        self.retry_count += 1
        self.save()

    @property
    def processing_duration_ms(self):
        """Return processing time in milliseconds"""
        return round(self.processing_time * 1000, 2)

    @property
    def is_recent(self):
        """Check if email was processed in the last 24 hours"""
        return self.created_at >= timezone.now() - timezone.timedelta(hours=24)


class EmailSettings(models.Model):
    """User-specific email processing settings"""

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Processing preferences
    auto_process_job_alerts = models.BooleanField(default=True)
    auto_process_interviews = models.BooleanField(default=True)
    auto_create_calendar_events = models.BooleanField(default=True)
    auto_research_companies = models.BooleanField(default=True)

    # Filtering settings
    minimum_confidence_score = models.FloatField(default=70.0,
                                                 validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    blacklisted_senders = models.JSONField(default=list)
    keyword_filters = models.JSONField(default=list)
    required_keywords = models.JSONField(default=list)

    # Notification preferences
    notify_new_jobs = models.BooleanField(default=True)
    notify_interviews = models.BooleanField(default=True)
    notify_processing_errors = models.BooleanField(default=True)
    notify_low_confidence = models.BooleanField(default=True)

    # Data retention
    keep_email_logs_days = models.IntegerField(default=90)
    auto_delete_failed_processing = models.BooleanField(default=False)

    # Advanced settings
    max_emails_per_day = models.IntegerField(default=100)
    processing_delay_seconds = models.IntegerField(default=5)
    enable_duplicate_detection = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Email Settings'
        verbose_name_plural = 'Email Settings'

    def __str__(self):
        return f"Email Settings - {self.user.username}"

    def is_sender_blacklisted(self, sender_email):
        """Check if sender is blacklisted"""
        return sender_email.lower() in [s.lower() for s in self.blacklisted_senders]

    def should_process_email(self, email_data):
        """Determine if email should be processed based on settings"""
        # Check blacklist
        if self.is_sender_blacklisted(email_data.get('sender', '')):
            return False

        # Check required keywords
        if self.required_keywords:
            email_text = (email_data.get('subject', '') + ' ' + email_data.get('body', '')).lower()
            has_required_keyword = any(keyword.lower() in email_text for keyword in self.required_keywords)
            if not has_required_keyword:
                return False

        # Check filter keywords (exclusions)
        if self.keyword_filters:
            email_text = (email_data.get('subject', '') + ' ' + email_data.get('body', '')).lower()
            has_filter_keyword = any(keyword.lower() in email_text for keyword in self.keyword_filters)
            if has_filter_keyword:
                return False

        return True

    def get_processing_stats(self):
        """Get processing statistics for this user"""
        logs = EmailProcessingLog.objects.filter(user=self.user)

        return {
            'total_processed': logs.count(),
            'success_rate': self.calculate_success_rate(logs),
            'jobs_found': logs.filter(email_type='job_alert', processing_result='success').count(),
            'interviews_detected': logs.filter(email_type='interview_invite', processing_result='success').count(),
            'avg_confidence': logs.aggregate(avg_confidence=models.Avg('confidence_score'))['avg_confidence'] or 0,
            'recent_activity': logs.filter(created_at__gte=timezone.now() - timezone.timedelta(hours=24)).count()
        }

    def calculate_success_rate(self, logs):
        """Calculate success rate percentage"""
        total = logs.count()
        if total == 0:
            return 100.0
        successful = logs.filter(processing_result='success').count()
        return round((successful / total) * 100, 1)


class EmailQueue(models.Model):
    """Queue for processing emails asynchronously"""

    QUEUE_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('retry', 'Retry')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email_data = models.JSONField()  # Store raw email data

    # Queue management
    status = models.CharField(max_length=20, choices=QUEUE_STATUS, default='pending')
    priority = models.IntegerField(default=1)  # 1=high, 2=medium, 3=low

    # Processing tracking
    processing_attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    next_attempt_at = models.DateTimeField(null=True, blank=True)

    # Results
    processing_log = models.ForeignKey(EmailProcessingLog, null=True, blank=True,
                                       on_delete=models.SET_NULL)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', 'created_at']
        indexes = [
            models.Index(fields=['status', 'priority', 'created_at']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['next_attempt_at'])
        ]

    def __str__(self):
        return f"Email Queue - {self.user.username} - {self.status}"

    def can_retry(self):
        """Check if email can be retried"""
        return (self.processing_attempts < self.max_attempts and
                self.status in ['failed', 'retry'])

    def schedule_retry(self, delay_minutes=5):
        """Schedule email for retry"""
        if self.can_retry():
            self.status = 'retry'
            self.next_attempt_at = timezone.now() + timezone.timedelta(minutes=delay_minutes)
            self.save()

    def mark_processing(self):
        """Mark email as being processed"""
        self.status = 'processing'
        self.processing_attempts += 1
        self.save()

    def mark_completed(self, processing_log):
        """Mark email as completed"""
        self.status = 'completed'
        self.processing_log = processing_log
        self.save()

    def mark_failed(self, error_message):
        """Mark email as failed"""
        self.status = 'failed'
        self.error_message = error_message

        # Schedule retry if possible
        if self.can_retry():
            self.schedule_retry()

        self.save()

    @property
    def is_ready_for_processing(self):
        """Check if email is ready for processing"""
        if self.status == 'pending':
            return True
        if self.status == 'retry' and self.next_attempt_at:
            return timezone.now() >= self.next_attempt_at
        return False