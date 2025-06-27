# documents/models.py - COMPLETE FILE REPLACEMENT
from django.db import models
from django.contrib.auth.models import User
from jobs.models import JobApplication


class GeneratedDocument(models.Model):
    DOCUMENT_TYPES = [
        ('resume', 'Resume'),
        ('cover_letter', 'Cover Letter'),
        ('email_templates', 'Email Templates'),
        ('linkedin_messages', 'LinkedIn Messages'),
        ('video_script', 'Video Pitch Script'),
        ('company_research', 'Company Research'),
        ('followup_schedule', 'Follow-up Schedule'),
        ('skills_analysis', 'Skills Analysis'),
    ]

    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    file_path = models.CharField(max_length=500)
    content = models.TextField(blank=True)  # Store content for preview
    generated_at = models.DateTimeField(auto_now_add=True)
    file_size = models.IntegerField(default=0)  # in bytes

    # New fields for AI tracking
    ai_provider = models.CharField(max_length=20, default='groq')  # groq, openrouter
    tokens_used = models.IntegerField(default=0)
    generation_time = models.FloatField(default=0.0)  # seconds
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)

    def __str__(self):
        return f"{self.document_type} for {self.application.job_title}"

    class Meta:
        unique_together = ['application', 'document_type']


class DocumentGenerationJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # New fields for tracking
    ai_provider_used = models.CharField(max_length=20, default='groq')
    total_tokens = models.IntegerField(default=0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)
    documents_generated = models.IntegerField(default=0)

    def __str__(self):
        return f"Doc generation for {self.application.job_title} - {self.status}"


class AIUsageLog(models.Model):
    """Track AI API usage for cost monitoring"""
    PROVIDER_CHOICES = [
        ('groq', 'Groq'),
        ('openrouter', 'OpenRouter'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    model_used = models.CharField(max_length=100)
    tokens_used = models.IntegerField()
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6)
    request_type = models.CharField(max_length=50)  # document_generation, research, etc.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['provider', 'created_at']),
        ]


class AIProviderStatus(models.Model):
    """Track AI provider status and performance"""
    provider = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    last_success = models.DateTimeField(null=True, blank=True)
    last_failure = models.DateTimeField(null=True, blank=True)
    failure_count = models.IntegerField(default=0)
    average_response_time = models.FloatField(default=0.0)
    total_requests = models.IntegerField(default=0)
    successful_requests = models.IntegerField(default=0)

    # Monthly usage tracking
    monthly_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    monthly_requests = models.IntegerField(default=0)
    last_reset = models.DateTimeField(auto_now_add=True)

    def success_rate(self):
        if self.total_requests == 0:
            return 0
        return (self.successful_requests / self.total_requests) * 100

    def __str__(self):
        return f"{self.provider} - Active: {self.is_active}"


class CompanyResearch(models.Model):
    """Store company research data"""
    application = models.OneToOneField(JobApplication, on_delete=models.CASCADE)
    company_overview = models.TextField(blank=True)
    recent_news = models.TextField(blank=True)
    interview_talking_points = models.TextField(blank=True)
    questions_to_ask = models.TextField(blank=True)
    industry_context = models.TextField(blank=True)
    research_date = models.DateTimeField(auto_now_add=True)
    research_source = models.CharField(max_length=20, default='serper')  # serper, manual

    def __str__(self):
        return f"Research for {self.application.company_name}"


# from django.db import models
#
# # Create your models here.
# # documents/models.py
# from django.db import models
# from jobs.models import JobApplication
#
#
# class GeneratedDocument(models.Model):
#     DOCUMENT_TYPES = [
#         ('resume', 'Resume'),
#         ('cover_letter', 'Cover Letter'),
#         ('email_templates', 'Email Templates'),
#         ('linkedin_messages', 'LinkedIn Messages'),
#         ('video_script', 'Video Pitch Script'),
#         ('company_research', 'Company Research'),
#         ('followup_schedule', 'Follow-up Schedule'),
#         ('skills_analysis', 'Skills Analysis'),
#     ]
#
#     application = models.ForeignKey(JobApplication, on_delete=models.CASCADE)
#     document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
#     file_path = models.CharField(max_length=500)
#     content = models.TextField(blank=True)  # Store content for preview
#     generated_at = models.DateTimeField(auto_now_add=True)
#     file_size = models.IntegerField(default=0)  # in bytes
#
#     def __str__(self):
#         return f"{self.document_type} for {self.application.job_title}"
#
#     class Meta:
#         unique_together = ['application', 'document_type']
#
#
# class DocumentGenerationJob(models.Model):
#     STATUS_CHOICES = [
#         ('pending', 'Pending'),
#         ('processing', 'Processing'),
#         ('completed', 'Completed'),
#         ('failed', 'Failed'),
#     ]
#
#     application = models.ForeignKey(JobApplication, on_delete=models.CASCADE)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
#     started_at = models.DateTimeField(auto_now_add=True)
#     completed_at = models.DateTimeField(null=True, blank=True)
#     error_message = models.TextField(blank=True)
#
#     def __str__(self):
#         return f"Doc generation for {self.application.job_title} - {self.status}"