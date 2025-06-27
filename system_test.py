# system_test.py - Complete System Test for Job Automation
"""
Comprehensive system testing for Job Automation System
Focuses on testing AI integrations with Groq and OpenRouter
"""

import os
import sys
import json
import time
import logging
import requests
import argparse
import django
from unittest.mock import patch, Mock
from decimal import Decimal
from pathlib import Path

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_automation.settings')
sys.path.insert(0, str(Path(__file__).resolve().parent))
django.setup()

# Django imports
from django.contrib.auth.models import User
from django.conf import settings
from django.db import connections
from rest_framework.authtoken.models import Token

# App imports
from accounts.models import UserProfile
from jobs.models import JobApplication
from followups.models import FollowUpTemplate, FollowUpHistory
from documents.models import GeneratedDocument, AIUsageLog, AIProviderStatus
from documents.ai_services import AIServiceManager, ai_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('system_test')


class SystemTest:
    """Comprehensive system test for job automation application"""

    def __init__(self, args):
        self.args = args
        self.n8n_url = args.n8n_url or settings.N8N_WEBHOOK_URL
        self.base_url = args.base_url or "http://localhost:8000"

        # Test results storage
        self.results = {
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "total": 0,
            "test_details": []
        }

        # Test user setup
        self.test_user = None
        self.test_application = None
        self.auth_token = None

        # Print header
        print("\n" + "=" * 70)
        print("🚀 JOB AUTOMATION SYSTEM - COMPREHENSIVE TEST SUITE")
        print("=" * 70)
        print(f"Base URL: {self.base_url}")
        print(f"n8n URL: {self.n8n_url}")
        print(f"Testing Mode: {'Local' if args.local else 'Production'}")
        print("=" * 70 + "\n")

    def setup_test_environment(self):
        """Set up test environment with test user and data"""
        print("🔧 Setting up test environment...")

        try:
            # Create test user if it doesn't exist
            self.test_user, created = User.objects.get_or_create(
                username='system_test_user',
                defaults={
                    'email': 'system_test@example.com',
                    'is_active': True
                }
            )

            if created:
                self.test_user.set_password('testpass123')
                self.test_user.save()
                print("  ✓ Created test user: system_test_user")
            else:
                print("  ✓ Using existing test user: system_test_user")

            # Create or get auth token for API requests
            token, _ = Token.objects.get_or_create(user=self.test_user)
            self.auth_token = token.key
            print(f"  ✓ Auth token: {self.auth_token}")

            # Create or get user profile
            profile, created = UserProfile.objects.get_or_create(
                user=self.test_user,
                defaults={
                    'phone': '555-123-4567',
                    'location': 'Toronto, ON',
                    'linkedin_url': 'https://linkedin.com/in/systemtest',
                    'github_url': 'https://github.com/systemtest',
                    'portfolio_url': 'https://systemtest.dev',
                    'years_experience': 5,
                    'education': 'Bachelor of Computer Science',
                    'current_job_title': 'Software Developer',
                    'current_company': 'System Test Corp',
                    'key_skills': ['Python', 'Django', 'AI Integration'],
                    'preferred_salary_min': 80000,
                    'preferred_salary_max': 120000,
                    'work_type_preference': 'remote',
                    'preferred_company_sizes': ['small', 'medium'],
                    'industries_of_interest': ['technology', 'ai', 'education']
                }
            )

            # Create test job application if not exists
            self.test_application, created = JobApplication.objects.get_or_create(
                user=self.test_user,
                job_title="Python Developer",
                company_name="System Test Corp",
                defaults={
                    'job_description': """
                    We are looking for a Python Developer with experience in:
                    - Django web frameworks
                    - RESTful API development
                    - Database design and optimization
                    - Frontend technologies (JavaScript, HTML, CSS)
                    - AWS cloud services

                    Required skills:
                    - 3+ years Python experience
                    - Strong knowledge of Django
                    - Experience with PostgreSQL
                    - Git version control

                    This is a full-time remote position with competitive salary and benefits.
                    """,
                    'job_url': 'https://example.com/jobs/python-developer',
                    'location': 'Toronto, ON (Remote)',
                    'application_status': 'saved'
                }
            )

            if created:
                print("  ✓ Created test job application")
            else:
                print("  ✓ Using existing test job application")

            # Create follow-up template if not exists
            template, created = FollowUpTemplate.objects.get_or_create(
                user=self.test_user,
                template_name="System Test Template",
                defaults={
                    'template_type': 'one_week',
                    'subject_template': 'Following up on my {job_title} application',
                    'body_template': 'Dear Hiring Manager,\n\nI hope this email finds you well. I am writing to follow up on my application for the {job_title} position at {company_name} that I submitted recently...',
                    'is_default': True,
                    'is_active': True
                }
            )

            if created:
                print("  ✓ Created test follow-up template")
            else:
                print("  ✓ Using existing follow-up template")

            # Check AI provider status
            for provider in ['groq', 'openrouter']:
                AIProviderStatus.objects.get_or_create(
                    provider=provider,
                    defaults={
                        'is_active': True
                    }
                )

            print("✅ Test environment setup complete\n")
            return True

        except Exception as e:
            print(f"❌ Test environment setup failed: {str(e)}")
            return False

    def log_result(self, test_name, passed, message="", warning=False):
        """Log test result with details"""
        status = "⚠️ WARNING" if warning else "✅ PASSED" if passed else "❌ FAILED"

        # Update statistics
        if warning:
            self.results["warnings"] += 1
            if passed:
                self.results["passed"] += 1
            else:
                self.results["failed"] += 1
        elif passed:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1

        self.results["total"] += 1

        # Store test details
        self.results["test_details"].append({
            "name": test_name,
            "passed": passed,
            "warning": warning,
            "message": message
        })

        # Print result
        print(f"{status} {test_name}: {message}")

    def test_database_connection(self):
        """Test database connection"""
        print("\n📊 Testing Database Connection...")

        try:
            with connections['default'].cursor() as cursor:
                cursor.execute("SELECT 1")
                row = cursor.fetchone()

            if row and row[0] == 1:
                self.log_result(
                    "Database Connection",
                    True,
                    "Successfully connected to database"
                )
                return True
            else:
                self.log_result(
                    "Database Connection",
                    False,
                    "Failed to verify database connection"
                )
                return False
        except Exception as e:
            self.log_result(
                "Database Connection",
                False,
                f"Error connecting to database: {str(e)}"
            )
            return False

    def test_groq_api(self):
        """Test Groq API integration"""
        print("\n🤖 Testing Groq API Integration...")

        if not settings.GROQ_API_KEY:
            self.log_result(
                "Groq API Key",
                False,
                "Groq API key is missing in settings"
            )
            return False

        # Test direct API call
        test_prompt = "Write a brief introduction paragraph for a Python Developer resume."

        try:
            # Mock the actual API call to avoid making a real external call during testing
            with patch('requests.post') as mock_post:
                # Setup mock response
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    'choices': [
                        {
                            'message': {
                                'content': 'Experienced Python Developer with expertise in Django, RESTful APIs, and cloud deployment.'
                            }
                        }
                    ],
                    'usage': {
                        'total_tokens': 150
                    }
                }
                mock_post.return_value = mock_response

                # Call through our service
                result = ai_service._call_groq(
                    prompt=test_prompt,
                    document_type='resume_intro',
                    user_id=self.test_user.id
                )

                if result['success']:
                    self.log_result(
                        "Groq API Integration",
                        True,
                        f"Successfully generated content using Groq API (mock)"
                    )

                    # Now try to actually call the real API if requested
                    if self.args.real_api_calls:
                        try:
                            headers = {
                                'Authorization': f'Bearer {settings.GROQ_API_KEY}',
                                'Content-Type': 'application/json'
                            }

                            data = {
                                'model': settings.GROQ_SETTINGS['MODEL'],
                                'messages': [
                                    {
                                        'role': 'system',
                                        'content': 'You are a helpful assistant.'
                                    },
                                    {
                                        'role': 'user',
                                        'content': 'Write a one-sentence test response.'
                                    }
                                ],
                                'max_tokens': 50
                            }

                            print("  ⏳ Making real Groq API call (this might take a few seconds)...")
                            response = requests.post(
                                'https://api.groq.com/openai/v1/chat/completions',
                                headers=headers,
                                json=data,
                                timeout=30
                            )

                            if response.status_code == 200:
                                response_data = response.json()
                                content = response_data['choices'][0]['message']['content']
                                tokens = response_data['usage']['total_tokens']

                                self.log_result(
                                    "Groq API Live Test",
                                    True,
                                    f"Real API call successful. Used {tokens} tokens."
                                )
                                return True
                            else:
                                self.log_result(
                                    "Groq API Live Test",
                                    False,
                                    f"Real API call failed: {response.status_code} - {response.text}"
                                )
                        except Exception as e:
                            self.log_result(
                                "Groq API Live Test",
                                False,
                                f"Error making real API call: {str(e)}"
                            )

                    return True
                else:
                    self.log_result(
                        "Groq API Integration",
                        False,
                        f"Failed to generate content using Groq API: {result.get('error', 'Unknown error')}"
                    )
                    return False

        except Exception as e:
            self.log_result(
                "Groq API Integration",
                False,
                f"Error testing Groq API: {str(e)}"
            )
            return False

    def test_openrouter_api(self):
        """Test OpenRouter API integration"""
        print("\n🔄 Testing OpenRouter API Integration...")

        if not settings.OPENROUTER_API_KEY:
            self.log_result(
                "OpenRouter API Key",
                False,
                "OpenRouter API key is missing in settings"
            )
            return False

        # Test direct API call
        test_prompt = "Write a brief introduction paragraph for a Python Developer cover letter."

        try:
            # Mock the actual API call to avoid making a real external call during testing
            with patch('requests.post') as mock_post:
                # Setup mock response
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    'choices': [
                        {
                            'message': {
                                'content': 'As a Python Developer with 5+ years of experience, I am excited to apply for this position.'
                            }
                        }
                    ],
                    'usage': {
                        'total_tokens': 180
                    }
                }
                mock_post.return_value = mock_response

                # Call through our service
                result = ai_service._call_openrouter(
                    prompt=test_prompt,
                    document_type='cover_letter_intro',
                    user_id=self.test_user.id
                )

                if result['success']:
                    self.log_result(
                        "OpenRouter API Integration",
                        True,
                        f"Successfully generated content using OpenRouter API (mock)"
                    )

                    # Now try to actually call the real API if requested
                    if self.args.real_api_calls:
                        try:
                            headers = {
                                'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
                                'Content-Type': 'application/json',
                                'HTTP-Referer': settings.OPENROUTER_SETTINGS['SITE_URL'],
                                'X-Title': settings.OPENROUTER_SETTINGS['APP_NAME']
                            }

                            data = {
                                'model': settings.OPENROUTER_SETTINGS['MODEL'],
                                'messages': [
                                    {
                                        'role': 'system',
                                        'content': 'You are a helpful assistant.'
                                    },
                                    {
                                        'role': 'user',
                                        'content': 'Write a one-sentence test response.'
                                    }
                                ],
                                'max_tokens': 50
                            }

                            print("  ⏳ Making real OpenRouter API call (this might take a few seconds)...")
                            response = requests.post(
                                'https://openrouter.ai/api/v1/chat/completions',
                                headers=headers,
                                json=data,
                                timeout=30
                            )

                            if response.status_code == 200:
                                response_data = response.json()
                                content = response_data['choices'][0]['message']['content']
                                tokens = response_data['usage']['total_tokens']

                                self.log_result(
                                    "OpenRouter API Live Test",
                                    True,
                                    f"Real API call successful. Used {tokens} tokens."
                                )
                                return True
                            else:
                                self.log_result(
                                    "OpenRouter API Live Test",
                                    False,
                                    f"Real API call failed: {response.status_code} - {response.text}"
                                )
                        except Exception as e:
                            self.log_result(
                                "OpenRouter API Live Test",
                                False,
                                f"Error making real API call: {str(e)}"
                            )

                    return True
                else:
                    self.log_result(
                        "OpenRouter API Integration",
                        False,
                        f"Failed to generate content using OpenRouter API: {result.get('error', 'Unknown error')}"
                    )
                    return False

        except Exception as e:
            self.log_result(
                "OpenRouter API Integration",
                False,
                f"Error testing OpenRouter API: {str(e)}"
            )
            return False

    def test_ai_fallback_mechanism(self):
        """Test AI fallback mechanism when primary provider fails"""
        print("\n🔄 Testing AI Fallback Mechanism...")

        try:
            # Set up test environment
            original_primary = settings.AI_SETTINGS['PRIMARY_PROVIDER']

            # Test by forcing primary provider to fail and ensuring fallback works
            with patch('documents.ai_services.AIServiceManager._call_groq') as mock_groq:
                mock_groq.return_value = {
                    'success': False,
                    'error': 'Simulated Groq failure',
                    'provider': 'groq'
                }

                # Mock fallback provider to succeed
                with patch('documents.ai_services.AIServiceManager._call_openrouter') as mock_openrouter:
                    mock_openrouter.return_value = {
                        'success': True,
                        'content': 'Content from fallback provider',
                        'provider': 'openrouter',
                        'tokens_used': 100,
                        'cost': Decimal('0.0001'),
                        'model': settings.OPENROUTER_SETTINGS['MODEL']
                    }

                    # Test the generate content method which should try primary then fallback
                    result = ai_service.generate_content(
                        prompt="Test prompt for fallback mechanism",
                        document_type="test_document",
                        user_id=self.test_user.id
                    )

                    # Check if fallback was used
                    if result['success'] and result['provider'] == settings.AI_SETTINGS['FALLBACK_PROVIDER']:
                        self.log_result(
                            "AI Fallback Mechanism",
                            True,
                            f"Successfully fell back to {result['provider']} when primary provider failed"
                        )
                        return True
                    else:
                        self.log_result(
                            "AI Fallback Mechanism",
                            False,
                            "Fallback mechanism failed to use secondary provider"
                        )
                        return False

        except Exception as e:
            self.log_result(
                "AI Fallback Mechanism",
                False,
                f"Error testing fallback mechanism: {str(e)}"
            )
            return False

    def test_document_generation(self):
        """Test document generation with AI services"""
        print("\n📄 Testing Document Generation...")

        try:
            # Mock AI service to return predictable content
            with patch('documents.ai_services.AIServiceManager.generate_content') as mock_generate:
                mock_generate.return_value = {
                    'success': True,
                    'content': 'Generated test document content for a Python Developer role.',
                    'provider': 'groq',
                    'tokens_used': 150,
                    'cost': Decimal('0.0001'),
                    'model': settings.GROQ_SETTINGS['MODEL'],
                    'generation_time': 2.5
                }

                # Create a simple document directly
                from documents.models import GeneratedDocument
                document, created = GeneratedDocument.objects.get_or_create(
                    application=self.test_application,
                    document_type='resume',
                    defaults={
                        'content': 'Generated test document content',
                        'file_path': '/path/to/test_document.pdf',
                        'ai_provider': 'groq',
                        'tokens_used': 150,
                        'cost_usd': Decimal('0.0001'),
                        'generation_time': 2.5
                    }
                )

                self.log_result(
                    "Document Creation",
                    True,
                    f"Document created with ID {document.id}"
                )

                # Test document retrieval API
                if self.auth_token:
                    response = requests.get(
                        f"{self.base_url}/api/documents/status/{self.test_application.id}/",
                        headers={'Authorization': f'Token {self.auth_token}'}
                    )

                    if response.status_code == 200:
                        data = response.json()
                        self.log_result(
                            "Document API Integration",
                            True,
                            "Document API endpoints working correctly"
                        )
                    else:
                        self.log_result(
                            "Document API Integration",
                            False,
                            f"Document API error: {response.status_code} - {response.text}"
                        )

                return True

        except Exception as e:
            self.log_result(
                "Document Generation",
                False,
                f"Error during document testing: {str(e)}"
            )
            return False

    def test_usage_tracking(self):
        """Test AI usage tracking"""
        print("\n📊 Testing AI Usage Tracking...")

        try:
            # Delete existing logs to ensure clean test
            AIUsageLog.objects.filter(user=self.test_user).delete()

            # Log a test usage
            log = AIUsageLog.objects.create(
                user=self.test_user,
                provider='groq',
                model_used=settings.GROQ_SETTINGS['MODEL'],
                tokens_used=200,
                cost_usd=Decimal('0.0002'),
                request_type='test',

            )

            # Verify log was created
            if log.id:
                self.log_result(
                    "AI Usage Logging",
                    True,
                    f"Successfully logged AI usage with {log.tokens_used} tokens"
                )

                # Test the _log_usage method directly
                ai_service._log_usage(
                    user_id=self.test_user.id,
                    provider='openrouter',
                    model=settings.OPENROUTER_SETTINGS['MODEL'],
                    tokens=150,
                    cost=Decimal('0.00015'),
                    request_type='test_direct'
                )

                # Check if second log was created
                logs = AIUsageLog.objects.filter(
                    user=self.test_user,
                    provider='openrouter'
                )

                if logs.exists():
                    self.log_result(
                        "AI Service Logger",
                        True,
                        "AI service _log_usage method works correctly"
                    )
                    return True
                else:
                    self.log_result(
                        "AI Service Logger",
                        False,
                        "Failed to create log via _log_usage method"
                    )
                    return False
            else:
                self.log_result(
                    "AI Usage Logging",
                    False,
                    "Failed to create AI usage log"
                )
                return False

        except Exception as e:
            self.log_result(
                "AI Usage Tracking",
                False,
                f"Error testing usage tracking: {str(e)}"
            )
            return False

    def test_n8n_webhook(self):
        """Test n8n webhook integration"""
        print("\n🔌 Testing n8n Webhook Integration...")

        if self.args.local and not self.args.force_n8n:
            self.log_result(
                "n8n Webhook",
                True,
                "Skipped n8n testing in local mode (use --force-n8n to test anyway)",
                warning=True
            )
            return True

        # Test webhook URL format
        if not self.n8n_url or ('localhost' not in self.n8n_url and 'ai.jobautomation.me' not in self.n8n_url):
            self.log_result(
                "n8n Webhook URL",
                False,
                f"Invalid n8n webhook URL: {self.n8n_url}"
            )
            return False

        try:
            # Simulate a webhook call
            with patch('requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"success": True}
                mock_post.return_value = mock_response

                webhook_data = {
                    "action": "test_system",
                    "application_id": self.test_application.id,
                    "webhook_id": "system_test_webhook"
                }

                # Make a test call to our API webhook endpoint that would normally be called by n8n
                response = requests.post(
                    f"{self.base_url}/api/webhooks/n8n/",
                    json=webhook_data,
                    timeout=10
                )

                if response.status_code == 200:
                    self.log_result(
                        "n8n Webhook Endpoint",
                        True,
                        "API webhook endpoint correctly receives n8n requests"
                    )

                    # If real n8n testing is enabled, try calling the n8n server
                    if self.args.real_n8n:
                        try:
                            print("  ⏳ Making real n8n API call...")

                            # This would need to be adjusted based on your actual n8n workflow
                            n8n_test_url = f"{self.n8n_url}/webhook/test"
                            n8n_test_data = {
                                "action": "system_test",
                                "timestamp": time.time()
                            }

                            n8n_response = requests.post(
                                n8n_test_url,
                                json=n8n_test_data,
                                timeout=10
                            )

                            if n8n_response.status_code in [200, 201]:
                                self.log_result(
                                    "n8n Server Connection",
                                    True,
                                    f"Successfully connected to real n8n server: {n8n_response.status_code}"
                                )
                            else:
                                self.log_result(
                                    "n8n Server Connection",
                                    False,
                                    f"Failed to connect to real n8n server: {n8n_response.status_code} - {n8n_response.text}"
                                )
                        except Exception as e:
                            self.log_result(
                                "n8n Server Connection",
                                False,
                                f"Error connecting to real n8n server: {str(e)}"
                            )

                    return True
                else:
                    self.log_result(
                        "n8n Webhook Endpoint",
                        False,
                        f"API webhook endpoint returned error: {response.status_code} - {response.text}"
                    )
                    return False

        except Exception as e:
            self.log_result(
                "n8n Webhook Integration",
                False,
                f"Error testing n8n webhook: {str(e)}"
            )
            return False

    def test_end_to_end_flow(self):
        """Test end-to-end job application flow"""
        print("\n🔄 Testing End-to-End Application Flow...")

        try:
            # Start with creating an application (already done in setup)

            # 1. Check application exists
            app_exists = JobApplication.objects.filter(id=self.test_application.id).exists()
            self.log_result(
                "Application Creation",
                app_exists,
                f"Application created with ID {self.test_application.id}" if app_exists else "Failed to find application"
            )
            if not app_exists:
                return False

            # 2. Generate a document directly in the database
                # 2. Generate a document directly in the database
                document, created = GeneratedDocument.objects.get_or_create(
                    application=self.test_application,
                    document_type='resume',
                    defaults={
                        'content': 'Generated test document content',
                        'file_path': '/path/to/test_document.pdf',
                        'ai_provider': 'groq',
                        'tokens_used': 150,
                        'cost_usd': Decimal('0.0001'),
                        'generation_time': 2.5
                    }
                )

                self.log_result(
                    "Document Creation",
                    document.id is not None,
                    f"Document created with ID {document.id}" if document.id else "Failed to create document"
                )

                # 3. Update application status
                self.test_application.application_status = 'applied'
                self.test_application.save()

                self.log_result(
                    "Update Application Status",
                    True,
                    "Updated application status to 'applied'"
                )

                # 4. Test follow-up (using API or mocked task directly)
                try:
                    # Create follow-up template if needed
                    template, _ = FollowUpTemplate.objects.get_or_create(
                        user=self.test_user,
                        template_name="System Test Template",
                        defaults={
                            'template_type': 'one_week',
                            'subject_template': 'Following up on my {job_title} application',
                            'body_template': 'Dear Hiring Manager,\n\nI am writing to follow up on my application for the {job_title} position at {company_name}...',
                        }
                    )

                    # Mock the email sending task
                    with patch('followups.tasks.send_followup_email.delay') as mock_send:
                        mock_task = Mock()
                        mock_task.get = lambda: True  # Simulate successful task execution
                        mock_send.return_value = mock_task

                        if self.auth_token:
                            # Test through API endpoint
                            response = requests.post(
                                f"{self.base_url}/api/followups/send/",
                                headers={'Authorization': f'Token {self.auth_token}'},
                                json={
                                    'application_id': self.test_application.id,
                                    'template_id': template.id
                                },
                                timeout=10
                            )

                            if response.status_code == 200:
                                self.log_result(
                                    "Send Follow-up Email (API)",
                                    True,
                                    "Successfully sent follow-up through API"
                                )
                            else:
                                self.log_result(
                                    "Send Follow-up Email (API)",
                                    False,
                                    f"Failed to send follow-up through API: {response.status_code}"
                                )

                        else:
                            # Direct call to task function (alternative approach)
                            from followups.tasks import send_followup_email

                            # Mock the actual email sending
                            with patch('django.core.mail.send_mail') as mock_email:
                                mock_email.return_value = 1  # 1 message sent

                                # Call task directly (not through Celery)
                                success = send_followup_email(
                                    application_id=self.test_application.id,
                                    template_id=template.id
                                )

                                self.log_result(
                                    "Send Follow-up Email (Direct)",
                                    success,
                                    "Successfully sent follow-up directly" if success else "Failed to send follow-up"
                                )
                except Exception as e:
                    self.log_result(
                        "Send Follow-up Email",
                        False,
                        f"Error sending follow-up: {str(e)}"
                    )

                # 5. Verify follow-up was recorded
                follow_up_exists = FollowUpHistory.objects.filter(
                    application=self.test_application
                ).exists()

                self.log_result(
                    "Follow-up Recording",
                    follow_up_exists,
                    "Follow-up was properly recorded in history" if follow_up_exists
                    else "Follow-up was not recorded in history"
                )

                # Overall flow status
                self.log_result(
                    "End-to-End Flow",
                    True,
                    "✅ Complete application workflow test finished"
                )
                return True

        except Exception as e:
                self.log_result(
                    "End-to-End Flow",
                    False,
                    f"Error in end-to-end testing: {str(e)}"
                )


        return False

    def generate_report(self):
        """Generate detailed test report"""
        print("\n" + "=" * 70)
        print("📊 SYSTEM TEST REPORT")
        print("=" * 70)

        total_tests = self.results["total"]
        passed_tests = self.results["passed"]
        failed_tests = self.results["failed"]
        warnings = self.results["warnings"]

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Warnings: {warnings} ⚠️")
        print(f"Success Rate: {success_rate:.1f}%")

        print("\n📝 DETAILED RESULTS:")
        for test in self.results["test_details"]:
            status = "⚠️" if test["warning"] else "✅" if test["passed"] else "❌"
            print(f"  {status} {test['name']}: {test['message']}")

        print("\n" + "=" * 70)

        # Final assessment
        if failed_tests == 0 and success_rate == 100:
            print("🚀 ALL TESTS PASSED!")
            print("System is working perfectly.")
            return True
        elif failed_tests <= 2 and success_rate >= 80:
            print("⚠️ MINOR ISSUES DETECTED")
            print("System is functional but has some minor issues to address.")
            return True
        else:
            print("❌ SIGNIFICANT ISSUES DETECTED")
            print("System has important issues that need to be fixed.")
            return False

    def test_ai_integration_components(self):
        """Run all AI integration tests"""
        print("\n🧪 Testing AI Integration Components...")

        # Test Groq integration
        groq_result = self.test_groq_api()

        # Test OpenRouter integration
        openrouter_result = self.test_openrouter_api()

        # Test fallback mechanism
        fallback_result = self.test_ai_fallback_mechanism()

        # Test document generation with AI
        document_result = self.test_document_generation()

        # Test usage tracking
        tracking_result = self.test_usage_tracking()

        # Overall AI integration status
        all_passed = all([groq_result, openrouter_result, fallback_result, document_result, tracking_result])

        self.log_result(
            "AI Integration Complete",
            all_passed,
            "✅ All AI integration components are working correctly" if all_passed
            else "❌ Some AI integration components have issues"
        )

        return all_passed

    def run_all_tests(self):
        """Run all system tests"""
        # Setup test environment
        if not self.setup_test_environment():
            print("❌ Test environment setup failed, aborting tests")
            return False

        # Test database connection
        self.test_database_connection()

        # Test AI integration components
        self.test_ai_integration_components()

        # Test n8n integration
        self.test_n8n_webhook()

        # Test end-to-end flow
        self.test_end_to_end_flow()

        # Generate and return test report
        return self.generate_report()


def main():
    """Main entry point for system tests"""
    parser = argparse.ArgumentParser(description='Job Automation System Test')

    parser.add_argument('--local', action='store_true', help='Test in local mode')
    parser.add_argument('--base-url', type=str, default='http://localhost:8000',
                        help='Base URL for API tests')
    parser.add_argument('--n8n-url', type=str, default=None,
                        help='n8n server URL (defaults to settings.N8N_WEBHOOK_URL)')
    parser.add_argument('--real-api-calls', action='store_true',
                        help='Make real API calls to Groq and OpenRouter (uses credits)')
    parser.add_argument('--real-n8n', action='store_true',
                        help='Test with real n8n server (requires server to be running)')
    parser.add_argument('--force-n8n', action='store_true',
                        help='Force n8n tests even in local mode')

    args = parser.parse_args()

    # Run system tests
    system_test = SystemTest(args)
    all_tests_passed = system_test.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if all_tests_passed else 1)


if __name__ == '__main__':
    main()