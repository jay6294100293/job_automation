# followups/urls.py
from django.urls import path
from . import views

app_name = 'followups'

urlpatterns = [
    path('', views.FollowUpDashboardView.as_view(), name='dashboard'),
    path('send/<int:application_id>/', views.SendFollowUpView.as_view(), name='send_followup'),
    path('bulk-send/', views.BulkFollowUpView.as_view(), name='bulk_followup'),
    path('schedule/<int:application_id>/', views.ScheduleFollowUpView.as_view(), name='schedule_followup'),
    path('templates/', views.TemplateManagementView.as_view(), name='templates'),
    path('templates/create/', views.CreateTemplateView.as_view(), name='create_template'),
    path('templates/<int:pk>/edit/', views.EditTemplateView.as_view(), name='edit_template'),
    path('history/', views.FollowUpHistoryView.as_view(), name='history'),
]