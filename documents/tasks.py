# documents/tasks.py
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
import os
import openai
import google.generativeai as genai
from datetime import datetime
import json
import logging

from .models import GeneratedDocument, DocumentGenerationJob
from jobs.models import JobApplication
from accounts.models import UserProfile

logger = logging.getLogger(__name__)

# Configure AI APIs
openai.api_key = settings.OPENAI_API_KEY
genai.configure(api_key=settings.GEMINI_API_KEY)


@shared_task(bind=True)
def generate_all_documents(self, application_id):
    """Generate all documents for a job application"""
    try:
        application = JobApplication.objects.get(id=application_id)
        user_profile = UserProfile.objects.get(user=application.user)

        # Create document generation job
        job = DocumentGenerationJob.objects.create(
            application=application,
            status='processing'
        )

        logger.info(f"Starting document generation for {application.job_title} at {application.company_name}")

        # Generate each document type
        documents = {}

        # 1. Generate Resume
        documents['resume'] = generate_resume.delay(application_id, user_profile.id).get()

        # 2. Generate Cover Letter
        documents['cover_letter'] = generate_cover_letter.delay(application_id, user_profile.id).get()

        # 3. Generate Email Templates
        documents['email_templates'] = generate_email_templates.delay(application_id, user_profile.id).get()

        # 4. Generate LinkedIn Messages
        documents['linkedin_messages'] = generate_linkedin_messages.delay(application_id, user_profile.id).get()

        # 5. Generate Video Script
        documents['video_script'] = generate_video_script.delay(application_id, user_profile.id).get()

        # 6. Generate Company Research
        documents['company_research'] = generate_company_research.delay(application_id).get()

        # 7. Generate Follow-up Schedule
        documents['followup_schedule'] = generate_followup_schedule.delay(application_id).get()

        # 8. Generate Skills Analysis
        documents['skills_analysis'] = generate_skills_analysis.delay(application_id, user_profile.id).get()

        # Create folder structure
        folder_path = create_document_folder(application)

        # Save all documents
        for doc_type, content in documents.items():
            if content:
                save_document(application, doc_type, content, folder_path)

        # Update application
        application.documents_generated = True
        application.documents_folder_path = folder_path
        application.save()

        # Update job status
        job.status = 'completed'
        job.completed_at = datetime.now()
        job.save()

        logger.info(f"Document generation completed for {application.job_title}")
        return f"Successfully generated all documents for {application.job_title}"

    except Exception as e:
        logger.error(f"Error generating documents: {str(e)}")
        job.status = 'failed'
        job.error_message = str(e)
        job.save()
        raise


@shared_task
def generate_resume(application_id, user_profile_id):
    """Generate ATS-optimized resume"""
    try:
        application = JobApplication.objects.get(id=application_id)
        user_profile = UserProfile.objects.get(id=user_profile_id)

        # Prepare context for AI
        context = {
            'user_name': user_profile.user.get_full_name(),
            'email': user_profile.user.email,
            'phone': user_profile.phone,
            'location': user_profile.location,
            'linkedin': user_profile.linkedin_url,
            'github': user_profile.github_url,
            'years_experience': user_profile.years_experience,
            'current_title': user_profile.current_job_title,
            'current_company': user_profile.current_company,
            'education': user_profile.education,
            'skills': user_profile.key_skills,
            'job_title': application.job_title,
            'company_name': application.company_name,
            'job_description': application.job_description,
        }

        prompt = f"""
        Create an ATS-optimized resume for {context['user_name']} applying for {context['job_title']} at {context['company_name']}.

        User Profile:
        - Experience: {context['years_experience']} years
        - Current Role: {context['current_title']} at {context['current_company']}
        - Education: {context['education']}
        - Skills: {', '.join(context['skills']) if context['skills'] else 'Not specified'}

        Job Requirements:
        {context['job_description'][:2000]}...

        Requirements:
        1. Use professional formatting suitable for ATS parsing
        2. Include relevant keywords from job description
        3. Quantify achievements where possible
        4. Tailor experience to match job requirements
        5. Keep to 1-2 pages maximum
        6. Use action verbs and measurable results

        Format as clean, professional resume content.
        """

        # Use Gemini for resume generation
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)

        return response.text

    except Exception as e:
        logger.error(f"Error generating resume: {str(e)}")
        return None


@shared_task
def generate_cover_letter(application_id, user_profile_id):
    """Generate personalized cover letter"""
    try:
        application = JobApplication.objects.get(id=application_id)
        user_profile = UserProfile.objects.get(id=user_profile_id)

        prompt = f"""
        Write a compelling cover letter for {user_profile.user.get_full_name()} applying for {application.job_title} at {application.company_name}.

        User Background:
        - {user_profile.years_experience} years of experience
        - Current role: {user_profile.current_job_title}
        - Key skills: {', '.join(user_profile.key_skills) if user_profile.key_skills else 'Various technical skills'}

        Job Details:
        {application.job_description[:1500]}...

        Requirements:
        1. Professional business letter format
        2. 3-4 paragraphs maximum
        3. Address specific job requirements
        4. Highlight relevant experience and achievements
        5. Show enthusiasm for the company and role
        6. Include a strong call-to-action
        7. Research-based company insights if possible

        Make it personal, engaging, and directly relevant to this specific position.
        """

        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)

        return response.text

    except Exception as e:
        logger.error(f"Error generating cover letter: {str(e)}")
        return None


@shared_task
def generate_email_templates(application_id, user_profile_id):
    """Generate email templates for application process"""
    try:
        application = JobApplication.objects.get(id=application_id)
        user_profile = UserProfile.objects.get(id=user_profile_id)

        prompt = f"""
        Create 4 professional email templates for {user_profile.user.get_full_name()} applying to {application.company_name} for {application.job_title}:

        1. APPLICATION EMAIL
        Subject: Application for {application.job_title} Position
        Content: Initial application submission email

        2. FOLLOW-UP EMAIL (1 week later)
        Subject: Following up on {application.job_title} Application
        Content: Professional follow-up after 1 week

        3. THANK YOU EMAIL (after interview)
        Subject: Thank you for the {application.job_title} Interview
        Content: Post-interview thank you note

        4. NETWORKING EMAIL (to current employees)
        Subject: Inquiry about {application.job_title} Opportunity at {application.company_name}
        Content: Networking email to connect with current employees

        Requirements:
        - Professional and concise
        - Personalized to the company and role
        - Include appropriate subject lines
        - Ready to copy-paste
        - Under 200 words each
        """

        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)

        return response.text

    except Exception as e:
        logger.error(f"Error generating email templates: {str(e)}")
        return None


@shared_task
def generate_linkedin_messages(application_id, user_profile_id):
    """Generate LinkedIn connection and messaging templates"""
    try:
        application = JobApplication.objects.get(id=application_id)
        user_profile = UserProfile.objects.get(id=user_profile_id)

        prompt = f"""
        Create 4 LinkedIn message templates for {user_profile.user.get_full_name()} regarding {application.job_title} at {application.company_name}:

        1. CONNECTION REQUEST to employees
        Subject: {application.company_name} {application.job_title} Opportunity
        Message: Brief connection request (under 200 characters)

        2. MESSAGE TO HR/RECRUITER
        Subject: Interest in {application.job_title} Position
        Message: Professional inquiry to HR

        3. MESSAGE TO HIRING MANAGER
        Subject: {application.job_title} - Experienced Professional
        Message: Direct message to potential hiring manager

        4. FOLLOW-UP MESSAGE
        Subject: Following up on {application.job_title} Discussion
        Message: Follow-up after initial connection

        Requirements:
        - LinkedIn character limits (300 chars for messages)
        - Professional yet personable tone
        - Specific to the role and company
        - Clear call-to-action
        - Respectful of recipient's time
        """

        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)

        return response.text

    except Exception as e:
        logger.error(f"Error generating LinkedIn messages: {str(e)}")
        return None


@shared_task
def generate_video_script(application_id, user_profile_id):
    """Generate 2-minute video pitch script"""
    try:
        application = JobApplication.objects.get(id=application_id)
        user_profile = UserProfile.objects.get(id=user_profile_id)

        prompt = f"""
        Write a compelling 2-minute video pitch script for {user_profile.user.get_full_name()} applying for {application.job_title} at {application.company_name}.

        Background:
        - {user_profile.years_experience} years experience
        - Current: {user_profile.current_job_title}
        - Skills: {', '.join(user_profile.key_skills) if user_profile.key_skills else 'Various'}

        Job: {application.job_title}
        Company: {application.company_name}

        Structure (exactly 2 minutes):
        [0:00-0:15] HOOK: Attention-grabbing opener
        [0:15-0:45] BACKGROUND: Relevant experience overview
        [0:45-1:45] VALUE PROPOSITION: What you bring to THIS company
        [1:45-2:00] CALL TO ACTION: Next steps

        Requirements:
        - Conversational, not scripted
        - Include timing cues
        - Stage directions for gestures
        - Company-specific details
        - Confident but humble tone
        - Clear pronunciation notes
        """

        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)

        return response.text

    except Exception as e:
        logger.error(f"Error generating video script: {str(e)}")
        return None


@shared_task
def generate_company_research(application_id):
    """Generate comprehensive company research report"""
    try:
        application = JobApplication.objects.get(id=application_id)

        prompt = f"""
        Create a comprehensive research report for {application.company_name} for someone applying for {application.job_title}.

        Include the following sections:

        1. COMPANY OVERVIEW
        - Mission, vision, values
        - Industry position
        - Size and locations
        - Business model

        2. RECENT NEWS (Last 6 months)
        - Major announcements
        - Funding/acquisitions
        - Product launches
        - Leadership changes

        3. CULTURE & WORK ENVIRONMENT
        - Company culture
        - Work-life balance
        - Diversity initiatives
        - Employee reviews insights

        4. GROWTH & FUTURE
        - Growth trajectory
        - Future plans
        - Market challenges
        - Opportunities

        5. INTERVIEW INSIGHTS
        - Common interview questions
        - Interview process
        - What they value in candidates
        - Red flags to avoid

        Make it actionable for job interview preparation.
        """

        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)

        return response.text

    except Exception as e:
        logger.error(f"Error generating company research: {str(e)}")
        return None


@shared_task
def generate_followup_schedule(application_id):
    """Generate personalized follow-up schedule"""
    try:
        application = JobApplication.objects.get(id=application_id)

        prompt = f"""
        Create a strategic follow-up schedule for {application.job_title} application at {application.company_name}.

        Consider:
        - Company size: {application.company_name}
        - Industry standards
        - Role level: {application.job_title}
        - Application urgency: {application.urgency_level}

        Provide a timeline with:
        1. Day 1: Application submitted
        2. Day 7: First follow-up
        3. Day 14: Second follow-up
        4. Day 21: Third follow-up
        5. Day 30: Final follow-up

        For each follow-up, include:
        - Timing rationale
        - Message tone/approach
        - Alternative contact methods
        - What to include
        - When to stop

        Format as actionable calendar with specific dates and actions.
        """

        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)

        return response.text

    except Exception as e:
        logger.error(f"Error generating follow-up schedule: {str(e)}")
        return None


@shared_task
def generate_skills_analysis(application_id, user_profile_id):
    """Generate skills gap analysis and recommendations"""
    try:
        application = JobApplication.objects.get(id=application_id)
        user_profile = UserProfile.objects.get(id=user_profile_id)

        prompt = f"""
        Analyze the skills match between the candidate and job requirements:

        CANDIDATE SKILLS:
        {', '.join(user_profile.key_skills) if user_profile.key_skills else 'Not specified'}

        JOB REQUIREMENTS:
        {application.job_description}

        Provide analysis in these sections:

        1. SKILLS YOU HAVE (matching requirements)
        - List skills that directly match
        - Rate proficiency level needed
        - How to highlight in interview

        2. SKILLS TO EMPHASIZE
        - Transferable skills
        - Related experience
        - Learning examples

        3. SKILLS GAP ANALYSIS
        - Missing requirements
        - Priority level (high/medium/low)
        - Learning difficulty

        4. QUICK WINS
        - Skills you can learn quickly
        - Certifications to get
        - Online courses to take

        5. INTERVIEW STRATEGY
        - How to address gaps honestly
        - Skills to emphasize most
        - Examples to prepare

        Make it actionable with specific recommendations.
        """

        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)

        return response.text

    except Exception as e:
        logger.error(f"Error generating skills analysis: {str(e)}")
        return None


def create_document_folder(application):
    """Create folder structure for application documents"""
    date_str = datetime.now().strftime("%Y_%m_%d")
    folder_name = f"Job_{application.id}_{application.company_name}_{application.job_title}_{date_str}"
    folder_name = "".join(c for c in folder_name if c.isalnum() or c in (' ', '-', '_')).rstrip()

    base_path = os.path.join(settings.MEDIA_ROOT, 'documents', str(application.user.id))
    folder_path = os.path.join(base_path, folder_name)

    os.makedirs(folder_path, exist_ok=True)

    return folder_path


def save_document(application, doc_type, content, folder_path):
    """Save generated document to file and database"""
    try:
        # Create filename
        date_str = datetime.now().strftime("%Y_%m_%d")
        doc_type_map = {
            'resume': f'Resume_{application.company_name}_{application.job_title}_{date_str}.pdf',
            'cover_letter': f'CoverLetter_{application.company_name}_{application.job_title}_{date_str}.pdf',
            'email_templates': f'EmailTemplates_{application.company_name}_{application.job_title}_{date_str}.txt',
            'linkedin_messages': f'LinkedInMessages_{application.company_name}_{application.job_title}_{date_str}.txt',
            'video_script': f'VideoPitchScript_{application.company_name}_{application.job_title}_{date_str}.txt',
            'company_research': f'CompanyResearch_{application.company_name}_{date_str}.pdf',
            'followup_schedule': f'FollowUpSchedule_{application.company_name}_{application.job_title}_{date_str}.pdf',
            'skills_analysis': f'SkillsAnalysis_{application.company_name}_{application.job_title}_{date_str}.pdf',
        }

        filename = doc_type_map.get(doc_type, f'{doc_type}_{date_str}.txt')
        file_path = os.path.join(folder_path, filename)

        # Write content to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Save to database
        GeneratedDocument.objects.update_or_create(
            application=application,
            document_type=doc_type,
            defaults={
                'file_path': file_path,
                'content': content[:5000],  # Store first 5000 chars for preview
                'file_size': len(content.encode('utf-8')),
            }
        )

        logger.info(f"Saved {doc_type} document for {application.job_title}")

    except Exception as e:
        logger.error(f"Error saving document {doc_type}: {str(e)}")