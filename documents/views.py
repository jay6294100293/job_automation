# documents/views.py
import json
import logging
import os
import zipfile
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse, FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, View, ListView

from accounts.models import UserProfile
from jobs.models import JobApplication, JobSearchConfig
from .models import GeneratedDocument, DocumentGenerationJob
from .tasks import generate_all_documents

logger = logging.getLogger(__name__)


class GenerateDocumentsView(LoginRequiredMixin, View):
    """Generate all documents for a specific job application"""

    def post(self, request, application_id):
        try:
            # Get the application
            application = get_object_or_404(
                JobApplication,
                id=application_id,
                user=request.user
            )

            # Check if documents are already being generated
            existing_job = DocumentGenerationJob.objects.filter(
                application=application,
                status__in=['pending', 'processing']
            ).first()

            if existing_job:
                return JsonResponse({
                    'success': False,
                    'message': 'Documents are already being generated for this application.',
                    'job_id': existing_job.id
                })

            # Check if user profile is complete enough
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                if user_profile.profile_completion_percentage < 50:
                    return JsonResponse({
                        'success': False,
                        'message': 'Please complete your profile (at least 50%) before generating documents.',
                        'redirect_url': reverse_lazy('accounts:profile')
                    })
            except UserProfile.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Please create your profile before generating documents.',
                    'redirect_url': reverse_lazy('accounts:profile')
                })

            # Start document generation task
            task = generate_all_documents.delay(application.id)

            # Create document generation job record
            DocumentGenerationJob.objects.create(
                application=application,
                status='pending'
            )

            logger.info(f"Started document generation for application {application.id}")

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Document generation started successfully.',
                    'task_id': task.id,
                    'estimated_time': '2-3 minutes'
                })
            else:
                messages.success(
                    request,
                    'Document generation started! You will be notified when complete.'
                )
                return redirect('jobs:application_detail', pk=application_id)

        except Exception as e:
            logger.error(f"Error starting document generation: {str(e)}")

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'Error starting document generation: {str(e)}'
                }, status=500)
            else:
                messages.error(request, 'Error starting document generation. Please try again.')
                return redirect('jobs:application_detail', pk=application_id)


class DownloadDocumentsView(LoginRequiredMixin, View):
    """Download all documents for a specific application as a ZIP file"""

    def get(self, request, application_id):
        try:
            # Get the application
            application = get_object_or_404(
                JobApplication,
                id=application_id,
                user=request.user
            )

            # Get generated documents
            documents = GeneratedDocument.objects.filter(application=application)

            if not documents.exists():
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'No documents found for this application.'
                    })
                else:
                    messages.error(request, 'No documents found for this application.')
                    return redirect('jobs:application_detail', pk=application_id)

            # Create ZIP file in memory
            zip_buffer = BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for document in documents:
                    if os.path.exists(document.file_path):
                        # Get the filename from the path
                        filename = os.path.basename(document.file_path)

                        # Add file to ZIP
                        zip_file.write(document.file_path, filename)
                    else:
                        # If file doesn't exist, create a text file with the content
                        if document.content:
                            filename = f"{document.get_document_type_display()}.txt"
                            zip_file.writestr(filename, document.content.encode('utf-8'))

            zip_buffer.seek(0)

            # Create response
            response = HttpResponse(
                zip_buffer.getvalue(),
                content_type='application/zip'
            )

            # Set filename
            filename = f"Documents_{application.company_name}_{application.job_title}_{timezone.now().strftime('%Y%m%d')}.zip"
            filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()

            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            logger.info(f"Downloaded documents for application {application.id}")
            return response

        except Exception as e:
            logger.error(f"Error downloading documents: {str(e)}")

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'Error downloading documents: {str(e)}'
                }, status=500)
            else:
                messages.error(request, 'Error downloading documents. Please try again.')
                return redirect('jobs:application_detail', pk=application_id)


class DownloadAllDocumentsView(LoginRequiredMixin, View):
    """Download all documents for a search configuration as a ZIP file"""

    def get(self, request, search_id):
        try:
            # Get the search configuration
            search_config = get_object_or_404(
                JobSearchConfig,
                id=search_id,
                user=request.user
            )

            # Get applications from this search
            applications = JobApplication.objects.filter(
                search_config=search_config,
                documents_generated=True
            )

            if not applications.exists():
                messages.error(request, 'No applications with documents found for this search.')
                return redirect('jobs:search_config')

            # Create ZIP file in memory
            zip_buffer = BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for application in applications:
                    documents = GeneratedDocument.objects.filter(application=application)

                    # Create folder for each application
                    app_folder = f"{application.company_name}_{application.job_title}/"
                    app_folder = "".join(c for c in app_folder if c.isalnum() or c in (' ', '-', '_', '/')).rstrip()

                    for document in documents:
                        if os.path.exists(document.file_path):
                            filename = os.path.basename(document.file_path)
                            zip_file.write(document.file_path, app_folder + filename)
                        elif document.content:
                            filename = f"{document.get_document_type_display()}.txt"
                            zip_file.writestr(app_folder + filename, document.content.encode('utf-8'))

            zip_buffer.seek(0)

            # Create response
            response = HttpResponse(
                zip_buffer.getvalue(),
                content_type='application/zip'
            )

            filename = f"All_Documents_{search_config.config_name}_{timezone.now().strftime('%Y%m%d')}.zip"
            filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()

            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            logger.info(f"Downloaded all documents for search {search_config.id}")
            return response

        except Exception as e:
            logger.error(f"Error downloading all documents: {str(e)}")
            messages.error(request, 'Error downloading documents. Please try again.')
            return redirect('jobs:search_config')


class PreviewDocumentView(LoginRequiredMixin, TemplateView):
    """Preview a specific document"""
    template_name = 'documents/preview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        application_id = kwargs.get('application_id')
        doc_type = kwargs.get('doc_type')

        try:
            # Get the application
            application = get_object_or_404(
                JobApplication,
                id=application_id,
                user=self.request.user
            )

            # Get the document
            document = get_object_or_404(
                GeneratedDocument,
                application=application,
                document_type=doc_type
            )

            context.update({
                'application': application,
                'document': document,
                'content': document.content,
                'file_exists': os.path.exists(document.file_path) if document.file_path else False
            })

        except Exception as e:
            logger.error(f"Error loading document preview: {str(e)}")
            context['error'] = str(e)

        return context


class DocumentListView(LoginRequiredMixin, ListView):
    """List all generated documents for the user"""
    model = GeneratedDocument
    template_name = 'documents/document_list.html'
    context_object_name = 'documents'
    paginate_by = 20

    def get_queryset(self):
        return GeneratedDocument.objects.filter(
            application__user=self.request.user
        ).select_related('application').order_by('-generated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get summary statistics
        total_documents = self.get_queryset().count()
        recent_documents = self.get_queryset().filter(
            generated_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).count()

        # Group by document type
        doc_types = self.get_queryset().values('document_type').annotate(
            count=models.Count('id')
        ).order_by('-count')

        context.update({
            'total_documents': total_documents,
            'recent_documents': recent_documents,
            'doc_types': doc_types,
        })

        return context



class DownloadSingleDocumentView(LoginRequiredMixin, View):
    """Download a single document file"""

    def get(self, request, application_id, doc_type):
        try:
            # Get the application
            application = get_object_or_404(
                JobApplication,
                id=application_id,
                user=request.user
            )

            # Get the document
            document = get_object_or_404(
                GeneratedDocument,
                application=application,
                document_type=doc_type
            )

            # Check if file exists
            if document.file_path and os.path.exists(document.file_path):
                # Serve the actual file
                response = FileResponse(
                    open(document.file_path, 'rb'),
                    as_attachment=True,
                    filename=os.path.basename(document.file_path)
                )
                return response

            elif document.content:
                # Serve content as text file
                response = HttpResponse(
                    document.content,
                    content_type='text/plain; charset=utf-8'
                )
                filename = f"{document.get_document_type_display()}_{application.company_name}.txt"
                filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response

            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Document file not found.'
                }, status=404)

        except Exception as e:
            logger.error(f"Error downloading single document: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error downloading document: {str(e)}'
            }, status=500)


class RegenerateDocumentView(LoginRequiredMixin, View):
    """Regenerate a specific document"""

    def post(self, request, application_id, doc_type):
        try:
            application = get_object_or_404(
                JobApplication,
                id=application_id,
                user=request.user
            )

            # Check if this document type is valid
            valid_types = [choice[0] for choice in GeneratedDocument.DOCUMENT_TYPES]
            if doc_type not in valid_types:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid document type.'
                }, status=400)

            # Import the specific task for this document type
            from .tasks import (
                generate_resume, generate_cover_letter, generate_email_templates,
                generate_linkedin_messages, generate_video_script,
                generate_company_research, generate_followup_schedule,
                generate_skills_analysis
            )

            task_map = {
                'resume': generate_resume,
                'cover_letter': generate_cover_letter,
                'email_templates': generate_email_templates,
                'linkedin_messages': generate_linkedin_messages,
                'video_script': generate_video_script,
                'company_research': generate_company_research,
                'followup_schedule': generate_followup_schedule,
                'skills_analysis': generate_skills_analysis,
            }

            if doc_type not in task_map:
                return JsonResponse({
                    'success': False,
                    'message': 'Document regeneration not supported for this type.'
                }, status=400)

            # Get user profile
            user_profile = UserProfile.objects.get(user=request.user)

            # Start regeneration task
            if doc_type in ['resume', 'cover_letter', 'email_templates', 'linkedin_messages', 'video_script',
                            'skills_analysis']:
                task = task_map[doc_type].delay(application.id, user_profile.id)
            else:
                task = task_map[doc_type].delay(application.id)

            logger.info(f"Started regeneration of {doc_type} for application {application.id}")

            return JsonResponse({
                'success': True,
                'message': f'{doc_type.replace("_", " ").title()} regeneration started.',
                'task_id': task.id
            })

        except Exception as e:
            logger.error(f"Error regenerating document: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error regenerating document: {str(e)}'
            }, status=500)


class BulkDocumentActionView(LoginRequiredMixin, View):
    """Handle bulk actions on documents"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            action = data.get('action')
            document_ids = data.get('document_ids', [])

            if not document_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'No documents selected.'
                })

            # Get documents belonging to the user
            documents = GeneratedDocument.objects.filter(
                id__in=document_ids,
                application__user=request.user
            )

            if action == 'delete':
                # Delete selected documents
                deleted_count = 0
                for doc in documents:
                    if doc.file_path and os.path.exists(doc.file_path):
                        try:
                            os.remove(doc.file_path)
                        except OSError:
                            pass
                    doc.delete()
                    deleted_count += 1

                return JsonResponse({
                    'success': True,
                    'message': f'Deleted {deleted_count} documents.'
                })

            elif action == 'download':
                # Create ZIP of selected documents
                zip_buffer = BytesIO()

                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for doc in documents:
                        if os.path.exists(doc.file_path):
                            filename = f"{doc.application.company_name}_{doc.get_document_type_display()}_{os.path.basename(doc.file_path)}"
                            filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
                            zip_file.write(doc.file_path, filename)
                        elif doc.content:
                            filename = f"{doc.application.company_name}_{doc.get_document_type_display()}.txt"
                            filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
                            zip_file.writestr(filename, doc.content.encode('utf-8'))

                zip_buffer.seek(0)

                response = HttpResponse(
                    zip_buffer.getvalue(),
                    content_type='application/zip'
                )
                filename = f"Selected_Documents_{timezone.now().strftime('%Y%m%d')}.zip"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'

                return response

            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action.'
                }, status=400)

        except Exception as e:
            logger.error(f"Error in bulk document action: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error performing action: {str(e)}'
            }, status=500)



class DocumentStatusView(LoginRequiredMixin, View):
    """Check document generation status via AJAX"""

    def get(self, request, application_id):
        try:
            application = get_object_or_404(
                JobApplication,
                id=application_id,
                user=request.user
            )

            # Check document generation job status
            generation_job = DocumentGenerationJob.objects.filter(
                application=application
            ).order_by('-started_at').first()

            # Get generated documents
            documents = GeneratedDocument.objects.filter(
                application=application
            ).values('document_type', 'generated_at', 'file_size')

            status_data = {
                'application_id': application_id,
                'job_status': generation_job.status if generation_job else 'not_started',
                'started_at': generation_job.started_at.isoformat() if generation_job else None,
                'completed_at': generation_job.completed_at.isoformat() if generation_job and generation_job.completed_at else None,
                'error_message': generation_job.error_message if generation_job else None,
                'documents': list(documents),
                'total_documents': documents.count()
            }

            return JsonResponse(status_data)

        except Exception as e:
            logger.error(f"Error checking document status: {str(e)}")
            return JsonResponse({
                'error': str(e)
            }, status=500)


class ApplicationDocumentsView(LoginRequiredMixin, ListView):
    """List all documents for a specific application"""
    model = GeneratedDocument
    template_name = 'documents/application_documents.html'
    context_object_name = 'documents'
    paginate_by = 10

    def get_queryset(self):
        application_id = self.kwargs.get('application_id')
        return GeneratedDocument.objects.filter(
            application_id=application_id,
            application__user=self.request.user
        ).order_by('-generated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application_id = self.kwargs.get('application_id')

        try:
            application = get_object_or_404(
                JobApplication,
                id=application_id,
                user=self.request.user
            )
            context['application'] = application

            # Get generation job status
            generation_job = DocumentGenerationJob.objects.filter(
                application=application
            ).order_by('-started_at').first()
            context['generation_job'] = generation_job

            # Document type completion status
            all_types = dict(GeneratedDocument.DOCUMENT_TYPES)
            existing_types = set(self.get_queryset().values_list('document_type', flat=True))
            missing_types = set(all_types.keys()) - existing_types

            context.update({
                'all_document_types': all_types,
                'existing_types': existing_types,
                'missing_types': missing_types,
                'completion_percentage': (len(existing_types) / len(all_types)) * 100
            })

        except Exception as e:
            logger.error(f"Error loading application documents: {str(e)}")
            context['error'] = str(e)

        return context


class DownloadOptionsView(LoginRequiredMixin, TemplateView):
    """Show download options for documents"""
    template_name = 'documents/download_options.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get user's recent applications with documents
        recent_applications = JobApplication.objects.filter(
            user=self.request.user,
            generateddocument__isnull=False
        ).distinct().order_by('-created_at')[:10]

        # Get user's search configurations
        search_configs = JobSearchConfig.objects.filter(
            user=self.request.user
        ).order_by('-last_search_date')[:5]

        # Get document statistics
        total_documents = GeneratedDocument.objects.filter(
            application__user=self.request.user
        ).count()

        recent_documents = GeneratedDocument.objects.filter(
            application__user=self.request.user,
            generated_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).count()

        context.update({
            'recent_applications': recent_applications,
            'search_configs': search_configs,
            'total_documents': total_documents,
            'recent_documents': recent_documents
        })

        return context