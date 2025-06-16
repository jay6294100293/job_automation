from django.db.models import Q
from django.shortcuts import render

# Create your views here.
# jobs/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
import requests
import json
from .models import JobApplication, JobSearchConfig
from .forms import JobSearchConfigForm, JobApplicationUpdateForm, BulkApplicationForm


class JobSearchConfigView(LoginRequiredMixin, ListView):
    model = JobSearchConfig
    template_name = 'jobs/search_config.html'
    context_object_name = 'configs'

    def get_queryset(self):
        return JobSearchConfig.objects.filter(user=self.request.user)


class CreateSearchConfigView(LoginRequiredMixin, CreateView):
    model = JobSearchConfig
    form_class = JobSearchConfigForm
    template_name = 'jobs/create_config.html'
    success_url = reverse_lazy('jobs:search_config')

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, f'Search configuration "{form.instance.config_name}" created successfully!')
        return super().form_valid(form)


class EditSearchConfigView(LoginRequiredMixin, UpdateView):
    model = JobSearchConfig
    form_class = JobSearchConfigForm
    template_name = 'jobs/edit_config.html'
    success_url = reverse_lazy('jobs:search_config')

    def get_queryset(self):
        return JobSearchConfig.objects.filter(user=self.request.user)


class DeleteSearchConfigView(LoginRequiredMixin, DeleteView):
    model = JobSearchConfig
    template_name = 'jobs/delete_config.html'
    success_url = reverse_lazy('jobs:search_config')

    def get_queryset(self):
        return JobSearchConfig.objects.filter(user=self.request.user)


class ExecuteSearchView(LoginRequiredMixin, View):
    def post(self, request, config_id):
        config = get_object_or_404(JobSearchConfig, id=config_id, user=request.user)

        # Trigger n8n workflow
        try:
            webhook_data = {
                'user_id': request.user.id,
                'config_id': config.id,
                'job_categories': config.job_categories,
                'target_locations': config.target_locations,
                'salary_min': config.salary_min,
                'salary_max': config.salary_max,
                'remote_preference': config.remote_preference,
            }

            # Send to n8n webhook
            from django.conf import settings
            response = requests.post(
                f"{settings.N8N_WEBHOOK_URL}/job-search",
                json=webhook_data,
                headers={'Authorization': f'Bearer {settings.N8N_API_TOKEN}'}
            )

            if response.status_code == 200:
                config.last_search_date = timezone.now()
                config.save()
                messages.success(request, 'Job search started! Results will appear in your dashboard shortly.')
            else:
                messages.error(request, 'Failed to start job search. Please try again.')

        except Exception as e:
            messages.error(request, f'Error starting job search: {str(e)}')

        return redirect('jobs:search_config')


class JobListView(LoginRequiredMixin, ListView):
    model = JobApplication
    template_name = 'jobs/job_list.html'
    context_object_name = 'jobs'
    paginate_by = 20

    def get_queryset(self):
        queryset = JobApplication.objects.filter(user=self.request.user)

        # Filtering
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(application_status=status)

        urgency = self.request.GET.get('urgency')
        if urgency:
            queryset = queryset.filter(urgency_level=urgency)

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(job_title__icontains=search) |
                Q(company_name__icontains=search)
            )

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bulk_form'] = BulkApplicationForm(user=self.request.user)
        return context


class ApplicationListView(LoginRequiredMixin, ListView):
    model = JobApplication
    template_name = 'jobs/applications.html'
    context_object_name = 'applications'

    def get_queryset(self):
        return JobApplication.objects.filter(user=self.request.user).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        applications = self.get_queryset()

        # Group by status for pipeline view
        context['pipeline'] = {
            'found': applications.filter(application_status='found'),
            'applied': applications.filter(application_status='applied'),
            'responded': applications.filter(application_status='responded'),
            'interview': applications.filter(application_status='interview'),
            'offer': applications.filter(application_status='offer'),
        }

        return context


class ApplicationDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'jobs/application_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = get_object_or_404(
            JobApplication,
            id=kwargs['pk'],
            user=self.request.user
        )
        context['application'] = application
        context['update_form'] = JobApplicationUpdateForm(instance=application)
        return context


class UpdateApplicationStatusView(LoginRequiredMixin, View):
    def post(self, request, pk):
        application = get_object_or_404(JobApplication, id=pk, user=request.user)
        form = JobApplicationUpdateForm(request.POST, instance=application)

        if form.is_valid():
            form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            messages.success(request, 'Application status updated!')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
            messages.error(request, 'Error updating application status')

        return redirect('jobs:application_detail', pk=pk)