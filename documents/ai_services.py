# documents/ai_services.py - MAIN AI SERVICE MANAGER
import os

import requests
import time
import json
import logging
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from .models import AIUsageLog, AIProviderStatus

logger = logging.getLogger('documents.ai_services')


class AIServiceManager:
    """
    Manages dual AI providers: Groq (primary) + OpenRouter (fallback)
    Handles automatic failover, cost tracking, and performance monitoring
    """

    def __init__(self):
        self.primary_provider = settings.AI_SETTINGS.get('PRIMARY_PROVIDER', 'groq')
        self.fallback_provider = settings.AI_SETTINGS.get('FALLBACK_PROVIDER', 'openrouter')
        self.max_retries = settings.AI_SETTINGS.get('MAX_RETRIES', 3)
        self.timeout = settings.AI_SETTINGS.get('TIMEOUT_SECONDS', 30)

        # Initialize provider status
        # self._ensure_provider_status()

    def _ensure_provider_status(self):
        """Safely ensure provider status exists - only call when tables exist"""
        try:
            # Check if we can access the database and table exists
            from django.db import connection
            from .models import AIProviderStatus
            from django.utils import timezone

            # Check if table exists before querying
            table_names = connection.introspection.table_names()
            if 'documents_aiproviderstatus' not in table_names:
                logger.warning("AIProviderStatus table doesn't exist yet. Skipping provider status check.")
                return

            # Your existing code here - just add the table check above it
            AIProviderStatus.objects.get_or_create(
                provider_name='groq',
                defaults={
                    'is_available': True,
                    'api_key_configured': bool(os.getenv('GROQ_API_KEY')),
                    'last_checked': timezone.now()
                }
            )

            AIProviderStatus.objects.get_or_create(
                provider_name='openrouter',
                defaults={
                    'is_available': True,
                    'api_key_configured': bool(os.getenv('OPENROUTER_API_KEY')),
                    'last_checked': timezone.now()
                }
            )

        except Exception as e:
            # During migrations or initial setup, tables might not exist
            logger.warning(f"Could not ensure provider status (this is normal during migrations): {e}")

    def generate_content(self, prompt: str, document_type: str, user_id: int) -> Dict[str, Any]:
        """
        Main method to generate content using dual provider system
        Returns: {
            'content': str,
            'provider': str,
            'tokens_used': int,
            'cost': Decimal,
            'generation_time': float,
            'success': bool,
            'error': str (if any)
        }
        """
        start_time = time.time()

        # Try primary provider first
        result = self._try_provider(
            provider=self.primary_provider,
            prompt=prompt,
            document_type=document_type,
            user_id=user_id
        )

        if result['success']:
            result['generation_time'] = time.time() - start_time
            return result

        logger.warning(f"Primary provider {self.primary_provider} failed: {result.get('error')}")

        # Fallback to secondary provider
        result = self._try_provider(
            provider=self.fallback_provider,
            prompt=prompt,
            document_type=document_type,
            user_id=user_id
        )

        result['generation_time'] = time.time() - start_time
        return result

    def _try_provider(self, provider: str, prompt: str, document_type: str, user_id: int) -> Dict[str, Any]:
        """Try a specific AI provider"""

        # Check if provider is active
        status_obj = AIProviderStatus.objects.get(provider=provider)
        if not status_obj.is_active:
            return {
                'success': False,
                'error': f'{provider} is currently inactive',
                'provider': provider
            }

        # Check monthly budget
        if self._is_over_budget(provider):
            return {
                'success': False,
                'error': f'{provider} monthly budget exceeded',
                'provider': provider
            }

        try:
            if provider == 'groq':
                return self._call_groq(prompt, document_type, user_id)
            elif provider == 'openrouter':
                return self._call_openrouter(prompt, document_type, user_id)
            else:
                return {
                    'success': False,
                    'error': f'Unknown provider: {provider}',
                    'provider': provider
                }

        except Exception as e:
            logger.error(f"Error calling {provider}: {str(e)}")
            self._update_provider_failure(provider)
            return {
                'success': False,
                'error': str(e),
                'provider': provider
            }

    def _call_groq(self, prompt: str, document_type: str, user_id: int) -> Dict[str, Any]:
        """Call Groq API"""
        headers = {
            'Authorization': f'Bearer {settings.GROQ_API_KEY}',
            'Content-Type': 'application/json'
        }

        data = {
            'model': settings.GROQ_SETTINGS['MODEL'],
            'messages': [
                {
                    'role': 'system',
                    'content': f'You are an expert job application assistant. Generate a professional {document_type}.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': settings.GROQ_SETTINGS['MAX_TOKENS'],
            'temperature': settings.GROQ_SETTINGS['TEMPERATURE'],
            'top_p': settings.GROQ_SETTINGS['TOP_P']
        }

        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=self.timeout
        )

        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            tokens_used = result['usage']['total_tokens']

            # Calculate cost (Groq pricing: ~$0.59/1M tokens for 70B model)
            cost = Decimal(str(tokens_used * 0.59 / 1000000))

            # Log usage
            self._log_usage(user_id, 'groq', settings.GROQ_SETTINGS['MODEL'],
                            tokens_used, cost, document_type)

            # Update provider success
            self._update_provider_success('groq')

            return {
                'success': True,
                'content': content,
                'provider': 'groq',
                'tokens_used': tokens_used,
                'cost': cost,
                'model': settings.GROQ_SETTINGS['MODEL']
            }
        else:
            error_msg = f"Groq API error: {response.status_code} - {response.text}"
            self._update_provider_failure('groq')
            return {
                'success': False,
                'error': error_msg,
                'provider': 'groq'
            }

    def _call_openrouter(self, prompt: str, document_type: str, user_id: int) -> Dict[str, Any]:
        """Call OpenRouter API"""
        headers = {
            'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': settings.OPENROUTER_SETTINGS['SITE_URL'],
            'X-Title': settings.OPENROUTER_SETTINGS['APP_NAME']
        }

        data = {
            'model': settings.OPENROUTER_SETTINGS['MODEL'],
            'messages': [
                {
                    'role': 'system',
                    'content': f'You are an expert job application assistant. Generate a professional {document_type}.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': settings.OPENROUTER_SETTINGS['MAX_TOKENS'],
            'temperature': settings.OPENROUTER_SETTINGS['TEMPERATURE'],
            'top_p': settings.OPENROUTER_SETTINGS['TOP_P']
        }

        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=self.timeout
        )

        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            tokens_used = result['usage']['total_tokens']

            # Calculate cost (OpenRouter Llama 3.1 70B: ~$0.88/1M tokens)
            cost = Decimal(str(tokens_used * 0.88 / 1000000))

            # Log usage
            self._log_usage(user_id, 'openrouter', settings.OPENROUTER_SETTINGS['MODEL'],
                            tokens_used, cost, document_type)

            # Update provider success
            self._update_provider_success('openrouter')

            return {
                'success': True,
                'content': content,
                'provider': 'openrouter',
                'tokens_used': tokens_used,
                'cost': cost,
                'model': settings.OPENROUTER_SETTINGS['MODEL']
            }
        else:
            error_msg = f"OpenRouter API error: {response.status_code} - {response.text}"
            self._update_provider_failure('openrouter')
            return {
                'success': False,
                'error': error_msg,
                'provider': 'openrouter'
            }

    def _log_usage(self, user_id: int, provider: str, model: str, tokens: int, cost: Decimal, request_type: str):
        """Log API usage for cost tracking"""
        from django.contrib.auth.models import User

        try:
            user = User.objects.get(id=user_id)
            AIUsageLog.objects.create(
                user=user,
                provider=provider,
                model_used=model,
                tokens_used=tokens,
                cost_usd=cost,
                request_type=request_type
            )
            logger.info(f"Logged usage: {provider} - {tokens} tokens - ${cost}")
        except Exception as e:
            logger.error(f"Failed to log usage: {e}")

    def _update_provider_success(self, provider: str):
        """Update provider status on successful request"""
        try:
            status = AIProviderStatus.objects.get(provider=provider)
            status.last_success = timezone.now()
            status.total_requests += 1
            status.successful_requests += 1
            status.failure_count = 0  # Reset failure count on success

            # Update average response time (simplified)
            # In production, you'd track actual response times

            status.save()
        except Exception as e:
            logger.error(f"Failed to update provider success: {e}")

    def _update_provider_failure(self, provider: str):
        """Update provider status on failed request"""
        try:
            status = AIProviderStatus.objects.get(provider=provider)
            status.last_failure = timezone.now()
            status.total_requests += 1
            status.failure_count += 1

            # Deactivate provider if too many failures
            if status.failure_count >= 5:
                status.is_active = False
                logger.warning(f"Deactivated {provider} due to repeated failures")

            status.save()
        except Exception as e:
            logger.error(f"Failed to update provider failure: {e}")

    def _is_over_budget(self, provider: str) -> bool:
        """Check if provider is over monthly budget"""
        try:
            status = AIProviderStatus.objects.get(provider=provider)

            # Reset monthly counters if it's a new month
            now = timezone.now()
            if status.last_reset.month != now.month:
                status.monthly_cost = Decimal('0.0')
                status.monthly_requests = 0
                status.last_reset = now
                status.save()

            # Check budget limits
            if provider == 'groq':
                limit = settings.AI_SETTINGS.get('GROQ_MONTHLY_LIMIT', 10)
            else:
                limit = settings.AI_SETTINGS.get('OPENROUTER_MONTHLY_LIMIT', 10)

            return float(status.monthly_cost) >= limit

        except Exception as e:
            logger.error(f"Budget check failed: {e}")
            return False

    def get_provider_status(self) -> Dict[str, Any]:
        """Get current status of all providers"""
        status_data = {}

        for provider in ['groq', 'openrouter']:
            try:
                status = AIProviderStatus.objects.get(provider=provider)
                status_data[provider] = {
                    'active': status.is_active,
                    'success_rate': status.success_rate(),
                    'monthly_cost': float(status.monthly_cost),
                    'monthly_requests': status.monthly_requests,
                    'last_success': status.last_success,
                    'last_failure': status.last_failure,
                    'failure_count': status.failure_count
                }
            except AIProviderStatus.DoesNotExist:
                status_data[provider] = {
                    'active': False,
                    'error': 'Status not found'
                }

        return status_data

    def toggle_provider(self, provider: str, active: bool) -> bool:
        """Manually activate/deactivate a provider"""
        try:
            status = AIProviderStatus.objects.get(provider=provider)
            status.is_active = active
            if active:
                status.failure_count = 0  # Reset failures when manually activated
            status.save()
            logger.info(f"Provider {provider} {'activated' if active else 'deactivated'}")
            return True
        except Exception as e:
            logger.error(f"Failed to toggle provider {provider}: {e}")
            return False


# Singleton instance
ai_service = AIServiceManager()

