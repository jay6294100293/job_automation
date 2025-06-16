from django.db import models

# Create your models here.
# documents/models.py
from django.db import models
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

    def __str__(self):
        return f"Doc generation for {self.application.job_title} - {self.status}"