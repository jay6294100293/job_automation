# dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [

    path('', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/', views.DashboardView.as_view(), name='main_dashboard'),

    # Analytics and reporting
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),

    # Quick actions
    path('quick-search/', views.QuickSearchView.as_view(), name='quick_search'),
    path('profile-health/', views.ProfileHealthCheckView.as_view(), name='profile_health'),

    # Pipeline management
    path('pipeline-update/', views.PipelineUpdateView.as_view(), name='pipeline_update'),

    # API endpoints for real-time updates
    path('api/stats/', views.DashboardAPIView.as_view(), name='dashboard_api'),
    path('api/notifications/', views.NotificationView.as_view(), name='notifications_api'),
    path('api/settings/', views.DashboardSettingsView.as_view(), name='dashboard_settings_api'),

    # Notification management
    path('notifications/', views.NotificationView.as_view(), name='notifications'),

    # Dashboard customization
    path('settings/', views.DashboardSettingsView.as_view(), name='settings'),

    # Skills Analysis & Development
    path('skills-analysis/', views.SkillsAnalysisView.as_view(), name='skills_analysis'),

    # ✅ INTERVIEW PREPARATION HUB - ADD THESE LINES
    path('interview-prep/', views.interview_prep_view, name='interview_prep'),
    path('interview-prep/<int:application_id>/', views.interview_prep_detail_view, name='interview_prep_detail'),

    # ✅ INTERVIEW PREP API ENDPOINTS - ADD THESE LINES
    path('api/practice-questions/<int:application_id>/', views.get_practice_questions, name='get_practice_questions'),
    path('api/generate-questions/<int:application_id>/', views.generate_additional_questions, name='generate_additional_questions'),
    path('api/save-notes/<int:application_id>/', views.save_notes, name='save_notes'),
    path('api/track-practice/', views.track_practice_session, name='track_practice'),
    path('api/practice-analytics/', views.get_practice_analytics, name='practice_analytics'),
    path('api/export-prep/<int:application_id>/', views.export_prep_materials, name='export_prep'),
    path('api/trigger-documents/<int:application_id>/', views.trigger_document_generation, name='trigger_document_generation'),

    # Market Intelligence
    path('market-intelligence/', views.MarketIntelligenceView.as_view(), name='market_intelligence'),

    # Weekly/Monthly Reports
    path('weekly-report/', views.WeeklyReportView.as_view(), name='weekly_report'),
    path('monthly-report/', views.WeeklyReportView.as_view(), name='monthly_report'),  # Can reuse same view

    # Bulk Document Download
    path('bulk-download/', views.BulkDocumentDownloadView.as_view(), name='bulk_download'),

    # Enhanced Pipeline Visualization
    path('pipeline-visualization/', views.PipelineVisualizationView.as_view(), name='pipeline_visualization'),

    # ========================================
    # NEW API ENDPOINTS FOR REAL-TIME UPDATES
    # ========================================

    # Quick stats for dashboard widgets
    path('api/quick-stats/', views.QuickStatsAPIView.as_view(), name='quick_stats_api'),

    # Application timeline data for charts
    path('api/application-timeline/', views.ApplicationTimelineAPIView.as_view(), name='application_timeline_api'),

    # Skills analysis API
    path('api/skills-analysis/', views.SkillsAnalysisView.as_view(), name='skills_analysis_api'),

    # Market intelligence API
    path('api/market-data/', views.MarketIntelligenceView.as_view(), name='market_data_api'),

    path('email-settings/', views.EmailSettingsView.as_view(), name='email_settings'),
    path('email-log/', views.EmailLogView.as_view(), name='email_log'),

    # API endpoints for AJAX requests
    path('api/email-stats/', views.EmailStatsAPIView.as_view(), name='email_stats_api'),
    path('api/recent-emails/', views.RecentEmailsAPIView.as_view(), name='recent_emails_api'),
    path('api/test-email-processing/', views.TestEmailProcessingView.as_view(), name='test_email_processing'),

    # Email processing actions
    path('email-action/', views.EmailProcessingActionView.as_view(), name='email_action'),
    path('bulk-email-action/', views.BulkEmailActionView.as_view(), name='bulk_email_action'),

    path('jobs/approval/', views.job_approval_dashboard, name='job_approval'),
]