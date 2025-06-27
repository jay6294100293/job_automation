from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# DRF Router for viewsets
router = DefaultRouter()
router.register(r'applications', views.ApplicationViewSet, basename='application')
router.register(r'followups', views.FollowUpViewSet, basename='followup')

app_name = 'api'

urlpatterns = [
    # DRF Router URLs (for standard CRUD operations)
    path('', include(router.urls)),

    # Token Authentication Endpoints (ADD THESE LINES)
    path('auth/token/', views.ObtainAuthTokenView.as_view(), name='obtain_token'),
    path('auth/token/refresh/', views.RefreshAuthTokenView.as_view(), name='refresh_token'),
    path('auth/token/validate/', views.ValidateTokenView.as_view(), name='validate_token'),
    path('auth/token/revoke/', views.RevokeTokenView.as_view(), name='revoke_token'),
    path('auth/register/', views.CreateUserWithTokenView.as_view(), name='register_user'),
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='change_password'),

    path('documents/', views.DocumentAPIView.as_view(), name='documents'),
    path('documents/bulk-action/', views.DocumentBulkActionAPIView.as_view(), name='documents_bulk_action'),
    path('documents/status/<int:application_id>/', views.DocumentStatusAPIView.as_view(), name='documents_status'),
    path('documents/generate/', views.DocumentAPIView.as_view(), name='documents_generate'),

    # User Profile API
    path('user/<int:user_id>/', views.UserProfileAPIView.as_view(), name='user_profile'),
    path('user/', views.UserProfileAPIView.as_view(), name='current_user_profile'),

    path('followups/send/', views.FollowUpAPIView.as_view(), name='followup_send'),
    path('followups/bulk/', views.BulkFollowUpAPIView.as_view(), name='followup_bulk'),
    path('followups/templates/', views.FollowUpTemplateAPIView.as_view(), name='followup_templates'),
    path('followups/history/', views.FollowUpHistoryAPIView.as_view(), name='followup_history_all'),
    path('followups/history/<int:application_id>/', views.FollowUpHistoryAPIView.as_view(), name='followup_history'),

    # Search Configurations API
    path('search-configs/<int:user_id>/', views.SearchConfigAPIView.as_view(), name='search_configs'),
    path('search-configs/', views.SearchConfigAPIView.as_view(), name='current_user_search_configs'),

    path('dashboard/stats/', views.DashboardStatsAPIView.as_view(), name='dashboard_stats'),
    path('dashboard/pipeline/', views.PipelineAPIView.as_view(), name='dashboard_pipeline'),
    path('dashboard/notifications/', views.NotificationAPIView.as_view(), name='dashboard_notifications'),

    # N8N Webhook Endpoints (No authentication required)
    path('n8n/webhook/job-search/', views.N8NJobSearchWebhook.as_view(), name='n8n_job_search'),
    path('n8n/webhook/followup/', views.N8NFollowUpWebhook.as_view(), name='n8n_followup'),
    path('n8n/webhook/document/', views.N8NDocumentWebhook.as_view(), name='n8n_document'),

    # Health check endpoint for monitoring
    path('health/', views.HealthCheckAPIView.as_view(), name='health_check'),


]