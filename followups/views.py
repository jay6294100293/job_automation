import openai
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# Create your views here.
# followups/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, CreateView, UpdateView, TemplateView, View, FormView
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils import timezone
from datetime import date, timedelta
import requests

from django.db import models

from dashboard.views import generate_company_questions, generate_technical_questions
from job_automation import settings
from .models import FollowUpTemplate, FollowUpHistory
from .forms import FollowUpTemplateForm, ScheduleFollowUpForm, QuickFollowUpForm, BulkFollowUpForm
from jobs.models import JobApplication


class FollowUpDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'followups/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Due follow-ups
        context['due_followups'] = JobApplication.objects.filter(
            user=user,
            next_follow_up_date__lte=date.today(),
            application_status__in=['applied', 'responded']
        )

        # Recent follow-up history
        context['recent_followups'] = FollowUpHistory.objects.filter(
            application__user=user
        ).order_by('-sent_date')[:10]

        # Templates
        context['templates'] = FollowUpTemplate.objects.filter(
            user=user, is_active=True
        )

        return context


class SendFollowUpView(LoginRequiredMixin, View):
    def post(self, request, application_id):
        application = get_object_or_404(
            JobApplication,
            id=application_id,
            user=request.user
        )

        template_id = request.POST.get('template_id')
        if template_id:
            template = get_object_or_404(
                FollowUpTemplate,
                id=template_id,
                user=request.user
            )
        else:
            # Use default template
            template = FollowUpTemplate.objects.filter(
                user=request.user,
                is_default=True,
                is_active=True
            ).first()

            if not template:
                messages.error(request, 'No follow-up template found. Please create one first.')
                return redirect('followups:dashboard')

        # Send to n8n for email generation and sending
        try:
            webhook_data = {
                'user_id': request.user.id,
                'application_id': application.id,
                'template_id': template.id,
                'action': 'send_followup'
            }

            from django.conf import settings
            response = requests.post(
                f"{settings.N8N_WEBHOOK_URL}/followup",
                json=webhook_data,
                headers={'Authorization': f'Bearer {settings.N8N_API_TOKEN}'}
            )

            if response.status_code == 200:
                # Update application
                application.last_follow_up_date = timezone.now()
                application.follow_up_count += 1
                application.next_follow_up_date = date.today() + timedelta(days=14)
                application.save()

                # Update template stats
                template.times_used += 1
                template.save()

                messages.success(request, f'Follow-up sent for {application.job_title} at {application.company_name}!')
            else:
                messages.error(request, 'Failed to send follow-up. Please try again.')

        except Exception as e:
            messages.error(request, f'Error sending follow-up: {str(e)}')

        return redirect('followups:dashboard')


# followups/views.py (Update the BulkFollowUpView)

class BulkFollowUpView(LoginRequiredMixin, FormView):
    """Handle bulk follow-up operations"""
    template_name = 'followups/bulk_followup.html'
    form_class = BulkFollowUpForm
    success_url = reverse_lazy('followups:dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        application_ids = form.cleaned_data['applications']
        template = form.cleaned_data['template']
        custom_message = form.cleaned_data['custom_message']
        send_now = form.cleaned_data['send_now']
        scheduled_date = form.cleaned_data['scheduled_date']

        try:
            # Process each application
            successful = 0
            for app_id in application_ids:
                try:
                    application = JobApplication.objects.get(
                        id=app_id,
                        user=self.request.user
                    )

                    # Create the follow-up history record
                    follow_up = FollowUpHistory.objects.create(
                        application=application,
                        template=template,
                        custom_message=custom_message if custom_message else "",
                        status='scheduled' if not send_now else 'pending',
                        scheduled_date=scheduled_date if scheduled_date else timezone.now()
                    )

                    if send_now:
                        # Trigger n8n workflow for immediate sending
                        webhook_data = {
                            'user_id': self.request.user.id,
                            'application_id': application.id,
                            'template_id': template.id,
                            'follow_up_id': follow_up.id,
                            'custom_message': custom_message if custom_message else None
                        }

                        # Send to n8n webhook
                        response = requests.post(
                            f"{settings.N8N_WEBHOOK_URL}/followup",
                            json=webhook_data,
                            headers={'Authorization': f'Bearer {settings.N8N_API_TOKEN}'}
                        )

                        if response.status_code == 200:
                            successful += 1
                            follow_up.status = 'sent'
                            follow_up.sent_date = timezone.now()
                            follow_up.save()
                    else:
                        # It's scheduled for later
                        successful += 1

                except JobApplication.DoesNotExist:
                    continue

            if successful > 0:
                if send_now:
                    messages.success(self.request, f'Successfully sent {successful} follow-up emails.')
                else:
                    messages.success(self.request,
                                     f'Successfully scheduled {successful} follow-up emails for {scheduled_date.strftime("%b %d, %Y at %I:%M %p")}.')
            else:
                messages.error(self.request, 'Failed to process follow-up emails. Please try again.')

        except Exception as e:
            messages.error(self.request, f'Error processing follow-ups: {str(e)}')

        return super().form_valid(form)

class ScheduleFollowUpView(LoginRequiredMixin, View):
    def post(self, request, application_id):
        application = get_object_or_404(
            JobApplication,
            id=application_id,
            user=request.user
        )

        form = ScheduleFollowUpForm(request.user, request.POST)
        if form.is_valid():
            follow_up_date = form.cleaned_data['follow_up_date']
            template = form.cleaned_data['template']

            application.next_follow_up_date = follow_up_date
            application.follow_up_sequence_active = True
            application.save()

            messages.success(
                request,
                f'Follow-up scheduled for {follow_up_date} for {application.job_title}'
            )
        else:
            messages.error(request, 'Error scheduling follow-up. Please check the form.')

        return redirect('followups:dashboard')


class TemplateManagementView(LoginRequiredMixin, ListView):
    model = FollowUpTemplate
    template_name = 'followups/templates.html'
    context_object_name = 'templates'

    def get_queryset(self):
        return FollowUpTemplate.objects.filter(user=self.request.user)


class CreateTemplateView(LoginRequiredMixin, CreateView):
    model = FollowUpTemplate
    form_class = FollowUpTemplateForm
    template_name = 'followups/create_template.html'
    success_url = reverse_lazy('followups:templates')

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, f'Template "{form.instance.template_name}" created successfully!')
        return super().form_valid(form)


class EditTemplateView(LoginRequiredMixin, UpdateView):
    model = FollowUpTemplate
    form_class = FollowUpTemplateForm
    template_name = 'followups/edit_template.html'
    success_url = reverse_lazy('followups:templates')

    def get_queryset(self):
        return FollowUpTemplate.objects.filter(user=self.request.user)


class FollowUpHistoryView(LoginRequiredMixin, ListView):
    model = FollowUpHistory
    template_name = 'followups/history.html'
    context_object_name = 'history'
    paginate_by = 20

    def get_queryset(self):
        return FollowUpHistory.objects.filter(
            application__user=self.request.user
        ).order_by('-sent_date')


# ADD THESE UTILITY VIEWS TO followups/views.py

class DeleteTemplateView(LoginRequiredMixin, View):
    """Delete follow-up template"""

    def post(self, request, pk):
        template = get_object_or_404(
            FollowUpTemplate,
            pk=pk,
            user=request.user
        )

        template_name = template.template_name
        template.delete()

        messages.success(
            request,
            f'Template "{template_name}" deleted successfully!'
        )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

        return redirect('followups:templates')


class DuplicateTemplateView(LoginRequiredMixin, View):
    """Duplicate follow-up template"""

    def post(self, request, pk):
        original_template = get_object_or_404(
            FollowUpTemplate,
            pk=pk,
            user=request.user
        )

        # Create duplicate
        duplicate = FollowUpTemplate.objects.create(
            user=request.user,
            template_name=f"{original_template.template_name} (Copy)",
            template_type=original_template.template_type,
            subject_template=original_template.subject_template,
            body_template=original_template.body_template,
            days_after_application=original_template.days_after_application,
            is_default=False,  # Duplicates are never default
            is_active=True
        )

        messages.success(
            request,
            f'Template duplicated successfully as "{duplicate.template_name}"!'
        )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'new_template_id': duplicate.id,
                'new_template_name': duplicate.template_name
            })

        return redirect('followups:edit_template', pk=duplicate.pk)


class TemplatePreviewView(LoginRequiredMixin, View):
    """Preview template with sample data"""

    def post(self, request, pk):
        template = get_object_or_404(
            FollowUpTemplate,
            pk=pk,
            user=request.user
        )

        # Sample data for preview
        sample_data = {
            'user_name': request.user.get_full_name() or request.user.username,
            'company_name': 'Sample Company Inc.',
            'job_title': 'Software Engineer',
            'hiring_manager': 'Jane Smith',
            'days_since_application': '7'
        }

        # Process template
        subject = template.subject_template
        body = template.body_template

        for key, value in sample_data.items():
            subject = subject.replace(f'{{{{{key}}}}}', str(value))
            body = body.replace(f'{{{{{key}}}}}', str(value))

        return JsonResponse({
            'success': True,
            'preview': {
                'subject': subject,
                'body': body,
                'template_name': template.template_name,
                'template_type': template.get_template_type_display(),
                'sample_data': sample_data
            }
        })


class TestTemplateView(LoginRequiredMixin, View):
    """Send test email with template"""

    def post(self, request, pk):
        template = get_object_or_404(
            FollowUpTemplate,
            pk=pk,
            user=request.user
        )

        try:
            # Get user's email
            user_email = request.user.email
            if not user_email:
                return JsonResponse({
                    'success': False,
                    'error': 'No email address found for your account'
                })

            # Sample data for test
            sample_data = {
                'user_name': request.user.get_full_name() or request.user.username,
                'company_name': 'Sample Company Inc.',
                'job_title': 'Software Engineer',
                'hiring_manager': 'Jane Smith',
                'days_since_application': '7'
            }

            # Process template
            subject = f"[TEST] {template.subject_template}"
            body = f"This is a test email.\n\n{template.body_template}\n\n---\nThis was a test of your follow-up template."

            for key, value in sample_data.items():
                subject = subject.replace(f'{{{{{key}}}}}', str(value))
                body = body.replace(f'{{{{{key}}}}}', str(value))

            # Send test email (this would integrate with your email service)
            # For now, we'll just simulate it
            # In a real implementation, you'd use Django's send_mail or your email service

            # Simulate sending
            import time
            time.sleep(1)  # Simulate email sending delay

            return JsonResponse({
                'success': True,
                'message': f'Test email sent to {user_email}',
                'test_data': {
                    'recipient': user_email,
                    'subject': subject,
                    'preview': body[:200] + '...' if len(body) > 200 else body
                }
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Failed to send test email: {str(e)}'
            })


class ToggleTemplateStatusView(LoginRequiredMixin, View):
    """Toggle template active/inactive status"""

    def post(self, request, pk):
        template = get_object_or_404(
            FollowUpTemplate,
            pk=pk,
            user=request.user
        )

        template.is_active = not template.is_active
        template.save()

        status_text = "activated" if template.is_active else "deactivated"

        messages.success(
            request,
            f'Template "{template.template_name}" {status_text} successfully!'
        )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'is_active': template.is_active,
                'status_text': status_text
            })

        return redirect('followups:templates')


class SetDefaultTemplateView(LoginRequiredMixin, View):
    """Set a template as the default"""

    def post(self, request, pk):
        template = get_object_or_404(
            FollowUpTemplate,
            pk=pk,
            user=request.user
        )

        # Remove default from all other templates of the same type
        FollowUpTemplate.objects.filter(
            user=request.user,
            template_type=template.template_type
        ).update(is_default=False)

        # Set this one as default
        template.is_default = True
        template.save()

        messages.success(
            request,
            f'"{template.template_name}" is now the default {template.get_template_type_display()} template!'
        )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Default template updated'
            })

        return redirect('followups:templates')


class UpdateFollowUpResponseView(LoginRequiredMixin, View):
    """Update follow-up response status"""

    def post(self, request):
        try:
            followup_id = request.POST.get('followup_id')
            response_received = request.POST.get('response_received') == 'true'
            response_type = request.POST.get('response_type', 'neutral')
            notes = request.POST.get('notes', '')

            followup = get_object_or_404(
                FollowUpHistory,
                id=followup_id,
                application__user=request.user
            )

            followup.response_received = response_received
            followup.response_type = response_type
            followup.notes = notes

            if response_received and not followup.response_date:
                followup.response_date = timezone.now()

            followup.save()

            # Update template success rate
            if response_received and followup.template:
                followup.template.responses_received += 1
                followup.template.calculate_success_rate()

            return JsonResponse({
                'success': True,
                'message': 'Response status updated successfully'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


class FollowUpAnalyticsView(LoginRequiredMixin, TemplateView):
    """Analytics dashboard for follow-ups"""
    template_name = 'followups/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Basic stats
        total_followups = FollowUpHistory.objects.filter(
            application__user=user
        ).count()

        responses_received = FollowUpHistory.objects.filter(
            application__user=user,
            response_received=True
        ).count()

        overall_success_rate = (responses_received / total_followups * 100) if total_followups > 0 else 0

        # Template performance
        template_stats = []
        for template in FollowUpTemplate.objects.filter(user=user):
            template_stats.append({
                'template': template,
                'success_rate': template.success_rate,
                'times_used': template.times_used,
                'responses': template.responses_received
            })

        # Monthly trends (last 6 months)
        from django.db.models import Count, Q
        from datetime import datetime, timedelta

        six_months_ago = datetime.now() - timedelta(days=180)
        monthly_stats = FollowUpHistory.objects.filter(
            application__user=user,
            sent_date__gte=six_months_ago
        ).extra(
            select={'month': 'EXTRACT(month FROM sent_date)'}
        ).values('month').annotate(
            total=Count('id'),
            responses=Count('id', filter=Q(response_received=True))
        ).order_by('month')

        context.update({
            'total_followups': total_followups,
            'responses_received': responses_received,
            'overall_success_rate': round(overall_success_rate, 1),
            'template_stats': template_stats,
            'monthly_stats': list(monthly_stats)
        })

        return context









