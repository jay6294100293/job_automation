from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# DRF Router for viewsets
router = DefaultRouter()
router.register(r'applications', views.ApplicationViewSet)
router.register(r'followups', views.FollowUpViewSet)

app_name = 'api'

urlpatterns = [
    path('', include(router.urls)),
    path('n8n/webhook/job-search/', views.N8NJobSearchWebhook.as_view(), name='n8n_job_search'),
    path('n8n/webhook/followup/', views.N8NFollowUpWebhook.as_view(), name='n8n_followup'),
    path('user/<int:user_id>/', views.UserProfileAPIView.as_view(), name='user_profile'),
    path('search-configs/<int:user_id>/', views.SearchConfigAPIView.as_view(), name='search_configs'),
]