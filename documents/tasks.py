# documents/tasks.py - UPDATED WITH DUAL AI SYSTEM
import logging
import os
from datetime import datetime
from decimal import Decimal
from typing import Dict

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from accounts.models import UserProfile
from jobs.models import JobApplication
from .ai_services import ai_service
from .models import GeneratedDocument, DocumentGenerationJob
from .prompts import prompts, optimizer
from .research import research_service

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def generate_all_documents(self, application_id):
    """Generate all documents for a job application using dual AI system"""
    try:
        application = JobApplication.objects.get(id=application_id)
        user_profile = UserProfile.objects.get(user=application.user)

        # Create document generation job
        job = DocumentGenerationJob.objects.create(
            application=application,
            status='processing'
        )

        logger.info(f"Starting dual AI document generation for {application.job_title} at {application.company_name}")

        # Prepare user and job data for prompts
        user_data = {
            'name': f"{application.user.first_name} {application.user.last_name}",
            'email': application.user.email,
            'phone': user_profile.phone_number or 'Not provided',
            'location': f"{user_profile.city}, {user_profile.country}" if user_profile.city else 'Not provided',
            'experience': user_profile.experience_summary or 'Professional background',
            'skills': user_profile.key_skills or 'Relevant skills',
            'education': user_profile.education_background or 'Educational background'
        }

        job_data = {
            'title': application.job_title,
            'company': application.company_name,
            'requirements': application.job_requirements or 'Not specified',
            'description': application.job_description or 'Not specified'
        }

        # Track generation stats
        total_tokens = 0
        total_cost = Decimal('0.0')
        documents_generated = 0
        provider_used = 'unknown'

        # Generate each document type using dual AI system
        document_types = [
            'resume',
            'cover_letter',
            'email_templates',
            'linkedin_messages',
            'video_script',
            'followup_schedule',
            'skills_analysis'
        ]

        for doc_type in document_types:
            try:
                result = generate_single_document.delay(
                    application_id, user_profile.id, doc_type, user_data, job_data
                ).get()

                if result['success']:
                    documents_generated += 1
                    total_tokens += result.get('tokens_used', 0)
                    total_cost += Decimal(str(result.get('cost', 0)))
                    provider_used = result.get('provider', provider_used)
                    logger.info(f"Generated {doc_type} using {result.get('provider')}")
                else:
                    logger.error(f"Failed to generate {doc_type}: {result.get('error')}")

            except Exception as e:
                logger.error(f"Error generating {doc_type}: {str(e)}")

        # Generate company research separately
        try:
            research_result = generate_company_research.delay(application_id).get()
            if research_result['success']:
                logger.info("Generated company research")
            else:
                logger.error(f"Company research failed: {research_result.get('error')}")
        except Exception as e:
            logger.error(f"Company research error: {str(e)}")

        # Update job status
        job.status = 'completed'
        job.completed_at = timezone.now()
        job.ai_provider_used = provider_used
        job.total_tokens = total_tokens
        job.total_cost = total_cost
        job.documents_generated = documents_generated
        job.save()

        logger.info(
            f"Document generation completed. Generated {documents_generated} documents using {total_tokens} tokens, cost: ${total_cost}")

        return {
            'success': True,
            'documents_generated': documents_generated,
            'total_tokens': total_tokens,
            'total_cost': float(total_cost),
            'provider_used': provider_used
        }

    except Exception as e:
        logger.error(f"Document generation failed: {str(e)}")
        if 'job' in locals():
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
        return {'success': False, 'error': str(e)}


@shared_task
def generate_single_document(application_id, user_profile_id, document_type, user_data=None, job_data=None):
    """Generate a single document using dual AI system"""
    try:
        application = JobApplication.objects.get(id=application_id)
        user_profile = UserProfile.objects.get(id=user_profile_id)

        # Prepare data if not provided
        if not user_data:
            user_data = {
                'name': f"{application.user.first_name} {application.user.last_name}",
                'email': application.user.email,
                'phone': user_profile.phone_number or 'Not provided',
                'location': f"{user_profile.city}, {user_profile.country}" if user_profile.city else 'Not provided',
                'experience': user_profile.experience_summary or 'Professional background',
                'skills': user_profile.key_skills or 'Relevant skills',
                'education': user_profile.education_background or 'Educational background'
            }

        if not job_data:
            job_data = {
                'title': application.job_title,
                'company': application.company_name,
                'requirements': application.job_requirements or 'Not specified',
                'description': application.job_description or 'Not specified'
            }

        # Get optimized prompt for document type
        prompt = _get_optimized_prompt(document_type, user_data, job_data)

        # Generate content using dual AI system
        result = ai_service.generate_content(
            prompt=prompt,
            document_type=document_type,
            user_id=application.user.id
        )

        if result['success']:
            # Save document
            content = result['content']
            file_path = _save_document_file(application, document_type, content)

            # Create/update database record
            document, created = GeneratedDocument.objects.update_or_create(
                application=application,
                document_type=document_type,
                defaults={
                    'file_path': file_path,
                    'content': content[:1000],  # Store preview
                    'ai_provider': result['provider'],
                    'tokens_used': result.get('tokens_used', 0),
                    'generation_time': result.get('generation_time', 0),
                    'cost_usd': result.get('cost', Decimal('0.0')),
                    'file_size': len(content.encode('utf-8'))
                }
            )

            logger.info(f"Generated {document_type} using {result['provider']} - {result.get('tokens_used')} tokens")

            return {
                'success': True,
                'document_id': document.id,
                'provider': result['provider'],
                'tokens_used': result.get('tokens_used', 0),
                'cost': float(result.get('cost', 0)),
                'generation_time': result.get('generation_time', 0),
                'file_path': file_path
            }
        else:
            logger.error(f"Failed to generate {document_type}: {result.get('error')}")
            return {
                'success': False,
                'error': result.get('error', 'Generation failed')
            }

    except Exception as e:
        logger.error(f"Single document generation error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def generate_company_research(application_id):
    """Generate company research using hybrid research system"""
    try:
        application = JobApplication.objects.get(id=application_id)

        logger.info(f"Starting company research for {application.company_name}")

        # Use hybrid research service
        research_result = research_service.research_company(
            application_id=application_id,
            company_name=application.company_name,
            job_title=application.job_title
        )

        if research_result['success']:
            # Create document record for research
            content = _format_research_content(research_result['data'])
            file_path = _save_document_file(application, 'company_research', content)

            document, created = GeneratedDocument.objects.update_or_create(
                application=application,
                document_type='company_research',
                defaults={
                    'file_path': file_path,
                    'content': content[:1000],
                    'ai_provider': 'hybrid_research',
                    'tokens_used': 0,  # Research may use tokens but tracked separately
                    'generation_time': 0,
                    'cost_usd': Decimal('0.0'),
                    'file_size': len(content.encode('utf-8'))
                }
            )

            logger.info(f"Company research completed for {application.company_name}")

            return {
                'success': True,
                'document_id': document.id,
                'research_source': research_result.get('source', 'unknown'),
                'file_path': file_path
            }
        else:
            logger.error(f"Company research failed: {research_result.get('error')}")
            return {
                'success': False,
                'error': research_result.get('error', 'Research failed')
            }

    except Exception as e:
        logger.error(f"Company research error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def _get_optimized_prompt(document_type: str, user_data: Dict, job_data: Dict) -> str:
    """Get optimized prompt for specific document type"""
    prompt_methods = {
        'resume': prompts.get_resume_prompt,
        'cover_letter': prompts.get_cover_letter_prompt,
        'email_templates': prompts.get_email_templates_prompt,
        'linkedin_messages': prompts.get_linkedin_messages_prompt,
        'video_script': prompts.get_video_script_prompt,
        'followup_schedule': prompts.get_followup_schedule_prompt,
        'skills_analysis': prompts.get_skills_analysis_prompt
    }

    if document_type in prompt_methods:
        prompt = prompt_methods[document_type](user_data, job_data)
        # Apply optimization
        optimized_prompt = optimizer.optimize_prompt(prompt)
        # Add format instructions
        final_prompt = optimizer.add_format_instructions(optimized_prompt, document_type)
        return final_prompt
    else:
        return f"Generate a professional {document_type} for {job_data['title']} at {job_data['company']}."


def _save_document_file(application, document_type, content):
    """Save document content to file"""
    try:
        # Create directory if it doesn't exist
        doc_dir = os.path.join(settings.MEDIA_ROOT, 'documents', str(application.user.id))
        os.makedirs(doc_dir, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{application.company_name}_{document_type}_{timestamp}.txt"
        filename = filename.replace(' ', '_').replace('/', '_')

        file_path = os.path.join(doc_dir, filename)

        # Save content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Return relative path for database storage
        relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
        return relative_path

    except Exception as e:
        logger.error(f"File save error: {str(e)}")
        return f"documents/{application.user.id}/error_{document_type}.txt"


def _format_research_content(research_data: Dict) -> str:
    """Format research data into readable content"""
    content = f"""COMPANY RESEARCH REPORT
Company: {research_data.get('company_name', 'Unknown')}
Research Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

COMPANY OVERVIEW
{research_data.get('overview', 'Not available')}

RECENT DEVELOPMENTS
{research_data.get('recent_news', 'Not available')}

INTERVIEW TALKING POINTS
{research_data.get('talking_points', 'Not available')}

QUESTIONS TO ASK
{research_data.get('questions', 'Not available')}

INDUSTRY CONTEXT
{research_data.get('industry_context', 'Not available')}
"""
    return content


# Legacy compatibility functions (update existing calls)
@shared_task
def generate_resume(application_id, user_profile_id):
    """Legacy compatibility for resume generation"""
    return generate_single_document(application_id, user_profile_id, 'resume')


@shared_task
def generate_cover_letter(application_id, user_profile_id):
    """Legacy compatibility for cover letter generation"""
    return generate_single_document(application_id, user_profile_id, 'cover_letter')


@shared_task
def generate_email_templates(application_id, user_profile_id):
    """Legacy compatibility for email templates generation"""
    return generate_single_document(application_id, user_profile_id, 'email_templates')