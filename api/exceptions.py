# CREATE NEW FILE: api/exceptions.py

import logging
from django.http import Http404
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    ValidationError, PermissionDenied as DRFPermissionDenied,
    NotAuthenticated, AuthenticationFailed, NotFound,
    MethodNotAllowed, ParseError, UnsupportedMediaType,
    Throttled, APIException
)

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for consistent API error responses
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # Get request info for logging
    request = context.get('request')
    view = context.get('view')

    if response is not None:
        # DRF handled the exception, customize the response format
        custom_response_data = {
            'success': False,
            'error': {
                'type': exc.__class__.__name__,
                'message': get_error_message(exc, response.data),
                'status_code': response.status_code,
                'details': response.data if isinstance(response.data, dict) else {'detail': response.data}
            }
        }

        # Add request info for debugging (only in development)
        from django.conf import settings
        if settings.DEBUG:
            custom_response_data['debug'] = {
                'path': request.path if request else None,
                'method': request.method if request else None,
                'view': view.__class__.__name__ if view else None,
                'user': str(request.user) if request and hasattr(request, 'user') else None
            }

        response.data = custom_response_data

        # Log the error
        log_api_exception(exc, request, response.status_code)

    else:
        # DRF didn't handle the exception, create our own response
        custom_response_data, status_code = handle_non_drf_exception(exc, context)
        response = Response(custom_response_data, status=status_code)

        # Log the error
        log_api_exception(exc, request, status_code)

    return response


def get_error_message(exc, response_data):
    """
    Extract a user-friendly error message from the exception
    """
    if hasattr(exc, 'detail'):
        if isinstance(exc.detail, dict):
            # Field-specific errors
            messages = []
            for field, errors in exc.detail.items():
                if isinstance(errors, list):
                    field_errors = ', '.join(str(error) for error in errors)
                else:
                    field_errors = str(errors)
                messages.append(f"{field}: {field_errors}")
            return '; '.join(messages)
        elif isinstance(exc.detail, list):
            return ', '.join(str(error) for error in exc.detail)
        else:
            return str(exc.detail)

    # Fallback to exception message
    return str(exc)


def handle_non_drf_exception(exc, context):
    """
    Handle exceptions that DRF doesn't handle by default
    """
    request = context.get('request')

    if isinstance(exc, Http404):
        return {
            'success': False,
            'error': {
                'type': 'NotFound',
                'message': 'The requested resource was not found.',
                'status_code': 404,
                'details': {'detail': 'Not found.'}
            }
        }, status.HTTP_404_NOT_FOUND

    elif isinstance(exc, PermissionDenied):
        return {
            'success': False,
            'error': {
                'type': 'PermissionDenied',
                'message': 'You do not have permission to perform this action.',
                'status_code': 403,
                'details': {'detail': 'Permission denied.'}
            }
        }, status.HTTP_403_FORBIDDEN

    elif isinstance(exc, DjangoValidationError):
        return {
            'success': False,
            'error': {
                'type': 'ValidationError',
                'message': 'Invalid data provided.',
                'status_code': 400,
                'details': {'detail': exc.messages if hasattr(exc, 'messages') else str(exc)}
            }
        }, status.HTTP_400_BAD_REQUEST

    else:
        # Unexpected server error
        logger.error(f"Unexpected API error: {exc}", exc_info=True)

        from django.conf import settings
        if settings.DEBUG:
            error_message = str(exc)
            error_details = {'detail': str(exc), 'type': exc.__class__.__name__}
        else:
            error_message = 'An internal server error occurred.'
            error_details = {'detail': 'Internal server error.'}

        return {
            'success': False,
            'error': {
                'type': 'InternalServerError',
                'message': error_message,
                'status_code': 500,
                'details': error_details
            }
        }, status.HTTP_500_INTERNAL_SERVER_ERROR


def log_api_exception(exc, request, status_code):
    """
    Log API exceptions with relevant context
    """
    try:
        user_info = f"User: {request.user}" if request and hasattr(request, 'user') else "User: Anonymous"
        path_info = f"Path: {request.path}" if request else "Path: Unknown"
        method_info = f"Method: {request.method}" if request else "Method: Unknown"

        log_message = f"API Exception - {exc.__class__.__name__}: {str(exc)} | {user_info} | {path_info} | {method_info}"

        if status_code >= 500:
            logger.error(log_message, exc_info=True)
        elif status_code >= 400:
            logger.warning(log_message)
        else:
            logger.info(log_message)

    except Exception as log_exc:
        # Don't let logging errors break the API
        logger.error(f"Error logging API exception: {log_exc}")


class CustomAPIException(APIException):
    """
    Custom API exception for business logic errors
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'A business logic error occurred.'
    default_code = 'business_error'

    def __init__(self, detail=None, code=None, status_code=None):
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail, code)


class JobApplicationNotFound(CustomAPIException):
    """
    Exception for when a job application is not found
    """
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Job application not found.'
    default_code = 'job_application_not_found'


class DocumentGenerationError(CustomAPIException):
    """
    Exception for document generation errors
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'Document generation failed.'
    default_code = 'document_generation_error'


class FollowUpError(CustomAPIException):
    """
    Exception for follow-up related errors
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Follow-up operation failed.'
    default_code = 'followup_error'