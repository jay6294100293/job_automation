import os
import subprocess
import sys


def setup_project():
    """Setup script to initialize the Django project"""

    print("🚀 Setting up Job Automation System...")

    # Create .env file if it doesn't exist
    if not os.path.exists('.env'):
        print("📝 Creating .env file...")
        with open('.env', 'w') as f:
            f.write(ENV_TEMPLATE)
        print("✅ .env file created. Please update it with your credentials.")

    # Install dependencies
    print("📦 Installing dependencies...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])

    # Create necessary directories
    directories = [
        'media',
        'media/documents',
        'media/resumes',
        'staticfiles',
        'logs'
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 Created directory: {directory}")

    # Database setup
    print("🗄️ Setting up database...")

    management_commands = [
        ['python', 'manage.py', 'makemigrations'],
        ['python', 'manage.py', 'migrate'],
        ['python', 'manage.py', 'collectstatic', '--noinput'],
    ]

    for command in management_commands:
        print(f"Running: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error running {' '.join(command)}: {result.stderr}")
        else:
            print(f"✅ Successfully ran {' '.join(command)}")

    print("🎉 Project setup completed!")
    print("\nNext steps:")
    print("1. Update the .env file with your API keys and database credentials")
    print("2. Run: python manage.py setup_initial_data")
    print("3. Run: python manage.py create_sample_jobs --user-id=1 --count=15")
    print("4. Start Redis server")
    print("5. Start Celery worker: celery -A job_automation worker --loglevel=info")
    print("6. Start Django server: python manage.py runserver")


if __name__ == "__main__":
    setup_project()