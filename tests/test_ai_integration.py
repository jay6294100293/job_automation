# tests/test_ai_integration.py
"""
Test module for AI integration with Groq and OpenRouter
"""
import json
from decimal import Decimal
from unittest.mock import patch, Mock
from django.test import TestCase
from django.contrib.auth.models import User
from django.conf import settings

from accounts.models import UserProfile
from jobs.models import JobApplication
from documents.models import GeneratedDocument, AIUsageLog, AIProviderStatus
from documents.ai_services import AIServiceManager, ai_service


class AIProviderTests(TestCase):
    """Test AI provider integrations"""

    def setUp(self):
        """Set up test environment"""
        self.user = User.objects.create_user(
            username='ai_test_user',
            email='ai_test@example.com',
            password='testpass123'
        )

        self.profile = UserProfile.objects.create(
            user=self.user,
            full_name='AI Test User',
            current_job_title='Software Developer'
        )

        self.application = JobApplication.objects.create(
            user=self.user,
            job_title='Python Developer',
            company_name='AI Test Company',
            job_description='Looking for a Python developer with Django experience.',
            job_url='https://example.com/job',
            location='Remote',
            application_status='saved'
        )

        # Ensure provider status records exist
        for provider in ['groq', 'openrouter']:
            AIProviderStatus.objects.get_or_create(
                provider=provider,
                defaults={
                    'is_active': True,
                }
            )

    def test_groq_api_call(self):
        """Test Groq API call"""
        with patch('requests.post') as mock_post:
            # Mock response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'choices': [
                    {
                        'message': {
                            'content': 'Test content from Groq API'
                        }
                    }
                ],
                'usage': {
                    'total_tokens': 100
                }
            }
            mock_post.return_value = mock_response

            # Call the API
            result = ai_service._call_groq(
                prompt='Test prompt',
                document_type='test',
                user_id=self.user.id
            )

            # Assert success
            self.assertTrue(result['success'])
            self.assertEqual(result['provider'], 'groq')
            self.assertEqual(result['content'], 'Test content from Groq API')
            self.assertEqual(result['tokens_used'], 100)

            # Verify the API was called correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args

            # Check API URL
            self.assertEqual(call_args[0][0], 'https://api.groq.com/openai/v1/chat/completions')

            # Check model
            call_kwargs = call_args[1]['json']
            self.assertEqual(call_kwargs['model'], settings.GROQ_SETTINGS['MODEL'])

    def test_openrouter_api_call(self):
        """Test OpenRouter API call"""
        with patch('requests.post') as mock_post:
            # Mock response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'choices': [
                    {
                        'message': {
                            'content': 'Test content from OpenRouter API'
                        }
                    }
                ],
                'usage': {
                    'total_tokens': 120
                }
            }
            mock_post.return_value = mock_response

            # Call the API
            result = ai_service._call_openrouter(
                prompt='Test prompt',
                document_type='test',
                user_id=self.user.id
            )

            # Assert success
            self.assertTrue(result['success'])
            self.assertEqual(result['provider'], 'openrouter')
            self.assertEqual(result['content'], 'Test content from OpenRouter API')
            self.assertEqual(result['tokens_used'], 120)

            # Verify the API was called correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args

            # Check API URL
            self.assertEqual(call_args[0][0], 'https://openrouter.ai/api/v1/chat/completions')

            # Check model and headers
            headers = call_args[1]['headers']
            self.assertIn('X-Title', headers)
            self.assertIn('HTTP-Referer', headers)

            call_kwargs = call_args[1]['json']
            self.assertEqual(call_kwargs['model'], settings.OPENROUTER_SETTINGS['MODEL'])

    def test_provider_fallback(self):
        """Test provider fallback mechanism"""
        # Mock primary provider to fail
        with patch('documents.ai_services.AIServiceManager._call_groq') as mock_primary:
            mock_primary.return_value = {
                'success': False,
                'error': 'Test failure',
                'provider': 'groq'
            }

            # Mock fallback provider to succeed
            with patch('documents.ai_services.AIServiceManager._call_openrouter') as mock_fallback:
                mock_fallback.return_value = {
                    'success': True,
                    'content': 'Test content from fallback',
                    'provider': 'openrouter',
                    'tokens_used': 150,
                    'cost': Decimal('0.0001'),
                    'model': settings.OPENROUTER_SETTINGS['MODEL']
                }

                # Call generate_content which should try primary then fallback
                result = ai_service.generate_content(
                    prompt='Test prompt',
                    document_type='test',
                    user_id=self.user.id
                )

                # Assert fallback was used
                self.assertTrue(result['success'])
                self.assertEqual(result['provider'], 'openrouter')
                self.assertEqual(result['content'], 'Test content from fallback')

                # Verify both providers were called in order
                mock_primary.assert_called_once()
                mock_fallback.assert_called_once()

    def test_usage_logging(self):
        """Test usage logging functionality"""
        # Clear existing logs
        AIUsageLog.objects.all().delete()

        # Use the _log_usage method
        ai_service._log_usage(
            user_id=self.user.id,
            provider='groq',
            model=settings.GROQ_SETTINGS['MODEL'],
            tokens=200,
            cost=Decimal('0.0002'),
            request_type='test'
        )

        # Check if log was created
        logs = AIUsageLog.objects.all()
        self.assertEqual(logs.count(), 1)

        log = logs.first()
        self.assertEqual(log.user.id, self.user.id)
        self.assertEqual(log.provider, 'groq')
        self.assertEqual(log.tokens_used, 200)
        self.assertEqual(log.cost_usd, Decimal('0.0002'))
        self.assertEqual(log.request_type, 'test')

    def test_provider_status_tracking(self):
        """Test provider status tracking"""
        # Test success tracking
        initial_status = AIProviderStatus.objects.get(provider='groq')
        initial_success = initial_status.success_count

        # Record a success
        ai_service._update_provider_success('groq')

        # Verify status was updated
        updated_status = AIProviderStatus.objects.get(provider='groq')
        self.assertEqual(updated_status.success_count, initial_success + 1)
        self.assertIsNotNone(updated_status.last_success)

        # Test failure tracking
        initial_failures = updated_status.failure_count

        # Record a failure
        ai_service._update_provider_failure('groq')

        # Verify failure was recorded
        final_status = AIProviderStatus.objects.get(provider='groq')
        self.assertEqual(final_status.failure_count, initial_failures + 1)
        self.assertIsNotNone(final_status.last_failure)

    def test_budget_control(self):
        """Test monthly budget control"""
        # Mock provider to be over budget
        with patch('documents.ai_services.AIServiceManager._is_over_budget') as mock_budget:
            mock_budget.return_value = True

            # Try to generate content
            result = ai_service._try_provider(
                provider='groq',
                prompt='Test prompt',
                document_type='test',
                user_id=self.user.id
            )

            # Verify content generation was blocked due to budget
            self.assertFalse(result['success'])
            self.assertIn('budget', result['error'])


class DocumentGenerationTests(TestCase):
    """Test document generation with AI integration"""

    def setUp(self):
        """Set up test environment"""
        self.user = User.objects.create_user(
            username='doc_test_user',
            email='doc_test@example.com',
            password='testpass123'
        )

        self.profile = UserProfile.objects.create(
            user=self.user,
            full_name='Document Test User',
            current_job_title='Software Developer'
        )

        self.application = JobApplication.objects.create(
            user=self.user,
            job_title='Python Developer',
            company_name='Doc Test Company',
            job_description='Looking for a Python developer with Django experience.',
            job_url='https://example.com/job',
            location='Remote',
            application_status='saved'
        )

    def test_document_generation(self):
        """Test document generation with AI"""
        # Mock AI service
        with patch('documents.ai_services.AIServiceManager.generate_content') as mock_generate:
            mock_generate.return_value = {
                'success': True,
                'content': 'Generated document content',
                'provider': 'groq',
                'tokens_used': 200,
                'cost': Decimal('0.0002'),
                'model': 'llama3-70b-8192',
                'generation_time': 3.5
            }

            # Use document generator
            from documents.services import DocumentGenerator
            generator = DocumentGenerator()

            # Generate a document
            result = generator.generate_document(
                application_id=self.application.id,
                document_type='resume'
            )

            # Verify result
            self.assertTrue(result['success'])
            self.assertEqual(result['document_type'], 'resume')

            # Check if document was created in database
            doc = GeneratedDocument.objects.filter(
                application=self.application,
                document_type='resume'
            ).first()

            self.assertIsNotNone(doc)
            self.assertEqual(doc.content, 'Generated document content')
            self.assertEqual(doc.ai_provider, 'groq')
            self.assertEqual(doc.tokens_used, 200)

    def test_document_generation_failure_handling(self):
        """Test handling of document generation failures"""
        # Mock AI service to fail
        with patch('documents.ai_services.AIServiceManager.generate_content') as mock_generate:
            mock_generate.return_value = {
                'success': False,
                'error': 'Test failure',
                'provider': 'groq'
            }

            # Use document generator
            from documents.services import DocumentGenerator
            generator = DocumentGenerator()

            # Try to generate a document
            result = generator.generate_document(
                application_id=self.application.id,
                document_type='cover_letter'
            )

            # Verify failure was handled gracefully
            self.assertFalse(result['success'])
            self.assertEqual(result['error'], 'Test failure')

            # Ensure no document was created
            doc_count = GeneratedDocument.objects.filter(
                application=self.application,
                document_type='cover_letter'
            ).count()

            self.assertEqual(doc_count, 0)


if __name__ == '__main__':
    from django.core.management import execute_from_command_line

    execute_from_command_line(['manage.py', 'test', 'tests.test_ai_integration'])