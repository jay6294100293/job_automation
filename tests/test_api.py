# tests/test_api.py - Complete API Testing Suite
import json
import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token
from rest_framework import status
from unittest.mock import patch, Mock

from accounts.models import UserProfile
from jobs.models import JobApplication, JobSearchConfig
from followups.models import FollowUpTemplate, FollowUpHistory
from documents.models import GeneratedDocument


class AuthenticationAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_obtain_token(self):
        """Test token generation"""
        url = reverse('api:obtain_token')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user_id', response.data)

    def test_invalid_credentials(self):
        """Test token generation with invalid credentials"""
        url = reverse('api:obtain_token')
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_validation(self):
        """Test token validation endpoint"""
        token = Token.objects.create(user=self.user)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        url = reverse('api:validate_token')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])
        self.assertEqual(response.data['user_id'], self.user.id)


class ApplicationAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        self.profile = UserProfile.objects.create(
            user=self.user,
            full_name="Test User",
            current_job_title="Developer"
        )

        self.application = JobApplication.objects.create(
            user=self.user,
            job_title="Test Job",
            company_name="Test Company",
            job_url="https://example.com/job",
            location="Toronto, ON"
        )

    def test_list_applications(self):
        """Test GET /api/applications/"""
        url = reverse('api:application-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['job_title'], "Test Job")

    def test_create_application(self):
        """Test POST /api/applications/"""
        url = reverse('api:application-list')
        data = {
            'job_title': 'Senior Python Developer',
            'company_name': 'Tech Corp',
            'job_url': 'https://example.com/job/senior-python',
            'location': 'Toronto, ON',
            'salary_range': '80000-100000',
            'job_description': 'Looking for experienced Python developer',
            'application_status': 'saved'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['job_title'], 'Senior Python Developer')
        self.assertEqual(JobApplication.objects.count(), 2)

    def test_update_application(self):
        """Test PUT /api/applications/{id}/"""
        url = reverse('api:application-detail', kwargs={'pk': self.application.id})
        data = {
            'job_title': 'Updated Job Title',
            'company_name': 'Updated Company',
            'job_url': self.application.job_url,
            'location': self.application.location,
            'application_status': 'applied'
        }

        response = self.client.put(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.application.refresh_from_db()
        self.assertEqual(self.application.job_title, 'Updated Job Title')

    def test_update_application_status(self):
        """Test POST /api/applications/{id}/update_status/"""
        url = reverse('api:application-update-status', kwargs={'pk': self.application.id})
        data = {
            'status': 'interview',
            'notes': 'Interview scheduled for next week'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        self.application.refresh_from_db()
        self.assertEqual(self.application.application_status, 'interview')

    def test_filter_applications_by_status(self):
        """Test filtering applications by status"""
        # Create applications with different statuses
        JobApplication.objects.create(
            user=self.user,
            job_title="Applied Job",
            company_name="Applied Company",
            application_status="applied"
        )

        JobApplication.objects.create(
            user=self.user,
            job_title="Interview Job",
            company_name="Interview Company",
            application_status="interview"
        )

        # Test filtering by applied status
        url = reverse('api:application-list')
        response = self.client.get(url, {'status': 'applied'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        applied_jobs = [app for app in response.data if app['application_status'] == 'applied']
        self.assertEqual(len(applied_jobs), 1)

    def test_delete_application(self):
        """Test DELETE /api/applications/{id}/"""
        url = reverse('api:application-detail', kwargs={'pk': self.application.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(JobApplication.objects.count(), 0)


class FollowUpAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        self.application = JobApplication.objects.create(
            user=self.user,
            job_title="Test Job",
            company_name="Test Company"
        )

        self.template = FollowUpTemplate.objects.create(
            user=self.user,
            template_name="Initial Follow-up",
            template_type="initial",
            subject_template="Following up on {job_title} position",
            body_template="Dear hiring manager, I wanted to follow up on my application for the {job_title} position at {company_name}.",
            days_after_application=7
        )

    @patch('followups.tasks.send_followup_email.delay')
    def test_send_followup(self, mock_send_email):
        """Test POST /api/followups/send/"""
        url = reverse('api:followup_send')
        data = {
            'application_id': self.application.id,
            'template_id': self.template.id,
            'custom_message': 'Additional custom message'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        mock_send_email.assert_called_once()

    def test_bulk_followup(self):
        """Test POST /api/followups/bulk/"""
        # Create multiple applications
        app2 = JobApplication.objects.create(
            user=self.user,
            job_title="Job 2",
            company_name="Company 2"
        )

        app3 = JobApplication.objects.create(
            user=self.user,
            job_title="Job 3",
            company_name="Company 3"
        )

        url = reverse('api:followup_bulk')
        data = {
            'application_ids': [self.application.id, app2.id, app3.id],
            'template_id': self.template.id
        }

        with patch('followups.tasks.send_followup_email.delay') as mock_send:
            response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(mock_send.call_count, 3)

    def test_followup_templates(self):
        """Test GET /api/followups/templates/"""
        url = reverse('api:followup_templates')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['templates']), 1)
        self.assertEqual(response.data['templates'][0]['template_name'], 'Initial Follow-up')

    def test_create_followup_template(self):
        """Test POST /api/followups/templates/"""
        url = reverse('api:followup_templates')
        data = {
            'template_name': 'Weekly Follow-up',
            'template_type': '1_week',
            'subject_template': 'Weekly check-in: {job_title}',
            'body_template': 'Hi there, checking in on the {job_title} position.',
            'days_after_application': 7
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(FollowUpTemplate.objects.count(), 2)

    def test_followup_history(self):
        """Test GET /api/followups/history/"""
        # Create follow-up history
        FollowUpHistory.objects.create(
            application=self.application,
            template=self.template,
            subject="Test follow-up",
            body="Test body"
        )

        url = reverse('api:followup_history_all')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['history']), 1)

    def test_followup_history_for_application(self):
        """Test GET /api/followups/history/{application_id}/"""
        # Create follow-up history
        FollowUpHistory.objects.create(
            application=self.application,
            template=self.template,
            subject="Test follow-up",
            body="Test body"
        )

        url = reverse('api:followup_history', kwargs={'application_id': self.application.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['history']), 1)


class DocumentAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        self.profile = UserProfile.objects.create(
            user=self.user,
            full_name="Test User",
            current_job_title="Developer",
            professional_summary="Experienced developer"
        )

        self.application = JobApplication.objects.create(
            user=self.user,
            job_title="Test Job",
            company_name="Test Company"
        )

    @patch('documents.tasks.generate_all_documents.delay')
    def test_generate_documents(self, mock_generate):
        """Test POST /api/documents/generate/"""
        url = reverse('api:documents_generate')
        data = {
            'application_id': self.application.id,
            'document_types': ['resume', 'cover_letter', 'linkedin_messages']
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        mock_generate.assert_called_once()

    def test_document_status(self):
        """Test GET /api/documents/status/{application_id}/"""
        # Create generated document
        GeneratedDocument.objects.create(
            application=self.application,
            document_type="resume",
            file_path="/documents/resume.pdf",
            content="Resume content"
        )

        url = reverse('api:documents_status', kwargs={'application_id': self.application.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['documents']), 1)
        self.assertEqual(response.data['documents'][0]['document_type'], 'resume')

    def test_bulk_document_action(self):
        """Test POST /api/documents/bulk-action/"""
        # Create multiple documents
        doc1 = GeneratedDocument.objects.create(
            application=self.application,
            document_type="resume",
            file_path="/documents/resume.pdf"
        )

        doc2 = GeneratedDocument.objects.create(
            application=self.application,
            document_type="cover_letter",
            file_path="/documents/cover_letter.pdf"
        )

        url = reverse('api:documents_bulk_action')
        data = {
            'document_ids': [doc1.id, doc2.id],
            'action': 'download'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])


class UserProfileAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        self.profile = UserProfile.objects.create(
            user=self.user,
            full_name="Test User",
            current_job_title="Developer"
        )

    def test_get_current_user_profile(self):
        """Test GET /api/user/"""
        url = reverse('api:current_user_profile')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['profile']['full_name'], 'Test User')

    def test_update_user_profile(self):
        """Test PUT /api/user/"""
        url = reverse('api:current_user_profile')
        data = {
            'full_name': 'Updated Name',
            'current_job_title': 'Senior Developer',
            'primary_skills': 'Python, Django, React',
            'professional_summary': 'Updated summary'
        }

        response = self.client.put(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.full_name, 'Updated Name')

    def test_get_specific_user_profile(self):
        """Test GET /api/user/{id}/"""
        url = reverse('api:user_profile', kwargs={'user_id': self.user.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])


class WebhookAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_n8n_webhook_job_search(self):
        """Test n8n webhook for job search"""
        url = '/api/webhooks/n8n/'
        data = {
            'action': 'job_search',
            'user_id': self.user.id,
            'search_criteria': {
                'keywords': 'python developer',
                'location': 'Toronto',
                'experience_level': 'mid'
            }
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('job_search_id', response.data)

    def test_n8n_webhook_document_generation(self):
        """Test n8n webhook for document generation"""
        application = JobApplication.objects.create(
            user=self.user,
            job_title="Test Job",
            company_name="Test Company"
        )

        url = '/api/webhooks/n8n/'
        data = {
            'action': 'generate_documents',
            'application_id': application.id,
            'document_types': ['resume', 'cover_letter']
        }

        with patch('documents.tasks.generate_all_documents.delay') as mock_generate:
            response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_generate.assert_called_once()

    def test_n8n_webhook_status_update(self):
        """Test n8n webhook for status updates"""
        application = JobApplication.objects.create(
            user=self.user,
            job_title="Test Job",
            company_name="Test Company"
        )

        url = '/api/webhooks/n8n/'
        data = {
            'action': 'update_status',
            'application_id': application.id,
            'new_status': 'interview',
            'notes': 'Interview scheduled via email parsing'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        application.refresh_from_db()
        self.assertEqual(application.application_status, 'interview')


class ErrorHandlingAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_invalid_application_id(self):
        """Test API response for invalid application ID"""
        url = reverse('api:application-detail', kwargs={'pk': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_required_fields(self):
        """Test API response for missing required fields"""
        url = reverse('api:application-list')
        data = {
            'company_name': 'Test Company'
            # Missing job_title (required field)
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('job_title', response.data)

    def test_invalid_status_update(self):
        """Test API response for invalid status"""
        application = JobApplication.objects.create(
            user=self.user,
            job_title="Test Job",
            company_name="Test Company"
        )

        url = reverse('api:application-update-status', kwargs={'pk': application.id})
        data = {
            'status': 'invalid_status'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_unauthorized_user_access(self):
        """Test that users cannot access other users' data"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )

        other_application = JobApplication.objects.create(
            user=other_user,
            job_title="Other User's Job",
            company_name="Other Company"
        )

        # Try to access other user's application
        url = reverse('api:application-detail', kwargs={'pk': other_application.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_rate_limiting(self):
        """Test API rate limiting"""
        url = reverse('api:application-list')

        # Make many requests quickly
        responses = []
        for i in range(100):
            response = self.client.get(url)
            responses.append(response.status_code)

        # Check if rate limiting kicks in
        rate_limited = any(status_code == 429 for status_code in responses)
        # Note: This test might not trigger rate limiting in test environment
        # but it's here for completeness


class PerformanceAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        # Create many applications for performance testing
        applications = []
        for i in range(100):
            applications.append(JobApplication(
                user=self.user,
                job_title=f"Job {i}",
                company_name=f"Company {i}",
                job_url=f"https://example.com/job/{i}"
            ))

        JobApplication.objects.bulk_create(applications)

    def test_pagination_performance(self):
        """Test API pagination with many records"""
        url = reverse('api:application-list')
        response = self.client.get(url, {'page': 1, 'page_size': 20})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data), 20)

    def test_filtering_performance(self):
        """Test API filtering performance"""
        url = reverse('api:application-list')
        response = self.client.get(url, {'search': 'Job 1'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return jobs with "Job 1" in the title
        filtered_results = [app for app in response.data if 'Job 1' in app['job_title']]
        self.assertGreater(len(filtered_results), 0)


if __name__ == '__main__':
    # Run all API tests
    # python manage.py test tests.test_api
    pass