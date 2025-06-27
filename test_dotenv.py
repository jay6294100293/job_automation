import os
from dotenv import load_dotenv
from pathlib import Path

# Get the directory containing this file
BASE_DIR = Path(__file__).resolve().parent

# Path to .env file
env_path = BASE_DIR / '.env'
print(f"Looking for .env at: {env_path}")
print(f".env exists: {env_path.exists()}")

# Load environment variables from .env file
load_dotenv(env_path)

# Check if environment variables are set
print("\nEnvironment variables after load_dotenv:")
print(f"GROQ_API_KEY set: {'Yes' if 'GROQ_API_KEY' in os.environ else 'No'}")
print(f"OPENROUTER_API_KEY set: {'Yes' if 'OPENROUTER_API_KEY' in os.environ else 'No'}")

# Set up Django to check settings
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_automation.settings')
django.setup()

from django.conf import settings
print("\nSettings values:")
print(f"settings.GROQ_API_KEY set: {'Yes' if settings.GROQ_API_KEY else 'No'}")
print(f"settings.OPENROUTER_API_KEY set: {'Yes' if settings.OPENROUTER_API_KEY else 'No'}")