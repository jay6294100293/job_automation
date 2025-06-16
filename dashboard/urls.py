# dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/', views.DashboardView.as_view(), name='main_dashboard'),
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),
]