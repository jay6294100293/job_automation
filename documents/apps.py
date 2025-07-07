from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'documents'

    def ready(self):
        """Called when Django is fully loaded"""
        try:
            from .ai_services import ai_service
            ai_service._ensure_provider_status()  # Safe to call here
        except Exception:
            pass
