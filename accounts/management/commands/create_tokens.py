from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


class Command(BaseCommand):
    help = 'Create API tokens for all users'

    def handle(self, *args, **options):
        created_count = 0
        for user in User.objects.all():
            token, created = Token.objects.get_or_create(user=user)
            if created:
                created_count += 1
                self.stdout.write(f"Created token for user: {user.username}")

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} tokens')
        )
