from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import requests
import logging
import json
import uuid
from .models import DeploymentEvent, TestEvent, ServerMetrics

logger = logging.getLogger(__name__)


class APIKeyAuthentication:
    """Custom API key authentication for webhooks"""

    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        expected_key = getattr(settings, 'MONITORING_API_KEY', 'default-monitoring-key')

        if api_key and api_key == expected_key:
            return True
        return False


@method_decorator(csrf_exempt, name='dispatch')
class DeploymentStatusAPIView(APIView):
    """API endpoint to receive deployment status updates"""

    def post(self, request):
        try:
            # Authenticate request
            if not APIKeyAuthentication().authenticate(request):
                return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)

            data = request.data

            # Create deployment event
            deployment_event = DeploymentEvent.objects.create(
                event_id=data.get('event_id', str(uuid.uuid4())),
                repository=data.get('repository', 'job_automation'),
                branch=data.get('branch', 'main'),
                commit_sha=data.get('commit_sha', ''),
                status=data.get('status', 'unknown'),
                severity=data.get('severity', 'medium'),
                duration=data.get('duration', ''),
                deployment_url=data.get('deployment_url', ''),
                error_message=data.get('error_message', ''),
                raw_data=data
            )

            # Send to n8n webhook
            self.send_to_n8n('deployment-status', data)

            logger.info(f"Deployment status received: {data.get('status')} for {data.get('commit_sha', 'unknown')[:8]}")

            return Response({
                'status': 'success',
                'message': 'Deployment status recorded',
                'event_id': deployment_event.event_id
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error processing deployment status: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def send_to_n8n(self, webhook_path, data):
        """Send data to n8n webhook"""
        try:
            n8n_url = f"https://n8n.jobautomation.me/webhook/{webhook_path}"
            response = requests.post(n8n_url, json=data, timeout=30)
            if response.status_code == 200:
                logger.info(f"Successfully sent data to n8n webhook: {webhook_path}")
            else:
                logger.warning(f"n8n webhook responded with status {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to send data to n8n: {str(e)}")


@method_decorator(csrf_exempt, name='dispatch')
class TestResultsAPIView(APIView):
    """API endpoint to receive test results"""

    def post(self, request):
        try:
            if not APIKeyAuthentication().authenticate(request):
                return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)

            data = request.data

            # Calculate health status
            failed_count = data.get('failed', 0)
            pass_rate = data.get('pass_rate', 0)

            if failed_count > 0:
                health_status = 'unhealthy'
            elif pass_rate < 80:
                health_status = 'warning'
            else:
                health_status = 'healthy'

            # Create test event
            test_event = TestEvent.objects.create(
                event_id=data.get('event_id', str(uuid.uuid4())),
                total_tests=data.get('total_tests', 0),
                passed=data.get('passed', 0),
                failed=data.get('failed', 0),
                skipped=data.get('skipped', 0),
                pass_rate=data.get('pass_rate', 0),
                coverage=data.get('coverage'),
                duration=data.get('duration', ''),
                health_status=health_status,
                raw_data=data
            )

            # Send to n8n webhook
            self.send_to_n8n('test-results', data)

            logger.info(f"Test results received: {data.get('passed', 0)} passed, {failed_count} failed")

            return Response({
                'status': 'success',
                'message': 'Test results recorded',
                'event_id': test_event.event_id,
                'health_status': health_status
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error processing test results: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def send_to_n8n(self, webhook_path, data):
        """Send data to n8n webhook"""
        try:
            n8n_url = f"https://n8n.jobautomation.me/webhook/{webhook_path}"
            response = requests.post(n8n_url, json=data, timeout=30)
            logger.info(f"Sent test results to n8n: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to send test results to n8n: {str(e)}")


@method_decorator(csrf_exempt, name='dispatch')
class ServerMetricsAPIView(APIView):
    """API endpoint to receive server metrics"""

    def post(self, request):
        try:
            if not APIKeyAuthentication().authenticate(request):
                return Response({'error': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)

            data = request.data

            # Determine overall health
            cpu_usage = float(data.get('cpu_usage', 0))
            memory_usage = float(data.get('memory_usage', 0))
            disk_usage = float(data.get('disk_usage', 0))

            if cpu_usage > 90 or memory_usage > 90 or disk_usage > 90:
                overall_health = 'critical'
            elif cpu_usage > 70 or memory_usage > 80 or disk_usage > 80:
                overall_health = 'warning'
            else:
                overall_health = 'healthy'

            # Create metrics event
            metrics_event = ServerMetrics.objects.create(
                event_id=data.get('event_id', str(uuid.uuid4())),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                load_average=data.get('load_average', ''),
                uptime=data.get('uptime', ''),
                containers_running=data.get('containers_running', 0),
                containers_total=data.get('containers_total', 0),
                overall_health=overall_health,
                raw_data=data
            )

            # Send to n8n webhook
            self.send_to_n8n('server-metrics', data)

            logger.info(f"Server metrics received: CPU {cpu_usage}%, Memory {memory_usage}%, Disk {disk_usage}%")

            return Response({
                'status': 'success',
                'message': 'Server metrics recorded',
                'event_id': metrics_event.event_id,
                'overall_health': overall_health
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error processing server metrics: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def send_to_n8n(self, webhook_path, data):
        """Send data to n8n webhook"""
        try:
            n8n_url = f"https://n8n.jobautomation.me/webhook/{webhook_path}"
            response = requests.post(n8n_url, json=data, timeout=30)
            logger.info(f"Sent server metrics to n8n: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to send server metrics to n8n: {str(e)}")


# Health check endpoint
@csrf_exempt
def health_check(request):
    """Health check endpoint for monitoring"""
    try:
        from django.db import connection
        import redis

        # Check database
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Check Redis
        redis_client = redis.from_url(getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0'))
        redis_client.ping()

        return JsonResponse({
            'status': 'healthy',
            'database': 'ok',
            'redis': 'ok',
            'timestamp': '2024-01-01T00:00:00Z'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': '2024-01-01T00:00:00Z'
        }, status=500)