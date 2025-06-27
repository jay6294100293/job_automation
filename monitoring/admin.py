from django.contrib import admin
from .models import DeploymentEvent, TestEvent, ServerMetrics

@admin.register(DeploymentEvent)
class DeploymentEventAdmin(admin.ModelAdmin):
    list_display = ['event_id', 'repository', 'branch', 'status', 'severity', 'timestamp']
    list_filter = ['status', 'severity', 'repository', 'branch']
    search_fields = ['event_id', 'commit_sha', 'repository']
    readonly_fields = ['event_id', 'timestamp']
    ordering = ['-timestamp']

@admin.register(TestEvent)
class TestEventAdmin(admin.ModelAdmin):
    list_display = ['event_id', 'total_tests', 'passed', 'failed', 'pass_rate', 'health_status', 'timestamp']
    list_filter = ['health_status', 'timestamp']
    search_fields = ['event_id']
    readonly_fields = ['event_id', 'timestamp']
    ordering = ['-timestamp']

@admin.register(ServerMetrics)
class ServerMetricsAdmin(admin.ModelAdmin):
    list_display = ['event_id', 'cpu_usage', 'memory_usage', 'disk_usage', 'overall_health', 'timestamp']
    list_filter = ['overall_health', 'timestamp']
    search_fields = ['event_id']
    readonly_fields = ['event_id', 'timestamp']
    ordering = ['-timestamp']