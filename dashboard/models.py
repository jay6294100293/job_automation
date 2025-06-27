# dashboard/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class DashboardWidget(models.Model):
    """User customizable dashboard widgets"""

    WIDGET_TYPES = [
        ('stats_card', 'Statistics Card'),
        ('pipeline', 'Application Pipeline'),
        ('recent_activity', 'Recent Activity'),
        ('follow_ups', 'Due Follow-ups'),
        ('job_search', 'Job Search Status'),
        ('profile_completion', 'Profile Completion'),
        ('analytics_chart', 'Analytics Chart'),
        ('quick_actions', 'Quick Actions'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    widget_type = models.CharField(max_length=50, choices=WIDGET_TYPES)
    title = models.CharField(max_length=255)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=1)  # Grid units
    height = models.IntegerField(default=1)  # Grid units
    is_visible = models.BooleanField(default=True)
    settings = models.JSONField(default=dict)  # Widget-specific settings
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position_y', 'position_x']
        unique_together = ['user', 'widget_type']

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class UserNotification(models.Model):
    """Dashboard notifications and alerts"""

    NOTIFICATION_TYPES = [
        ('success', 'Success'),
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('follow_up', 'Follow-up Due'),
        ('job_found', 'New Jobs Found'),
        ('response_received', 'Response Received'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('document_ready', 'Documents Ready'),
    ]

    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS, default='normal')

    # Optional references
    related_application = models.ForeignKey(
        'jobs.JobApplication',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    related_search_config = models.ForeignKey(
        'jobs.JobSearchConfig',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    # Status tracking
    is_read = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    # Action data
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def is_expired(self):
        """Check if notification has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class DashboardSettings(models.Model):
    """User dashboard preferences and settings"""

    THEME_CHOICES = [
        ('light', 'Light Theme'),
        ('dark', 'Dark Theme'),
        ('auto', 'Auto (System)'),
    ]

    LAYOUT_CHOICES = [
        ('compact', 'Compact'),
        ('comfortable', 'Comfortable'),
        ('spacious', 'Spacious'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Appearance settings
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='light')
    layout_density = models.CharField(max_length=20, choices=LAYOUT_CHOICES, default='comfortable')

    # Dashboard behavior
    auto_refresh_enabled = models.BooleanField(default=True)
    auto_refresh_interval = models.IntegerField(default=30)  # seconds
    show_welcome_message = models.BooleanField(default=True)

    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    browser_notifications = models.BooleanField(default=True)
    follow_up_reminders = models.BooleanField(default=True)
    job_alert_notifications = models.BooleanField(default=True)

    # Widget preferences
    default_widget_layout = models.JSONField(default=dict)
    hidden_widgets = models.JSONField(default=list)  # List of widget types to hide

    # Quick actions customization
    favorite_actions = models.JSONField(default=list)  # List of favorite quick actions

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Dashboard Settings"

    @classmethod
    def get_for_user(cls, user):
        """Get or create dashboard settings for user"""
        settings, created = cls.objects.get_or_create(user=user)
        return settings


class DashboardActivity(models.Model):
    """Track user activity on dashboard for analytics"""

    ACTIVITY_TYPES = [
        ('login', 'User Login'),
        ('search_created', 'Search Configuration Created'),
        ('search_executed', 'Job Search Executed'),
        ('application_status_changed', 'Application Status Changed'),
        ('follow_up_sent', 'Follow-up Sent'),
        ('document_generated', 'Document Generated'),
        ('document_downloaded', 'Document Downloaded'),
        ('profile_updated', 'Profile Updated'),
        ('dashboard_viewed', 'Dashboard Viewed'),
        ('widget_customized', 'Widget Customized'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    description = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict)  # Additional activity data

    # Session tracking
    session_id = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'activity_type', 'created_at']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()}"

    @classmethod
    def log_activity(cls, user, activity_type, description, metadata=None, request=None):
        """Convenience method to log user activity"""
        activity_data = {
            'user': user,
            'activity_type': activity_type,
            'description': description,
            'metadata': metadata or {}
        }

        if request:
            activity_data.update({
                'session_id': request.session.session_key,
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')
            })

        return cls.objects.create(**activity_data)