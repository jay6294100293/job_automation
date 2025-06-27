#!/usr/bin/env python
# test_all.py - One Command Testing Suite
"""
Complete testing suite for Job Automation System
Run this script to execute all tests in one command
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / '.env'
load_dotenv(env_path)
# Add project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))


def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"🚀 {title}")
    print("=" * 70)


def run_command(command, show_output=True):
    """Run a command and return success status"""
    print(f"Running: {command}")
    start_time = time.time()

    try:
        # Get the current Python executable
        python_executable = sys.executable

        # If the command starts with 'python', replace it with the current executable
        if isinstance(command, list) and command[0] == 'python':
            command[0] = python_executable
        elif isinstance(command, str) and command.startswith('python '):
            command = f"{python_executable} {command[7:]}"

        print(f"Executing: {command}")

        # Run the command
        result = subprocess.run(
            command if isinstance(command, list) else command.split(),
            capture_output=not show_output,
            text=True
        )

        success = result.returncode == 0
        end_time = time.time()
        duration = end_time - start_time

        if success:
            print(f"✅ Command completed successfully in {duration:.2f} seconds")
        else:
            print(f"❌ Command failed in {duration:.2f} seconds")
            if not show_output and result.stdout:
                print("Output:")
                print(result.stdout)
            if not show_output and result.stderr:
                print("Error output:")
                print(result.stderr)

        return success

    except Exception as e:
        print(f"❌ Error running command: {str(e)}")
        return False


def check_environment():
    """Check environment setup"""
    print_header("CHECKING ENVIRONMENT")

    # Check Python version
    python_version = sys.version.split()[0]
    print(f"Python version: {python_version}")

    # Check Django
    try:
        import django
        print(f"Django version: {django.__version__}")
    except ImportError:
        print("❌ Django not installed")
        return False

    # Check if manage.py exists
    if not Path("manage.py").exists():
        print("❌ manage.py not found. Are you in the project root directory?")
        return False

    # Check for required environment variables
    required_env_vars = ['GROQ_API_KEY', 'OPENROUTER_API_KEY']
    missing_vars = [var for var in required_env_vars if not os.environ.get(var) and not os.environ.get(f'{var}_FILE')]

    if missing_vars:
        print(f"⚠️ Missing environment variables: {', '.join(missing_vars)}")
        print("You may need to set these for some tests to pass.")
    else:
        print("✅ Required environment variables found")

    # Check for critical files
    critical_files = [
        "job_automation/settings.py",
        "documents/ai_services.py",
        "documents/models.py"
    ]

    missing_files = [file for file in critical_files if not Path(file).exists()]

    if missing_files:
        print(f"❌ Missing critical files: {', '.join(missing_files)}")
        return False
    else:
        print("✅ Critical files found")

    return True


def run_django_tests(test_suite=None):
    """Run Django test suite"""
    print_header("RUNNING DJANGO TESTS")

    if test_suite:
        return run_command(f"python manage.py test {test_suite}")
    else:
        # Run all existing tests
        return run_command("python manage.py test")


def run_system_test(args):
    """Run system test"""
    print_header("RUNNING SYSTEM TEST")

    cmd = ["python", "system_test.py"]

    if args.local:
        cmd.append("--local")

    if args.base_url:
        cmd.extend(["--base-url", args.base_url])

    if args.n8n_url:
        cmd.extend(["--n8n-url", args.n8n_url])

    if args.real_api_calls:
        cmd.append("--real-api-calls")

    if args.real_n8n:
        cmd.append("--real-n8n")

    if args.force_n8n:
        cmd.append("--force-n8n")

    return run_command(cmd, show_output=True)


def run_all_tests(args):
    """Run all tests"""
    overall_start = time.time()

    print_header("JOB AUTOMATION SYSTEM - COMPLETE TEST SUITE")
    print(f"Mode: {'Local' if args.local else 'Production'}")
    print(f"Base URL: {args.base_url}")
    if args.n8n_url:
        print(f"n8n URL: {args.n8n_url}")

    # Check environment
    if not check_environment():
        print("❌ Environment check failed. Please fix the issues before running tests.")
        return False

    # Run migrations if local
    if args.local and not args.skip_migrate:
        print_header("RUNNING MIGRATIONS")
        run_command("python manage.py migrate")

    # Results tracking
    results = {
        "django_tests": None,
        "system_test": None
    }

    # Run system test
    results["system_test"] = run_system_test(args)

    # Run Django tests if requested
    if not args.skip_django_tests:
        results["django_tests"] = run_django_tests(args.test_suite)

    # Generate final report
    overall_end = time.time()
    overall_duration = overall_end - overall_start

    print_header("FINAL REPORT")
    print(f"Total testing time: {overall_duration:.2f} seconds")

    # List test results
    if results["system_test"] is not None:
        status = "✅ PASSED" if results["system_test"] else "❌ FAILED"
        print(f"System Test: {status}")

    if results["django_tests"] is not None:
        status = "✅ PASSED" if results["django_tests"] else "❌ FAILED"
        print(f"Django Tests: {status}")

    # Overall assessment
    if all(result for result in results.values() if result is not None):
        print("\n🎉 ALL TESTS PASSED!")
        print("The system is working correctly.")
        return True
    else:
        print("\n⚠️ SOME TESTS FAILED")
        print("Please review the test output and fix the issues.")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Run all Job Automation System tests')

    parser.add_argument('--local', action='store_true',
                        help='Run tests in local mode')
    parser.add_argument('--base-url', type=str, default='http://localhost:8000',
                        help='Base URL for testing')
    parser.add_argument('--n8n-url', type=str, default=None,
                        help='n8n server URL')
    parser.add_argument('--real-api-calls', action='store_true',
                        help='Make real API calls (uses credits)')
    parser.add_argument('--real-n8n', action='store_true',
                        help='Test with real n8n server')
    parser.add_argument('--force-n8n', action='store_true',
                        help='Force n8n tests even in local mode')
    parser.add_argument('--skip-django-tests', action='store_true',
                        help='Skip running Django tests')
    parser.add_argument('--skip-migrate', action='store_true',
                        help='Skip running migrations')
    parser.add_argument('--test-suite', type=str, default=None,
                        help='Specific Django test suite to run (e.g., "documents.tests")')

    args = parser.parse_args()

    # Run all tests
    all_passed = run_all_tests(args)

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()