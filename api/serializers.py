import os

from django.urls import reverse
# api/serializers.py
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from jobs.models import JobApplication, JobSearchConfig
from followups.models import FollowUpHistory, FollowUpTemplate
from accounts.models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'id', 'full_name', 'email', 'phone', 'location',
            'linkedin_url', 'github_url', 'portfolio_url',
            'years_experience', 'education', 'current_job_title',
            'current_company', 'key_skills', 'preferred_salary_min',
            'preferred_salary_max', 'work_type_preference',
            'preferred_company_sizes', 'industries_of_interest',
            'profile_completion_percentage'
        ]


class JobSearchConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobSearchConfig
        fields = [
            'id', 'config_name', 'job_categories', 'target_locations',
            'remote_preference', 'salary_min', 'salary_max',
            'company_size_preference', 'auto_follow_up_enabled',
            'is_active', 'last_search_date'
        ]


# REPLACE your existing JobApplicationSerializer in api/serializers.py with this COMPLETE version:

class JobApplicationSerializer(serializers.ModelSerializer):
    # Read-only computed fields
    status_display_color = serializers.CharField(source='get_status_display_color', read_only=True)
    urgency_color = serializers.CharField(source='get_urgency_color', read_only=True)
    days_since_application = serializers.IntegerField(read_only=True)
    is_follow_up_due = serializers.BooleanField(read_only=True)

    # Related data
    search_config_name = serializers.CharField(source='search_config.config_name', read_only=True)
    # NEW: Enhanced display fields with icons
    employment_type_display = serializers.CharField(source='get_employment_type_display_with_icon', read_only=True)
    experience_level_display = serializers.CharField(source='get_experience_level_display_with_icon', read_only=True)
    remote_type_display = serializers.CharField(source='get_remote_type_display_with_icon', read_only=True)
    class Meta:
        model = JobApplication
        fields = [
            # Basic Job Information
            'id', 'job_title', 'company_name', 'job_url',
            'job_description', 'salary_range', 'location', 'remote_option',

            # Application Status & Tracking
            'application_status', 'applied_date', 'urgency_level',
            'status_display_color', 'urgency_color',  # Computed fields

            # Follow-up Management
            'last_follow_up_date', 'follow_up_count', 'next_follow_up_date',
            'follow_up_sequence_active', 'is_follow_up_due',  # Computed field

            # Interview & Offer Tracking (PREVIOUSLY MISSING)
            'interview_scheduled_date', 'offer_received', 'offer_amount',
            'rejection_received', 'rejection_reason',

            # Company & Job Analysis
            'company_rating', 'glassdoor_rating', 'match_percentage',
            'skills_match_analysis',  # PREVIOUSLY MISSING

            # Document Management
            'documents_generated', 'documents_folder_path',  # PREVIOUSLY MISSING

            # Additional Information
            'notes',  # PREVIOUSLY MISSING

            # Related Data
            'search_config', 'search_config_name',  # search_config_name is read-only

            # Computed Properties
            'days_since_application',  # Computed field

            # Timestamps
            'created_at', 'updated_at'
        ]

        # Read-only fields that shouldn't be updated via API
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'days_since_application',
            'is_follow_up_due', 'status_display_color', 'urgency_color',
            'search_config_name','employment_type_display',
            'experience_level_display', 'remote_type_display'
        ]

    def validate_employment_type(self, value):
        """Validate employment type"""
        valid_types = [choice[0] for choice in JobApplication._meta.get_field('employment_type').choices]
        if value and value not in valid_types:
            raise serializers.ValidationError(f"Invalid employment type. Valid options: {valid_types}")
        return value

    def validate_experience_level(self, value):
        """Validate experience level"""
        valid_levels = [choice[0] for choice in JobApplication._meta.get_field('experience_level').choices]
        if value and value not in valid_levels:
            raise serializers.ValidationError(f"Invalid experience level. Valid options: {valid_levels}")
        return value

    def validate_remote_type(self, value):
        """Validate remote type"""
        valid_types = [choice[0] for choice in JobApplication._meta.get_field('remote_type').choices]
        if value and value not in valid_types:
            raise serializers.ValidationError(f"Invalid remote type. Valid options: {valid_types}")
        return value

    def validate_application_status(self, value):
        """Validate application status transitions"""
        if self.instance and self.instance.application_status == 'hired':
            if value != 'hired':
                raise serializers.ValidationError(
                    "Cannot change status from 'hired' to another status"
                )
        return value

    def validate_offer_amount(self, value):
        """Validate offer amount is positive if provided"""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Offer amount must be positive")
        return value

    def validate(self, attrs):
        """Cross-field validation"""
        # If offer_received is True, offer_amount should be provided
        if attrs.get('offer_received') and not attrs.get('offer_amount'):
            if not (self.instance and self.instance.offer_amount):
                attrs['offer_amount'] = None  # Allow null but warn

        # If rejection_received is True, rejection_reason should be provided
        if attrs.get('rejection_received') and not attrs.get('rejection_reason'):
            if not (self.instance and self.instance.rejection_reason):
                attrs['rejection_reason'] = 'No reason provided'

        if attrs.get('remote_option') and 'remote' in attrs.get('remote_option', '').lower():
            if not attrs.get('remote_type') or attrs.get('remote_type') == 'onsite':
                attrs['remote_type'] = 'remote'

            # If employment_type is internship, experience_level should be entry_level or intern
        if attrs.get('employment_type') == 'internship':
            if attrs.get('experience_level') and attrs.get('experience_level') not in ['entry_level', 'intern']:
                attrs['experience_level'] = 'intern'

        return attrs


class FollowUpTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUpTemplate
        fields = [
            'id', 'template_name', 'template_type',
            'subject_template', 'body_template',
            'days_after_application', 'is_default',
            'success_rate', 'times_used', 'responses_received'
        ]


class FollowUpHistorySerializer(serializers.ModelSerializer):
    application_title = serializers.CharField(source='application.job_title', read_only=True)
    company_name = serializers.CharField(source='application.company_name', read_only=True)
    template_name = serializers.CharField(source='template.template_name', read_only=True)

    class Meta:
        model = FollowUpHistory
        fields = [
            'id', 'application_title', 'company_name',
            'template_name', 'sent_date', 'subject',
            'response_received', 'response_date',
            'response_type', 'notes'
        ]


# ADD THESE TO api/serializers.py

from documents.models import GeneratedDocument, DocumentGenerationJob


class GeneratedDocumentSerializer(serializers.ModelSerializer):
    """Serializer for GeneratedDocument model"""

    application_title = serializers.CharField(source='application.job_title', read_only=True)
    company_name = serializers.CharField(source='application.company_name', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    file_exists = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedDocument
        fields = [
            'id', 'application', 'application_title', 'company_name',
            'document_type', 'document_type_display', 'file_path',
            'content', 'generated_at', 'file_size', 'file_exists',
            'download_url', 'preview_url'
        ]
        read_only_fields = ['id', 'generated_at', 'file_size']

    def get_file_exists(self, obj):
        """Check if the file exists on disk"""
        return bool(obj.file_path and os.path.exists(obj.file_path))

    def get_download_url(self, obj):
        """Get download URL for the document"""
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(
                reverse('documents:download_single', kwargs={'document_id': obj.id})
            )
        return None

    def get_preview_url(self, obj):
        """Get preview URL for the document"""
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(
                reverse('documents:preview', kwargs={
                    'application_id': obj.application.id,
                    'doc_type': obj.document_type
                })
            )
        return None


class DocumentGenerationJobSerializer(serializers.ModelSerializer):
    """Serializer for DocumentGenerationJob model"""

    application_title = serializers.CharField(source='application.job_title', read_only=True)
    company_name = serializers.CharField(source='application.company_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration = serializers.SerializerMethodField()

    class Meta:
        model = DocumentGenerationJob
        fields = [
            'id', 'application', 'application_title', 'company_name',
            'status', 'status_display', 'started_at', 'completed_at',
            'error_message', 'duration'
        ]
        read_only_fields = ['id', 'started_at', 'completed_at', 'duration']

    def get_duration(self, obj):
        """Calculate job duration in seconds"""
        if obj.completed_at and obj.started_at:
            return (obj.completed_at - obj.started_at).total_seconds()
        return None


class DocumentGenerationRequestSerializer(serializers.Serializer):
    """Serializer for document generation requests"""

    application_id = serializers.IntegerField()
    document_types = serializers.MultipleChoiceField(
        choices=GeneratedDocument.DOCUMENT_TYPES,
        required=False,
        help_text="Specific document types to generate. If empty, generates all types."
    )
    regenerate_existing = serializers.BooleanField(
        default=False,
        help_text="Whether to regenerate existing documents"
    )
    priority = serializers.ChoiceField(
        choices=[
            ('normal', 'Normal'),
            ('high', 'High'),
            ('urgent', 'Urgent')
        ],
        default='normal'
    )
    custom_instructions = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Custom instructions for document generation"
    )


class BulkDocumentActionSerializer(serializers.Serializer):
    """Serializer for bulk document actions"""

    action = serializers.ChoiceField(
        choices=[
            ('download', 'Download'),
            ('delete', 'Delete'),
            ('regenerate', 'Regenerate'),
            ('export', 'Export')
        ]
    )
    document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="List of document IDs to perform action on"
    )
    export_format = serializers.ChoiceField(
        choices=[
            ('zip', 'ZIP Archive'),
            ('pdf', 'Combined PDF'),
            ('json', 'JSON Export')
        ],
        required=False,
        default='zip'
    )


# ADD THESE TO api/views.py

from documents.models import GeneratedDocument, DocumentGenerationJob
from documents.tasks import generate_all_documents


class DocumentAPIView(APIView):
    """API endpoint for document operations"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List user's documents with filtering"""
        # Get query parameters
        application_id = request.query_params.get('application_id')
        document_type = request.query_params.get('document_type')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        # Base queryset
        queryset = GeneratedDocument.objects.filter(
            application__user=request.user
        ).select_related('application')

        # Apply filters
        if application_id:
            queryset = queryset.filter(application_id=application_id)

        if document_type:
            queryset = queryset.filter(document_type=document_type)

        if date_from:
            queryset = queryset.filter(generated_at__gte=date_from)

        if date_to:
            queryset = queryset.filter(generated_at__lte=date_to)

        # Serialize and return
        serializer = GeneratedDocumentSerializer(
            queryset.order_by('-generated_at'),
            many=True,
            context={'request': request}
        )

        return Response({
            'documents': serializer.data,
            'total_count': queryset.count()
        })

    def post(self, request):
        """Generate documents for an application"""
        serializer = DocumentGenerationRequestSerializer(data=request.data)

        if serializer.is_valid():
            application_id = serializer.validated_data['application_id']

            # Verify application belongs to user
            try:
                application = JobApplication.objects.get(
                    id=application_id,
                    user=request.user
                )
            except JobApplication.DoesNotExist:
                return Response(
                    {'error': 'Application not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check if generation is already in progress
            existing_job = DocumentGenerationJob.objects.filter(
                application=application,
                status__in=['pending', 'processing']
            ).first()

            if existing_job:
                return Response(
                    {'error': 'Document generation already in progress'},
                    status=status.HTTP_409_CONFLICT
                )

            # Start generation task
            task = generate_all_documents.delay(application_id)

            return Response({
                'message': 'Document generation started',
                'task_id': task.id,
                'estimated_time': '2-3 minutes'
            }, status=status.HTTP_202_ACCEPTED)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class DocumentBulkActionAPIView(APIView):
    """API endpoint for bulk document actions"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Perform bulk actions on documents"""
        serializer = BulkDocumentActionSerializer(data=request.data)

        if serializer.is_valid():
            action = serializer.validated_data['action']
            document_ids = serializer.validated_data['document_ids']

            # Get documents belonging to user
            documents = GeneratedDocument.objects.filter(
                id__in=document_ids,
                application__user=request.user
            )

            if not documents.exists():
                return Response(
                    {'error': 'No valid documents found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            if action == 'delete':
                # Delete documents
                deleted_count = 0
                for doc in documents:
                    if doc.file_path and os.path.exists(doc.file_path):
                        try:
                            os.remove(doc.file_path)
                        except OSError:
                            pass
                    doc.delete()
                    deleted_count += 1

                return Response({
                    'message': f'Deleted {deleted_count} documents'
                })

            elif action == 'regenerate':
                # Start regeneration for all applications
                applications = set(doc.application for doc in documents)
                task_ids = []

                for application in applications:
                    task = generate_all_documents.delay(application.id)
                    task_ids.append(task.id)

                return Response({
                    'message': f'Regeneration started for {len(applications)} applications',
                    'task_ids': task_ids
                })

            elif action == 'download' or action == 'export':
                # Return download URLs or create export
                document_data = GeneratedDocumentSerializer(
                    documents,
                    many=True,
                    context={'request': request}
                ).data

                return Response({
                    'documents': document_data,
                    'download_urls': [doc['download_url'] for doc in document_data]
                })

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class DocumentStatusAPIView(APIView):
    """API endpoint for checking document generation status"""
    permission_classes = [IsAuthenticated]

    def get(self, request, application_id):
        """Get document generation status for an application"""
        try:
            application = JobApplication.objects.get(
                id=application_id,
                user=request.user
            )
        except JobApplication.DoesNotExist:
            return Response(
                {'error': 'Application not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get latest generation job
        generation_job = DocumentGenerationJob.objects.filter(
            application=application
        ).order_by('-started_at').first()

        # Get generated documents
        documents = GeneratedDocument.objects.filter(
            application=application
        )

        response_data = {
            'application_id': application_id,
            'generation_job': None,
            'documents': GeneratedDocumentSerializer(
                documents,
                many=True,
                context={'request': request}
            ).data,
            'total_documents': documents.count(),
            'completion_percentage': (documents.count() / len(GeneratedDocument.DOCUMENT_TYPES)) * 100
        }

        if generation_job:
            response_data['generation_job'] = DocumentGenerationJobSerializer(
                generation_job,
                context={'request': request}
            ).data

        return Response(response_data)


class JobApplicationCreateSerializer(serializers.ModelSerializer):
    """Serializer specifically for creating job applications with enhanced validation"""

    class Meta:
        model = JobApplication
        fields = [
            'job_title', 'company_name', 'job_url', 'job_description',
            'salary_range', 'location', 'remote_option',
            'employment_type', 'experience_level', 'remote_type',
            'application_status', 'urgency_level', 'notes',
            'source_platform', 'extraction_confidence', 'extraction_method',
            'auto_discovered', 'saved_from_extension'
        ]

    def create(self, validated_data):
        # Set user from context
        validated_data['user'] = self.context['request'].user

        # Auto-detect and set fields if not provided
        if not validated_data.get('employment_type'):
            validated_data['employment_type'] = self._detect_employment_type(validated_data)

        if not validated_data.get('experience_level'):
            validated_data['experience_level'] = self._detect_experience_level(validated_data)

        if not validated_data.get('remote_type'):
            validated_data['remote_type'] = self._detect_remote_type(validated_data)

        return super().create(validated_data)

    def _detect_employment_type(self, data):
        """Auto-detect employment type from job title or description"""
        job_text = f"{data.get('job_title', '')} {data.get('job_description', '')}".lower()

        if any(word in job_text for word in ['intern', 'internship']):
            return 'internship'
        elif any(word in job_text for word in ['contract', 'contractor', 'freelance']):
            return 'contract'
        elif any(word in job_text for word in ['part time', 'part-time', 'pt ']):
            return 'part_time'
        elif any(word in job_text for word in ['temporary', 'temp ', 'seasonal']):
            return 'temporary'
        elif any(word in job_text for word in ['volunteer']):
            return 'volunteer'
        else:
            return 'full_time'  # Default assumption

    def _detect_experience_level(self, data):
        """Auto-detect experience level from job title or description"""
        job_text = f"{data.get('job_title', '')} {data.get('job_description', '')}".lower()

        if any(word in job_text for word in ['intern', 'internship']):
            return 'intern'
        elif any(word in job_text for word in ['entry', 'entry-level', 'graduate', 'junior']):
            return 'entry_level'
        elif any(word in job_text for word in ['senior', 'sr.', 'sr ']):
            return 'senior'
        elif any(word in job_text for word in ['lead', 'principal', 'staff']):
            return 'lead'
        elif any(word in job_text for word in ['director', 'head of', 'vp', 'vice president']):
            return 'director'
        elif any(word in job_text for word in ['manager', 'mgr']):
            return 'manager'
        elif any(word in job_text for word in ['associate']):
            return 'associate'
        else:
            return 'mid_level'  # Default assumption

    def _detect_remote_type(self, data):
        """Auto-detect remote type from location and job description"""
        location = data.get('location', '').lower()
        remote_option = data.get('remote_option', '').lower()
        job_text = f"{data.get('job_title', '')} {data.get('job_description', '')}".lower()

        if any(word in f"{location} {remote_option} {job_text}" for word in ['remote', 'work from home', 'wfh']):
            if any(word in f"{location} {remote_option} {job_text}" for word in ['hybrid', 'flexible']):
                return 'hybrid'
            else:
                return 'remote'
        elif any(word in f"{location} {remote_option} {job_text}" for word in ['hybrid']):
            return 'hybrid'
        elif any(word in f"{location} {remote_option} {job_text}" for word in ['travel', 'traveling']):
            return 'travel_required'
        elif any(word in f"{location} {remote_option} {job_text}" for word in ['relocat', 'relocation']):
            return 'relocate_required'
        else:
            return 'onsite'  # Default assumption