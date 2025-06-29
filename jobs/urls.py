# jobs/urls.py
from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.JobListView.as_view(), name='job_list'),
    path('applications/', views.ApplicationListView.as_view(), name='applications'),
    path('applications/<int:pk>/', views.ApplicationDetailView.as_view(), name='application_detail'),
    path('applications/<int:pk>/update-status/', views.UpdateApplicationStatusView.as_view(), name='update_status'),

    # Universal search configuration management
    path('search-config/', views.JobSearchConfigView.as_view(), name='search_config'),
    path('search-config/create/', views.CreateSearchConfigView.as_view(), name='create_config'),
    path('search-config/<int:pk>/edit/', views.EditSearchConfigView.as_view(), name='edit_config'),
    path('search-config/<int:pk>/delete/', views.DeleteSearchConfigView.as_view(), name='delete_config'),

    # Search execution and automation
    path('search/<int:config_id>/', views.ExecuteSearchView.as_view(), name='execute_search'),
    path('bulk-action/', views.BulkActionView.as_view(), name='bulk_action'),

    # API endpoints for configuration management
    path('api/config/<int:config_id>/stats/', views.ConfigurationStatsView.as_view(), name='config_stats'),
    path('api/config/<int:config_id>/export/', views.ExportConfigurationView.as_view(), name='export_config'),
    path('api/search/<str:search_id>/progress/', views.SearchProgressView.as_view(), name='search_progress'),

    # N8N webhook endpoints for automation integration
    path('webhook/<str:webhook_type>/', views.N8NWebhookView.as_view(), name='n8n_webhook'),

    # Additional utility endpoints
    path('api/duplicate-config/<int:config_id>/', views.DuplicateConfigView.as_view(), name='duplicate_config'),
    path('api/toggle-config/<int:config_id>/', views.ToggleConfigView.as_view(), name='toggle_config'),
    path('api/schedule-search/<int:config_id>/', views.ScheduleSearchView.as_view(), name='schedule_search'),
]