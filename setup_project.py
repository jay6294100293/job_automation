# setup_project.py - Auto-generate complete project structure
"""
Quick setup script to create all necessary files and directories
Run this before testing: python setup_project.py
"""

import os
import sys
from pathlib import Path


def create_directory_structure():
    """Create all necessary directories"""
    directories = [
        'accounts/migrations',
        'jobs/migrations',
        'followups/migrations',
        'documents/migrations',
        'dashboard/migrations',
        'api/migrations',
        'templates/dashboard',
        'templates/accounts',
        'templates/jobs',
        'templates/followups',
        'templates/documents',
        'static/css',
        'static/js',
        'static/images',
        'media/documents',
        'tests',
        'logs'
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")


def create_init_files():
    """Create __init__.py files"""
    apps = ['accounts', 'jobs', 'followups', 'documents', 'dashboard', 'api', 'tests']

    for app in apps:
        init_file = Path(f"{app}/__init__.py")
        init_file.touch()
        print(f"✅ Created: {init_file}")


def create_requirements_txt():
    """Create requirements.txt file"""
    requirements = """Django==5.2.3
djangorestframework==3.14.0
django-cors-headers==4.0.0
django-crispy-forms==2.0
crispy-bootstrap5==0.7
python-decouple==3.8
psycopg2-binary==2.9.7
redis==4.5.5
celery==5.3.1
requests==2.31.0
openai==1.3.0
google-generativeai==0.3.0
Pillow==10.0.0
python-dotenv==1.0.0
discord.py==2.3.0
django-extensions==3.2.3
django-debug-toolbar==4.2.0

# Testing packages
pytest==7.4.0
pytest-django==4.5.2
coverage==7.3.0
factory-boy==3.3.0
freezegun==1.2.2

# Optional but recommended
flake8==6.0.0
black==23.7.0
isort==5.12.0
locust==2.17.0
"""

    with open('requirements.txt', 'w') as f:
        f.write(requirements)
    print("✅ Created requirements.txt")


def create_settings_py():
    """Create Django settings.py"""
    settings_content = """import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-key-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,ai.jobautomation.me').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'crispy_forms',
    'crispy_bootstrap5',

    # Local apps
    'accounts',
    'jobs',
    'followups',
    'documents',
    'dashboard',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'job_automation.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'job_automation.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Toronto'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "https://ai.jobautomation.me",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# Celery
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

# API Keys
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
N8N_WEBHOOK_URL = config('N8N_WEBHOOK_URL', default='')
DISCORD_BOT_TOKEN = config('DISCORD_BOT_TOKEN', default='')

# Auth
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
"""

    # Create job_automation directory if it doesn't exist
    Path('job_automation').mkdir(exist_ok=True)

    with open('job_automation/settings.py', 'w') as f:
        f.write(settings_content)
    print("✅ Created job_automation/settings.py")


def create_main_urls():
    """Create main urls.py"""
    urls_content = """from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('jobs/', include('jobs.urls')),
    path('followups/', include('followups.urls')),
    path('documents/', include('documents.urls')),
    path('api/', include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

admin.site.site_header = "Job Automation Admin"
admin.site.site_title = "Job Automation Admin Portal"
admin.site.index_title = "Welcome to Job Automation Administration"
"""

    with open('job_automation/urls.py', 'w') as f:
        f.write(urls_content)
    print("✅ Created job_automation/urls.py")


def create_app_files():
    """Create basic files for each app"""

    # Create models for each app
    app_models = {
        'accounts': """from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=255, blank=True)
    current_job_title = models.CharField(max_length=255, default='Developer')
    experience_level = models.CharField(max_length=20, default='mid')
    years_of_experience = models.IntegerField(default=0)
    primary_skills = models.TextField(blank=True)
    desired_job_titles = models.TextField(blank=True)
    professional_summary = models.TextField(blank=True)
    profile_completion_percentage = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name or self.user.username}"
""",
        'jobs': """from django.contrib.auth.models import User
from django.db import models

class JobApplication(models.Model):
    STATUS_CHOICES = [
        ('saved', 'Saved'),
        ('applied', 'Applied'),
        ('interview', 'Interview'),
        ('offer', 'Offer'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job_title = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    job_url = models.URLField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    salary_range = models.CharField(max_length=100, blank=True)
    job_description = models.TextField(blank=True)
    application_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='saved')
    applied_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.job_title} at {self.company_name}"

class JobSearchConfig(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    config_name = models.CharField(max_length=255)
    keywords = models.CharField(max_length=500)
    location = models.CharField(max_length=255)
    experience_level = models.CharField(max_length=50, default='mid')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.config_name
""",
        'followups': """from django.contrib.auth.models import User
from django.db import models
from jobs.models import JobApplication

class FollowUpTemplate(models.Model):
    TEMPLATE_TYPES = [
        ('initial', 'Initial Follow-up'),
        ('1_week', '1 Week Follow-up'),
        ('2_week', '2 Week Follow-up'),
        ('custom', 'Custom Template'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    template_name = models.CharField(max_length=255)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    subject_template = models.TextField()
    body_template = models.TextField()
    days_after_application = models.IntegerField(default=7)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.template_name

class FollowUpHistory(models.Model):
    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE)
    template = models.ForeignKey(FollowUpTemplate, on_delete=models.SET_NULL, null=True)
    sent_date = models.DateTimeField(auto_now_add=True)
    subject = models.CharField(max_length=500)
    body = models.TextField()
    response_received = models.BooleanField(default=False)

    def __str__(self):
        return f"Follow-up for {self.application.job_title}"
""",
        'documents': """from django.db import models
from jobs.models import JobApplication

class GeneratedDocument(models.Model):
    DOCUMENT_TYPES = [
        ('resume', 'Resume'),
        ('cover_letter', 'Cover Letter'),
        ('email_templates', 'Email Templates'),
        ('linkedin_messages', 'LinkedIn Messages'),
    ]

    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    file_path = models.CharField(max_length=500)
    content = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document_type} for {self.application.job_title}"

class DocumentGenerationJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"Doc generation for {self.application.job_title}"
""",
        'dashboard': """from django.contrib.auth.models import User
from django.db import models

class DashboardSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email_notifications = models.BooleanField(default=True)
    dashboard_layout = models.CharField(max_length=50, default='default')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Settings for {self.user.username}"
""",
        'api': """# API models - mostly handled by serializers
from django.db import models

# API-specific models if needed
"""
    }

    # Create models.py for each app
    for app, model_content in app_models.items():
        with open(f'{app}/models.py', 'w') as f:
            f.write(model_content)
        print(f"✅ Created {app}/models.py")

    # Create basic views for each app
    app_views = {
        'accounts': """from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'
""",
        'jobs': """from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from .models import JobApplication

class ApplicationListView(LoginRequiredMixin, ListView):
    model = JobApplication
    template_name = 'jobs/application_list.html'
    context_object_name = 'applications'

    def get_queryset(self):
        return JobApplication.objects.filter(user=self.request.user)

class ApplicationDetailView(LoginRequiredMixin, DetailView):
    model = JobApplication
    template_name = 'jobs/application_detail.html'
    context_object_name = 'application'

    def get_queryset(self):
        return JobApplication.objects.filter(user=self.request.user)
""",
        'followups': """from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from .models import FollowUpHistory

class FollowUpHistoryView(LoginRequiredMixin, ListView):
    model = FollowUpHistory
    template_name = 'followups/history.html'
    context_object_name = 'followups'

    def get_queryset(self):
        return FollowUpHistory.objects.filter(
            application__user=self.request.user
        )
""",
        'documents': """from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from .models import GeneratedDocument

class DocumentListView(LoginRequiredMixin, ListView):
    model = GeneratedDocument
    template_name = 'documents/document_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        return GeneratedDocument.objects.filter(
            application__user=self.request.user
        )
""",
        'dashboard': """from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from jobs.models import JobApplication

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['total_applications'] = JobApplication.objects.filter(user=user).count()
        context['recent_applications'] = JobApplication.objects.filter(user=user)[:5]

        return context
""",
        'api': """from rest_framework.viewsets import ModelViewSet
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from jobs.models import JobApplication

class ApplicationViewSet(ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return JobApplication.objects.filter(user=self.request.user)
"""
    }

    # Create views.py for each app
    for app, view_content in app_views.items():
        with open(f'{app}/views.py', 'w') as f:
            f.write(view_content)
        print(f"✅ Created {app}/views.py")

    # Create URLs for each app
    app_urls = {
        'accounts': """from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
]
""",
        'jobs': """from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('applications/', views.ApplicationListView.as_view(), name='application_list'),
    path('applications/<int:pk>/', views.ApplicationDetailView.as_view(), name='application_detail'),
]
""",
        'followups': """from django.urls import path
from . import views

app_name = 'followups'

urlpatterns = [
    path('history/', views.FollowUpHistoryView.as_view(), name='history'),
]
""",
        'documents': """from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.DocumentListView.as_view(), name='list'),
]
""",
        'dashboard': """from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
]
""",
        'api': """from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'applications', views.ApplicationViewSet, basename='application')

app_name = 'api'

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('rest_framework.urls')),
]
"""
    }

    # Create urls.py for each app
    for app, url_content in app_urls.items():
        with open(f'{app}/urls.py', 'w') as f:
            f.write(url_content)
        print(f"✅ Created {app}/urls.py")

    # Create admin.py for each app
    app_admins = {
        'accounts': """from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'current_job_title', 'created_at']
    search_fields = ['user__username', 'full_name']
""",
        'jobs': """from django.contrib import admin
from .models import JobApplication, JobSearchConfig

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ['job_title', 'company_name', 'application_status', 'created_at']
    list_filter = ['application_status', 'created_at']
    search_fields = ['job_title', 'company_name']

@admin.register(JobSearchConfig)
class JobSearchConfigAdmin(admin.ModelAdmin):
    list_display = ['config_name', 'keywords', 'location', 'is_active']
""",
        'followups': """from django.contrib import admin
from .models import FollowUpTemplate, FollowUpHistory

@admin.register(FollowUpTemplate)
class FollowUpTemplateAdmin(admin.ModelAdmin):
    list_display = ['template_name', 'template_type', 'user', 'is_active']

@admin.register(FollowUpHistory)
class FollowUpHistoryAdmin(admin.ModelAdmin):
    list_display = ['application', 'sent_date', 'response_received']
""",
        'documents': """from django.contrib import admin
from .models import GeneratedDocument, DocumentGenerationJob

@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ['application', 'document_type', 'generated_at']

@admin.register(DocumentGenerationJob)
class DocumentGenerationJobAdmin(admin.ModelAdmin):
    list_display = ['application', 'status', 'started_at']
""",
        'dashboard': """from django.contrib import admin
from .models import DashboardSettings

@admin.register(DashboardSettings)
class DashboardSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_notifications', 'created_at']
""",
        'api': """from django.contrib import admin
# API admin registrations if needed
"""
    }

    # Create admin.py for each app
    for app, admin_content in app_admins.items():
        with open(f'{app}/admin.py', 'w') as f:
            f.write(admin_content)
        print(f"✅ Created {app}/admin.py")

    # Create apps.py for each app
    for app in ['accounts', 'jobs', 'followups', 'documents', 'dashboard', 'api']:
        app_config = f"""from django.apps import AppConfig

class {app.title()}Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = '{app}'
"""
        with open(f'{app}/apps.py', 'w') as f:
            f.write(app_config)
        print(f"✅ Created {app}/apps.py")


def create_basic_templates():
    """Create basic HTML templates"""

    # Base template
    base_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Automation System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="{% url 'dashboard:dashboard' %}">Job Automation</a>
            <div class="navbar-nav ms-auto">
                {% if user.is_authenticated %}
                    <a class="nav-link" href="{% url 'dashboard:dashboard' %}">Dashboard</a>
                    <a class="nav-link" href="{% url 'jobs:application_list' %}">Applications</a>
                    <a class="nav-link" href="{% url 'accounts:logout' %}">Logout</a>
                {% else %}
                    <a class="nav-link" href="{% url 'accounts:login' %}">Login</a>
                {% endif %}
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% if messages %}
            {% for message in messages %}
                <div class="alert alert-{{ message.tags }}">{{ message }}</div>
            {% endfor %}
        {% endif %}

        {% block content %}
        {% endblock %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

    with open('templates/base.html', 'w') as f:
        f.write(base_template)
    print("✅ Created templates/base.html")

    # Dashboard template
    dashboard_template = """{% extends 'base.html' %}

{% block content %}
<div class="row">
    <div class="col-md-12">
        <h1>Dashboard</h1>
        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Total Applications</h5>
                        <h2 class="text-primary">{{ total_applications }}</h2>
                    </div>
                </div>
            </div>
        </div>

        <div class="mt-4">
            <h3>Recent Applications</h3>
            <div class="table-responsive">
                <table class="table">
                    <thead>
                        <tr>
                            <th>Job Title</th>
                            <th>Company</th>
                            <th>Status</th>
                            <th>Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for app in recent_applications %}
                        <tr>
                            <td>{{ app.job_title }}</td>
                            <td>{{ app.company_name }}</td>
                            <td>{{ app.get_application_status_display }}</td>
                            <td>{{ app.created_at|date:"M d, Y" }}</td>
                        </tr>
                        {% empty %}
                        <tr>
                            <td colspan="4">No applications yet</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

    with open('templates/dashboard/dashboard.html', 'w') as f:
        f.write(dashboard_template)
    print("✅ Created templates/dashboard/dashboard.html")


def create_wsgi_asgi():
    """Create WSGI and ASGI files"""

    wsgi_content = """import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_automation.settings')
application = get_wsgi_application()
"""

    asgi_content = """import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_automation.settings')
application = get_asgi_application()
"""

    with open('job_automation/wsgi.py', 'w') as f:
        f.write(wsgi_content)
    print("✅ Created job_automation/wsgi.py")

    with open('job_automation/asgi.py', 'w') as f:
        f.write(asgi_content)
    print("✅ Created job_automation/asgi.py")

    # Create __init__.py
    with open('job_automation/__init__.py', 'w') as f:
        f.write("")
    print("✅ Created job_automation/__init__.py")


def create_manage_py():
    """Create manage.py file"""
    manage_content = """#!/usr/bin/env python
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_automation.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
"""

    with open('manage.py', 'w') as f:
        f.write(manage_content)

    # Make manage.py executable
    os.chmod('manage.py', 0o755)
    print("✅ Created manage.py")


def run_initial_setup():
    """Run initial Django setup commands"""
    print("\n🔧 Running initial Django setup...")

    try:
        # Install requirements
        print("📦 Installing requirements...")
        os.system("pip install -r requirements.txt")

        # Make migrations
        print("🗄️ Creating migrations...")
        os.system("python manage.py makemigrations")

        # Apply migrations
        print("🗄️ Applying migrations...")
        os.system("python manage.py migrate")

        # Create superuser (optional, interactive)
        print("👤 You can create a superuser by running: python manage.py createsuperuser")

        # Collect static files
        print("📁 Collecting static files...")
        os.system("python manage.py collectstatic --noinput")

        print("✅ Initial setup complete!")

    except Exception as e:
        print(f"⚠️ Error during setup: {e}")
        print("You may need to run these commands manually:")
        print("1. pip install -r requirements.txt")
        print("2. python manage.py makemigrations")
        print("3. python manage.py migrate")
        print("4. python manage.py createsuperuser")


def main():
    """Main setup function"""
    print("🚀 Setting up Job Automation Django Project")
    print("=" * 50)

    # Check if we're in the right directory
    if not Path('manage.py').exists() and not Path('job_automation').exists():
        print("📂 Creating new Django project structure...")

        create_directory_structure()
        create_init_files()
        create_requirements_txt()
        create_settings_py()
        create_main_urls()
        create_wsgi_asgi()
        create_manage_py()
        create_app_files()
        create_basic_templates()

        print("\n✅ Project structure created successfully!")
        print("\n📋 Next steps:")
        print("1. Activate your virtual environment")
        print("2. Run: python setup_project.py --setup")
        print("3. Run: python run_tests.py")
        print("4. Start development: python manage.py runserver")

    elif '--setup' in sys.argv:
        run_initial_setup()
    else:
        print("Project structure already exists.")
        print("Run: python setup_project.py --setup to complete initial setup")


if __name__ == '__main__':
    main()