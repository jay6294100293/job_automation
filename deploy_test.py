# deploy_test.py - Production Deployment Testing
"""
Production deployment testing script
Tests the system in production-like environment before going live
"""

import os
import sys
import requests
import time
import json
import subprocess
from pathlib import Path


class ProductionDeploymentTest:
    def __init__(self, base_url="https://ai.jobautomation.me"):
        self.base_url = base_url
        self.test_results = []
        self.critical_failures = []

    def log_result(self, test_name, passed, message="", critical=False):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            'test': test_name,
            'passed': passed,
            'message': message,
            'critical': critical
        }
        self.test_results.append(result)

        if not passed and critical:
            self.critical_failures.append(test_name)

        print(f"{status} {test_name}: {message}")

    def test_domain_accessibility(self):
        """Test domain is accessible"""
        try:
            response = requests.get(self.base_url, timeout=10)
            passed = response.status_code == 200
            self.log_result(
                "Domain Accessibility",
                passed,
                f"Status: {response.status_code}" if passed else f"Failed to connect: {response.status_code}",
                critical=True
            )
        except Exception as e:
            self.log_result(
                "Domain Accessibility",
                False,
                f"Connection error: {str(e)}",
                critical=True
            )

    def test_ssl_certificate(self):
        """Test SSL certificate is valid"""
        try:
            response = requests.get(self.base_url, timeout=10, verify=True)
            passed = True
            self.log_result(
                "SSL Certificate",
                passed,
                "SSL certificate is valid",
                critical=True
            )
        except requests.exceptions.SSLError as e:
            self.log_result(
                "SSL Certificate",
                False,
                f"SSL Error: {str(e)}",
                critical=True
            )
        except Exception as e:
            self.log_result(
                "SSL Certificate",
                False,
                f"Error checking SSL: {str(e)}",
                critical=True
            )

    def test_database_connection(self):
        """Test database connectivity"""
        try:
            # Test through health check endpoint
            response = requests.get(f"{self.base_url}/api/health/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                db_status = data.get('database', False)
                self.log_result(
                    "Database Connection",
                    db_status,
                    "Database is connected" if db_status else "Database connection failed",
                    critical=True
                )
            else:
                self.log_result(
                    "Database Connection",
                    False,
                    f"Health check failed: {response.status_code}",
                    critical=True
                )
        except Exception as e:
            self.log_result(
                "Database Connection",
                False,
                f"Error checking database: {str(e)}",
                critical=True
            )

    def test_static_files(self):
        """Test static files are served correctly"""
        static_files = [
            "/static/css/style.css",
            "/static/js/main.js",
            "/static/images/logo.png"
        ]

        for file_path in static_files:
            try:
                response = requests.get(f"{self.base_url}{file_path}", timeout=5)
                passed = response.status_code == 200
                self.log_result(
                    f"Static File: {file_path}",
                    passed,
                    f"Status: {response.status_code}",
                    critical=False
                )
            except Exception as e:
                self.log_result(
                    f"Static File: {file_path}",
                    False,
                    f"Error: {str(e)}",
                    critical=False
                )

    def test_api_endpoints(self):
        """Test critical API endpoints"""
        # First, get authentication token
        auth_data = {
            "username": "admin",  # Replace with actual test credentials
            "password": "your_test_password"
        }

        try:
            # Test authentication
            auth_response = requests.post(
                f"{self.base_url}/api/auth/token/",
                json=auth_data,
                timeout=10
            )

            if auth_response.status_code == 200:
                token = auth_response.json().get('token')
                headers = {'Authorization': f'Token {token}'}

                # Test protected endpoints
                endpoints = [
                    ("/api/applications/", "GET"),
                    ("/api/user/", "GET"),
                    ("/api/followups/templates/", "GET")
                ]

                for endpoint, method in endpoints:
                    try:
                        if method == "GET":
                            response = requests.get(
                                f"{self.base_url}{endpoint}",
                                headers=headers,
                                timeout=10
                            )
                        else:
                            response = requests.post(
                                f"{self.base_url}{endpoint}",
                                headers=headers,
                                timeout=10
                            )

                        passed = response.status_code in [200, 201]
                        self.log_result(
                            f"API Endpoint: {method} {endpoint}",
                            passed,
                            f"Status: {response.status_code}",
                            critical=True
                        )
                    except Exception as e:
                        self.log_result(
                            f"API Endpoint: {method} {endpoint}",
                            False,
                            f"Error: {str(e)}",
                            critical=True
                        )
            else:
                self.log_result(
                    "API Authentication",
                    False,
                    f"Auth failed: {auth_response.status_code}",
                    critical=True
                )

        except Exception as e:
            self.log_result(
                "API Authentication",
                False,
                f"Auth error: {str(e)}",
                critical=True
            )

    def test_n8n_integration(self):
        """Test n8n webhook integration"""
        try:
            # Test n8n webhook endpoint
            webhook_data = {
                "action": "test",
                "webhook_id": "production_test"
            }

            response = requests.post(
                f"{self.base_url}/api/webhooks/n8n/",
                json=webhook_data,
                timeout=10
            )

            # n8n webhooks might return different status codes
            passed = response.status_code in [200, 202, 400]  # 400 for invalid test action is OK
            self.log_result(
                "n8n Webhook Integration",
                passed,
                f"Webhook responsive: {response.status_code}",
                critical=False
            )

        except Exception as e:
            self.log_result(
                "n8n Webhook Integration",
                False,
                f"Webhook error: {str(e)}",
                critical=False
            )

    def test_email_configuration(self):
        """Test email configuration"""
        try:
            # Test email health check
            response = requests.get(f"{self.base_url}/api/health/email/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                email_status = data.get('email', False)
                self.log_result(
                    "Email Configuration",
                    email_status,
                    "Email service is configured" if email_status else "Email service not configured",
                    critical=False
                )
            else:
                self.log_result(
                    "Email Configuration",
                    False,
                    f"Email health check failed: {response.status_code}",
                    critical=False
                )
        except Exception as e:
            self.log_result(
                "Email Configuration",
                False,
                f"Error checking email: {str(e)}",
                critical=False
            )

    def test_performance_metrics(self):
        """Test performance metrics"""
        response_times = []

        for i in range(5):
            try:
                start_time = time.time()
                response = requests.get(self.base_url, timeout=10)
                end_time = time.time()

                if response.status_code == 200:
                    response_time = (end_time - start_time) * 1000  # Convert to ms
                    response_times.append(response_time)

            except Exception:
                pass

        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            passed = avg_response_time < 2000  # Less than 2 seconds

            self.log_result(
                "Performance - Response Time",
                passed,
                f"Average: {avg_response_time:.0f}ms",
                critical=False
            )
        else:
            self.log_result(
                "Performance - Response Time",
                False,
                "Could not measure response time",
                critical=False
            )

    def test_security_headers(self):
        """Test security headers"""
        try:
            response = requests.get(self.base_url, timeout=10)
            headers = response.headers

            security_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Strict-Transport-Security': True  # Just check if present
            }

            for header, expected_value in security_headers.items():
                if header in headers:
                    if expected_value is True:
                        # Just check if header exists
                        self.log_result(
                            f"Security Header: {header}",
                            True,
                            f"Present: {headers[header][:50]}...",
                            critical=False
                        )
                    else:
                        # Check exact value
                        passed = headers[header] == expected_value
                        self.log_result(
                            f"Security Header: {header}",
                            passed,
                            f"Expected: {expected_value}, Got: {headers.get(header, 'Missing')}",
                            critical=False
                        )
                else:
                    self.log_result(
                        f"Security Header: {header}",
                        False,
                        "Header missing",
                        critical=False
                    )

        except Exception as e:
            self.log_result(
                "Security Headers",
                False,
                f"Error checking headers: {str(e)}",
                critical=False
            )

    def test_error_pages(self):
        """Test error page handling"""
        error_pages = [
            ("/nonexistent-page", 404),
            ("/api/nonexistent-endpoint", 404)
        ]

        for path, expected_status in error_pages:
            try:
                response = requests.get(f"{self.base_url}{path}", timeout=10)
                passed = response.status_code == expected_status

                self.log_result(
                    f"Error Page: {path}",
                    passed,
                    f"Expected {expected_status}, got {response.status_code}",
                    critical=False
                )
            except Exception as e:
                self.log_result(
                    f"Error Page: {path}",
                    False,
                    f"Error: {str(e)}",
                    critical=False
                )

    def test_load_handling(self):
        """Test basic load handling"""
        print("🔄 Running basic load test...")

        import threading
        import queue

        results_queue = queue.Queue()

        def make_request():
            try:
                start_time = time.time()
                response = requests.get(self.base_url, timeout=10)
                end_time = time.time()

                results_queue.put({
                    'status_code': response.status_code,
                    'response_time': end_time - start_time
                })
            except Exception as e:
                results_queue.put({
                    'status_code': 0,
                    'response_time': 999,
                    'error': str(e)
                })

        # Create 10 concurrent requests
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Collect results
        successful_requests = 0
        total_response_time = 0

        while not results_queue.empty():
            result = results_queue.get()
            if result['status_code'] == 200:
                successful_requests += 1
                total_response_time += result['response_time']

        success_rate = (successful_requests / 10) * 100
        avg_response_time = (total_response_time / successful_requests * 1000) if successful_requests > 0 else 0

        passed = success_rate >= 80 and avg_response_time < 5000

        self.log_result(
            "Load Handling",
            passed,
            f"Success rate: {success_rate}%, Avg response: {avg_response_time:.0f}ms",
            critical=False
        )

    def run_all_tests(self):
        """Run all production tests"""
        print("🚀 Running Production Deployment Tests")
        print("=" * 60)

        test_methods = [
            self.test_domain_accessibility,
            self.test_ssl_certificate,
            self.test_database_connection,
            self.test_static_files,
            self.test_api_endpoints,
            self.test_n8n_integration,
            self.test_email_configuration,
            self.test_performance_metrics,
            self.test_security_headers,
            self.test_error_pages,
            self.test_load_handling
        ]

        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                print(f"❌ Test {test_method.__name__} failed with exception: {e}")

        self.generate_deployment_report()

    def generate_deployment_report(self):
        """Generate deployment readiness report"""
        print("\n" + "=" * 60)
        print("📊 PRODUCTION DEPLOYMENT REPORT")
        print("=" * 60)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        failed_tests = total_tests - passed_tests
        critical_failures = len(self.critical_failures)

        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Critical Failures: {critical_failures} 🚨")
        print(f"Success Rate: {success_rate:.1f}%")

        if self.critical_failures:
            print("\n🚨 CRITICAL FAILURES:")
            for failure in self.critical_failures:
                print(f"  - {failure}")

        print("\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result['passed'] else "❌"
            critical_mark = " 🚨" if not result['passed'] and result['critical'] else ""
            print(f"  {status} {result['test']}: {result['message']}{critical_mark}")

        print("\n" + "=" * 60)

        # Deployment decision
        if critical_failures == 0 and success_rate >= 90:
            print("🚀 DEPLOYMENT APPROVED!")
            print("✅ All critical tests passed. System is ready for production.")
            deployment_ready = True
        elif critical_failures == 0 and success_rate >= 80:
            print("⚠️ DEPLOYMENT WITH CAUTION")
            print("✅ Critical tests passed but some non-critical issues found.")
            print("📝 Consider fixing non-critical issues after deployment.")
            deployment_ready = True
        else:
            print("❌ DEPLOYMENT NOT RECOMMENDED")
            print("🚨 Critical failures detected. Fix issues before deployment.")
            deployment_ready = False

        # Additional recommendations
        print("\n📝 RECOMMENDATIONS:")
        if critical_failures > 0:
            print("1. Fix all critical failures before deployment")
        if success_rate < 90:
            print("2. Investigate and fix failed tests")
        print("3. Monitor system closely after deployment")
        print("4. Have rollback plan ready")
        print("5. Run health checks post-deployment")

        return deployment_ready


def main():
    """Main function"""
    # Get base URL from environment or command line
    base_url = os.getenv('DEPLOYMENT_URL', 'https://ai.jobautomation.me')

    if len(sys.argv) > 1:
        base_url = sys.argv[1]

    print(f"🎯 Testing deployment at: {base_url}")

    tester = ProductionDeploymentTest(base_url)
    deployment_ready = tester.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if deployment_ready else 1)


if __name__ == '__main__':
    main()

# Quick deployment test commands:
"""
Deployment Testing Commands:

# Test production deployment
python deploy_test.py https://ai.jobautomation.me

# Test staging deployment
python deploy_test.py https://staging.jobautomation.me

# Test local deployment
python deploy_test.py http://localhost:8000

# Environment variable approach
export DEPLOYMENT_URL=https://ai.jobautomation.me
python deploy_test.py

# Combined with CI/CD
python deploy_test.py && echo "Deployment approved" || echo "Deployment failed"
"""