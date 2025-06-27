# tests/test_views.py - Frontend and Integration Testing
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, Mock
import json

from accounts.models import UserProfile
from jobs.models import JobApplication, JobSearchConfig
from followups.models import FollowUpTemplate, FollowUpHistory
from documents.models import GeneratedDocument


class DashboardViewTest(TestCase):
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

        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

        # Create test applications
        for i in range(5):
            JobApplication.objects.create(
                user=self.user,
                job_title=f"Job {i}",
                company_name=f"Company {i}",
                application_status=['saved', 'applied', 'interview', 'offer', 'rejected'][i]
            )

    def test_dashboard_loads(self):
        """Test dashboard page loads correctly"""
        url = reverse('dashboard:dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')
        self.assertContains(response, 'Recent Applications')
        self.assertContains(response, 'Quick Stats')

    def test_dashboard_statistics(self):
        """Test dashboard shows correct statistics"""
        url = reverse('dashboard:dashboard')
        response = self.client.get(url)

        # Check that statistics are displayed
        self.assertContains(response, '5')  # Total applications
        self.assertContains(response, 'Test User')  # User name

    def test_dashboard_recent_applications(self):
        """Test dashboard shows recent applications"""
        url = reverse('dashboard:dashboard')
        response = self.client.get(url)

        # Check that recent applications are shown
        self.assertContains(response, 'Job 0')
        self.assertContains(response, 'Company 0')

    def test_dashboard_unauthenticated(self):
        """Test dashboard redirects unauthenticated users"""
        self.client.logout()
        url = reverse('dashboard:dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)


class JobViewsTest(TestCase):
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

        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_job_list_view(self):
        """Test job list page"""
        # Create test applications
        JobApplication.objects.create(
            user=self.user,
            job_title="Test Job",
            company_name="Test Company"
        )

        url = reverse('jobs:application_list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Job')
        self.assertContains(response, 'Test Company')

    def test_add_job_application_get(self):
        """Test add job application form loads"""
        url = reverse('jobs:add_application')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add New Job Application')
        self.assertContains(response, 'Job Title')
        self.assertContains(response, 'Company Name')

    def test_add_job_application_post(self):
        """Test creating job application via form"""
        url = reverse('jobs:add_application')
        data = {
            'job_title': 'Senior Python Developer',
            'company_name': 'Tech Corp',
            'job_url': 'https://example.com/job/123',
            'location': 'Toronto, ON',
            'salary_range': '80000-100000',
            'job_description': 'Looking for experienced Python developer...',
            'application_status': 'saved'
        }

        response = self.client.post(url, data)

        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)

        # Check that application was created
        application = JobApplication.objects.get(job_title='Senior Python Developer')
        self.assertEqual(application.user, self.user)
        self.assertEqual(application.company_name, 'Tech Corp')

    def test_edit_job_application(self):
        """Test editing job application"""
        application = JobApplication.objects.create(
            user=self.user,
            job_title="Original Title",
            company_name="Original Company"
        )

        url = reverse('jobs:edit_application', kwargs={'pk': application.id})
        data = {
            'job_title': 'Updated Title',
            'company_name': 'Updated Company',
            'job_url': application.job_url or '',
            'location': application.location or '',
            'application_status': 'applied'
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)

        application.refresh_from_db()
        self.assertEqual(application.job_title, 'Updated Title')
        self.assertEqual(application.application_status, 'applied')

    def test_delete_job_application(self):
        """Test deleting job application"""
        application = JobApplication.objects.create(
            user=self.user,
            job_title="To Delete",
            company_name="Delete Company"
        )

        url = reverse('jobs:delete_application', kwargs={'pk': application.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(JobApplication.objects.count(), 0)

    def test_job_search_config_view(self):
        """Test job search configuration page"""
        url = reverse('jobs:search_config')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Job Search Configuration')

    @patch('jobs.tasks.search_jobs_task.delay')
    def test_job_search_trigger(self, mock_search):
        """Test triggering job search"""
        url = reverse('jobs:trigger_search')
        data = {
            'keywords': 'python developer',
            'location': 'Toronto',
            'experience_level': 'mid'
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        mock_search.assert_called_once()


class AccountViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_profile_view_get(self):
        """Test profile page loads"""
        url = reverse('accounts:profile')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Profile')

    def test_profile_update(self):
        """Test updating user profile"""
        url = reverse('accounts:profile')
        data = {
            'full_name': 'Test User',
            'phone': '1234567890',
            'location': 'Toronto, ON, Canada',
            'current_job_title': 'Senior Developer',
            'experience_level': 'senior',
            'years_of_experience': 7,
            'primary_skills': 'Python, Django, React',
            'desired_job_titles': 'Senior Developer, Tech Lead',
            'professional_summary': 'Experienced developer with 7 years...',
            'preferred_employment_type': 'full_time',
            'remote_work_preference': 'hybrid'
        }

        response = self.client.post(url, data)

        # Should redirect after successful update
        self.assertEqual(response.status_code, 302)

        # Check that profile was created/updated
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.full_name, 'Test User')
        self.assertEqual(profile.current_job_title, 'Senior Developer')

    def test_user_registration(self):
        """Test user registration"""
        self.client.logout()

        url = reverse('accounts:register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123',
            'first_name': 'New',
            'last_name': 'User'
        }

        response = self.client.post(url, data)

        # Should redirect after successful registration
        self.assertEqual(response.status_code, 302)

        # Check that user was created
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')

    def test_login_view(self):
        """Test login functionality"""
        self.client.logout()

        url = reverse('accounts:login')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }

        response = self.client.post(url, data)

        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)

        # Check that user is logged in
        user = response.wsgi_request.user
        self.assertTrue(user.is_authenticated)


class FollowUpViewsTest(TestCase):
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
            template_name="Test Template",
            template_type="initial",
            subject_template="Test Subject",
            body_template="Test Body",
            days_after_application=7
        )

        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_followup_templates_list(self):
        """Test follow-up templates list view"""
        url = reverse('followups:template_list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Follow-up Templates')
        self.assertContains(response, 'Test Template')

    def test_create_followup_template(self):
        """Test creating follow-up template"""
        url = reverse('followups:create_template')
        data = {
            'template_name': 'New Template',
            'template_type': '1_week',
            'subject_template': 'New Subject',
            'body_template': 'New Body',
            'days_after_application': 14
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)

        template = FollowUpTemplate.objects.get(template_name='New Template')
        self.assertEqual(template.user, self.user)
        self.assertEqual(template.days_after_application, 14)

    @patch('followups.tasks.send_followup_email.delay')
    def test_send_followup_view(self, mock_send):
        """Test sending follow-up via view"""
        url = reverse('followups:send_followup')
        data = {
            'application_id': self.application.id,
            'template_id': self.template.id
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        mock_send.assert_called_once()

    def test_followup_history_view(self):
        """Test follow-up history view"""
        # Create follow-up history
        FollowUpHistory.objects.create(
            application=self.application,
            template=self.template,
            subject="Test follow-up",
            body="Test body"
        )

        url = reverse('followups:history')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Follow-up History')
        self.assertContains(response, 'Test follow-up')


class DocumentViewsTest(TestCase):
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
            professional_summary="Test summary"
        )

        self.application = JobApplication.objects.create(
            user=self.user,
            job_title="Test Job",
            company_name="Test Company"
        )

        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_documents_list_view(self):
        """Test documents list view"""
        # Create test document
        GeneratedDocument.objects.create(
            application=self.application,
            document_type="resume",
            file_path="/documents/resume.pdf",
            content="Resume content"
        )

        url = reverse('documents:list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Generated Documents')
        self.assertContains(response, 'resume')

    @patch('documents.tasks.generate_all_documents.delay')
    def test_generate_documents_view(self, mock_generate):
        """Test document generation trigger"""
        url = reverse('documents:generate', kwargs={'application_id': self.application.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        mock_generate.assert_called_once()

    def test_document_preview(self):
        """Test document preview functionality"""
        document = GeneratedDocument.objects.create(
            application=self.application,
            document_type="resume",
            file_path="/documents/resume.pdf",
            content="Resume content for preview"
        )

        url = reverse('documents:preview', kwargs={'document_id': document.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Resume content for preview')

    def test_document_download(self):
        """Test document download"""
        document = GeneratedDocument.objects.create(
            application=self.application,
            document_type="resume",
            file_path="/documents/resume.pdf",
            content="Resume content"
        )

        with patch('os.path.exists', return_value=True):
            with patch('django.http.FileResponse') as mock_response:
                url = reverse('documents:download', kwargs={'document_id': document.id})
                response = self.client.get(url)

                mock_response.assert_called_once()

    def test_bulk_document_download(self):
        """Test bulk document download"""
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

        url = reverse('documents:bulk_download')
        data = {
            'document_ids': [doc1.id, doc2.id]
        }

        with patch('documents.views.create_zip_file') as mock_zip:
            mock_zip.return_value = b'fake zip content'
            response = self.client.post(url, data)

            self.assertEqual(response.status_code, 200)
            mock_zip.assert_called_once()


class AjaxViewsTest(TestCase):
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

        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_ajax_application_status_update(self):
        """Test AJAX application status update"""
        url = reverse('jobs:ajax_update_status')
        data = {
            'application_id': self.application.id,
            'status': 'interview'
        }

        response = self.client.post(
            url,
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])

        self.application.refresh_from_db()
        self.assertEqual(self.application.application_status, 'interview')

    def test_ajax_get_application_details(self):
        """Test AJAX get application details"""
        url = reverse('jobs:ajax_get_details')
        data = {'application_id': self.application.id}

        response = self.client.get(
            url,
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['job_title'], 'Test Job')

    def test_ajax_search_suggestions(self):
        """Test AJAX search suggestions"""
        # Create more applications for search
        JobApplication.objects.create(
            user=self.user,
            job_title="Python Developer",
            company_name="Tech Corp"
        )

        url = reverse('jobs:ajax_search_suggestions')
        data = {'q': 'python'}

        response = self.client.get(
            url,
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('suggestions', response_data)


class FormValidationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_job_application_form_validation(self):
        """Test job application form validation"""
        url = reverse('jobs:add_application')

        # Test with missing required fields
        data = {
            'company_name': 'Test Company'
            # Missing job_title
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required')

    def test_profile_form_validation(self):
        """Test profile form validation"""
        url = reverse('accounts:profile')

        # Test with invalid email format
        data = {
            'full_name': 'Test User',
            'years_of_experience': -1  # Invalid negative value
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        # Should show validation errors

    def test_followup_template_validation(self):
        """Test follow-up template validation"""
        url = reverse('followups:create_template')

        # Test with empty template
        data = {
            'template_name': '',
            'template_type': 'initial',
            'subject_template': '',
            'body_template': ''
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required')


class SecurityTest(TestCase):
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

    def test_unauthorized_application_access(self):
        """Test that users cannot access other users' applications"""
        self.client.login(username='user2', password='testpass123')

        url = reverse('jobs:application_detail', kwargs={'pk': self.application.id})
        response = self.client.get(url)

        # Should return 404 or redirect
        self.assertIn(response.status_code, [404, 302, 403])

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

    def test_sql_injection_protection(self):
        """Test SQL injection protection"""
        self.client.login(username='user1', password='testpass123')

        # Try SQL injection in search
        url = reverse('jobs:application_list')
        malicious_query = "'; DROP TABLE jobs_jobapplication; --"

        response = self.client.get(url, {'search': malicious_query})

        # Should not cause any issues
        self.assertEqual(response.status_code, 200)
        # Table should still exist
        self.assertTrue(JobApplication.objects.all().exists())

    def test_xss_protection(self):
        """Test XSS protection"""
        self.client.login(username='user1', password='testpass123')

        # Try XSS in job title
        url = reverse('jobs:add_application')
        data = {
            'job_title': '<script>alert("XSS")</script>',
            'company_name': 'Test Company'
        }

        response = self.client.post(url, data)

        # Check that the application was created but script was escaped
        if response.status_code == 302:  # Successful creation
            application = JobApplication.objects.get(company_name='Test Company')
            # Script should be escaped in the database or display
            self.assertIn('&lt;script&gt;', str(application.job_title))


class PerformanceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create many applications for performance testing
        applications = []
        for i in range(100):
            applications.append(JobApplication(
                user=self.user,
                job_title=f"Job {i}",
                company_name=f"Company {i}"
            ))

        JobApplication.objects.bulk_create(applications)

        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_dashboard_performance(self):
        """Test dashboard loads quickly with many applications"""
        import time

        start_time = time.time()
        url = reverse('dashboard:dashboard')
        response = self.client.get(url)
        end_time = time.time()

        self.assertEqual(response.status_code, 200)

        # Dashboard should load in under 2 seconds
        load_time = end_time - start_time
        self.assertLess(load_time, 2.0)

    def test_application_list_pagination(self):
        """Test application list pagination"""
        url = reverse('jobs:application_list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Should be paginated (not showing all 100 items)
        applications_shown = response.context['applications'].count()
        self.assertLessEqual(applications_shown, 25)  # Assuming 25 per page

    def test_search_performance(self):
        """Test search performance"""
        import time

        url = reverse('jobs:application_list')

        start_time = time.time()
        response = self.client.get(url, {'search': 'Job 5'})
        end_time = time.time()

        self.assertEqual(response.status_code, 200)

        # Search should complete quickly
        search_time = end_time - start_time
        self.assertLess(search_time, 1.0)


class MobileResponsivenessTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_mobile_dashboard(self):
        """Test dashboard on mobile viewport"""
        url = reverse('dashboard:dashboard')

        # Simulate mobile user agent
        response = self.client.get(
            url,
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'viewport')  # Should have mobile viewport meta tag

    def test_mobile_forms(self):
        """Test forms on mobile"""
        url = reverse('jobs:add_application')

        response = self.client.get(
            url,
            HTTP_USER_AGENT='Mozilla/5.0 (Android 10; Mobile)'
        )

        self.assertEqual(response.status_code, 200)
        # Forms should be mobile-friendly


class IntegrationTest(TestCase):
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
            professional_summary="Test summary"
        )

        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    @patch('documents.tasks.generate_all_documents.delay')
    @patch('followups.tasks.send_followup_email.delay')
    def test_complete_application_workflow(self, mock_followup, mock_generate):
        """Test complete application workflow"""
        # Step 1: Create application
        url = reverse('jobs:add_application')
        data = {
            'job_title': 'Full Stack Developer',
            'company_name': 'Amazing Tech',
            'job_url': 'https://example.com/job/123',
            'location': 'Toronto, ON',
            'application_status': 'saved'
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        application = JobApplication.objects.get(job_title='Full Stack Developer')

        # Step 2: Generate documents
        url = reverse('documents:generate', kwargs={'application_id': application.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        mock_generate.assert_called_once()

        # Step 3: Update status to applied
        url = reverse('jobs:ajax_update_status')
        data = {
            'application_id': application.id,
            'status': 'applied'
        }

        response = self.client.post(
            url,
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)

        # Step 4: Send follow-up
        template = FollowUpTemplate.objects.create(
            user=self.user,
            template_name="Initial Follow-up",
            template_type="initial",
            subject_template="Following up on {job_title}",
            body_template="Dear hiring manager..."
        )

        url = reverse('followups:send_followup')
        data = {
            'application_id': application.id,
            'template_id': template.id
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        mock_followup.assert_called_once()

        # Step 5: Check dashboard shows updated stats
        url = reverse('dashboard:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Full Stack Developer')


if __name__ == '__main__':
    # Run all view tests
    # python manage.py test tests.test_views
    pass