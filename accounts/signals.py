# File: accounts/signals.py
# REPLACE the problematic signal with this safe version

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


@receiver(post_save, sender=User)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """
    Automatically create API token when a new user is created
    """
    if created:
        Token.objects.create(user=instance)


@receiver(post_save, sender=User)
def create_extension_activity_on_user_creation(sender, instance, created, **kwargs):
    """Create extension activity log when user is created - SAFE VERSION"""
    if created:
        try:
            # Check if table exists before trying to create record
            from django.db import connection
            from accounts.models import ExtensionActivity

            # Check if the table exists
            table_names = connection.introspection.table_names()
            if 'accounts_extensionactivity' not in table_names:
                # Table doesn't exist yet, skip logging
                return

            # Safe to create the activity record
            ExtensionActivity.log_activity(
                user=instance,
                activity_type='login',
                metadata={'source': 'user_creation'}
            )

        except Exception as e:
            # Silently fail during migrations - this is normal
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Could not create extension activity (normal during migrations): {e}")
            pass