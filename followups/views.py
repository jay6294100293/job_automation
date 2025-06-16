from django.shortcuts import render

# Create your views here.
# followups/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, TemplateView, View
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils import timezone
from datetime import date, timedelta
import requests

from django.db import models
from .models import FollowUpTemplate, FollowUpHistory
from .forms import FollowUpTemplateForm, ScheduleFollowUpForm, QuickFollowUpForm
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


class BulkFollowUpView(LoginRequiredMixin, View):
    def post(self, request):
        application_ids = request.POST.getlist('applications')
        template_id = request.POST.get('template_id')

        if not application_ids:
            messages.error(request, 'Please select at least one application.')
            return redirect('followups:dashboard')

        applications = JobApplication.objects.filter(
            id__in=application_ids,
            user=request.user
        )

        template = get_object_or_404(
            FollowUpTemplate,
            id=template_id,
            user=request.user
        )

        # Send bulk request to n8n
        try:
            webhook_data = {
                'user_id': request.user.id,
                'application_ids': application_ids,
                'template_id': template.id,
                'action': 'bulk_followup'
            }

            from django.conf import settings
            response = requests.post(
                f"{settings.N8N_WEBHOOK_URL}/followup",
                json=webhook_data,
                headers={'Authorization': f'Bearer {settings.N8N_API_TOKEN}'}
            )

            if response.status_code == 200:
                # Update all applications
                applications.update(
                    last_follow_up_date=timezone.now(),
                    follow_up_count=models.F('follow_up_count') + 1,
                    next_follow_up_date=date.today() + timedelta(days=14)
                )

                messages.success(request, f'Bulk follow-up sent to {applications.count()} applications!')
            else:
                messages.error(request, 'Failed to send bulk follow-up. Please try again.')

        except Exception as e:
            messages.error(request, f'Error sending bulk follow-up: {str(e)}')

        return redirect('followups:dashboard')


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