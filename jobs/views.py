# jobs/views.py - Enhanced Universal Version
import os
import zipfile
from io import BytesIO
import requests
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, Avg
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.db.models import F
from django.core.paginator import Paginator
from django.conf import settings
from .forms import UniversalJobSearchConfigForm, JobApplicationUpdateForm, BulkApplicationForm
from .models import JobApplication, JobSearchConfig


class JobSearchConfigView(LoginRequiredMixin, ListView):
    """Enhanced view for displaying all user configurations"""
    model = JobSearchConfig
    template_name = 'jobs/search_config.html'
    context_object_name = 'configs'

    def get_queryset(self):
        queryset = JobSearchConfig.objects.filter(user=self.request.user)

        # Apply filters from query parameters
        status_filter = self.request.GET.get('status')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)

        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(config_name__icontains=search_query) |
                Q(job_categories__icontains=search_query) |
                Q(target_locations__icontains=search_query)
            )

        sort_by = self.request.GET.get('sort', 'updated')
        if sort_by == 'name':
            queryset = queryset.order_by('config_name')
        elif sort_by == 'created':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'jobs_found':
            queryset = queryset.order_by('-total_jobs_found')
        else:  # default to updated
            queryset = queryset.order_by('-updated_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add statistics for the dashboard
        configs = self.get_queryset()
        context.update({
            'total_configs': configs.count(),
            'active_configs': configs.filter(is_active=True).count(),
            'total_jobs_found': sum([config.total_jobs_found or 0 for config in configs]),
            'recent_searches': configs.filter(last_search_date__isnull=False).count(),
        })

        return context


class CreateSearchConfigView(LoginRequiredMixin, CreateView):
    """Enhanced view for creating universal job search configurations"""
    model = JobSearchConfig
    form_class = UniversalJobSearchConfigForm
    template_name = 'jobs/create_config.html'
    success_url = reverse_lazy('jobs:search_config')

    def form_valid(self, form):
        form.instance.user = self.request.user

        # Set default currency based on user profile or location
        if not form.instance.salary_currency:
            # You could determine this from user profile location
            form.instance.salary_currency = 'CAD'  # Default for Canadian users

        messages.success(
            self.request,
            f'Universal job search configuration "{form.instance.config_name}" created successfully! '
            f'The system will search for {len(form.instance.job_categories)} job categories '
            f'across {len(form.instance.target_locations)} locations.'
        )

        # Trigger initial search if requested
        if self.request.POST.get('run_initial_search'):
            self._trigger_initial_search(form.instance)

        return super().form_valid(form)

    def _trigger_initial_search(self, config):
        """Trigger an initial search for the newly created configuration"""
        try:
            webhook_data = {
                'user_id': self.request.user.id,
                'config_id': config.id,
                'job_categories': config.job_categories,
                'target_locations': config.target_locations,
                'salary_min': config.salary_min,
                'salary_max': config.salary_max,
                'salary_currency': config.salary_currency,
                'remote_preference': config.remote_preference,
                'required_keywords': getattr(config, 'required_keywords', []),
                'excluded_keywords': getattr(config, 'excluded_keywords', []),
                'excluded_companies': getattr(config, 'excluded_companies', []),
                'auto_follow_up': config.auto_follow_up_enabled,
            }

            # Send to n8n webhook
            if hasattr(settings, 'N8N_WEBHOOK_URL'):
                response = requests.post(
                    f"{settings.N8N_WEBHOOK_URL}/universal-job-search",
                    json=webhook_data,
                    headers={'Authorization': f'Bearer {getattr(settings, "N8N_API_TOKEN", "")}'},
                    timeout=30
                )

                if response.status_code == 200:
                    config.last_search_date = timezone.now()
                    config.save()
                    messages.info(
                        self.request,
                        'Initial job search has been started! Results will appear in your dashboard shortly.'
                    )
        except Exception as e:
            messages.warning(
                self.request,
                f'Configuration created successfully, but initial search failed: {str(e)}'
            )


class EditSearchConfigView(LoginRequiredMixin, UpdateView):
    """Enhanced view for editing universal job search configurations"""
    model = JobSearchConfig
    form_class = UniversalJobSearchConfigForm
    template_name = 'jobs/edit_config.html'
    success_url = reverse_lazy('jobs:search_config')

    def get_queryset(self):
        return JobSearchConfig.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(
            self.request,
            f'Configuration "{form.instance.config_name}" updated successfully!'
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add statistics about this configuration
        config = self.object
        applications = JobApplication.objects.filter(
            user=self.request.user,
            search_config=config
        )

        context.update({
            'applications_count': applications.count(),
            'recent_applications': applications.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=30)
            ).count(),
            'successful_applications': applications.filter(
                application_status__in=['hired', 'offer_received']
            ).count(),
        })

        return context


class DeleteSearchConfigView(LoginRequiredMixin, DeleteView):
    """Enhanced view for deleting job search configurations"""
    model = JobSearchConfig
    template_name = 'jobs/delete_config.html'
    success_url = reverse_lazy('jobs:search_config')

    def get_queryset(self):
        return JobSearchConfig.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add statistics about what will be affected
        config = self.object
        context.update({
            'applications_count': JobApplication.objects.filter(
                user=self.request.user,
                search_config=config
            ).count(),
            'searches_count': 1 if config.last_search_date else 0,
            'documents_count': JobApplication.objects.filter(
                user=self.request.user,
                search_config=config,
                documents_generated=True
            ).count(),
            'followups_count': JobApplication.objects.filter(
                user=self.request.user,
                search_config=config,
                follow_up_count__gt=0
            ).count(),
        })

        return context

    def delete(self, request, *args, **kwargs):
        config = self.get_object()
        config_name = config.config_name

        # Optionally preserve applications by setting search_config to None
        # instead of deleting them
        JobApplication.objects.filter(search_config=config).update(search_config=None)

        messages.success(
            request,
            f'Configuration "{config_name}" has been deleted. Associated job applications have been preserved.'
        )

        return super().delete(request, *args, **kwargs)


class ExecuteSearchView(LoginRequiredMixin, View):
    """Enhanced view for executing universal job searches"""

    def post(self, request, config_id):
        config = get_object_or_404(JobSearchConfig, id=config_id, user=request.user)

        if not config.is_active:
            return JsonResponse({
                'success': False,
                'error': 'Configuration is not active'
            }, status=400)

        try:
            # Prepare comprehensive webhook data for universal search
            webhook_data = {
                'search_id': f"{config.id}_{timezone.now().timestamp()}",
                'user_id': request.user.id,
                'config_id': config.id,
                'config_name': config.config_name,

                # Job criteria
                'job_categories': config.job_categories,
                'target_locations': config.target_locations,
                'remote_preference': config.remote_preference,

                # Salary information
                'salary_min': config.salary_min,
                'salary_max': config.salary_max,
                'salary_currency': config.salary_currency,

                # Advanced filters
                'required_keywords': getattr(config, 'required_keywords', []),
                'excluded_keywords': getattr(config, 'excluded_keywords', []),
                'excluded_companies': getattr(config, 'excluded_companies', []),

                # Automation settings
                'auto_follow_up_enabled': config.auto_follow_up_enabled,

                # User information for personalization
                'user_email': request.user.email,
                'user_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,

                # Search metadata
                'timestamp': timezone.now().isoformat(),
                'search_type': 'manual',
            }

            # Send to n8n universal job search webhook
            if hasattr(settings, 'N8N_WEBHOOK_URL'):
                response = requests.post(
                    f"{settings.N8N_WEBHOOK_URL}/universal-job-search",
                    json=webhook_data,
                    headers={
                        'Authorization': f'Bearer {getattr(settings, "N8N_API_TOKEN", "")}',
                        'Content-Type': 'application/json'
                    },
                    timeout=60
                )

                if response.status_code == 200:
                    # Update configuration
                    config.last_search_date = timezone.now()
                    config.save()

                    return JsonResponse({
                        'success': True,
                        'message': 'Universal job search started successfully!',
                        'search_id': webhook_data['search_id']
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f'Search service returned status {response.status_code}'
                    }, status=500)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Job search service not configured'
                }, status=500)

        except requests.exceptions.Timeout:
            return JsonResponse({
                'success': False,
                'error': 'Search request timed out. Please try again.'
            }, status=500)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error starting job search: {str(e)}'
            }, status=500)


class BulkActionView(LoginRequiredMixin, View):
    """Enhanced bulk operations on job applications"""

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
            elif action == 'schedule_interview':
                return self._handle_schedule_interview(request, applications)
            elif action == 'add_to_calendar':
                return self._handle_add_to_calendar(request, applications)
            else:
                messages.error(request, 'Invalid action selected.')
                return redirect('jobs:applications')

        except Exception as e:
            messages.error(request, f'Error performing bulk action: {str(e)}')
            return redirect('jobs:applications')

    def _handle_send_followup(self, request, applications):
        """Send follow-up emails for selected applications"""
        followup_ready = applications.filter(
            application_status__in=['applied', 'responded', 'application_viewed']
        )

        if not followup_ready.exists():
            messages.warning(request,
                             'No applications are ready for follow-up. Applications must be in "Applied", "Responded", or "Application Viewed" status.')
            return redirect('jobs:applications')

        # Enhanced follow-up data with more context
        try:
            followup_data = []
            for app in followup_ready:
                followup_data.append({
                    'application_id': app.id,
                    'job_title': app.job_title,
                    'company_name': app.company_name,
                    'user_email': app.user.email,
                    'user_name': f"{app.user.first_name} {app.user.last_name}".strip() or app.user.username,
                    'days_since_application': app.days_since_application,
                    'application_source': app.application_source,
                    'hiring_manager_email': app.hiring_manager_email,
                    'recruiter_email': app.recruiter_email,
                    'follow_up_count': app.follow_up_count,
                    'last_follow_up_date': app.last_follow_up_date.isoformat() if app.last_follow_up_date else None,
                    'job_url': app.job_url,
                    'match_percentage': app.match_percentage,
                })

            # Send to n8n webhook for follow-up processing
            if hasattr(settings, 'N8N_WEBHOOK_URL'):
                response = requests.post(
                    f"{settings.N8N_WEBHOOK_URL}/bulk-followup",
                    json={
                        'user_id': request.user.id,
                        'applications': followup_data,
                        'followup_type': 'bulk_manual',
                        'timestamp': timezone.now().isoformat()
                    },
                    headers={'Authorization': f'Bearer {getattr(settings, "N8N_API_TOKEN", "")}'},
                    timeout=30
                )

                if response.status_code == 200:
                    # Update follow-up tracking
                    followup_ready.update(
                        last_follow_up_date=timezone.now(),
                        follow_up_count=F('follow_up_count') + 1,
                        next_follow_up_date=timezone.now().date() + timezone.timedelta(days=14)
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
        applicable_apps = applications.filter(application_status__in=['discovered', 'saved'])

        if not applicable_apps.exists():
            messages.warning(request, 'No applications in "Discovered" or "Saved" status to mark as applied.')
            return redirect('jobs:applications')

        # Update status and applied date
        updated_count = applicable_apps.update(
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
                    try:
                        from documents.models import GeneratedDocument
                        documents = GeneratedDocument.objects.filter(application=app)
                    except ImportError:
                        # Fallback if documents app is not available
                        continue

                    if documents.exists():
                        # Create folder name for this application
                        folder_name = f"{app.company_name}_{app.job_title}".replace(' ', '_')
                        folder_name = "".join(c for c in folder_name if c.isalnum() or c in ('_', '-'))

                        for doc in documents:
                            if os.path.exists(doc.file_path):
                                filename = os.path.basename(doc.file_path)
                                zip_path = f"{folder_name}/{filename}"
                                zip_file.write(doc.file_path, zip_path)
                            elif hasattr(doc, 'content') and doc.content:
                                filename = f"{doc.get_document_type_display()}.txt"
                                zip_path = f"{folder_name}/{filename}"
                                zip_file.writestr(zip_path, doc.content.encode('utf-8'))

            zip_buffer.seek(0)

            # Create response
            response = HttpResponse(
                zip_buffer.getvalue(),
                content_type='application/zip'
            )

            filename = f"JobDocuments_{timezone.now().strftime('%Y%m%d_%H%M%S')}.zip"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            return response

        except Exception as e:
            messages.error(request, f'Error creating document archive: {str(e)}')
            return redirect('jobs:applications')

    def _handle_schedule_interview(self, request, applications):
        """Schedule interview reminders for selected applications"""
        interview_apps = applications.filter(
            application_status__in=['interview', 'first_interview', 'second_interview', 'final_interview']
        )

        if not interview_apps.exists():
            messages.warning(request, 'No applications in interview status found.')
            return redirect('jobs:applications')

        # This would integrate with calendar systems
        # For now, just update the applications
        updated_count = interview_apps.update(
            next_follow_up_date=timezone.now().date() + timezone.timedelta(days=1)
        )

        messages.success(request, f'Interview reminders set for {updated_count} applications.')
        return redirect('jobs:applications')

    def _handle_add_to_calendar(self, request, applications):
        """Add applications to calendar (integration placeholder)"""
        # This would integrate with Google Calendar, Outlook, etc.
        messages.info(request, f'Calendar integration for {applications.count()} applications is being processed.')
        return redirect('jobs:applications')


class JobListView(LoginRequiredMixin, ListView):
    """Enhanced view for listing all job applications"""
    model = JobApplication
    template_name = 'jobs/job_list.html'
    context_object_name = 'jobs'
    paginate_by = 25

    def get_queryset(self):
        queryset = JobApplication.objects.filter(user=self.request.user)

        # Enhanced filtering options
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(application_status=status)

        urgency = self.request.GET.get('urgency')
        if urgency:
            queryset = queryset.filter(urgency_level=urgency)

        source = self.request.GET.get('source')
        if source:
            queryset = queryset.filter(application_source=source)

        company = self.request.GET.get('company')
        if company:
            queryset = queryset.filter(company_name__icontains=company)

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(job_title__icontains=search) |
                Q(company_name__icontains=search) |
                Q(location__icontains=search)
            )

        # Date range filtering
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        # Salary range filtering
        salary_min = self.request.GET.get('salary_min')
        salary_max = self.request.GET.get('salary_max')
        if salary_min:
            queryset = queryset.filter(salary_min__gte=salary_min)
        if salary_max:
            queryset = queryset.filter(salary_max__lte=salary_max)

        # Sort options
        sort_by = self.request.GET.get('sort', '-created_at')
        if sort_by in ['-created_at', 'created_at', 'job_title', 'company_name',
                       'application_status', 'urgency_level', '-match_percentage']:
            queryset = queryset.order_by(sort_by)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bulk_form'] = BulkApplicationForm(user=self.request.user)

        # Add filter choices for the template
        applications = JobApplication.objects.filter(user=self.request.user)
        context.update({
            'status_choices': JobApplication.STATUS_CHOICES,
            'urgency_choices': JobApplication.URGENCY_LEVELS,
            'source_choices': JobApplication.APPLICATION_SOURCES,
            'companies': applications.values_list('company_name', flat=True).distinct().order_by('company_name'),
        })

        return context


class ApplicationListView(LoginRequiredMixin, ListView):
    """Enhanced pipeline view for job applications"""
    model = JobApplication
    template_name = 'jobs/applications.html'
    context_object_name = 'applications'

    def get_queryset(self):
        return JobApplication.objects.filter(user=self.request.user).select_related('search_config')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        applications = self.get_queryset()

        # Enhanced pipeline with more statuses
        context['pipeline'] = {
            'discovered': applications.filter(application_status='discovered'),
            'saved': applications.filter(application_status='saved'),
            'applied': applications.filter(application_status='applied'),
            'screening': applications.filter(application_status__in=['phone_screening', 'application_viewed']),
            'interview': applications.filter(application_status__in=[
                'first_interview', 'second_interview', 'final_interview', 'technical_assessment'
            ]),
            'offer': applications.filter(application_status__in=['offer_pending', 'offer_received']),
            'success': applications.filter(application_status__in=['hired', 'offer_accepted']),
            'closed': applications.filter(application_status__in=[
                'rejected_automated', 'rejected_screening', 'rejected_interview',
                'rejected_offer', 'withdrawn', 'ghosted'
            ]),
        }

        # Add analytics
        total_apps = applications.count()
        context['analytics'] = {
            'total_applications': total_apps,
            'success_rate': round((context['pipeline']['success'].count() / total_apps * 100),
                                  1) if total_apps > 0 else 0,
            'response_rate': round(
                (applications.exclude(application_status__in=['discovered', 'applied']).count() / total_apps * 100),
                1) if total_apps > 0 else 0,
            'avg_match_score': applications.aggregate(avg_match=Avg('match_percentage'))['avg_match'] or 0,
        }

        return context


class ApplicationDetailView(LoginRequiredMixin, TemplateView):
    """Enhanced detailed view for individual job applications"""
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

        # Add enhanced document types
        context['document_types'] = [
            ('resume', 'Tailored Resume'),
            ('cover_letter', 'Personalized Cover Letter'),
            ('email_templates', 'Email Templates'),
            ('linkedin_messages', 'LinkedIn Connection Messages'),
            ('video_script', 'Video Pitch Script'),
            ('company_research', 'Company Research Report'),
            ('followup_schedule', 'Follow-up Schedule'),
            ('skills_analysis', 'Skills Gap Analysis'),
            ('salary_negotiation', 'Salary Negotiation Guide'),
            ('interview_prep', 'Interview Preparation'),
        ]

        # Add related applications from same company
        context['related_applications'] = JobApplication.objects.filter(
            user=self.request.user,
            company_name=application.company_name
        ).exclude(id=application.id)[:5]

        # Add timeline events
        context['timeline_events'] = self._get_application_timeline(application)

        return context

    def _get_application_timeline(self, application):
        """Generate timeline events for the application"""
        events = []

        events.append({
            'date': application.created_at,
            'title': 'Job Discovered',
            'description': f'Found {application.job_title} at {application.company_name}',
            'icon': 'fas fa-search',
            'color': 'info'
        })

        if application.applied_date:
            events.append({
                'date': application.applied_date,
                'title': 'Application Submitted',
                'description': f'Applied via {application.get_application_source_display()}',
                'icon': 'fas fa-paper-plane',
                'color': 'primary'
            })

        if application.last_follow_up_date:
            events.append({
                'date': application.last_follow_up_date,
                'title': 'Follow-up Sent',
                'description': f'Follow-up #{application.follow_up_count}',
                'icon': 'fas fa-envelope',
                'color': 'warning'
            })

        if application.interview_scheduled_date:
            events.append({
                'date': application.interview_scheduled_date,
                'title': 'Interview Scheduled',
                'description': f'{application.get_interview_type_display()} interview',
                'icon': 'fas fa-calendar',
                'color': 'success'
            })

        return sorted(events, key=lambda x: x['date'], reverse=True)


class UpdateApplicationStatusView(LoginRequiredMixin, View):
    """Enhanced view for updating application status"""

    def post(self, request, pk):
        application = get_object_or_404(JobApplication, id=pk, user=request.user)
        form = JobApplicationUpdateForm(request.POST, instance=application)

        if form.is_valid():
            updated_app = form.save()

            # Trigger workflow updates based on status change
            self._handle_status_change(updated_app)

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Application updated successfully',
                    'new_status': updated_app.get_application_status_display(),
                    'status_color': updated_app.get_status_display_color()
                })
            messages.success(request, 'Application status updated successfully!')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
            messages.error(request, 'Error updating application status')

        return redirect('jobs:application_detail', pk=pk)

    def _handle_status_change(self, application):
        """Handle automated actions based on status changes"""
        try:
            status_actions = {
                'applied': self._handle_applied_status,
                'interview': self._handle_interview_status,
                'offer_received': self._handle_offer_status,
                'hired': self._handle_hired_status,
                'rejected_automated': self._handle_rejection_status,
                'rejected_screening': self._handle_rejection_status,
                'rejected_interview': self._handle_rejection_status,
            }

            action = status_actions.get(application.application_status)
            if action:
                action(application)

        except Exception as e:
            # Log error but don't fail the update
            print(f"Error handling status change for application {application.id}: {str(e)}")

    def _handle_applied_status(self, application):
        """Actions when application is marked as applied"""
        if application.auto_follow_up_enabled and not application.next_follow_up_date:
            # Schedule first follow-up
            application.next_follow_up_date = timezone.now().date() + timezone.timedelta(days=7)
            application.follow_up_sequence_active = True
            application.save()

    def _handle_interview_status(self, application):
        """Actions when interview is scheduled"""
        # Could integrate with calendar systems
        # Send preparation materials
        pass

    def _handle_offer_status(self, application):
        """Actions when offer is received"""
        # Could trigger salary negotiation workflow
        # Send congratulations and next steps
        pass

    def _handle_hired_status(self, application):
        """Actions when hired"""
        # Deactivate other applications
        # Send success notifications
        # Update statistics
        pass

    def _handle_rejection_status(self, application):
        """Actions when application is rejected"""
        # Stop follow-up sequence
        application.follow_up_sequence_active = False
        application.next_follow_up_date = None
        application.save()


# API Views for N8N Integration

class N8NWebhookView(View):
    """Webhook endpoint for N8N to send job search results"""

    def post(self, request, webhook_type):
        try:
            import json
            data = json.loads(request.body)

            if webhook_type == 'job_discovery':
                return self._handle_job_discovery(data)
            elif webhook_type == 'document_generation':
                return self._handle_document_generation(data)
            elif webhook_type == 'email_update':
                return self._handle_email_update(data)
            elif webhook_type == 'status_update':
                return self._handle_status_update(data)
            else:
                return JsonResponse({'error': 'Invalid webhook type'}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    def _handle_job_discovery(self, data):
        """Handle job discovery results from N8N"""
        try:
            user_id = data.get('user_id')
            config_id = data.get('config_id')
            jobs = data.get('jobs', [])

            if not user_id or not jobs:
                return JsonResponse({'error': 'Missing required data'}, status=400)

            from django.contrib.auth.models import User
            user = User.objects.get(id=user_id)

            config = None
            if config_id:
                config = JobSearchConfig.objects.filter(id=config_id, user=user).first()

            created_count = 0
            updated_count = 0

            for job_data in jobs:
                # Create or update job application
                application, created = JobApplication.objects.get_or_create(
                    user=user,
                    job_url=job_data.get('job_url', ''),
                    defaults={
                        'search_config': config,
                        'job_title': job_data.get('job_title', ''),
                        'company_name': job_data.get('company_name', ''),
                        'job_description': job_data.get('job_description', ''),
                        'salary_range': job_data.get('salary_range', ''),
                        'location': job_data.get('location', ''),
                        'remote_option': job_data.get('remote_option', ''),
                        'application_source': job_data.get('source', 'other'),
                        'match_percentage': job_data.get('match_percentage', 0),
                        'company_rating': job_data.get('company_rating'),
                        'application_status': 'discovered',
                        'urgency_level': job_data.get('urgency_level', 'medium'),
                    }
                )

                if created:
                    created_count += 1
                else:
                    # Update existing application with new data
                    for field, value in job_data.items():
                        if hasattr(application, field) and value:
                            setattr(application, field, value)
                    application.save()
                    updated_count += 1

            # Update config statistics
            if config:
                config.total_jobs_found = F('total_jobs_found') + created_count
                config.last_search_date = timezone.now()
                config.save()

            return JsonResponse({
                'success': True,
                'created': created_count,
                'updated': updated_count,
                'total_processed': len(jobs)
            })

        except Exception as e:
            return JsonResponse({'error': f'Job discovery error: {str(e)}'}, status=500)

    def _handle_document_generation(self, data):
        """Handle document generation completion from N8N"""
        try:
            application_id = data.get('application_id')
            documents = data.get('documents', [])

            if not application_id:
                return JsonResponse({'error': 'Missing application_id'}, status=400)

            application = JobApplication.objects.get(id=application_id)

            # Update application with document information
            if documents:
                application.documents_generated = True
                application.documents_folder_path = data.get('folder_path', '')
                application.save()

            return JsonResponse({
                'success': True,
                'application_id': application_id,
                'documents_count': len(documents)
            })

        except JobApplication.DoesNotExist:
            return JsonResponse({'error': 'Application not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': f'Document generation error: {str(e)}'}, status=500)

    def _handle_email_update(self, data):
        """Handle email response updates from N8N"""
        try:
            application_id = data.get('application_id')
            email_type = data.get('email_type')  # 'response', 'interview_invite', 'rejection'
            email_content = data.get('email_content', '')

            if not application_id or not email_type:
                return JsonResponse({'error': 'Missing required data'}, status=400)

            application = JobApplication.objects.get(id=application_id)

            # Update application based on email type
            if email_type == 'response':
                application.application_status = 'responded'
            elif email_type == 'interview_invite':
                application.application_status = 'interview'
            elif email_type == 'rejection':
                application.application_status = 'rejected_automated'
                application.rejection_received = True
                application.follow_up_sequence_active = False

            # Add to notes
            if email_content:
                timestamp = timezone.now().strftime('%Y-%m-%d %H:%M')
                new_note = f"[{timestamp}] Email {email_type}: {email_content[:200]}..."
                if application.notes:
                    application.notes += f"\n\n{new_note}"
                else:
                    application.notes = new_note

            application.save()

            return JsonResponse({
                'success': True,
                'application_id': application_id,
                'new_status': application.application_status
            })

        except JobApplication.DoesNotExist:
            return JsonResponse({'error': 'Application not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': f'Email update error: {str(e)}'}, status=500)

    def _handle_status_update(self, data):
        """Handle general status updates from N8N workflows"""
        try:
            workflow_id = data.get('workflow_id')
            status = data.get('status')
            message = data.get('message', '')

            # Log the status update
            print(f"N8N Workflow {workflow_id} status: {status} - {message}")

            return JsonResponse({
                'success': True,
                'workflow_id': workflow_id,
                'status': status
            })

        except Exception as e:
            return JsonResponse({'error': f'Status update error: {str(e)}'}, status=500)


# Utility Views

class ConfigurationStatsView(LoginRequiredMixin, View):
    """API endpoint for configuration statistics"""

    def get(self, request, config_id):
        try:
            config = get_object_or_404(JobSearchConfig, id=config_id, user=request.user)
            applications = JobApplication.objects.filter(search_config=config)

            stats = {
                'total_jobs': applications.count(),
                'applied': applications.filter(application_status='applied').count(),
                'interviews': applications.filter(
                    application_status__in=['interview', 'first_interview', 'second_interview', 'final_interview']
                ).count(),
                'offers': applications.filter(application_status='offer_received').count(),
                'hired': applications.filter(application_status='hired').count(),
                'avg_match': applications.aggregate(avg=Avg('match_percentage'))['avg'] or 0,
                'last_search': config.last_search_date.isoformat() if config.last_search_date else None,
                'success_rate': 0
            }

            # Calculate success rate
            if stats['total_jobs'] > 0:
                success_count = stats['hired'] + stats['offers']
                stats['success_rate'] = round((success_count / stats['total_jobs']) * 100, 2)

            return JsonResponse(stats)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class ExportConfigurationView(LoginRequiredMixin, View):
    """Export configuration as JSON or CSV"""

    def get(self, request, config_id):
        config = get_object_or_404(JobSearchConfig, id=config_id, user=request.user)
        export_format = request.GET.get('format', 'json')

        if export_format == 'json':
            return self._export_json(config)
        elif export_format == 'csv':
            return self._export_csv(config)
        else:
            return JsonResponse({'error': 'Invalid format'}, status=400)

    def _export_json(self, config):
        import json

        config_data = {
            'config_name': config.config_name,
            'job_categories': config.job_categories,
            'target_locations': config.target_locations,
            'remote_preference': config.remote_preference,
            'salary_min': config.salary_min,
            'salary_max': config.salary_max,
            'salary_currency': config.salary_currency,
            'required_keywords': getattr(config, 'required_keywords', []),
            'excluded_keywords': getattr(config, 'excluded_keywords', []),
            'excluded_companies': getattr(config, 'excluded_companies', []),
            'auto_follow_up_enabled': config.auto_follow_up_enabled,
            'created_at': config.created_at.isoformat(),
            'export_date': timezone.now().isoformat()
        }

        response = HttpResponse(
            json.dumps(config_data, indent=2),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="job_config_{config.id}.json"'
        return response

    def _export_csv(self, config):
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['Field', 'Value'])

        # Write configuration data
        writer.writerow(['Configuration Name', config.config_name])
        writer.writerow(['Job Categories', '; '.join(config.job_categories)])
        writer.writerow(['Target Locations', '; '.join(config.target_locations)])
        writer.writerow(['Remote Preference', config.remote_preference])
        writer.writerow(['Salary Min', config.salary_min or ''])
        writer.writerow(['Salary Max', config.salary_max or ''])
        writer.writerow(['Salary Currency', config.salary_currency])
        writer.writerow(['Auto Follow-up', config.auto_follow_up_enabled])
        writer.writerow(['Created', config.created_at.strftime('%Y-%m-%d %H:%M:%S')])

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="job_config_{config.id}.csv"'
        return response


class SearchProgressView(LoginRequiredMixin, View):
    """Real-time search progress updates"""

    def get(self, request, search_id):
        # This would typically connect to a Redis cache or database
        # to get real-time progress updates from N8N workflows

        # Simulated progress data
        progress_data = {
            'search_id': search_id,
            'status': 'in_progress',
            'progress_percentage': 75,
            'current_step': 'Analyzing job descriptions',
            'jobs_found': 127,
            'high_matches': 23,
            'platforms_searched': 4,
            'estimated_completion': '2 minutes'
        }

        return JsonResponse(progress_data)


# Add these missing views to the end of your jobs/views.py file

class DuplicateConfigView(LoginRequiredMixin, View):
    """API endpoint for duplicating job search configurations"""

    def post(self, request, config_id):
        try:
            # Get the original configuration
            original_config = get_object_or_404(JobSearchConfig, id=config_id, user=request.user)

            # Get new name from request
            new_name = request.POST.get('new_name') or f"{original_config.config_name} (Copy)"

            # Create duplicate
            duplicate_config = JobSearchConfig.objects.create(
                user=request.user,
                config_name=new_name,
                job_categories=original_config.job_categories.copy(),
                target_locations=original_config.target_locations.copy(),
                remote_preference=original_config.remote_preference,
                salary_min=original_config.salary_min,
                salary_max=original_config.salary_max,
                salary_currency=original_config.salary_currency,
                required_keywords=getattr(original_config, 'required_keywords', []).copy() if hasattr(original_config,
                                                                                                      'required_keywords') else [],
                excluded_keywords=getattr(original_config, 'excluded_keywords', []).copy() if hasattr(original_config,
                                                                                                      'excluded_keywords') else [],
                excluded_companies=getattr(original_config, 'excluded_companies', []).copy() if hasattr(original_config,
                                                                                                        'excluded_companies') else [],
                auto_follow_up_enabled=original_config.auto_follow_up_enabled,
                is_active=False,  # Start as inactive
            )

            return JsonResponse({
                'success': True,
                'message': 'Configuration duplicated successfully',
                'new_config_id': duplicate_config.id,
                'new_config_name': duplicate_config.config_name
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error duplicating configuration: {str(e)}'
            }, status=500)


class ToggleConfigView(LoginRequiredMixin, View):
    """API endpoint for toggling configuration active/inactive status"""

    def post(self, request, config_id):
        try:
            config = get_object_or_404(JobSearchConfig, id=config_id, user=request.user)

            # Toggle the active status
            config.is_active = not config.is_active
            config.save()

            status_text = 'activated' if config.is_active else 'deactivated'

            return JsonResponse({
                'success': True,
                'message': f'Configuration {status_text} successfully',
                'is_active': config.is_active,
                'status_text': status_text
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error toggling configuration status: {str(e)}'
            }, status=500)


class ScheduleSearchView(LoginRequiredMixin, View):
    """API endpoint for scheduling automated searches"""

    def post(self, request, config_id):
        try:
            config = get_object_or_404(JobSearchConfig, id=config_id, user=request.user)

            # Get schedule parameters from request
            frequency = request.POST.get('frequency')  # daily, weekly, monthly
            start_time = request.POST.get('start_time')  # HH:MM format
            email_notifications = request.POST.get('email_notifications') == 'true'

            # Validate parameters
            if not frequency or not start_time:
                return JsonResponse({
                    'success': False,
                    'error': 'Missing required parameters: frequency and start_time'
                }, status=400)

            if frequency not in ['daily', 'weekly', 'monthly']:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid frequency. Must be daily, weekly, or monthly'
                }, status=400)

            # Update configuration with schedule settings
            config.search_frequency = frequency
            # You can add additional fields to your model for scheduling:
            # config.schedule_time = start_time
            # config.email_notifications = email_notifications
            config.save()

            # Here you would typically integrate with a task scheduler like Celery
            # or send the schedule to your N8N server
            schedule_data = {
                'config_id': config.id,
                'user_id': request.user.id,
                'frequency': frequency,
                'start_time': start_time,
                'email_notifications': email_notifications,
                'config_name': config.config_name
            }

            # Send to N8N for scheduling (optional)
            try:
                if hasattr(settings, 'N8N_WEBHOOK_URL'):
                    response = requests.post(
                        f"{settings.N8N_WEBHOOK_URL}/schedule-search",
                        json=schedule_data,
                        headers={'Authorization': f'Bearer {getattr(settings, "N8N_API_TOKEN", "")}'},
                        timeout=30
                    )
            except Exception as schedule_error:
                # Log the error but don't fail the request
                print(f"Warning: Could not schedule in N8N: {schedule_error}")

            return JsonResponse({
                'success': True,
                'message': f'Search scheduled successfully for {frequency} at {start_time}',
                'schedule': {
                    'frequency': frequency,
                    'start_time': start_time,
                    'email_notifications': email_notifications
                }
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error scheduling search: {str(e)}'
            }, status=500)