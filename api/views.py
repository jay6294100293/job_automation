# api/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import logging

from jobs.models import JobApplication, JobSearchConfig
from followups.models import FollowUpHistory, FollowUpTemplate
from accounts.models import UserProfile
from documents.models import GeneratedDocument
from .serializers import (
    JobApplicationSerializer, FollowUpHistorySerializer,
    UserProfileSerializer, JobSearchConfigSerializer
)

logger = logging.getLogger(__name__)


class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = JobApplicationSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return JobApplication.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        application = self.get_object()
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')

        if new_status in dict(JobApplication.STATUS_CHOICES):
            application.application_status = new_status
            if notes:
                application.notes = notes
            application.save()

            return Response({
                'success': True,
                'message': f'Status updated to {new_status}'
            })

        return Response({
            'success': False,
            'message': 'Invalid status'
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def mark_applied(self, request, pk=None):
        application = self.get_object()
        application.application_status = 'applied'
        application.applied_date = timezone.now()
        application.save()

        return Response({
            'success': True,
            'message': 'Marked as applied'
        })


class FollowUpViewSet(viewsets.ModelViewSet):
    serializer_class = FollowUpHistorySerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FollowUpHistory.objects.filter(
            application__user=self.request.user
        )


class UserProfileAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = request.user

        try:
            profile = UserProfile.objects.get(user=user)
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({
                'error': 'Profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class SearchConfigAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = request.user

        configs = JobSearchConfig.objects.filter(user=user, is_active=True)
        serializer = JobSearchConfigSerializer(configs, many=True)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class N8NJobSearchWebhook(APIView):
    """
    Webhook endpoint for n8n to send job search results
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            data = json.loads(request.body)
            logger.info(f"Received job search webhook: {data}")

            user_id = data.get('user_id')
            config_id = data.get('config_id')
            jobs_data = data.get('jobs', [])

            user = get_object_or_404(User, id=user_id)
            config = get_object_or_404(JobSearchConfig, id=config_id, user=user)

            created_count = 0
            for job_data in jobs_data:
                application, created = JobApplication.objects.get_or_create(
                    user=user,
                    job_title=job_data.get('job_title'),
                    company_name=job_data.get('company_name'),
                    defaults={
                        'search_config': config,
                        'job_url': job_data.get('job_url', ''),
                        'job_description': job_data.get('job_description', ''),
                        'salary_range': job_data.get('salary_range', ''),
                        'location': job_data.get('location', ''),
                        'remote_option': job_data.get('remote_option', ''),
                        'urgency_level': job_data.get('urgency_level', 'medium'),
                        'company_rating': job_data.get('company_rating'),
                        'glassdoor_rating': job_data.get('glassdoor_rating'),
                        'match_percentage': job_data.get('match_percentage'),
                        'skills_match_analysis': job_data.get('skills_match_analysis', ''),
                    }
                )

                if created:
                    created_count += 1
                    # Trigger document generation if enabled
                    if config.auto_follow_up_enabled:
                        application.follow_up_sequence_active = True
                        application.save()

            # Update config last search date
            config.last_search_date = timezone.now()
            config.save()

            return JsonResponse({
                'success': True,
                'message': f'Created {created_count} new job applications',
                'created_count': created_count
            })

        except Exception as e:
            logger.error(f"Error processing job search webhook: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class N8NFollowUpWebhook(APIView):
    """
    Webhook endpoint for n8n follow-up automation
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            data = json.loads(request.body)
            logger.info(f"Received follow-up webhook: {data}")

            action = data.get('action')
            user_id = data.get('user_id')

            user = get_object_or_404(User, id=user_id)

            if action == 'send_followup':
                return self._handle_single_followup(data, user)
            elif action == 'bulk_followup':
                return self._handle_bulk_followup(data, user)
            elif action == 'followup_response':
                return self._handle_followup_response(data, user)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Unknown action'
                }, status=400)

        except Exception as e:
            logger.error(f"Error processing follow-up webhook: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

    def _handle_single_followup(self, data, user):
        application_id = data.get('application_id')
        template_id = data.get('template_id')
        email_sent = data.get('email_sent', False)

        application = get_object_or_404(
            JobApplication,
            id=application_id,
            user=user
        )
        template = get_object_or_404(
            FollowUpTemplate,
            id=template_id,
            user=user
        )

        if email_sent:
            # Create follow-up history record
            FollowUpHistory.objects.create(
                application=application,
                template=template,
                subject=data.get('email_subject', ''),
                body=data.get('email_body', ''),
            )

            # Update application
            application.last_follow_up_date = timezone.now()
            application.follow_up_count += 1
            application.save()

            # Update template stats
            template.times_used += 1
            template.save()

        return JsonResponse({
            'success': True,
            'message': 'Follow-up recorded successfully'
        })

    def _handle_bulk_followup(self, data, user):
        application_ids = data.get('application_ids', [])
        template_id = data.get('template_id')
        emails_sent = data.get('emails_sent', [])

        template = get_object_or_404(
            FollowUpTemplate,
            id=template_id,
            user=user
        )

        sent_count = 0
        for email_data in emails_sent:
            application_id = email_data.get('application_id')
            application = get_object_or_404(
                JobApplication,
                id=application_id,
                user=user
            )

            # Create follow-up history
            FollowUpHistory.objects.create(
                application=application,
                template=template,
                subject=email_data.get('subject', ''),
                body=email_data.get('body', ''),
            )

            # Update application
            application.last_follow_up_date = timezone.now()
            application.follow_up_count += 1
            application.save()

            sent_count += 1

        # Update template stats
        template.times_used += sent_count
        template.save()

        return JsonResponse({
            'success': True,
            'message': f'Bulk follow-up completed for {sent_count} applications'
        })

    def _handle_followup_response(self, data, user):
        """Handle when a follow-up email receives a response"""
        application_id = data.get('application_id')
        response_type = data.get('response_type', 'neutral')
        response_content = data.get('response_content', '')

        application = get_object_or_404(
            JobApplication,
            id=application_id,
            user=user
        )

        # Update application status based on response
        if response_type == 'interview_invite':
            application.application_status = 'interview'
        elif response_type == 'positive':
            application.application_status = 'responded'
        elif response_type == 'rejection':
            application.application_status = 'rejected'
            application.rejection_received = True

        application.save()

        # Update follow-up history
        latest_followup = FollowUpHistory.objects.filter(
            application=application
        ).order_by('-sent_date').first()

        if latest_followup:
            latest_followup.response_received = True
            latest_followup.response_date = timezone.now()
            latest_followup.response_type = response_type
            latest_followup.notes = response_content
            latest_followup.save()

            # Update template success rate
            if latest_followup.template:
                template = latest_followup.template
                template.responses_received += 1
                template.calculate_success_rate()

        return JsonResponse({
            'success': True,
            'message': 'Response recorded successfully'
        })


@method_decorator(csrf_exempt, name='dispatch')
class N8NDocumentWebhook(APIView):
    """
    Webhook endpoint for n8n document generation results
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            data = json.loads(request.body)
            logger.info(f"Received document webhook: {data}")

            application_id = data.get('application_id')
            documents = data.get('documents', [])

            application = get_object_or_404(JobApplication, id=application_id)

            # Save generated documents
            for doc_data in documents:
                GeneratedDocument.objects.update_or_create(
                    application=application,
                    document_type=doc_data.get('type'),
                    defaults={
                        'file_path': doc_data.get('file_path'),
                        'content': doc_data.get('content', ''),
                        'file_size': doc_data.get('file_size', 0),
                    }
                )

            # Mark documents as generated
            application.documents_generated = True
            application.documents_folder_path = data.get('folder_path', '')
            application.save()

            return JsonResponse({
                'success': True,
                'message': f'Documents saved for {application.job_title}'
            })

        except Exception as e:
            logger.error(f"Error processing document webhook: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

