# dashboard/context_processors.py - FIX THE IMPORT

from django.utils import timezone
from datetime import timedelta


def sidebar_context(request):
    """
    Context processor to provide sidebar navigation data
    """
    context = {
        'total_applications': 0,
        'due_followups': 0,
        'upcoming_interviews': 0,
        'profile': None,
    }

    if request.user.is_authenticated:
        try:
            # FIX: Import from jobs.models, not dashboard.models
            from jobs.models import JobApplication
            from django.contrib.auth.models import User

            # Get total applications
            context['total_applications'] = JobApplication.objects.filter(
                user=request.user
            ).count()

            # Get due follow-ups (next 7 days)
            upcoming_date = timezone.now() + timedelta(days=7)
            context['due_followups'] = JobApplication.objects.filter(
                user=request.user,
                next_follow_up_date__lte=upcoming_date,
                next_follow_up_date__gte=timezone.now(),
                follow_up_sequence_active=True
            ).count()

            # Get upcoming interviews (next 30 days)
            interview_date_threshold = timezone.now() + timedelta(days=30)
            context['upcoming_interviews'] = JobApplication.objects.filter(
                user=request.user,
                interview_scheduled_date__isnull=False,
                interview_scheduled_date__gte=timezone.now(),
                interview_scheduled_date__lte=interview_date_threshold
            ).count()

            # Get user profile (create a simple profile object if needed)
            context['profile'] = {
                'profile_completion_percentage': calculate_profile_completion(request.user)
            }

        except Exception as e:
            # If models don't exist yet or other errors, use defaults
            print(f"Context processor error: {e}")
            pass

    return context


def calculate_profile_completion(user):
    """
    Calculate profile completion percentage
    """
    completion = 0
    total_fields = 8

    # Basic user fields
    if user.email:
        completion += 1
    if user.first_name:
        completion += 1
    if user.last_name:
        completion += 1

    # Check if user has any job applications (indicates active use)
    try:
        # FIX: Import from jobs.models, not dashboard.models
        from jobs.models import JobApplication
        if JobApplication.objects.filter(user=user).exists():
            completion += 2
    except:
        pass

    # Additional profile fields would be checked here
    # For now, assume some baseline completion
    completion += 3

    return min(int((completion / total_fields) * 100), 100)