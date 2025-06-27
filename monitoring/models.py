from django.db import models
from django.contrib.auth.models import User
import json


class DeploymentEvent(models.Model):
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('in_progress', 'In Progress'),
        ('cancelled', 'Cancelled'),
    ]

    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    event_id = models.CharField(max_length=100, unique=True)
    repository = models.CharField(max_length=200, default='job_automation')
    branch = models.CharField(max_length=100, default='main')
    commit_sha = models.CharField(max_length=40)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    duration = models.CharField(max_length=50, blank=True)
    deployment_url = models.URLField(blank=True)
    error_message = models.TextField(blank=True)
    raw_data = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Deployment {self.commit_sha[:8]} - {self.status}"


class TestEvent(models.Model):
    HEALTH_CHOICES = [
        ('healthy', 'Healthy'),
        ('warning', 'Warning'),
        ('unhealthy', 'Unhealthy'),
    ]

    event_id = models.CharField(max_length=100, unique=True)
    total_tests = models.IntegerField(default=0)
    passed = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    skipped = models.IntegerField(default=0)
    pass_rate = models.FloatField(default=0.0)
    coverage = models.FloatField(null=True, blank=True)
    duration = models.CharField(max_length=50, blank=True)
    health_status = models.CharField(max_length=20, choices=HEALTH_CHOICES, default='healthy')
    raw_data = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Tests {self.timestamp.strftime('%Y-%m-%d %H:%M')} - {self.health_status}"


class ServerMetrics(models.Model):
    HEALTH_CHOICES = [
        ('healthy', 'Healthy'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]

    event_id = models.CharField(max_length=100, unique=True)
    cpu_usage = models.FloatField(default=0.0)
    memory_usage = models.FloatField(default=0.0)
    disk_usage = models.FloatField(default=0.0)
    load_average = models.CharField(max_length=50, blank=True)
    uptime = models.CharField(max_length=50, blank=True)
    containers_running = models.IntegerField(default=0)
    containers_total = models.IntegerField(default=0)
    overall_health = models.CharField(max_length=20, choices=HEALTH_CHOICES, default='healthy')
    raw_data = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Metrics {self.timestamp.strftime('%Y-%m-%d %H:%M')} - {self.overall_health}"