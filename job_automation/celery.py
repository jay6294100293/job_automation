# job_automation/celery.py
import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_automation.settings')

app = Celery('job_automation')
