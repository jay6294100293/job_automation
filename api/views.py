# api/views.py - COMPLETE FILE with Error Handling
# REPLACE your entire api/views.py file with this version

import json
import logging
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db import connection

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token

from jobs.models import JobApplication, JobSearchConfig
from followups.models import FollowUpHistory, FollowUpTemplate
from accounts.models import UserProfile
from documents.models import GeneratedDocument
from .exceptions import CustomAPIException, JobApplicationNotFound, FollowUpError, DocumentGenerationError
from .serializers import (
    JobApplicationSerializer, FollowUpHistorySerializer,
    UserProfileSerializer, JobSearchConfigSerializer, FollowUpTemplateSerializer
)


logger = logging.getLogger(__name__)


class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = JobApplicationSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return JobApplication.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Create application with validation"""
        try:
            serializer.save(user=self.request.user)
        except Exception as e:
            logger.error(f"Error creating application: {str(e)}")
            raise CustomAPIException(
                detail="Failed to create job application",
                code="creation_failed"
            )

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update application status with business logic validation"""
        try:
            application = self.get_object()
            new_status = request.data.get('status')
            notes = request.data.get('notes', '')

            if not new_status:
                raise CustomAPIException(
                    detail="Status is required",
                    code="missing_status"
                )

            if new_status not in dict(JobApplication.STATUS_CHOICES):
                valid_statuses = ', '.join(dict(JobApplication.STATUS_CHOICES).keys())
                raise CustomAPIException(
                    detail=f"Invalid status '{new_status}'. Valid options are: {valid_statuses}",
                    code="invalid_status"
                )

            # Business logic validation
            if application.application_status == 'hired' and new_status != 'hired':
                raise CustomAPIException(
                    detail="Cannot change status from 'hired' to another status",
                    code="invalid_status_transition"
                )

            application.application_status = new_status
            if notes:
                application.notes = notes
            application.save()

            return Response({
                'success': True,
                'message': f'Status updated to {new_status}',
                'application': JobApplicationSerializer(application).data
            })

        except JobApplication.DoesNotExist:
            raise JobApplicationNotFound(
                detail=f"Job application with ID {pk} not found"
            )
        except CustomAPIException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating application status: {str(e)}")
            raise CustomAPIException(
                detail="An error occurred while updating the application status",
                code="update_failed"
            )

    @action(detail=True, methods=['post'])
    def mark_applied(self, request, pk=None):
        """Mark application as applied with validation"""
        try:
            application = self.get_object()

            if application.application_status != 'found':
                raise CustomAPIException(
                    detail=f"Cannot mark application as applied. Current status is '{application.application_status}'. Only applications with 'found' status can be marked as applied.",
                    code="invalid_status_for_applied"
                )

            application.application_status = 'applied'
            application.applied_date = timezone.now()
            application.save()

            return Response({
                'success': True,
                'message': f'Application for {application.job_title} at {application.company_name} marked as applied',
                'application': JobApplicationSerializer(application).data
            })

        except JobApplication.DoesNotExist:
            raise JobApplicationNotFound(
                detail=f"Job application with ID {pk} not found"
            )
        except CustomAPIException:
            raise
        except Exception as e:
            logger.error(f"Error marking application as applied: {str(e)}")
            raise CustomAPIException(
                detail="Failed to mark application as applied",
                code="mark_applied_failed"
            )


class FollowUpViewSet(viewsets.ModelViewSet):
    serializer_class = FollowUpHistorySerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FollowUpHistory.objects.filter(
            application__user=self.request.user
        )

    def perform_create(self, serializer):
        """Create follow-up with business logic validation"""
        try:
            application = serializer.validated_data.get('application')

            # Validate application belongs to user
            if application.user != self.request.user:
                raise CustomAPIException(
                    detail="You can only create follow-ups for your own applications",
                    code="permission_denied",
                    status_code=403
                )

            if application.application_status not in ['applied', 'responded']:
                raise FollowUpError(
                    detail=f"Cannot send follow-up for application with status '{application.application_status}'. Application must be 'applied' or 'responded'.",
                    code="invalid_followup_status"
                )

            # Check if follow-up was sent recently (prevent spam)
            if application.last_follow_up_date:
                days_since_last = (timezone.now().date() - application.last_follow_up_date.date()).days
                if days_since_last < 3:
                    raise FollowUpError(
                        detail=f"Follow-up was sent {days_since_last} days ago. Please wait at least 3 days between follow-ups.",
                        code="followup_too_soon"
                    )

            # Save the follow-up
            followup = serializer.save()

            # Update application follow-up tracking
            application.last_follow_up_date = timezone.now()
            application.follow_up_count += 1
            application.next_follow_up_date = (timezone.now() + timedelta(days=7)).date()
            application.save()

            logger.info(f"Follow-up created for application {application.id}")

        except CustomAPIException:
            raise
        except FollowUpError:
            raise
        except Exception as e:
            logger.error(f"Error creating follow-up: {str(e)}")
            raise FollowUpError(
                detail="Failed to create follow-up record"
            )


class UserProfileAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        """Get user profile with validation"""
        try:
            if user_id:
                if user_id != request.user.id:
                    raise CustomAPIException(
                        detail="You can only access your own profile",
                        code="permission_denied",
                        status_code=403
                    )
                user = get_object_or_404(User, id=user_id)
            else:
                user = request.user

            try:
                profile = UserProfile.objects.get(user=user)
                serializer = UserProfileSerializer(profile)
                return Response({
                    'success': True,
                    'profile': serializer.data
                })
            except UserProfile.DoesNotExist:
                raise CustomAPIException(
                    detail="User profile not found. Please create your profile first.",
                    code="profile_not_found",
                    status_code=404
                )

        except CustomAPIException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving user profile: {str(e)}")
            raise CustomAPIException(
                detail="Failed to retrieve user profile",
                code="profile_retrieval_failed"
            )


class SearchConfigAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        """Get search configurations with validation"""
        try:
            if user_id:
                if user_id != request.user.id:
                    raise CustomAPIException(
                        detail="You can only access your own search configurations",
                        code="permission_denied",
                        status_code=403
                    )
                user = get_object_or_404(User, id=user_id)
            else:
                user = request.user

            configs = JobSearchConfig.objects.filter(user=user, is_active=True)
            serializer = JobSearchConfigSerializer(configs, many=True)

            return Response({
                'success': True,
                'count': configs.count(),
                'configs': serializer.data
            })

        except CustomAPIException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving search configurations: {str(e)}")
            raise CustomAPIException(
                detail="Failed to retrieve search configurations",
                code="search_config_retrieval_failed"
            )


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

            # Validate required data
            if not user_id:
                raise CustomAPIException(
                    detail="user_id is required",
                    code="missing_user_id"
                )

            if not config_id:
                raise CustomAPIException(
                    detail="config_id is required",
                    code="missing_config_id"
                )

            if not jobs_data:
                raise CustomAPIException(
                    detail="jobs array cannot be empty",
                    code="empty_jobs_data"
                )

            try:
                user = User.objects.get(id=user_id)
                config = JobSearchConfig.objects.get(id=config_id, user=user)
            except User.DoesNotExist:
                raise CustomAPIException(
                    detail=f"User with ID {user_id} not found",
                    code="user_not_found",
                    status_code=404
                )
            except JobSearchConfig.DoesNotExist:
                raise CustomAPIException(
                    detail=f"Search configuration with ID {config_id} not found",
                    code="config_not_found",
                    status_code=404
                )

            created_count = 0
            for job_data in jobs_data:
                try:
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
                        if config.auto_follow_up_enabled:
                            application.follow_up_sequence_active = True
                            application.save()

                except Exception as e:
                    logger.warning(f"Error creating job application: {str(e)}")
                    continue

            # Update config last search date
            config.last_search_date = timezone.now()
            config.save()

            return JsonResponse({
                'success': True,
                'message': f'Created {created_count} new job applications',
                'created_count': created_count,
                'total_processed': len(jobs_data)
            })

        except json.JSONDecodeError:
            raise CustomAPIException(
                detail="Invalid JSON payload",
                code="invalid_json"
            )
        except CustomAPIException:
            raise
        except Exception as e:
            logger.error(f"Error processing job search webhook: {str(e)}")
            raise CustomAPIException(
                detail="Failed to process job search webhook",
                code="webhook_processing_failed",
                status_code=500
            )


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

            webhook_type = data.get('type', 'send_followup')

            if webhook_type == 'send_followup':
                return self._handle_send_followup(data)
            elif webhook_type == 'record_response':
                return self._handle_record_response(data)
            elif webhook_type == 'bulk_followup':
                return self._handle_bulk_followup(data)
            else:
                raise CustomAPIException(
                    detail=f"Unknown webhook type: {webhook_type}",
                    code="unknown_webhook_type"
                )

        except json.JSONDecodeError:
            raise CustomAPIException(
                detail="Invalid JSON payload",
                code="invalid_json"
            )
        except CustomAPIException:
            raise
        except Exception as e:
            logger.error(f"Error processing follow-up webhook: {str(e)}")
            raise FollowUpError(
                detail="Failed to process follow-up webhook"
            )

    def _handle_send_followup(self, data):
        """Handle individual follow-up email sending"""
        application_id = data.get('application_id')
        template_id = data.get('template_id')
        custom_subject = data.get('custom_subject')
        custom_body = data.get('custom_body')

        if not application_id:
            raise CustomAPIException(
                detail="application_id is required",
                code="missing_application_id"
            )

        try:
            application = JobApplication.objects.get(id=application_id)

            template = None
            if template_id:
                try:
                    template = FollowUpTemplate.objects.get(id=template_id)
                except FollowUpTemplate.DoesNotExist:
                    raise CustomAPIException(
                        detail=f"Template with ID {template_id} not found",
                        code="template_not_found",
                        status_code=404
                    )

            followup = FollowUpHistory.objects.create(
                application=application,
                template=template,
                subject=custom_subject or (template.subject_template if template else 'Follow-up'),
                body=custom_body or (template.body_template if template else ''),
                sent_date=timezone.now()
            )

            application.last_follow_up_date = timezone.now()
            application.follow_up_count += 1
            application.next_follow_up_date = (timezone.now() + timedelta(days=7)).date()
            application.save()

            if template:
                template.times_used += 1
                template.save()

            logger.info(f"Follow-up sent for application {application.id}")

            return JsonResponse({
                'success': True,
                'message': f'Follow-up sent for {application.job_title} at {application.company_name}',
                'followup_id': followup.id,
                'application_id': application.id
            })

        except JobApplication.DoesNotExist:
            raise JobApplicationNotFound(
                detail=f"Application with ID {application_id} not found"
            )

    def _handle_bulk_followup(self, data):
        """Handle bulk follow-up email sending"""
        applications_data = data.get('applications', [])
        template_id = data.get('template_id')

        if not applications_data:
            raise CustomAPIException(
                detail="applications array is required",
                code="missing_applications"
            )

        results = []
        successful_count = 0
        failed_count = 0

        template = None
        if template_id:
            try:
                template = FollowUpTemplate.objects.get(id=template_id)
            except FollowUpTemplate.DoesNotExist:
                raise CustomAPIException(
                    detail=f"Template with ID {template_id} not found",
                    code="template_not_found",
                    status_code=404
                )

        for app_data in applications_data:
            try:
                application_id = app_data.get('application_id')
                application = JobApplication.objects.get(id=application_id)

                followup = FollowUpHistory.objects.create(
                    application=application,
                    template=template,
                    subject=app_data.get('subject', template.subject_template if template else 'Follow-up'),
                    body=app_data.get('body', template.body_template if template else ''),
                    sent_date=timezone.now()
                )

                application.last_follow_up_date = timezone.now()
                application.follow_up_count += 1
                application.next_follow_up_date = (timezone.now() + timedelta(days=7)).date()
                application.save()

                successful_count += 1
                results.append({
                    'application_id': application_id,
                    'success': True,
                    'followup_id': followup.id
                })

            except JobApplication.DoesNotExist:
                failed_count += 1
                results.append({
                    'application_id': app_data.get('application_id'),
                    'success': False,
                    'error': 'Application not found'
                })
            except Exception as e:
                failed_count += 1
                results.append({
                    'application_id': app_data.get('application_id'),
                    'success': False,
                    'error': str(e)
                })

        if template and successful_count > 0:
            template.times_used += successful_count
            template.save()

        return JsonResponse({
            'success': True,
            'message': f'Bulk follow-up completed: {successful_count} sent, {failed_count} failed',
            'total_processed': len(applications_data),
            'successful_count': successful_count,
            'failed_count': failed_count,
            'results': results
        })

    def _handle_record_response(self, data):
        """Handle recording follow-up responses"""
        followup_id = data.get('followup_id')
        application_id = data.get('application_id')
        response_type = data.get('response_type', 'positive')
        response_content = data.get('response_content', '')

        if not (followup_id or application_id):
            raise CustomAPIException(
                detail="Either followup_id or application_id is required",
                code="missing_identifiers"
            )

        try:
            if followup_id:
                followup = FollowUpHistory.objects.get(id=followup_id)
                application = followup.application
            else:
                application = JobApplication.objects.get(id=application_id)
                followup = FollowUpHistory.objects.filter(
                    application=application
                ).order_by('-sent_date').first()

                if not followup:
                    raise CustomAPIException(
                        detail="No follow-up history found for this application",
                        code="no_followup_history",
                        status_code=404
                    )

            followup.response_received = True
            followup.response_date = timezone.now()
            followup.response_type = response_type
            followup.notes = response_content
            followup.save()

            # Update application status based on response
            if response_type == 'interview_invite':
                application.application_status = 'interview'
            elif response_type == 'positive':
                application.application_status = 'responded'
            elif response_type == 'negative':
                application.application_status = 'rejected'

            application.save()

            if followup.template:
                template = followup.template
                template.responses_received += 1
                if template.times_used > 0:
                    template.success_rate = (template.responses_received / template.times_used) * 100
                template.save()

            return JsonResponse({
                'success': True,
                'message': f'Response recorded for {application.job_title} at {application.company_name}',
                'followup_id': followup.id,
                'application_id': application.id,
                'response_type': response_type,
                'new_status': application.application_status
            })

        except FollowUpHistory.DoesNotExist:
            raise CustomAPIException(
                detail=f"Follow-up with ID {followup_id} not found",
                code="followup_not_found",
                status_code=404
            )
        except JobApplication.DoesNotExist:
            raise JobApplicationNotFound(
                detail=f"Application with ID {application_id} not found"
            )

    def get(self, request):
        """GET request returns webhook documentation"""
        return JsonResponse({
            'webhook': 'N8N Follow-up Automation',
            'method': 'POST',
            'description': 'Handles follow-up email automation and response tracking',
            'supported_types': {
                'send_followup': 'Send individual follow-up email',
                'bulk_followup': 'Send multiple follow-up emails',
                'record_response': 'Record company response to follow-up'
            },
            'payload_examples': {
                'send_followup': {
                    'type': 'send_followup',
                    'application_id': 123,
                    'template_id': 456,
                    'custom_subject': 'Following up on my application',
                    'custom_body': 'Hi, I wanted to follow up...'
                },
                'bulk_followup': {
                    'type': 'bulk_followup',
                    'template_id': 456,
                    'applications': [{'application_id': 123, 'subject': 'Custom subject'}]
                },
                'record_response': {
                    'type': 'record_response',
                    'followup_id': 789,
                    'response_type': 'positive|negative|neutral|interview_invite',
                    'response_content': 'Thanks for your follow-up...'
                }
            }
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
            folder_path = data.get('folder_path', '')

            if not application_id:
                raise CustomAPIException(
                    detail="application_id is required",
                    code="missing_application_id"
                )

            if not documents:
                raise CustomAPIException(
                    detail="documents array cannot be empty",
                    code="empty_documents"
                )

            try:
                application = JobApplication.objects.get(id=application_id)
            except JobApplication.DoesNotExist:
                raise JobApplicationNotFound(
                    detail=f"Application with ID {application_id} not found"
                )

            saved_documents = []
            for doc_data in documents:
                doc_type = doc_data.get('type')
                file_path = doc_data.get('file_path', '')
                content = doc_data.get('content', '')
                file_size = doc_data.get('file_size', 0)

                if not doc_type:
                    logger.warning(f"Skipping document without type: {doc_data}")
                    continue

                try:
                    document, created = GeneratedDocument.objects.update_or_create(
                        application=application,
                        document_type=doc_type,
                        defaults={
                            'file_path': file_path,
                            'content': content[:5000] if content else '',
                            'file_size': file_size,
                        }
                    )

                    saved_documents.append({
                        'type': doc_type,
                        'created': created,
                        'file_path': file_path
                    })

                except Exception as e:
                    logger.error(f"Error saving document {doc_type}: {str(e)}")
                    continue

            application.documents_generated = True
            if folder_path:
                application.documents_folder_path = folder_path
            application.save()

            logger.info(f"Document generation completed for application {application.id}")

            return JsonResponse({
                'success': True,
                'message': f'Successfully saved {len(saved_documents)} documents for {application.job_title} at {application.company_name}',
                'application_id': application_id,
                'documents_saved': len(saved_documents),
                'documents': saved_documents
            })

        except json.JSONDecodeError:
            raise CustomAPIException(
                detail="Invalid JSON payload",
                code="invalid_json"
            )
        except CustomAPIException:
            raise
        except JobApplicationNotFound:
            raise
        except Exception as e:
            logger.error(f"Error processing document webhook: {str(e)}")
            raise DocumentGenerationError(
                detail="Failed to process document generation webhook"
            )

    def get(self, request):
        """GET request returns webhook information"""
        return JsonResponse({
            'webhook': 'N8N Document Generation',
            'method': 'POST',
            'description': 'Receives generated documents from n8n workflows',
            'expected_payload': {
                'application_id': 'integer (required)',
                'folder_path': 'string (optional)',
                'documents': [
                    {
                        'type': 'resume|cover_letter|email_templates|linkedin_messages|video_script|company_research|followup_schedule|skills_analysis',
                        'file_path': 'string (path to generated file)',
                        'content': 'string (document content for preview)',
                        'file_size': 'integer (file size in bytes)'
                    }
                ]
            }
        })


class ObtainAuthTokenView(APIView):
    """
    Get or create API token using username/password
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username:
            raise CustomAPIException(
                detail="Username is required",
                code="missing_username"
            )

        if not password:
            raise CustomAPIException(
                detail="Password is required",
                code="missing_password"
            )

        user = authenticate(username=username, password=password)
        if not user:
            raise CustomAPIException(
                detail="Invalid username or password",
                code="invalid_credentials",
                status_code=401
            )

        if not user.is_active:
            raise CustomAPIException(
                detail="Account is disabled. Please contact support.",
                code="account_disabled",
                status_code=401
            )

        try:
            token, created = Token.objects.get_or_create(user=user)

            return Response({
                'success': True,
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'created': created,
                'message': 'Token created successfully' if created else 'Token retrieved successfully'
            })

        except Exception as e:
            logger.error(f"Error creating/retrieving token: {str(e)}")
            raise CustomAPIException(
                detail="Failed to process authentication",
                code="auth_processing_failed",
                status_code=500
            )


class RefreshAuthTokenView(APIView):
    """
    Refresh/regenerate API token for authenticated user
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            old_token = request.user.auth_token
            old_token.delete()

            new_token = Token.objects.create(user=request.user)

            return Response({
                'success': True,
                'token': new_token.key,
                'user_id': request.user.id,
                'message': 'Token refreshed successfully'
            })

        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise CustomAPIException(
                detail="Failed to refresh token",
                code="token_refresh_failed",
                status_code=500
            )


class ValidateTokenView(APIView):
    """
    Validate if current token is still valid
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            token = request.user.auth_token

            return Response({
                'success': True,
                'valid': True,
                'token': token.key,
                'user_id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'token_created': token.created,
                'message': 'Token is valid'
            })

        except Token.DoesNotExist:
            raise CustomAPIException(
                detail="No token found for user",
                code="token_not_found",
                status_code=404
            )


class RevokeTokenView(APIView):
    """
    Revoke/delete current API token
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        try:
            token = request.user.auth_token
            token.delete()

            return Response({
                'success': True,
                'message': 'Token revoked successfully'
            })

        except Token.DoesNotExist:
            raise CustomAPIException(
                detail="No token found for user",
                code="token_not_found",
                status_code=404
            )


class CreateUserWithTokenView(APIView):
    """
    Create new user account and return API token
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')

        if not username:
            raise CustomAPIException(
                detail="Username is required",
                code="missing_username"
            )

        if not email:
            raise CustomAPIException(
                detail="Email is required",
                code="missing_email"
            )

        if not password:
            raise CustomAPIException(
                detail="Password is required",
                code="missing_password"
            )

        if User.objects.filter(username=username).exists():
            raise CustomAPIException(
                detail="Username already exists",
                code="username_exists"
            )

        if User.objects.filter(email=email).exists():
            raise CustomAPIException(
                detail="Email already exists",
                code="email_exists"
            )

        if len(password) < 8:
            raise CustomAPIException(
                detail="Password must be at least 8 characters long",
                code="password_too_short"
            )

        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            token = user.auth_token

            return Response({
                'success': True,
                'message': 'User created successfully',
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'token': token.key
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise CustomAPIException(
                detail="Failed to create user account",
                code="user_creation_failed",
                status_code=500
            )


class ChangePasswordView(APIView):
    """
    Change user password and optionally refresh token
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        refresh_token = request.data.get('refresh_token', False)

        if not current_password:
            raise CustomAPIException(
                detail="Current password is required",
                code="missing_current_password"
            )

        if not new_password:
            raise CustomAPIException(
                detail="New password is required",
                code="missing_new_password"
            )

        if not request.user.check_password(current_password):
            raise CustomAPIException(
                detail="Current password is incorrect",
                code="incorrect_current_password",
                status_code=401
            )

        if len(new_password) < 8:
            raise CustomAPIException(
                detail="New password must be at least 8 characters long",
                code="password_too_short"
            )

        try:
            request.user.set_password(new_password)
            request.user.save()

            response_data = {
                'success': True,
                'message': 'Password changed successfully'
            }

            if refresh_token:
                old_token = request.user.auth_token
                old_token.delete()
                new_token = Token.objects.create(user=request.user)
                response_data['new_token'] = new_token.key
                response_data['message'] += ' and token refreshed'

            return Response(response_data)

        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            raise CustomAPIException(
                detail="Failed to change password",
                code="password_change_failed",
                status_code=500
            )


class HealthCheckAPIView(APIView):
    """
    Simple health check endpoint for monitoring
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        """
        Returns API health status
        """
        try:
            # Test database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

            return Response({
                'status': 'healthy',
                'timestamp': timezone.now(),
                'database': 'connected',
                'api_version': 'v1',
                'message': 'Job Automation API is running'
            })

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return Response({
                'status': 'unhealthy',
                'timestamp': timezone.now(),
                'database': 'disconnected',
                'error': str(e),
                'message': 'Job Automation API has issues'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


# ADD THESE IMPORTS TO api/views.py
import os
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from documents.models import GeneratedDocument, DocumentGenerationJob
from documents.tasks import generate_all_documents
from jobs.models import JobApplication


# ADD THESE VIEW CLASSES TO api/views.py

class DocumentAPIView(APIView):
    """
    API endpoint for document operations
    Handles both listing documents (GET) and generating documents (POST)
    Used for both /documents/ and /documents/generate/ endpoints
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List user's documents with filtering"""
        try:
            # Get query parameters for filtering
            application_id = request.query_params.get('application_id')
            document_type = request.query_params.get('document_type')
            date_from = request.query_params.get('date_from')
            date_to = request.query_params.get('date_to')
            limit = request.query_params.get('limit', 50)

            # Base queryset - only user's documents
            queryset = GeneratedDocument.objects.filter(
                application__user=request.user
            ).select_related('application').order_by('-generated_at')

            # Apply filters
            if application_id:
                try:
                    application_id = int(application_id)
                    queryset = queryset.filter(application_id=application_id)
                except ValueError:
                    return Response(
                        {'error': 'Invalid application_id'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            if document_type:
                valid_types = [choice[0] for choice in GeneratedDocument.DOCUMENT_TYPES]
                if document_type in valid_types:
                    queryset = queryset.filter(document_type=document_type)
                else:
                    return Response(
                        {'error': f'Invalid document_type. Valid types: {valid_types}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            if date_from:
                queryset = queryset.filter(generated_at__gte=date_from)

            if date_to:
                queryset = queryset.filter(generated_at__lte=date_to)

            # Limit results
            try:
                limit = int(limit)
                if limit > 100:  # Max limit
                    limit = 100
                queryset = queryset[:limit]
            except ValueError:
                limit = 50

            # Prepare response data
            documents_data = []
            for doc in queryset:
                doc_data = {
                    'id': doc.id,
                    'application_id': doc.application.id,
                    'application_title': doc.application.job_title,
                    'company_name': doc.application.company_name,
                    'document_type': doc.document_type,
                    'document_type_display': doc.get_document_type_display(),
                    'generated_at': doc.generated_at.isoformat(),
                    'file_size': doc.file_size,
                    'has_content': bool(doc.content),
                    'file_exists': bool(doc.file_path and os.path.exists(doc.file_path)),
                    'download_url': request.build_absolute_uri(
                        reverse('documents:download_single', kwargs={'document_id': doc.id})
                    ) if doc.file_path else None,
                    'preview_url': request.build_absolute_uri(
                        reverse('documents:preview', kwargs={
                            'application_id': doc.application.id,
                            'doc_type': doc.document_type
                        })
                    )
                }
                documents_data.append(doc_data)

            # Get summary statistics
            total_documents = GeneratedDocument.objects.filter(
                application__user=request.user
            ).count()

            unique_applications = GeneratedDocument.objects.filter(
                application__user=request.user
            ).values('application').distinct().count()

            return Response({
                'success': True,
                'documents': documents_data,
                'pagination': {
                    'count': len(documents_data),
                    'total_count': total_documents,
                    'limit': limit,
                    'has_more': total_documents > limit
                },
                'summary': {
                    'total_documents': total_documents,
                    'unique_applications': unique_applications,
                    'document_types': dict(GeneratedDocument.DOCUMENT_TYPES)
                }
            })

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        """Generate documents for an application"""
        try:
            application_id = request.data.get('application_id')
            document_types = request.data.get('document_types', [])  # Optional: specific types
            regenerate_existing = request.data.get('regenerate_existing', False)
            priority = request.data.get('priority', 'normal')
            custom_instructions = request.data.get('custom_instructions', '')

            # Validate required fields
            if not application_id:
                return Response(
                    {'success': False, 'error': 'application_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Verify application belongs to user
            try:
                application = JobApplication.objects.get(
                    id=application_id,
                    user=request.user
                )
            except JobApplication.DoesNotExist:
                return Response(
                    {'success': False, 'error': 'Application not found or access denied'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check if generation is already in progress
            existing_job = DocumentGenerationJob.objects.filter(
                application=application,
                status__in=['pending', 'processing']
            ).first()

            if existing_job and not regenerate_existing:
                return Response(
                    {
                        'success': False,
                        'error': 'Document generation already in progress',
                        'job_id': existing_job.id,
                        'status': existing_job.status
                    },
                    status=status.HTTP_409_CONFLICT
                )

            # Validate document types if specified
            if document_types:
                valid_types = [choice[0] for choice in GeneratedDocument.DOCUMENT_TYPES]
                invalid_types = [dt for dt in document_types if dt not in valid_types]
                if invalid_types:
                    return Response(
                        {
                            'success': False,
                            'error': f'Invalid document types: {invalid_types}',
                            'valid_types': valid_types
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Start generation task
            task = generate_all_documents.delay(
                application_id,
                specific_types=document_types,
                custom_instructions=custom_instructions,
                priority=priority
            )

            # Create job record
            job = DocumentGenerationJob.objects.create(
                application=application,
                status='pending'
            )

            return Response({
                'success': True,
                'message': 'Document generation started successfully',
                'task_id': task.id,
                'job_id': job.id,
                'application_id': application_id,
                'estimated_time': '2-3 minutes',
                'status_url': request.build_absolute_uri(
                    reverse('api:documents_status', kwargs={'application_id': application_id})
                )
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DocumentBulkActionAPIView(APIView):
    """API endpoint for bulk document actions"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Perform bulk actions on multiple documents"""
        try:
            action = request.data.get('action')
            document_ids = request.data.get('document_ids', [])
            export_format = request.data.get('export_format', 'zip')

            # Validate required fields
            if not action:
                return Response(
                    {'success': False, 'error': 'action is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not document_ids:
                return Response(
                    {'success': False, 'error': 'document_ids is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate action
            valid_actions = ['download', 'delete', 'regenerate', 'export']
            if action not in valid_actions:
                return Response(
                    {
                        'success': False,
                        'error': f'Invalid action. Valid actions: {valid_actions}'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get documents belonging to user
            documents = GeneratedDocument.objects.filter(
                id__in=document_ids,
                application__user=request.user
            ).select_related('application')

            if not documents.exists():
                return Response(
                    {'success': False, 'error': 'No valid documents found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Perform the requested action
            if action == 'delete':
                deleted_count = 0
                deleted_files = []

                for doc in documents:
                    # Delete physical file if exists
                    if doc.file_path and os.path.exists(doc.file_path):
                        try:
                            os.remove(doc.file_path)
                            deleted_files.append(doc.file_path)
                        except OSError as e:
                            # Log error but continue
                            pass

                    # Delete database record
                    doc.delete()
                    deleted_count += 1

                return Response({
                    'success': True,
                    'message': f'Successfully deleted {deleted_count} documents',
                    'deleted_count': deleted_count,
                    'deleted_files': len(deleted_files)
                })

            elif action == 'regenerate':
                # Get unique applications
                applications = set(doc.application for doc in documents)
                task_ids = []
                job_ids = []

                for application in applications:
                    # Check if generation is already in progress
                    existing_job = DocumentGenerationJob.objects.filter(
                        application=application,
                        status__in=['pending', 'processing']
                    ).first()

                    if not existing_job:
                        # Start regeneration task
                        task = generate_all_documents.delay(application.id)
                        task_ids.append(task.id)

                        # Create job record
                        job = DocumentGenerationJob.objects.create(
                            application=application,
                            status='pending'
                        )
                        job_ids.append(job.id)

                return Response({
                    'success': True,
                    'message': f'Regeneration started for {len(task_ids)} applications',
                    'applications_count': len(applications),
                    'started_jobs': len(task_ids),
                    'task_ids': task_ids,
                    'job_ids': job_ids,
                    'estimated_time': '2-3 minutes per application'
                })

            elif action == 'download' or action == 'export':
                # Prepare download information
                download_data = []

                for doc in documents:
                    doc_info = {
                        'id': doc.id,
                        'document_type': doc.document_type,
                        'document_type_display': doc.get_document_type_display(),
                        'application_title': doc.application.job_title,
                        'company_name': doc.application.company_name,
                        'file_size': doc.file_size,
                        'generated_at': doc.generated_at.isoformat(),
                        'download_url': request.build_absolute_uri(
                            reverse('documents:download_single', kwargs={'document_id': doc.id})
                        ) if doc.file_path else None,
                        'file_exists': bool(doc.file_path and os.path.exists(doc.file_path))
                    }
                    download_data.append(doc_info)

                # For bulk download, provide ZIP download URL
                if len(set(doc.application.id for doc in documents)) == 1:
                    # All documents from same application
                    app_id = documents.first().application.id
                    zip_url = request.build_absolute_uri(
                        reverse('documents:download', kwargs={'application_id': app_id})
                    )
                else:
                    # Multiple applications - would need special bulk download endpoint
                    zip_url = None

                return Response({
                    'success': True,
                    'documents': download_data,
                    'total_documents': len(download_data),
                    'total_size': sum(doc.file_size or 0 for doc in documents),
                    'zip_download_url': zip_url,
                    'export_format': export_format
                })

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DocumentStatusAPIView(APIView):
    """API endpoint for checking document generation status"""
    permission_classes = [IsAuthenticated]

    def get(self, request, application_id):
        """Get document generation status for a specific application"""
        try:
            # Verify application belongs to user
            try:
                application = JobApplication.objects.get(
                    id=application_id,
                    user=request.user
                )
            except JobApplication.DoesNotExist:
                return Response(
                    {'success': False, 'error': 'Application not found or access denied'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get latest generation job
            generation_job = DocumentGenerationJob.objects.filter(
                application=application
            ).order_by('-started_at').first()

            # Get all generated documents for this application
            documents = GeneratedDocument.objects.filter(
                application=application
            ).order_by('-generated_at')

            # Prepare document data
            documents_data = []
            for doc in documents:
                doc_data = {
                    'id': doc.id,
                    'document_type': doc.document_type,
                    'document_type_display': doc.get_document_type_display(),
                    'generated_at': doc.generated_at.isoformat(),
                    'file_size': doc.file_size,
                    'has_content': bool(doc.content),
                    'file_exists': bool(doc.file_path and os.path.exists(doc.file_path)),
                    'download_url': request.build_absolute_uri(
                        reverse('documents:download_single', kwargs={'document_id': doc.id})
                    ) if doc.file_path else None
                }
                documents_data.append(doc_data)

            # Calculate completion stats
            total_possible_types = len(GeneratedDocument.DOCUMENT_TYPES)
            generated_types = documents.count()
            completion_percentage = (generated_types / total_possible_types) * 100 if total_possible_types > 0 else 0

            # Get missing document types
            existing_types = set(documents.values_list('document_type', flat=True))
            all_types = set(choice[0] for choice in GeneratedDocument.DOCUMENT_TYPES)
            missing_types = all_types - existing_types

            # Prepare generation job data
            job_data = None
            if generation_job:
                duration = None
                if generation_job.completed_at and generation_job.started_at:
                    duration = (generation_job.completed_at - generation_job.started_at).total_seconds()

                job_data = {
                    'id': generation_job.id,
                    'status': generation_job.status,
                    'status_display': generation_job.get_status_display(),
                    'started_at': generation_job.started_at.isoformat(),
                    'completed_at': generation_job.completed_at.isoformat() if generation_job.completed_at else None,
                    'duration_seconds': duration,
                    'error_message': generation_job.error_message
                }

            return Response({
                'success': True,
                'application_id': application_id,
                'application_title': application.job_title,
                'company_name': application.company_name,
                'generation_job': job_data,
                'documents': documents_data,
                'statistics': {
                    'total_documents': generated_types,
                    'total_possible': total_possible_types,
                    'completion_percentage': round(completion_percentage, 1),
                    'missing_types': list(missing_types),
                    'existing_types': list(existing_types)
                },
                'urls': {
                    'download_all': request.build_absolute_uri(
                        reverse('documents:download', kwargs={'application_id': application_id})
                    ),
                    'application_detail': request.build_absolute_uri(
                        reverse('jobs:application_detail', kwargs={'pk': application_id})
                    )
                }
            })

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ADD THESE IMPORTS TO api/views.py
from followups.models import FollowUpTemplate, FollowUpHistory
from datetime import date, timedelta


# ADD THESE API VIEW CLASSES TO api/views.py

class FollowUpAPIView(APIView):
    """API for sending individual follow-ups"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Send a follow-up email for a specific application"""
        try:
            application_id = request.data.get('application_id')
            template_id = request.data.get('template_id')
            custom_message = request.data.get('custom_message', '')
            send_immediately = request.data.get('send_immediately', True)

            if not application_id:
                return Response(
                    {'success': False, 'error': 'application_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Verify application belongs to user
            try:
                application = JobApplication.objects.get(
                    id=application_id,
                    user=request.user
                )
            except JobApplication.DoesNotExist:
                return Response(
                    {'success': False, 'error': 'Application not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get template
            if template_id:
                try:
                    template = FollowUpTemplate.objects.get(
                        id=template_id,
                        user=request.user
                    )
                except FollowUpTemplate.DoesNotExist:
                    return Response(
                        {'success': False, 'error': 'Template not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Use default template
                template = FollowUpTemplate.objects.filter(
                    user=request.user,
                    is_default=True,
                    is_active=True
                ).first()

                if not template:
                    return Response(
                        {'success': False, 'error': 'No default template found'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Prepare email data
            email_data = {
                'user_name': request.user.get_full_name() or request.user.username,
                'company_name': application.company_name,
                'job_title': application.job_title,
                'hiring_manager': 'Hiring Manager',  # Could be enhanced
                'days_since_application': (
                            date.today() - application.applied_date).days if application.applied_date else 0,
                'custom_message': custom_message
            }

            # Process template
            subject = template.subject_template
            body = template.body_template

            for key, value in email_data.items():
                subject = subject.replace(f'{{{{{key}}}}}', str(value))
                body = body.replace(f'{{{{{key}}}}}', str(value))

            if send_immediately:
                # Create follow-up history record
                followup_history = FollowUpHistory.objects.create(
                    application=application,
                    template=template,
                    subject=subject,
                    body=body
                )

                # Update application
                application.last_follow_up_date = timezone.now()
                application.follow_up_count += 1
                application.next_follow_up_date = date.today() + timedelta(days=template.days_after_application)
                application.save()

                # Update template stats
                template.times_used += 1
                template.save()

                return Response({
                    'success': True,
                    'message': 'Follow-up sent successfully',
                    'followup_id': followup_history.id,
                    'subject': subject,
                    'scheduled_date': application.next_follow_up_date.isoformat()
                })
            else:
                # Schedule for later
                schedule_date = request.data.get('schedule_date')
                if schedule_date:
                    application.next_follow_up_date = schedule_date
                    application.save()

                return Response({
                    'success': True,
                    'message': 'Follow-up scheduled successfully',
                    'scheduled_date': application.next_follow_up_date.isoformat()
                })

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BulkFollowUpAPIView(APIView):
    """API for bulk follow-up operations"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Send follow-ups to multiple applications"""
        try:
            application_ids = request.data.get('application_ids', [])
            template_id = request.data.get('template_id')
            delay_between_emails = request.data.get('delay_between_emails', 0)  # seconds

            if not application_ids:
                return Response(
                    {'success': False, 'error': 'application_ids is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not template_id:
                return Response(
                    {'success': False, 'error': 'template_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Verify template
            try:
                template = FollowUpTemplate.objects.get(
                    id=template_id,
                    user=request.user
                )
            except FollowUpTemplate.DoesNotExist:
                return Response(
                    {'success': False, 'error': 'Template not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get applications
            applications = JobApplication.objects.filter(
                id__in=application_ids,
                user=request.user
            )

            if not applications.exists():
                return Response(
                    {'success': False, 'error': 'No valid applications found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            sent_count = 0
            failed_count = 0
            results = []

            for application in applications:
                try:
                    # Prepare email data
                    email_data = {
                        'user_name': request.user.get_full_name() or request.user.username,
                        'company_name': application.company_name,
                        'job_title': application.job_title,
                        'hiring_manager': 'Hiring Manager',
                        'days_since_application': (
                                    date.today() - application.applied_date).days if application.applied_date else 0
                    }

                    # Process template
                    subject = template.subject_template
                    body = template.body_template

                    for key, value in email_data.items():
                        subject = subject.replace(f'{{{{{key}}}}}', str(value))
                        body = body.replace(f'{{{{{key}}}}}', str(value))

                    # Create follow-up history
                    followup_history = FollowUpHistory.objects.create(
                        application=application,
                        template=template,
                        subject=subject,
                        body=body
                    )

                    # Update application
                    application.last_follow_up_date = timezone.now()
                    application.follow_up_count += 1
                    application.next_follow_up_date = date.today() + timedelta(days=template.days_after_application)
                    application.save()

                    results.append({
                        'application_id': application.id,
                        'company_name': application.company_name,
                        'job_title': application.job_title,
                        'success': True,
                        'followup_id': followup_history.id
                    })
                    sent_count += 1

                except Exception as e:
                    results.append({
                        'application_id': application.id,
                        'company_name': application.company_name,
                        'job_title': application.job_title,
                        'success': False,
                        'error': str(e)
                    })
                    failed_count += 1

            # Update template stats
            template.times_used += sent_count
            template.save()

            return Response({
                'success': True,
                'message': f'Bulk follow-up completed: {sent_count} sent, {failed_count} failed',
                'sent_count': sent_count,
                'failed_count': failed_count,
                'results': results
            })

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FollowUpTemplateAPIView(APIView):
    """API for template management"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List user's follow-up templates"""
        templates = FollowUpTemplate.objects.filter(
            user=request.user,
            is_active=True
        ).order_by('template_name')

        serializer = FollowUpTemplateSerializer(templates, many=True)

        return Response({
            'success': True,
            'templates': serializer.data,
            'total_count': templates.count()
        })

    def post(self, request):
        """Create a new follow-up template"""
        try:
            data = request.data.copy()
            data['user'] = request.user.id

            serializer = FollowUpTemplateSerializer(data=data)

            if serializer.is_valid():
                template = serializer.save(user=request.user)

                return Response({
                    'success': True,
                    'message': 'Template created successfully',
                    'template': FollowUpTemplateSerializer(template).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FollowUpHistoryAPIView(APIView):
    """API for follow-up history"""
    permission_classes = [IsAuthenticated]

    def get(self, request, application_id=None):
        """Get follow-up history for an application or all applications"""
        try:
            if application_id:
                # Get history for specific application
                try:
                    application = JobApplication.objects.get(
                        id=application_id,
                        user=request.user
                    )
                except JobApplication.DoesNotExist:
                    return Response(
                        {'success': False, 'error': 'Application not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )

                history = FollowUpHistory.objects.filter(
                    application=application
                ).order_by('-sent_date')

                context_data = {
                    'application_id': application_id,
                    'application_title': application.job_title,
                    'company_name': application.company_name
                }
            else:
                # Get all history for user
                history = FollowUpHistory.objects.filter(
                    application__user=request.user
                ).order_by('-sent_date')

                context_data = {}

            # Apply filters
            date_from = request.query_params.get('date_from')
            date_to = request.query_params.get('date_to')
            response_type = request.query_params.get('response_type')

            if date_from:
                history = history.filter(sent_date__gte=date_from)
            if date_to:
                history = history.filter(sent_date__lte=date_to)
            if response_type:
                history = history.filter(response_type=response_type)

            # Pagination
            limit = int(request.query_params.get('limit', 20))
            offset = int(request.query_params.get('offset', 0))

            total_count = history.count()
            history = history[offset:offset + limit]

            serializer = FollowUpHistorySerializer(history, many=True)

            return Response({
                'success': True,
                'history': serializer.data,
                'pagination': {
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                },
                **context_data
            })

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, application_id=None):
        """Update follow-up history (mark response received, etc.)"""
        try:
            followup_id = request.data.get('followup_id')

            if not followup_id:
                return Response(
                    {'success': False, 'error': 'followup_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                followup = FollowUpHistory.objects.get(
                    id=followup_id,
                    application__user=request.user
                )
            except FollowUpHistory.DoesNotExist:
                return Response(
                    {'success': False, 'error': 'Follow-up not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Update fields
            response_received = request.data.get('response_received')
            response_type = request.data.get('response_type')
            response_date = request.data.get('response_date')
            notes = request.data.get('notes')

            if response_received is not None:
                followup.response_received = response_received
            if response_type:
                followup.response_type = response_type
            if response_date:
                followup.response_date = response_date
            if notes is not None:
                followup.notes = notes

            followup.save()

            # Update template success rate if response received
            if response_received and followup.template:
                followup.template.responses_received += 1
                followup.template.calculate_success_rate()

            return Response({
                'success': True,
                'message': 'Follow-up updated successfully',
                'followup': FollowUpHistorySerializer(followup).data
            })

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ADD THESE IMPORTS TO api/views.py
from dashboard.models import DashboardWidget, UserNotification, DashboardSettings, DashboardActivity


# ADD THESE API VIEW CLASSES TO api/views.py

class DashboardStatsAPIView(APIView):
    """Real-time dashboard statistics API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get comprehensive dashboard statistics"""
        try:
            user = request.user

            # Basic application statistics
            applications = JobApplication.objects.filter(user=user)
            today = timezone.now().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)

            stats = {
                'applications': {
                    'total': applications.count(),
                    'this_week': applications.filter(created_at__gte=week_ago).count(),
                    'this_month': applications.filter(created_at__gte=month_ago).count(),
                    'today': applications.filter(created_at__date=today).count()
                },
                'pipeline': {
                    'found': applications.filter(application_status='found').count(),
                    'applied': applications.filter(application_status='applied').count(),
                    'responded': applications.filter(application_status='responded').count(),
                    'interview': applications.filter(application_status='interview').count(),
                    'offer': applications.filter(application_status='offer').count(),
                    'hired': applications.filter(application_status='hired').count(),
                    'rejected': applications.filter(application_status='rejected').count()
                }
            }

            # Response rate calculation
            applied_count = stats['pipeline']['applied']
            responded_count = stats['pipeline']['responded'] + stats['pipeline']['interview'] + stats['pipeline'][
                'offer']
            stats['response_rate'] = (responded_count / applied_count * 100) if applied_count > 0 else 0

            # Follow-up statistics
            due_followups = applications.filter(
                next_follow_up_date__lte=today,
                application_status__in=['applied', 'responded']
            ).count()

            overdue_followups = applications.filter(
                next_follow_up_date__lt=today,
                application_status__in=['applied', 'responded']
            ).count()

            stats['follow_ups'] = {
                'due_today': due_followups,
                'overdue': overdue_followups,
                'total_sent': FollowUpHistory.objects.filter(application__user=user).count()
            }

            # Document statistics
            total_documents = GeneratedDocument.objects.filter(application__user=user).count()
            recent_documents = GeneratedDocument.objects.filter(
                application__user=user,
                generated_at__gte=week_ago
            ).count()

            stats['documents'] = {
                'total': total_documents,
                'recent': recent_documents,
                'avg_per_application': total_documents / max(stats['applications']['total'], 1)
            }

            # Activity trends (last 7 days)
            activity_data = []
            for i in range(7):
                day = today - timedelta(days=i)
                day_applications = applications.filter(created_at__date=day).count()
                day_followups = FollowUpHistory.objects.filter(
                    application__user=user,
                    sent_date__date=day
                ).count()

                activity_data.append({
                    'date': day.isoformat(),
                    'applications': day_applications,
                    'followups': day_followups
                })

            stats['activity_trend'] = list(reversed(activity_data))

            # Notifications
            unread_notifications = UserNotification.objects.filter(
                user=user,
                is_read=False,
                is_dismissed=False
            ).count()

            urgent_notifications = UserNotification.objects.filter(
                user=user,
                is_read=False,
                priority='urgent'
            ).count()

            stats['notifications'] = {
                'unread': unread_notifications,
                'urgent': urgent_notifications
            }

            # Profile completeness
            try:
                from accounts.models import UserProfile
                profile = UserProfile.objects.get(user=user)
                stats['profile'] = {
                    'completion_percentage': profile.profile_completion_percentage,
                    'needs_attention': profile.profile_completion_percentage < 80
                }
            except UserProfile.DoesNotExist:
                stats['profile'] = {
                    'completion_percentage': 0,
                    'needs_attention': True
                }

            return Response({
                'success': True,
                'stats': stats,
                'last_updated': timezone.now().isoformat()
            })

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PipelineAPIView(APIView):
    """Pipeline management API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get pipeline data with application details"""
        try:
            applications = JobApplication.objects.filter(user=request.user)

            pipeline_data = {}
            for app in applications:
                status = app.application_status
                if status not in pipeline_data:
                    pipeline_data[status] = []

                app_data = {
                    'id': app.id,
                    'job_title': app.job_title,
                    'company_name': app.company_name,
                    'created_at': app.created_at.isoformat(),
                    'match_percentage': app.match_percentage,
                    'urgency_level': app.urgency_level,
                    'salary_range': app.salary_range,
                    'location': app.location,
                    'remote_option': app.remote_option,
                    'next_follow_up_date': app.next_follow_up_date.isoformat() if app.next_follow_up_date else None,
                    'follow_up_count': app.follow_up_count,
                    'documents_generated': app.documents_generated
                }

                pipeline_data[status].append(app_data)

            return Response({
                'success': True,
                'pipeline': pipeline_data
            })

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        """Update application status in pipeline"""
        try:
            application_id = request.data.get('application_id')
            new_status = request.data.get('new_status')
            notes = request.data.get('notes', '')

            if not application_id or not new_status:
                return Response(
                    {'success': False, 'error': 'application_id and new_status are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            application = get_object_or_404(
                JobApplication,
                id=application_id,
                user=request.user
            )

            # Validate status
            valid_statuses = [choice[0] for choice in JobApplication.STATUS_CHOICES]
            if new_status not in valid_statuses:
                return Response(
                    {'success': False, 'error': 'Invalid status'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Update application
            old_status = application.application_status
            application.application_status = new_status

            if notes:
                application.notes = notes

            # Update date fields based on status
            if new_status == 'applied' and not application.applied_date:
                application.applied_date = timezone.now().date()

            application.save()

            # Log activity
            DashboardActivity.log_activity(
                user=request.user,
                activity_type='application_status_changed',
                description=f'Status changed from {old_status} to {new_status}',
                metadata={
                    'application_id': application_id,
                    'old_status': old_status,
                    'new_status': new_status,
                    'company': application.company_name,
                    'job_title': application.job_title
                }
            )

            # Create notification for important status changes
            if new_status in ['responded', 'interview', 'offer']:
                UserNotification.objects.create(
                    user=request.user,
                    notification_type='success',
                    title='Application Status Updated',
                    message=f'{application.job_title} at {application.company_name} - Status: {new_status.title()}',
                    related_application=application,
                    priority='high' if new_status == 'offer' else 'normal'
                )

            return Response({
                'success': True,
                'message': f'Status updated to {new_status}',
                'application': {
                    'id': application.id,
                    'status': application.application_status,
                    'updated_at': application.updated_at.isoformat()
                }
            })

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NotificationAPIView(APIView):
    """Dashboard notifications API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user notifications"""
        try:
            # Query parameters
            unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
            limit = int(request.query_params.get('limit', 20))

            notifications = UserNotification.objects.filter(
                user=request.user,
                is_dismissed=False
            )

            if unread_only:
                notifications = notifications.filter(is_read=False)

            notifications = notifications.order_by('-created_at')[:limit]

            notifications_data = []
            for notification in notifications:
                notifications_data.append({
                    'id': notification.id,
                    'type': notification.notification_type,
                    'title': notification.title,
                    'message': notification.message,
                    'priority': notification.priority,
                    'is_read': notification.is_read,
                    'action_url': notification.action_url,
                    'action_text': notification.action_text,
                    'created_at': notification.created_at.isoformat(),
                    'expires_at': notification.expires_at.isoformat() if notification.expires_at else None,
                    'related_application_id': notification.related_application.id if notification.related_application else None
                })

            # Get counts
            total_count = UserNotification.objects.filter(
                user=request.user,
                is_dismissed=False
            ).count()

            unread_count = UserNotification.objects.filter(
                user=request.user,
                is_read=False,
                is_dismissed=False
            ).count()

            return Response({
                'success': True,
                'notifications': notifications_data,
                'counts': {
                    'total': total_count,
                    'unread': unread_count,
                    'returned': len(notifications_data)
                }
            })

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        """Manage notifications (mark read, dismiss, etc.)"""
        try:
            action = request.data.get('action')
            notification_ids = request.data.get('notification_ids', [])

            if action == 'mark_read':
                UserNotification.objects.filter(
                    id__in=notification_ids,
                    user=request.user
                ).update(is_read=True, read_at=timezone.now())

                return Response({
                    'success': True,
                    'message': f'Marked {len(notification_ids)} notifications as read'
                })

            elif action == 'dismiss':
                UserNotification.objects.filter(
                    id__in=notification_ids,
                    user=request.user
                ).update(is_dismissed=True)

                return Response({
                    'success': True,
                    'message': f'Dismissed {len(notification_ids)} notifications'
                })

            elif action == 'mark_all_read':
                count = UserNotification.objects.filter(
                    user=request.user,
                    is_read=False
                ).update(is_read=True, read_at=timezone.now())

                return Response({
                    'success': True,
                    'message': f'Marked {count} notifications as read'
                })

            else:
                return Response(
                    {'success': False, 'error': 'Invalid action'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )