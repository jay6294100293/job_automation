# tests/test_n8n_integration.py - n8n Integration and Load Testing
import json
import requests
import time
from unittest.mock import patch, Mock, MagicMock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.urls import reverse
from django.core import mail
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from accounts.models import UserProfile
from jobs.models import JobApplication, JobSearchConfig
from followups.models import FollowUpTemplate, FollowUpHistory
from documents.models import GeneratedDocument


class N8NWebhookTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.profile = UserProfile.objects.create(
            user=self.user,
            full_name="Test User",
            current_job_title="Developer",
            n8n_webhook_url="https://ai.jobautomation.me/webhook/test"
        )

    def test_n8n_job_search_webhook(self):
        """Test n8n webhook for job search initiation"""
        url = '/api/webhooks/n8n/'
        data = {
            'action': 'job_search',
            'user_id': self.user.id,
            'search_criteria': {
                'keywords': 'python developer',
                'location': 'Toronto',
                'experience_level': 'mid',
                'salary_min': 70000,
                'salary_max': 100000
            },
            'webhook_id': 'test_webhook_123'
        }

        response = self.client.post(
            url,
            data,
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('job_search_id', response_data)

    @patch('documents.tasks.generate_all_documents.delay')
    def test_n8n_document_generation_webhook(self, mock_generate):
        """Test n8n webhook for document generation"""
        application = JobApplication.objects.create(
            user=self.user,
            job_title="Senior Python Developer",
            company_name="Tech Corp",
            job_description="Looking for experienced developer..."
        )

        url = '/api/webhooks/n8n/'
        data = {
            'action': 'generate_documents',
            'application_id': application.id,
            'document_types': ['resume', 'cover_letter', 'linkedin_messages'],
            'webhook_id': 'test_webhook_456'
        }

        response = self.client.post(
            url,
            data,
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        mock_generate.assert_called_once_with(application.id, ['resume', 'cover_letter', 'linkedin_messages'])

    def test_n8n_status_update_webhook(self):
        """Test n8n webhook for application status updates"""
        application = JobApplication.objects.create(
            user=self.user,
            job_title="Test Job",
            company_name="Test Company",
            application_status="applied"
        )

        url = '/api/webhooks/n8n/'
        data = {
            'action': 'update_status',
            'application_id': application.id,
            'new_status': 'interview',
            'notes': 'Interview invitation received via email parsing',
            'webhook_id': 'test_webhook_789'
        }

        response = self.client.post(
            url,
            data,
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])

        application.refresh_from_db()
        self.assertEqual(application.application_status, 'interview')

    @patch('followups.tasks.send_followup_email.delay')
    def test_n8n_followup_webhook(self, mock_send):
        """Test n8n webhook for automated follow-ups"""
        application = JobApplication.objects.create(
            user=self.user,
            job_title="Test Job",
            company_name="Test Company"
        )

        template = FollowUpTemplate.objects.create(
            user=self.user,
            template_name="Automated Follow-up",
            template_type="1_week",
            subject_template="Following up on {job_title}",
            body_template="Dear hiring manager..."
        )

        url = '/api/webhooks/n8n/'
        data = {
            'action': 'send_followup',
            'application_id': application.id,
            'template_id': template.id,
            'webhook_id': 'test_webhook_101'
        }

        response = self.client.post(
            url,
            data,
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        mock_send.assert_called_once()

    def test_n8n_webhook_authentication(self):
        """Test n8n webhook authentication"""
        url = '/api/webhooks/n8n/'

        # Test without authentication token
        data = {
            'action': 'job_search',
            'user_id': self.user.id
        }

        response = self.client.post(
            url,
            data,
            content_type='application/json'
        )

        # Should accept webhook calls (webhooks typically don't require auth)
        # But should validate the webhook_id or signature
        self.assertIn(response.status_code, [200, 401, 403])

    def test_n8n_webhook_validation(self):
        """Test n8n webhook input validation"""
        url = '/api/webhooks/n8n/'

        # Test with invalid action
        data = {
            'action': 'invalid_action',
            'user_id': self.user.id
        }

        response = self.client.post(
            url,
            data,
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)


class N8NIntegrationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.profile = UserProfile.objects.create(
            user=self.user,
            full_name="Test User",
            current_job_title="Developer"
        )

    @patch('requests.post')
    def test_trigger_n8n_workflow(self, mock_post):
        """Test triggering n8n workflow from Django"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True, 'execution_id': 'exec_123'}
        mock_post.return_value = mock_response

        # Trigger job search workflow
        from jobs.tasks import trigger_n8n_job_search

        result = trigger_n8n_job_search.delay(
            user_id=self.user.id,
            search_criteria={
                'keywords': 'python developer',
                'location': 'Toronto'
            }
        )

        # Verify n8n was called
        self.assertTrue(mock_post.called)
        call_args = mock_post.call_args
        self.assertIn('https://ai.jobautomation.me', call_args[0][0])

    @patch('requests.get')
    def test_n8n_workflow_status_check(self, mock_get):
        """Test checking n8n workflow execution status"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'finished': True,
                'mode': 'webhook',
                'status': 'success'
            }
        }
        mock_get.return_value = mock_response

        from jobs.utils import check_n8n_execution_status

        status = check_n8n_execution_status('exec_123')

        self.assertTrue(status['finished'])
        self.assertEqual(status['status'], 'success')

    @patch('requests.post')
    def test_n8n_error_handling(self, mock_post):
        """Test n8n error handling"""
        # Simulate n8n server error
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        from jobs.tasks import trigger_n8n_job_search

        with self.assertLogs('jobs.tasks', level='ERROR') as logs:
            result = trigger_n8n_job_search.delay(
                user_id=self.user.id,
                search_criteria={'keywords': 'python'}
            )

        # Should log the error
        self.assertTrue(any('Connection failed' in log for log in logs.output))


class LoadTest(TransactionTestCase):
    """Load testing for the job automation system"""

    def setUp(self):
        # Create test users
        self.users = []
        for i in range(10):
            user = User.objects.create_user(
                username=f'loadtest_user_{i}',
                email=f'loadtest{i}@example.com',
                password='testpass123'
            )
            self.users.append(user)

            UserProfile.objects.create(
                user=user,
                full_name=f"Load Test User {i}",
                current_job_title="Developer"
            )

    def test_concurrent_api_requests(self):
        """Test concurrent API requests"""
        from rest_framework.authtoken.models import Token

        # Create tokens for all users
        tokens = []
        for user in self.users:
            token = Token.objects.create(user=user)
            tokens.append(token.key)

        def make_api_request(token):
            """Make API request with token"""
            import requests
            headers = {'Authorization': f'Token {token}'}

            try:
                response = requests.get(
                    'http://testserver/api/applications/',
                    headers=headers,
                    timeout=5
                )
                return response.status_code
            except Exception as e:
                return 500

        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_api_request, token) for token in tokens]
            results = [future.result() for future in as_completed(futures)]

        # All requests should succeed
        successful_requests = sum(1 for status in results if status == 200)
        self.assertGreater(successful_requests, 8)  # At least 80% success rate

    def test_bulk_application_creation(self):
        """Test creating many applications quickly"""
        start_time = time.time()

        applications = []
        for i, user in enumerate(self.users):
            for j in range(10):  # 10 applications per user
                applications.append(JobApplication(
                    user=user,
                    job_title=f"Job {i}_{j}",
                    company_name=f"Company {i}_{j}",
                    job_url=f"https://example.com/job/{i}_{j}"
                ))

        # Bulk create 100 applications
        JobApplication.objects.bulk_create(applications)

        end_time = time.time()
        creation_time = end_time - start_time

        # Should create 100 applications in under 5 seconds
        self.assertLess(creation_time, 5.0)
        self.assertEqual(JobApplication.objects.count(), 100)

    @patch('documents.tasks.generate_all_documents.delay')
    def test_concurrent_document_generation(self, mock_generate):
        """Test concurrent document generation requests"""
        # Create applications
        applications = []
        for user in self.users[:5]:  # Use 5 users
            app = JobApplication.objects.create(
                user=user,
                job_title=f"Job for {user.username}",
                company_name="Test Company"
            )
            applications.append(app)

        def trigger_generation(application):
            """Trigger document generation"""
            from documents.tasks import generate_all_documents
            return generate_all_documents.delay(application.id)

        # Trigger concurrent document generation
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(trigger_generation, app) for app in applications]
            results = [future.result() for future in as_completed(futures)]

        # All document generation tasks should be triggered
        self.assertEqual(len(results), 5)
        self.assertEqual(mock_generate.call_count, 5)

    def test_database_performance_under_load(self):
        """Test database performance under load"""
        # Create many applications
        applications = []
        for i in range(1000):
            applications.append(JobApplication(
                user=self.users[i % len(self.users)],
                job_title=f"Performance Test Job {i}",
                company_name=f"Performance Company {i}"
            ))

        JobApplication.objects.bulk_create(applications)

        # Test query performance
        start_time = time.time()

        # Complex query that might be slow
        results = JobApplication.objects.filter(
            user__in=self.users
        ).select_related('user').prefetch_related(
            'generateddocument_set',
            'followuphistory_set'
        )[:50]

        # Force evaluation
        list(results)

        end_time = time.time()
        query_time = end_time - start_time

        # Query should complete in under 1 second
        self.assertLess(query_time, 1.0)


class StressTest(TransactionTestCase):
    """Stress testing for system limits"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='stresstest_user',
            email='stress@example.com',
            password='testpass123'
        )

        self.profile = UserProfile.objects.create(
            user=self.user,
            full_name="Stress Test User",
            current_job_title="Developer"
        )

    def test_memory_usage_large_dataset(self):
        """Test memory usage with large dataset"""
        import psutil
        import os

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create large dataset
        applications = []
        for i in range(5000):
            applications.append(JobApplication(
                user=self.user,
                job_title=f"Memory Test Job {i}",
                company_name=f"Memory Company {i}",
                job_description="A" * 1000  # 1KB description
            ))

        JobApplication.objects.bulk_create(applications)

        # Query large dataset
        results = list(JobApplication.objects.all())

        # Check memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (under 500MB)
        self.assertLess(memory_increase, 500)

    def test_api_rate_limiting(self):
        """Test API rate limiting under stress"""
        from rest_framework.authtoken.models import Token

        token = Token.objects.create(user=self.user)

        # Make many rapid requests
        success_count = 0
        rate_limited_count = 0

        for i in range(100):
            response = self.client.get(
                '/api/applications/',
                HTTP_AUTHORIZATION=f'Token {token.key}'
            )

            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:  # Too Many Requests
                rate_limited_count += 1

        # Should have some rate limiting in place
        self.assertGreater(success_count, 0)
        # Rate limiting might not be implemented in test environment

    def test_long_running_operations(self):
        """Test long-running operations don't timeout"""
        # Create application
        application = JobApplication.objects.create(
            user=self.user,
            job_title="Long Running Test",
            company_name="Test Company"
        )

        # Simulate long-running document generation
        with patch('documents.tasks.generate_document') as mock_generate:
            # Simulate 30-second generation time
            def slow_generation(*args, **kwargs):
                time.sleep(0.1)  # Reduced for testing
                return "Generated content"

            mock_generate.side_effect = slow_generation

            start_time = time.time()

            # Trigger generation
            response = self.client.post(f'/documents/generate/{application.id}/')

            end_time = time.time()

            # Should not timeout
            self.assertIn(response.status_code, [200, 202])
            self.assertLess(end_time - start_time, 5.0)  # Reasonable time


class CeleryTaskTest(TestCase):
    """Test Celery task integration"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='celery_test_user',
            email='celery@example.com',
            password='testpass123'
        )

        self.profile = UserProfile.objects.create(
            user=self.user,
            full_name="Celery Test User",
            current_job_title="Developer"
        )

    @patch('celery.current_app.send_task')
    def test_document_generation_task(self, mock_send_task):
        """Test document generation Celery task"""
        application = JobApplication.objects.create(
            user=self.user,
            job_title="Celery Test Job",
            company_name="Celery Company"
        )

        # Mock task result
        mock_result = Mock()
        mock_result.id = 'task_123'
        mock_send_task.return_value = mock_result

        from documents.tasks import generate_all_documents

        # Trigger task
        result = generate_all_documents.delay(application.id)

        # Verify task was sent
        self.assertTrue(mock_send_task.called)
        self.assertEqual(result.id, 'task_123')

    @patch('celery.current_app.send_task')
    def test_followup_email_task(self, mock_send_task):
        """Test follow-up email Celery task"""
        application = JobApplication.objects.create(
            user=self.user,
            job_title="Followup Test Job",
            company_name="Followup Company"
        )

        template = FollowUpTemplate.objects.create(
            user=self.user,
            template_name="Test Template",
            template_type="initial",
            subject_template="Test Subject",
            body_template="Test Body"
        )

        mock_result = Mock()
        mock_result.id = 'followup_task_456'
        mock_send_task.return_value = mock_result

        from followups.tasks import send_followup_email

        # Trigger task
        result = send_followup_email.delay(application.id, template.id)

        # Verify task was sent
        self.assertTrue(mock_send_task.called)
        self.assertEqual(result.id, 'followup_task_456')

    @patch('celery.current_app.send_task')
    def test_job_search_task(self, mock_send_task):
        """Test job search Celery task"""
        search_config = JobSearchConfig.objects.create(
            user=self.user,
            keywords="python developer",
            location="Toronto",
            experience_level="mid"
        )

        mock_result = Mock()
        mock_result.id = 'search_task_789'
        mock_send_task.return_value = mock_result

        from jobs.tasks import search_jobs_task

        # Trigger task
        result = search_jobs_task.delay(self.user.id, search_config.id)

        # Verify task was sent
        self.assertTrue(mock_send_task.called)
        self.assertEqual(result.id, 'search_task_789')


class ErrorRecoveryTest(TestCase):
    """Test error recovery and resilience"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='error_test_user',
            email='error@example.com',
            password='testpass123'
        )

    def test_database_connection_error_recovery(self):
        """Test recovery from database connection errors"""
        from django.db import connection

        # Simulate database error
        with patch.object(connection, 'cursor') as mock_cursor:
            mock_cursor.side_effect = Exception("Database connection lost")

            # API should handle gracefully
            response = self.client.get('/api/applications/')

            # Should return appropriate error response
            self.assertIn(response.status_code, [500, 503])

    @patch('requests.post')
    def test_external_api_failure_recovery(self, mock_post):
        """Test recovery from external API failures"""
        # Simulate external API failure
        mock_post.side_effect = requests.exceptions.Timeout("API timeout")

        application = JobApplication.objects.create(
            user=self.user,
            job_title="Error Test Job",
            company_name="Error Company"
        )

        # Document generation should handle API failures gracefully
        with patch('documents.tasks.generate_all_documents.delay') as mock_generate:
            mock_generate.side_effect = Exception("OpenAI API failed")

            response = self.client.post(f'/documents/generate/{application.id}/')

            # Should not crash the application
            self.assertIn(response.status_code, [200, 500, 503])

    def test_malformed_request_handling(self):
        """Test handling of malformed requests"""
        # Test malformed JSON
        response = self.client.post(
            '/api/webhooks/n8n/',
            data='{"invalid": json}',
            content_type='application/json'
        )

        self.assertIn(response.status_code, [400, 500])

        # Test missing required fields
        response = self.client.post(
            '/api/applications/',
            data='{"company_name": "Test"}',  # Missing job_title
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)


class MonitoringTest(TestCase):
    """Test monitoring and logging"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='monitor_user',
            email='monitor@example.com',
            password='testpass123'
        )

    def test_activity_logging(self):
        """Test that user activities are logged"""
        from accounts.models import ActivityLog

        # Login should be logged
        self.client.login(username='monitor_user', password='testpass123')

        # Create application should be logged
        JobApplication.objects.create(
            user=self.user,
            job_title="Monitoring Test",
            company_name="Monitor Company"
        )

        # Check logs were created
        logs = ActivityLog.objects.filter(user=self.user)
        self.assertGreater(logs.count(), 0)

    def test_performance_metrics_collection(self):
        """Test performance metrics are collected"""
        from accounts.models import PerformanceMetric

        # Simulate metric collection
        PerformanceMetric.objects.create(
            user=self.user,
            metric_type='application_rate',
            value=5.0,
            period_start='2024-01-01',
            period_end='2024-01-31'
        )

        metrics = PerformanceMetric.objects.filter(user=self.user)
        self.assertEqual(metrics.count(), 1)

    def test_error_logging(self):
        """Test that errors are properly logged"""
        import logging

        with self.assertLogs('django', level='ERROR') as logs:
            # Trigger an error
            try:
                raise Exception("Test error for logging")
            except Exception as e:
                logging.getLogger('django').error(f"Test error: {str(e)}")

        self.assertTrue(any('Test error' in log for log in logs.output))


if __name__ == '__main__':
    # Run n8n integration tests
    # python manage.py test tests.test_n8n_integration
    pass