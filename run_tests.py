# run_tests.py - Complete Test Runner
"""
Complete testing suite for Job Automation System
Run this script to execute all tests before production deployment
"""

import os
import sys
import django
import subprocess
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_automation.settings')
django.setup()

from django.test.utils import get_runner
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.contrib.auth.models import User


class TestRunner:
    """Custom test runner with comprehensive reporting"""

    def __init__(self):
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'skipped': 0,
            'total_time': 0
        }
        self.failed_tests = []

    def run_setup(self):
        """Setup test environment"""
        print("🔧 Setting up test environment...")

        # Create test database
        call_command('migrate', verbosity=0)

        # Create test superuser
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@test.com', 'admin123')

        print("✅ Test environment setup complete")

    def run_unit_tests(self):
        """Run all unit tests"""
        print("\n🧪 Running Unit Tests...")
        start_time = time.time()

        test_commands = [
            # Model tests
            'python manage.py test tests.test_models.UserProfileModelTest -v 2',
            'python manage.py test tests.test_models.JobApplicationModelTest -v 2',
            'python manage.py test tests.test_models.FollowUpModelTest -v 2',
            'python manage.py test tests.test_models.DocumentModelTest -v 2',

            # API tests
            'python manage.py test tests.test_api.AuthenticationAPITest -v 2',
            'python manage.py test tests.test_api.ApplicationAPITest -v 2',
            'python manage.py test tests.test_api.FollowUpAPITest -v 2',
            'python manage.py test tests.test_api.DocumentAPITest -v 2',

            # View tests
            'python manage.py test tests.test_views.DashboardViewTest -v 2',
            'python manage.py test tests.test_views.JobViewsTest -v 2',
            'python manage.py test tests.test_views.AccountViewsTest -v 2',
        ]

        for cmd in test_commands:
            print(f"Running: {cmd}")
            result = subprocess.run(cmd.split(), capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ PASSED")
                self.test_results['passed'] += 1
            else:
                print("❌ FAILED")
                print(result.stdout)
                print(result.stderr)
                self.test_results['failed'] += 1
                self.failed_tests.append(cmd)

        end_time = time.time()
        self.test_results['total_time'] += (end_time - start_time)
        print(f"Unit tests completed in {end_time - start_time:.2f} seconds")

    def run_integration_tests(self):
        """Run integration tests"""
        print("\n🔗 Running Integration Tests...")
        start_time = time.time()

        integration_commands = [
            'python manage.py test tests.test_views.IntegrationTest -v 2',
            'python manage.py test tests.test_n8n_integration.N8NWebhookTest -v 2',
            'python manage.py test tests.test_n8n_integration.N8NIntegrationTest -v 2',
        ]

        for cmd in integration_commands:
            print(f"Running: {cmd}")
            result = subprocess.run(cmd.split(), capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ PASSED")
                self.test_results['passed'] += 1
            else:
                print("❌ FAILED")
                print(result.stdout)
                self.test_results['failed'] += 1
                self.failed_tests.append(cmd)

        end_time = time.time()
        self.test_results['total_time'] += (end_time - start_time)
        print(f"Integration tests completed in {end_time - start_time:.2f} seconds")

    def run_performance_tests(self):
        """Run performance tests"""
        print("\n⚡ Running Performance Tests...")
        start_time = time.time()

        performance_commands = [
            'python manage.py test tests.test_views.PerformanceTest -v 2',
            'python manage.py test tests.test_api.PerformanceAPITest -v 2',
            'python manage.py test tests.test_n8n_integration.LoadTest -v 2',
        ]

        for cmd in performance_commands:
            print(f"Running: {cmd}")
            result = subprocess.run(cmd.split(), capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ PASSED")
                self.test_results['passed'] += 1
            else:
                print("❌ FAILED")
                print(result.stdout)
                self.test_results['failed'] += 1
                self.failed_tests.append(cmd)

        end_time = time.time()
        self.test_results['total_time'] += (end_time - start_time)
        print(f"Performance tests completed in {end_time - start_time:.2f} seconds")

    def run_security_tests(self):
        """Run security tests"""
        print("\n🔒 Running Security Tests...")
        start_time = time.time()

        security_commands = [
            'python manage.py test tests.test_views.SecurityTest -v 2',
            'python manage.py test tests.test_api.ErrorHandlingAPITest -v 2',
        ]

        for cmd in security_commands:
            print(f"Running: {cmd}")
            result = subprocess.run(cmd.split(), capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ PASSED")
                self.test_results['passed'] += 1
            else:
                print("❌ FAILED")
                print(result.stdout)
                self.test_results['failed'] += 1
                self.failed_tests.append(cmd)

        end_time = time.time()
        self.test_results['total_time'] += (end_time - start_time)
        print(f"Security tests completed in {end_time - start_time:.2f} seconds")

    def run_static_analysis(self):
        """Run static code analysis"""
        print("\n🔍 Running Static Code Analysis...")

        try:
            # Check if required packages are installed
            import flake8  # noqa
            import coverage  # noqa

            # Run flake8
            print("Running flake8...")
            result = subprocess.run(['flake8', '.', '--max-line-length=120'],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Flake8 checks passed")
            else:
                print("⚠️ Flake8 warnings:")
                print(result.stdout)

            # Run coverage
            print("Running coverage analysis...")
            subprocess.run(['coverage', 'run', 'manage.py', 'test'],
                           capture_output=True)
            result = subprocess.run(['coverage', 'report'],
                                    capture_output=True, text=True)
            print("📊 Coverage Report:")
            print(result.stdout)

        except ImportError:
            print("⚠️ Static analysis tools not installed. Install with:")
            print("pip install flake8 coverage")

    def run_load_tests(self):
        """Run load tests"""
        print("\n💪 Running Load Tests...")
        start_time = time.time()

        try:
            # Check if locust is installed
            import locust  # noqa

            # Create simple load test
            load_test_script = """
from locust import HttpUser, task, between

class JobAutomationUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        # Login
        response = self.client.post("/accounts/login/", {
            "username": "admin",
            "password": "admin123"
        })

    @task(3)
    def view_dashboard(self):
        self.client.get("/dashboard/")

    @task(2)
    def view_applications(self):
        self.client.get("/jobs/applications/")

    @task(1)
    def api_applications(self):
        self.client.get("/api/applications/")
"""

            # Write load test file
            with open('locustfile.py', 'w') as f:
                f.write(load_test_script)

            print("Running Locust load test (10 users, 30 seconds)...")
            result = subprocess.run([
                'locust', '-f', 'locustfile.py',
                '--headless', '-u', '10', '-r', '2', '-t', '30s',
                '--host', 'http://127.0.0.1:8000'
            ], capture_output=True, text=True)

            print("📈 Load Test Results:")
            print(result.stdout)

            # Clean up
            os.remove('locustfile.py')

        except ImportError:
            print("⚠️ Locust not installed. Install with: pip install locust")

        end_time = time.time()
        print(f"Load tests completed in {end_time - start_time:.2f} seconds")

    def check_database_performance(self):
        """Check database performance"""
        print("\n🗄️ Checking Database Performance...")

        # Test database connection
        try:
            with connection.cursor() as cursor:
                start_time = time.time()
                cursor.execute("SELECT 1")
                end_time = time.time()

                db_response_time = (end_time - start_time) * 1000
                print(f"Database response time: {db_response_time:.2f}ms")

                if db_response_time < 100:
                    print("✅ Database performance: Excellent")
                elif db_response_time < 500:
                    print("⚠️ Database performance: Good")
                else:
                    print("❌ Database performance: Needs optimization")

        except Exception as e:
            print(f"❌ Database connection failed: {e}")

    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST REPORT")
        print("=" * 60)

        total_tests = (self.test_results['passed'] +
                       self.test_results['failed'] +
                       self.test_results['errors'])

        if total_tests > 0:
            success_rate = (self.test_results['passed'] / total_tests) * 100
        else:
            success_rate = 0

        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.test_results['passed']} ✅")
        print(f"Failed: {self.test_results['failed']} ❌")
        print(f"Errors: {self.test_results['errors']} ⚠️")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Total Time: {self.test_results['total_time']:.2f} seconds")

        if self.failed_tests:
            print("\n❌ Failed Tests:")
            for test in self.failed_tests:
                print(f"  - {test}")

        print("\n" + "=" * 60)

        # Deployment readiness check
        if success_rate >= 95:
            print("🚀 DEPLOYMENT READY: All critical tests passed!")
            print("System is ready for production deployment.")
        elif success_rate >= 85:
            print("⚠️ DEPLOYMENT CAUTION: Some tests failed.")
            print("Review failed tests before deployment.")
        else:
            print("❌ NOT READY FOR DEPLOYMENT: Too many test failures.")
            print("Fix critical issues before attempting deployment.")

        return success_rate >= 95

    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting Comprehensive Test Suite")
        print("=" * 60)

        overall_start = time.time()

        try:
            self.run_setup()
            self.run_unit_tests()
            self.run_integration_tests()
            self.run_performance_tests()
            self.run_security_tests()
            self.run_static_analysis()
            self.check_database_performance()
            # self.run_load_tests()  # Uncomment for full load testing

        except KeyboardInterrupt:
            print("\n⏹️ Test suite interrupted by user")
        except Exception as e:
            print(f"\n❌ Test suite failed with error: {e}")
            self.test_results['errors'] += 1

        overall_end = time.time()
        self.test_results['total_time'] = overall_end - overall_start

        return self.generate_report()


def main():
    """Main test runner function"""
    runner = TestRunner()

    # Check for command line arguments
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()

        if test_type == 'unit':
            runner.run_setup()
            runner.run_unit_tests()
        elif test_type == 'integration':
            runner.run_setup()
            runner.run_integration_tests()
        elif test_type == 'performance':
            runner.run_setup()
            runner.run_performance_tests()
        elif test_type == 'security':
            runner.run_setup()
            runner.run_security_tests()
        elif test_type == 'load':
            runner.run_setup()
            runner.run_load_tests()
        else:
            print("Usage: python run_tests.py [unit|integration|performance|security|load|all]")
            return

        runner.generate_report()
    else:
        # Run all tests
        deployment_ready = runner.run_all_tests()

        # Exit with appropriate code
        sys.exit(0 if deployment_ready else 1)


if __name__ == '__main__':
    main()

# Individual test commands for quick testing:
"""
Quick Test Commands:

# Run specific test categories
python run_tests.py unit
python run_tests.py integration
python run_tests.py performance
python run_tests.py security
python run_tests.py load

# Run all tests
python run_tests.py

# Django's built-in test commands
python manage.py test                           # All tests
python manage.py test tests.test_models        # Model tests only
python manage.py test tests.test_api          # API tests only
python manage.py test tests.test_views        # View tests only

# Coverage testing
coverage run manage.py test
coverage report
coverage html

# Performance profiling
python -m cProfile manage.py test tests.test_views.PerformanceTest

# Memory profiling (requires memory_profiler)
mprof run manage.py test tests.test_n8n_integration.LoadTest
mprof plot

# Load testing with Locust
locust -f locustfile.py --host=http://localhost:8000

# Static analysis
flake8 . --max-line-length=120
bandit -r . -x tests/
safety check

# Database testing
python manage.py dbshell
EXPLAIN ANALYZE SELECT * FROM jobs_jobapplication WHERE user_id = 1;
"""