from django.db.models.signals import post_save
from django.dispatch import receiver

from jobs.models import EmailProcessingLog, EmailSettings


@receiver(post_save, sender=EmailSettings)
def create_default_keywords(sender, instance, created, **kwargs):
    """Set default keywords when EmailSettings is created"""
    if created:
        # Set default required keywords for job emails
        instance.required_keywords = [
            'job', 'position', 'opportunity', 'career', 'hiring', 'vacancy', 'role'
        ]

        # Set default filter keywords to exclude spam
        instance.keyword_filters = [
            'unsubscribe', 'spam', 'promotion', 'sale', 'discount', 'free', 'click here'
        ]

        instance.save()


@receiver(post_save, sender=EmailProcessingLog)
def update_user_email_stats(sender, instance, created, **kwargs):
    """Update user email processing statistics"""
    if created and instance.processing_result == 'success':
        user_profile = instance.user.userprofile

        if instance.email_type == 'job_alert':
            user_profile.jobs_found_via_email += 1
        elif instance.email_type == 'interview_invite':
            user_profile.interviews_detected += 1

        user_profile.total_emails_processed += 1
        user_profile.last_email_processed = timezone.now()
        user_profile.save()