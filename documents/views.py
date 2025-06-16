# documents/views.py
import logging
import os
import tempfile
import zipfile

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, TemplateView, View
from requests import request

from jobs.models import JobApplication
from .models import GeneratedDocument, DocumentGenerationJob
from .tasks import generate_all_documents, generate_single_document

logger = logging.getLogger(__name__)


class DocumentListView(LoginRequiredMixin, ListView):
    model = GeneratedDocument
    template_name = 'documents/list.html'
    context_object_name = 'documents'
    paginate_by = 20

    def get_queryset(self):
        return GeneratedDocument.objects.filter(
            application__user=self.request.user
        ).order_by('-generated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Document statistics
        user_docs = GeneratedDocument.objects.filter(application__user=self.request.user)
        context['total_documents'] = user_docs.count()
        context['document_types'] = user_docs.values('document_type').distinct().count()

        # Recent generation jobs
        context['recent_jobs'] = DocumentGenerationJob.objects.filter(
            application__user=self.request.user
        ).order_by('-started_at')[:5]

        return context


class DocumentPreviewView(LoginRequiredMixin, DetailView):
    model = GeneratedDocument
    template_name = 'documents/preview.html'
    context_object_name = 'document'

    def get_queryset(self):
        return GeneratedDocument.objects.filter(application__user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document = self.object

        # Read file content for preview
        try:
            if document.file_path and os.path.exists(document.file_path):
                with open(document.file_path, 'r', encoding='utf-8') as f:
                    context['file_content'] = f.read()
            else:
                context['file_content'] = document.content
        except Exception as e:
            logger.error(f"Error reading document file: {e}")
            context['file_content'] = document.content or "Content not available"

        # Related documents for the same job application
        context['related_documents'] = GeneratedDocument.objects.filter(
            application=document.application
        ).exclude(id=document.id)

        return context


class DocumentDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        document = get_object_or_404(
            GeneratedDocument,
            pk=pk,
            application__user=request.user
        )

        if not document.file_path or not os.path.exists(document.file_path):
            messages.error(request, 'Document file not found.')
            return redirect('documents:list')

        try:
            response = FileResponse(
                open(document.file_path, 'rb'),
                as_attachment=True,
                filename=os.path.basename(document.file_path)
            )
            return response
        except Exception as e:
            logger.error(f"Error downloading document: {e}")
            messages.error(request, 'Error downloading document.')
            return redirect('documents:list')


class BulkDownloadView(LoginRequiredMixin, View):
    def post(self, request):
        application_id = request.POST.get('application_id')
        document_ids = request.POST.getlist('document_ids')

        if application_id:
            # Download all documents for a specific application
            application = get_object_or_404(
                JobApplication,
                pk=application_id,
                user=request.user
            )
            documents = GeneratedDocument.objects.filter(application=application)
            zip_filename = f"{application.company_name}_{application.job_title}_documents.zip"
        elif document_ids:
            # Download selected documents
            documents = GeneratedDocument.objects.filter(
                pk__in=document_ids,
                application__user=request.user
            )
            zip_filename = "selected_documents.zip"
        else:
            messages.error(request, 'No documents selected.')
            return redirect('documents:list')

        # Create ZIP file
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                with zipfile.ZipFile(tmp_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for document in documents:
                        if document.file_path and os.path.exists(document.file_path):
                            # Add file to zip with organized folder structure
                            arcname = f"{document.application.company_name}/{os.path.basename(document.file_path)}"
                            zip_file.write(document.file_path, arcname)
                        elif document.content:
                            # Add content as text file
                            file_ext = 'txt'
                            if document.document_type in ['resume', 'cover_letter', 'company_research']:
                                file_ext = 'pdf'

                            filename = f"{document.get_document_type_display()}.{file_ext}"
                            arcname = f"{document.application.company_name}/{filename}"
                            zip_file.writestr(arcname, document.content.encode('utf-8'))

                # Return ZIP file as response
                response = FileResponse(
                    open(tmp_file.name, 'rb'),
                    as_attachment=True,
                    filename=zip_filename
                )

                # Clean up temp file after response
                def cleanup():
                    try:
                        os.unlink(tmp_file.name)
                    except:
                        pass

                response.cleanup = cleanup
                return response

        except Exception as e:
            logger.error(f"Error creating ZIP file: {e}")
            messages.error(request, 'Error creating download archive.')
            return redirect('documents:list')


class GenerateDocumentsView(LoginRequiredMixin, View):
    def post(self, request, application_id):
        application = get_object_or_404(
            JobApplication,
            pk=application_id,
            user=request.user
        )

        # Check if documents are already being generated
        existing_job = DocumentGenerationJob.objects.filter(
            application=application,
            status__in=['pending', 'processing']
        ).first()

        if existing_job:
            messages.warning(request, 'Documents are already being generated for this application.')
            return redirect('jobs:application_detail', pk=application_id)

        # Start document generation
        try:
            job = DocumentGenerationJob.objects.create(
                application=application,
                status='pending'
            )

            # Queue the generation task
            generate_all_documents.delay(application.id)

            messages.success(request, 'Document generation started! You will be notified when complete.')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Document generation started',
                    'job_id': job.id
                })

        except Exception as e:
            logger.error(f"Error starting document generation: {e}")
            messages.error(request, 'Error starting document generation.')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=500)

        return redirect('jobs:application_detail', pk=application_id)


class DocumentGenerationStatusView(LoginRequiredMixin, View):
    def get(self, request, job_id):
        job = get_object_or_404(
            DocumentGenerationJob,
            pk=job_id,
            application__user=request.user
        )

        data = {
            'status': job.status,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'error_message': job.error_message
        }

        if job.status == 'completed':
            data['documents_count'] = GeneratedDocument.objects.filter(
                application=job.application
            ).count()
            data['download_url'] = reverse_lazy('documents:bulk_download') + f'?application_id={job.application.id}'

        return JsonResponse(data)


class DocumentDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        document = get_object_or_404(
            GeneratedDocument,
            pk=pk,
            application__user=request.user
        )

        try:
            # Delete physical file
            if document.file_path and os.path.exists(document.file_path):
                os.remove(document.file_path)

            # Delete database record
            document.delete()

            messages.success(request, 'Document deleted successfully.')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})

        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            messages.error(request, 'Error deleting document.')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)}, status=500)

        return redirect('documents:list')


class DocumentRegenerateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        document = get_object_or_404(
            GeneratedDocument,
            pk=pk,
            application__user=request.user
        )

        try:
            # Delete existing document
            if document.file_path and os.path.exists(document.file_path):
                os.remove(document.file_path)

            document.delete()

            # Regenerate specific document type

            generate_single_document.delay(
                document.application.id,
                document.document_type
            )

            messages.success(request, f'{document.get_document_type_display()} is being regenerated.')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})

        except Exception as e:
            logger.error(f"Error regenerating document: {e}")
            messages.error(request, 'Error regenerating document.')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)}, status=500)

        return redirect('documents:list')


class ApplicationDocumentsView(LoginRequiredMixin, TemplateView):
    template_name = 'documents/application_documents.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application_id = kwargs.get('application_id')

        application = get_object_or_404(
            JobApplication,
            pk=application_id,
            user=self.request.user
        )

        context['application'] = application
        context['documents'] = GeneratedDocument.objects.filter(
            application=application
        ).order_by('document_type')

        # Group documents by type for better display
        documents_by_type = {}
        for doc in context['documents']:
            doc_type = doc.get_document_type_display()
            if doc_type not in documents_by_type:
                documents_by_type[doc_type] = []
            documents_by_type[doc_type].append(doc)

        context['documents_by_type'] = documents_by_type

        # Generation status
        context['generation_job'] = DocumentGenerationJob.objects.filter(
            application=application
        ).order_by('-started_at').first()

        return context


class DocumentStatsView(LoginRequiredMixin, TemplateView):
    template_name = 'documents/stats.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Document statistics
        documents = GeneratedDocument.objects.filter(application__user=user)

        context['total_documents'] = documents.count()
        context['total_applications'] = documents.values('application').distinct().count()

        # Documents by type
        context['documents_by_type'] = {}
        for doc_type, display_name in GeneratedDocument.DOCUMENT_TYPES:
            count = documents.filter(document_type=doc_type).count()
            if count > 0:
                context['documents_by_type'][display_name] = count

        # Recent generation activity
        context['recent_generations'] = DocumentGenerationJob.objects.filter(
            application__user=user
        ).order_by('-started_at')[:10]

        # Storage usage
        total_size = sum(doc.file_size for doc in documents if doc.file_size)
        context['storage_used'] = total_size
        context['storage_used_mb'] = round(total_size / (1024 * 1024), 2)

        return context


class BulkDocumentActionsView(LoginRequiredMixin, View):
    def post(self, request):
        action = request.POST.get('action')
        document_ids = request.POST.getlist('document_ids')

        if not document_ids:
            messages.error(request, 'No documents selected.')
            return redirect('documents:list')

        documents = GeneratedDocument.objects.filter(
            pk__in=document_ids,
            application__user=request.user
        )

        if action == 'delete':
            count = 0
            for document in documents:
                try:
                    if document.file_path and os.path.exists(document.file_path):
                        os.remove(document.file_path)
                    document.delete()
                    count += 1
                except Exception as e:
                    logger.error(f"Error deleting document {document.id}: {e}")

            messages.success(request, f'Deleted {count} documents.')

        elif action == 'download':
            return self._bulk_download(documents)

        elif action == 'regenerate':
            count = 0
            for document in documents:
                try:

                    generate_single_document.delay(
                        document.application.id,
                        document.document_type
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Error regenerating document {document.id}: {e}")

            messages.success(request, f'Regeneration started for {count} documents.')

        return redirect('documents:list')

    def _bulk_download(self, documents):
        """Handle bulk download of documents"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                with zipfile.ZipFile(tmp_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for document in documents:
                        if document.file_path and os.path.exists(document.file_path):
                            arcname = f"{document.application.company_name}_{document.application.job_title}/{os.path.basename(document.file_path)}"
                            zip_file.write(document.file_path, arcname)

                response = FileResponse(
                    open(tmp_file.name, 'rb'),
                    as_attachment=True,
                    filename="bulk_documents.zip"
                )
                return response

        except Exception as e:
            logger.error(f"Error creating bulk download: {e}")
            messages.error(request, 'Error creating download archive.')
            return redirect('documents:list')