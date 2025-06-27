from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from jobs.models import JobApplication


class FollowUpTemplate(models.Model):
    TEMPLATE_TYPES = [
        ('initial', 'Initial Follow-up'),
        ('1_week', '1 Week Follow-up'),
        ('2_week', '2 Week Follow-up'),
        ('1_month', '1 Month Follow-up'),
        ('thank_you', 'Thank You After Interview'),
        ('negotiation', 'Negotiation Follow-up'),
        ('custom', 'Custom Template'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    template_name = models.CharField(max_length=255)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    subject_template = models.TextField()
    body_template = models.TextField()
    days_after_application = models.IntegerField(default=7)
    is_default = models.BooleanField(default=False)

    # Analytics
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    times_used = models.IntegerField(default=0)
    responses_received = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.template_name} ({self.template_type})"

    def calculate_success_rate(self):
        if self.times_used > 0:
            self.success_rate = (self.responses_received / self.times_used) * 100
            self.save(update_fields=['success_rate'])
        return self.success_rate


class FollowUpHistory(models.Model):
    RESPONSE_TYPES = [
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
        ('interview_invite', 'Interview Invitation'),
        ('rejection', 'Rejection'),
        ('no_response', 'No Response'),
    ]

    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE)
    template = models.ForeignKey(FollowUpTemplate, on_delete=models.SET_NULL, null=True)
    sent_date = models.DateTimeField(auto_now_add=True)
    subject = models.CharField(max_length=500)
    body = models.TextField()

    # Response tracking
    response_received = models.BooleanField(default=False)
    response_date = models.DateTimeField(null=True, blank=True)
    response_type = models.CharField(
        max_length=50,
        choices=RESPONSE_TYPES,
        default='no_response'
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Follow-up for {self.application.job_title} at {self.application.company_name}"

    class Meta:
        ordering = ['-sent_date']
        verbose_name_plural = "Follow-up histories"