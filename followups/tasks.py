# followups/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import date, timedelta
import logging

from .models import FollowUpTemplate, FollowUpHistory
from jobs.models import JobApplication
from accounts.models import UserProfile

logger = logging.getLogger(__name__)


@shared_task
def send_followup_email(application_id, template_id, custom_message=None):
    """Send individual follow-up email"""
    try:
        application = JobApplication.objects.get(id=application_id)
        template = FollowUpTemplate.objects.get(id=template_id)
        user_profile = UserProfile.objects.get(user=application.user)

        # Generate personalized content
        subject = personalize_template(template.subject_template, application, user_profile)
        body = personalize_template(template.body_template, application, user_profile)

        if custom_message:
            body += f"\n\n{custom_message}"

        # Send email
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.user.email],  # In real implementation, this would be the company email
            fail_silently=False,
        )

        # Record in history
        FollowUpHistory.objects.create(
            application=application,
            template=template,
            subject=subject,
            body=body,
        )

        # Update application
        application.last_follow_up_date = timezone.now()
        application.follow_up_count += 1
        application.next_follow_up_date = date.today() + timedelta(days=14)
        application.save()

        # Update template stats
        template.times_used += 1
        template.save()

        logger.info(f"Follow-up sent for {application.job_title} at {application.company_name}")
        return True

    except Exception as e:
        logger.error(f"Error sending follow-up email: {str(e)}")
        return False


@shared_task
def send_bulk_followup_emails(application_ids, template_id):
    """Send bulk follow-up emails"""
    try:
        template = FollowUpTemplate.objects.get(id=template_id)
        sent_count = 0

        for app_id in application_ids:
            success = send_followup_email.delay(app_id, template_id).get()
            if success:
                sent_count += 1

            # Add delay between emails to avoid spam detection
            import time
            time.sleep(2)

        logger.info(f"Bulk follow-up completed: {sent_count}/{len(application_ids)} emails sent")
        return sent_count

    except Exception as e:
        logger.error(f"Error sending bulk follow-up emails: {str(e)}")
        return 0


@shared_task
def process_scheduled_followups():
    """Daily task to process scheduled follow-ups"""
    try:
        # Get applications with due follow-ups
        due_applications = JobApplication.objects.filter(
            next_follow_up_date__lte=date.today(),
            follow_up_sequence_active=True,
            application_status__in=['applied', 'responded']
        )

        sent_count = 0
        for application in due_applications:
            # Get default template for user
            template = FollowUpTemplate.objects.filter(
                user=application.user,
                is_default=True,
                is_active=True
            ).first()

            if template:
                success = send_followup_email.delay(application.id, template.id).get()
                if success:
                    sent_count += 1

        logger.info(f"Scheduled follow-ups processed: {sent_count} emails sent")
        return sent_count

    except Exception as e:
        logger.error(f"Error processing scheduled follow-ups: {str(e)}")
        return 0


def personalize_template(template_text, application, user_profile):
    """Replace template variables with actual values"""
    replacements = {
        '{{user_name}}': user_profile.user.get_full_name(),
        '{{first_name}}': user_profile.user.first_name,
        '{{company_name}}': application.company_name,
        '{{job_title}}': application.job_title,
        '{{hiring_manager}}': 'Hiring Manager',  # Could be enhanced with actual names
        '{{days_since_application}}': str(
            (timezone.now().date() - application.applied_date.date()).days) if application.applied_date else '0',
        '{{current_title}}': user_profile.current_job_title or 'Professional',
        '{{years_experience}}': str(user_profile.years_experience) if user_profile.years_experience else 'several',
    }

    personalized = template_text
    for placeholder, value in replacements.items():
        personalized = personalized.replace(placeholder, value)

    return personalized