# Create your views here.
# dashboard/views.py
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from accounts.models import UserProfile
from jobs.models import JobApplication, JobSearchConfig


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        context['profile'] = profile

        # Application statistics
        applications = JobApplication.objects.filter(user=user)
        context['total_applications'] = applications.count()
        context['applications_this_week'] = applications.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        context['applications_this_month'] = applications.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()

        # Response rate calculation
        applied_count = applications.filter(application_status='applied').count()
        responded_count = applications.filter(
            application_status__in=['responded', 'interview', 'offer']
        ).count()
        context['response_rate'] = (responded_count / applied_count * 100) if applied_count > 0 else 0

        # Interview statistics
        context['interviews_scheduled'] = applications.filter(
            application_status='interview'
        ).count()

        # Applications by status for pipeline
        context['pipeline_data'] = {
            'found': applications.filter(application_status='found').count(),
            'applied': applications.filter(application_status='applied').count(),
            'responded': applications.filter(application_status='responded').count(),
            'interview': applications.filter(application_status='interview').count(),
            'offer': applications.filter(application_status='offer').count(),
        }

        # Recent applications
        context['recent_applications'] = applications.order_by('-created_at')[:5]

        # Due follow-ups
        from django.utils import timezone
        context['due_followups'] = applications.filter(
            next_follow_up_date__lte=timezone.now().date(),
            application_status__in=['applied', 'responded']
        ).count()

        # Search configurations
        context['search_configs'] = JobSearchConfig.objects.filter(
            user=user, is_active=True
        )

        return context


class AnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Monthly application trends
        applications = JobApplication.objects.filter(user=user)
        monthly_data = []
        for i in range(6):
            month_start = timezone.now() - timedelta(days=30 * i)
            month_end = month_start + timedelta(days=30)
            count = applications.filter(
                created_at__gte=month_start,
                created_at__lt=month_end
            ).count()
            monthly_data.append({
                'month': month_start.strftime('%B'),
                'applications': count
            })

        context['monthly_data'] = list(reversed(monthly_data))

        # Success metrics
        total_apps = applications.count()
        total_responses = applications.filter(
            application_status__in=['responded', 'interview', 'offer']
        ).count()
        total_interviews = applications.filter(application_status='interview').count()
        total_offers = applications.filter(application_status='offer').count()

        context['success_metrics'] = {
            'total_applications': total_apps,
            'response_rate': (total_responses / total_apps * 100) if total_apps > 0 else 0,
            'interview_rate': (total_interviews / total_apps * 100) if total_apps > 0 else 0,
            'offer_rate': (total_offers / total_apps * 100) if total_apps > 0 else 0,
        }

        return context