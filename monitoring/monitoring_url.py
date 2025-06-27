from django.urls import path
from .views import (
    DeploymentStatusAPIView,
    TestResultsAPIView,
    ServerMetricsAPIView,
    health_check
)

app_name = 'monitoring'

urlpatterns = [
    path('deployment/', DeploymentStatusAPIView.as_view(), name='deployment_status'),
    path('tests/', TestResultsAPIView.as_view(), name='test_results'),
    path('metrics/', ServerMetricsAPIView.as_view(), name='server_metrics'),
    path('health/', health_check, name='health_check'),
]