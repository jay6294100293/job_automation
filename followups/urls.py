# followups/urls.py
from django.urls import path
from . import views

app_name = 'followups'

urlpatterns = [
    # Main dashboard and core functionality
    path('', views.FollowUpDashboardView.as_view(), name='dashboard'),
    path('send/<int:application_id>/', views.SendFollowUpView.as_view(), name='send_followup'),
    path('bulk-send/', views.BulkFollowUpView.as_view(), name='bulk_followup'),
    path('schedule/<int:application_id>/', views.ScheduleFollowUpView.as_view(), name='schedule_followup'),

    # Template management
    path('templates/', views.TemplateManagementView.as_view(), name='templates'),
    path('templates/create/', views.CreateTemplateView.as_view(), name='create_template'),
    path('templates/<int:pk>/edit/', views.EditTemplateView.as_view(), name='edit_template'),
    path('templates/<int:pk>/delete/', views.DeleteTemplateView.as_view(), name='delete_template'),
    path('templates/<int:pk>/duplicate/', views.DuplicateTemplateView.as_view(), name='duplicate_template'),
    path('templates/<int:pk>/preview/', views.TemplatePreviewView.as_view(), name='preview_template'),
    path('templates/<int:pk>/test/', views.TestTemplateView.as_view(), name='test_template'),
    path('templates/<int:pk>/toggle-status/', views.ToggleTemplateStatusView.as_view(), name='toggle_template_status'),
    path('templates/<int:pk>/set-default/', views.SetDefaultTemplateView.as_view(), name='set_default_template'),

    # Follow-up history and tracking
    path('history/', views.FollowUpHistoryView.as_view(), name='history'),
    path('update-response/', views.UpdateFollowUpResponseView.as_view(), name='update_response'),

    # Analytics
    path('analytics/', views.FollowUpAnalyticsView.as_view(), name='analytics'),
]