# job_automation/urls.py
from django.contrib import admin
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


# Custom admin site headers
admin.site.site_header = "Job Automation Admin"
admin.site.site_title = "Job Automation Admin Portal"
admin.site.index_title = "Welcome to Job Automation Administration"