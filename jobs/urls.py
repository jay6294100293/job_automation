# jobs/urls.py
from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.JobListView.as_view(), name='job_list'),
    path('search-config/', views.JobSearchConfigView.as_view(), name='search_config'),
    path('search-config/create/', views.CreateSearchConfigView.as_view(), name='create_config'),
    path('search-config/<int:pk>/edit/', views.EditSearchConfigView.as_view(), name='edit_config'),
    path('search-config/<int:pk>/delete/', views.DeleteSearchConfigView.as_view(), name='delete_config'),
    path('search/<int:config_id>/', views.ExecuteSearchView.as_view(), name='execute_search'),
    path('applications/', views.ApplicationListView.as_view(), name='applications'),
    path('applications/<int:pk>/', views.ApplicationDetailView.as_view(), name='application_detail'),
    path('applications/<int:pk>/update-status/', views.UpdateApplicationStatusView.as_view(), name='update_status'),
    path('bulk-action/', views.BulkActionView.as_view(), name='bulk_action'),
]