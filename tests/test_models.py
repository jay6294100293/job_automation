# tests/test_models.py - Complete Model Testing
import pytest
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token
from rest_framework import status

from accounts.models import UserProfile, ActivityLog
from jobs.models import JobApplication, JobSearchConfig
from followups.models import FollowUpTemplate, FollowUpHistory
from documents.models import GeneratedDocument, DocumentGenerationJob


class UserProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_user_profile(self):
        """Test creating a user profile"""
        profile = UserProfile.objects.create(
            user=self.user,
            full_name="Test User",
            phone="1234567890",
            location="Toronto, ON, Canada",
            current_job_title="Software Developer",
            experience_level="mid",
            years_of_experience=5,
            primary_skills="Python, Django, JavaScript",
            desired_job_titles="Senior Developer, Tech Lead",
            professional_summary="Experienced developer with 5 years...",
        )

        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.full_name, "Test User")
        self.assertTrue(profile.profile_completion_percentage > 80)

    def test_profile_completion_calculation(self):
        """Test profile completion percentage calculation"""
        profile = UserProfile.objects.create(
            user=self.user,
            full_name="Test User",
            current_job_title="Developer",
        )

        completion = profile.calculate_profile_completion()
        self.assertGreater(completion, 0)
        self.assertLessEqual(completion, 100)

    def test_get_skills_list(self):
        """Test skills list parsing"""
        profile = UserProfile.objects.create(
            user=self.user,
            full_name="Test User",
            primary_skills="Python, Django, React",
            secondary_skills="Docker, AWS"
        )

        skills = profile.get_skills_list()
        self.assertIn("Python", skills)
        self.assertIn("Django", skills)
        self.assertIn("Docker", skills)
        self.assertEqual(len(skills), 5)


class JobApplicationModelTest(TestCase):
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

    def test_create_job_application(self):
        """Test creating a job application"""
        application = JobApplication.objects.create(
            user=self.user,
            job_title="Senior Python Developer",
            company_name="Tech Corp",
            job_url="https://example.com/job/123",
            location="Toronto, ON",
            salary_range="80000-100000",
            job_description="Looking for experienced Python developer...",
            application_status="applied",
            applied_date=timezone.now()
        )

        self.assertEqual(application.user, self.user)
        self.assertEqual(application.job_title, "Senior Python Developer")
        self.assertEqual(application.application_status, "applied")

    def test_application_status_choices(self):
        """Test valid application statuses"""
        application = JobApplication.objects.create(
            user=self.user,
            job_title="Test Job",
            company_name="Test Company"
        )

        valid_statuses = [choice[0] for choice in JobApplication.STATUS_CHOICES]
        self.assertIn('saved', valid_statuses)
        self.assertIn('applied', valid_statuses)
        self.assertIn('interview', valid_statuses)
        self.assertIn('offer', valid_statuses)
        self.assertIn('rejected', valid_statuses)


class FollowUpModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

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
            body_template="Dear hiring manager, I wanted to follow up...",
            days_after_application=7
        )

    def test_create_followup_template(self):
        """Test creating follow-up template"""
        self.assertEqual(self.template.user, self.user)
        self.assertEqual(self.template.template_type, "initial")
        self.assertEqual(self.template.days_after_application, 7)

    def test_create_followup_history(self):
        """Test creating follow-up history"""
        history = FollowUpHistory.objects.create(
            application=self.application,
            template=self.template,
            subject="Following up on Test Job position",
            body="Dear hiring manager, I wanted to follow up..."
        )

        self.assertEqual(history.application, self.application)
        self.assertEqual(history.template, self.template)
        self.assertFalse(history.response_received)

    def test_success_rate_calculation(self):
        """Test template success rate calculation"""
        self.template.times_used = 10
        self.template.responses_received = 3

        success_rate = self.template.calculate_success_rate()
        self.assertEqual(success_rate, 30.0)


class DocumentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.application = JobApplication.objects.create(
            user=self.user,
            job_title="Test Job",
            company_name="Test Company"
        )

    def test_create_generated_document(self):
        """Test creating generated document"""
        document = GeneratedDocument.objects.create(
            application=self.application,
            document_type="resume",
            file_path="/documents/resume_123.pdf",
            content="Resume content preview...",
            file_size=150000
        )

        self.assertEqual(document.application, self.application)
        self.assertEqual(document.document_type, "resume")
        self.assertEqual(document.file_size, 150000)

    def test_document_generation_job(self):
        """Test document generation job tracking"""
        job = DocumentGenerationJob.objects.create(
            application=self.application,
            status="pending"
        )

        self.assertEqual(job.application, self.application)
        self.assertEqual(job.status, "pending")
        self.assertIsNotNone(job.started_at)


# API Tests
class APITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        self.profile = UserProfile.objects.create(
            user=self.user,
            full_name="Test User",
            current_job_title="Developer"
        )

        self.application = JobApplication.objects.create(
            user=self.user,
            job_title="Test Job",
            company_name="Test Company"
        )

    def test_get_applications_api(self):
        """Test GET /api/applications/"""
        url = reverse('api:application-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['job_title'], "Test Job")

    def test_create_application_api(self):
        """Test POST /api/applications/"""
        url = reverse('api:application-list')
        data = {
            'job_title': 'New Job',
            'company_name': 'New Company',
            'job_url': 'https://example.com/job/new',
            'location': 'Toronto, ON',
            'application_status': 'saved'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['job_title'], 'New Job')
        self.assertEqual(JobApplication.objects.count(), 2)

    def test_update_application_status_api(self):
        """Test PATCH /api/applications/{id}/update_status/"""
        url = reverse('api:application-update-status', kwargs={'pk': self.application.id})
        data = {
            'status': 'interview',
            'notes': 'Interview scheduled for next week'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.application.refresh_from_db()
        self.assertEqual(self.application.application_status, 'interview')

    def test_unauthorized_access(self):
        """Test API access without token"""
        self.client.credentials()  # Remove token
        url = reverse('api:application-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_send_followup_api(self):
        """Test POST /api/followups/send/"""
        template = FollowUpTemplate.objects.create(
            user=self.user,
            template_name="Test Template",
            template_type="initial",
            subject_template="Test Subject",
            body_template="Test Body"
        )

        url = reverse('api:followup_send')
        data = {
            'application_id': self.application.id,
            'template_id': template.id
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])


# Integration Tests
class IntegrationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

        self.profile = UserProfile.objects.create(
            user=self.user,
            full_name="Test User",
            current_job_title="Developer"
        )

    def test_dashboard_view(self):
        """Test dashboard loads correctly"""
        url = reverse('dashboard:dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')

    def test_create_application_flow(self):
        """Test complete application creation flow"""
        # Create application
        url = reverse('jobs:add_application')
        data = {
            'job_title': 'Test Job',
            'company_name': 'Test Company',
            'job_url': 'https://example.com/job',
            'location': 'Toronto, ON',
            'job_description': 'Test description',
            'application_status': 'saved'
        }

        response = self.client.post(url, data)

        # Check if application was created
        self.assertEqual(JobApplication.objects.count(), 1)
        application = JobApplication.objects.first()
        self.assertEqual(application.job_title, 'Test Job')

    def test_profile_update_flow(self):
        """Test profile update functionality"""
        url = reverse('accounts:profile')
        data = {
            'full_name': 'Updated Name',
            'current_job_title': 'Senior Developer',
            'primary_skills': 'Python, Django, React',
            'professional_summary': 'Updated summary'
        }

        response = self.client.post(url, data)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.full_name, 'Updated Name')


# Performance Tests
class PerformanceTestCase(TestCase):
    def setUp(self):
        self.users = []
        for i in range(100):
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password='testpass123'
            )
            self.users.append(user)

            UserProfile.objects.create(
                user=user,
                full_name=f"User {i}",
                current_job_title="Developer"
            )

    def test_bulk_application_creation(self):
        """Test creating many applications"""
        applications = []
        for i, user in enumerate(self.users):
            applications.append(JobApplication(
                user=user,
                job_title=f"Job {i}",
                company_name=f"Company {i}"
            ))

        start_time = timezone.now()
        JobApplication.objects.bulk_create(applications)
        end_time = timezone.now()

        duration = (end_time - start_time).total_seconds()
        self.assertLess(duration, 5.0)  # Should complete in under 5 seconds
        self.assertEqual(JobApplication.objects.count(), 100)

    def test_dashboard_query_performance(self):
        """Test dashboard query performance with many records"""
        # Create test data
        for user in self.users[:10]:  # Test with 10 users
            for j in range(10):  # 10 applications each
                JobApplication.objects.create(
                    user=user,
                    job_title=f"Job {j}",
                    company_name=f"Company {j}"
                )

        # Test query performance
        client = Client()
        client.login(username='user0', password='testpass123')

        start_time = timezone.now()
        response = client.get(reverse('dashboard:dashboard'))
        end_time = timezone.now()

        duration = (end_time - start_time).total_seconds()
        self.assertEqual(response.status_code, 200)
        self.assertLess(duration, 2.0)  # Dashboard should load in under 2 seconds


# Security Tests
class SecurityTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )

        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )

        self.application = JobApplication.objects.create(
            user=self.user1,
            job_title="Private Job",
            company_name="Private Company"
        )

    def test_user_data_isolation(self):
        """Test that users can only access their own data"""
        client = Client()
        client.login(username='user2', password='testpass123')

        # Try to access user1's application
        url = reverse('jobs:application_detail', kwargs={'pk': self.application.id})
        response = client.get(url)

        # Should return 404 or redirect, not the actual data
        self.assertNotEqual(response.status_code, 200)

    def test_api_token_security(self):
        """Test API token authentication"""
        token = Token.objects.create(user=self.user1)
        client = APIClient()

        # Test with valid token
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = client.get(reverse('api:application-list'))
        self.assertEqual(response.status_code, 200)

        # Test with invalid token
        client.credentials(HTTP_AUTHORIZATION='Token invalid_token')
        response = client.get(reverse('api:application-list'))
        self.assertEqual(response.status_code, 401)

    def test_csrf_protection(self):
        """Test CSRF protection on forms"""
        client = Client(enforce_csrf_checks=True)
        client.login(username='user1', password='testpass123')

        url = reverse('jobs:add_application')
        data = {
            'job_title': 'Test Job',
            'company_name': 'Test Company'
        }

        # Should fail without CSRF token
        response = client.post(url, data)
        self.assertEqual(response.status_code, 403)


if __name__ == '__main__':
    # Run specific test
    # python manage.py test tests.test_models.UserProfileModelTest.test_create_user_profile
    pass