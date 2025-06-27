import os
import zipfile
from io import BytesIO
import requests
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.db.models import F
from .forms import JobSearchConfigForm, JobApplicationUpdateForm, BulkApplicationForm
from .models import JobApplication, JobSearchConfig


class BulkActionView(LoginRequiredMixin, View):
    """Handle bulk operations on job applications"""

    def post(self, request):
        action = request.POST.get('action')
        application_ids = request.POST.getlist('applications')

        if not action:
            messages.error(request, 'Please select an action.')
            return redirect('jobs:applications')

        if not application_ids:
            messages.error(request, 'Please select at least one application.')
            return redirect('jobs:applications')

        # Get applications belonging to current user
        applications = JobApplication.objects.filter(
            id__in=application_ids,
            user=request.user
        )

        if not applications.exists():
            messages.error(request, 'No valid applications selected.')
            return redirect('jobs:applications')

        # Execute the selected action
        try:
            if action == 'send_followup':
                return self._handle_send_followup(request, applications)
            elif action == 'mark_applied':
                return self._handle_mark_applied(request, applications)
            elif action == 'update_status':
                return self._handle_update_status(request, applications)
            elif action == 'download_docs':
                return self._handle_download_docs(request, applications)
            else:
                messages.error(request, 'Invalid action selected.')
                return redirect('jobs:applications')

        except Exception as e:
            messages.error(request, f'Error performing bulk action: {str(e)}')
            return redirect('jobs:applications')

    def _handle_send_followup(self, request, applications):
        """Send follow-up emails for selected applications"""
        # Filter applications that can receive follow-ups
        followup_ready = applications.filter(
            application_status__in=['applied', 'responded']
        )

        if not followup_ready.exists():
            messages.warning(request,
                             'No applications are ready for follow-up. Applications must be in "Applied" or "Responded" status.')
            return redirect('jobs:applications')

        # Trigger follow-up process (integration with n8n)
        try:
            followup_data = []
            for app in followup_ready:
                followup_data.append({
                    'application_id': app.id,
                    'job_title': app.job_title,
                    'company_name': app.company_name,
                    'user_email': app.user.email,
                    'days_since_application': app.days_since_application
                })

            # Send to n8n webhook for follow-up processing
            from django.conf import settings
            import requests

            if hasattr(settings, 'N8N_WEBHOOK_URL'):
                response = requests.post(
                    f"{settings.N8N_WEBHOOK_URL}/bulk-followup",
                    json={
                        'user_id': request.user.id,
                        'applications': followup_data
                    },
                    headers={'Authorization': f'Bearer {getattr(settings, "N8N_API_TOKEN", "")}'},
                    timeout=30
                )

                if response.status_code == 200:
                    # Update follow-up tracking
                    followup_ready.update(
                        last_follow_up_date=timezone.now(),
                        follow_up_count=F('follow_up_count') + 1
                    )
                    messages.success(request, f'Follow-up emails sent for {followup_ready.count()} applications.')
                else:
                    messages.error(request, 'Failed to send follow-up emails. Please try again.')
            else:
                messages.warning(request, 'Follow-up system not configured. Please contact administrator.')

        except Exception as e:
            messages.error(request, f'Error sending follow-ups: {str(e)}')

        return redirect('jobs:applications')

    def _handle_mark_applied(self, request, applications):
        """Mark selected applications as applied"""
        # Only mark applications that are in 'found' status
        found_apps = applications.filter(application_status='found')

        if not found_apps.exists():
            messages.warning(request, 'No applications in "Found" status to mark as applied.')
            return redirect('jobs:applications')

        # Update status and applied date
        updated_count = found_apps.update(
            application_status='applied',
            applied_date=timezone.now()
        )

        messages.success(request, f'{updated_count} applications marked as applied.')
        return redirect('jobs:applications')

    def _handle_update_status(self, request, applications):
        """Update status for selected applications"""
        new_status = request.POST.get('new_status')

        if not new_status:
            messages.error(request, 'Please select a status to update to.')
            return redirect('jobs:applications')

        # Validate status
        valid_statuses = [choice[0] for choice in JobApplication.STATUS_CHOICES]
        if new_status not in valid_statuses:
            messages.error(request, 'Invalid status selected.')
            return redirect('jobs:applications')

        # Update applications
        update_data = {'application_status': new_status}

        # Set applied_date if marking as applied
        if new_status == 'applied':
            update_data['applied_date'] = timezone.now()

        updated_count = applications.update(**update_data)
        status_display = dict(JobApplication.STATUS_CHOICES)[new_status]

        messages.success(request, f'{updated_count} applications updated to "{status_display}" status.')
        return redirect('jobs:applications')

    def _handle_download_docs(self, request, applications):
        """Download documents for selected applications as ZIP"""
        # Filter applications that have documents
        apps_with_docs = applications.filter(documents_generated=True)

        if not apps_with_docs.exists():
            messages.error(request, 'No applications with generated documents found.')
            return redirect('jobs:applications')

        try:
            # Create ZIP file in memory
            zip_buffer = BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for app in apps_with_docs:
                    # Get documents for this application
                    from documents.models import GeneratedDocument
                    documents = GeneratedDocument.objects.filter(application=app)

                    if documents.exists():
                        # Create folder name for this application
                        folder_name = f"{app.company_name}_{app.job_title}".replace(' ', '_')
                        folder_name = "".join(c for c in folder_name if c.isalnum() or c in ('_', '-'))

                        for doc in documents:
                            if os.path.exists(doc.file_path):
                                # Get filename and add to ZIP with folder structure
                                filename = os.path.basename(doc.file_path)
                                zip_path = f"{folder_name}/{filename}"
                                zip_file.write(doc.file_path, zip_path)
                            elif doc.content:
                                # If file doesn't exist but content is available
                                filename = f"{doc.get_document_type_display()}.txt"
                                zip_path = f"{folder_name}/{filename}"
                                zip_file.writestr(zip_path, doc.content.encode('utf-8'))

            zip_buffer.seek(0)

            # Create response
            response = HttpResponse(
                zip_buffer.getvalue(),
                content_type='application/zip'
            )

            # Set filename
            filename = f"BulkDocuments_{timezone.now().strftime('%Y%m%d_%H%M%S')}.zip"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            return response

        except Exception as e:
            messages.error(request, f'Error creating document archive: {str(e)}')
            return redirect('jobs:applications')

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

        # Add document types for the template
        context['document_types'] = [
            ('resume', 'Resume'),
            ('cover_letter', 'Cover Letter'),
            ('email_templates', 'Email Templates'),
            ('linkedin_messages', 'LinkedIn Messages'),
            ('video_script', 'Video Pitch Script'),
            ('company_research', 'Company Research'),
            ('followup_schedule', 'Follow-up Schedule'),
            ('skills_analysis', 'Skills Analysis'),
        ]

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