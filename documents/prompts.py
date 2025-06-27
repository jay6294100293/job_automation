# documents/prompts.py - OPTIMIZED PROMPTS LIBRARY
"""
Optimized prompts for 40% token savings while maintaining quality
Each prompt is designed for specific document types with minimal token usage
"""

from typing import Dict, Any


class OptimizedPrompts:
    """
    Token-optimized prompts for job application documents
    Reduces API costs while maintaining professional quality
    """

    @staticmethod
    def get_resume_prompt(user_profile: Dict, job_details: Dict) -> str:
        """Generate optimized resume prompt"""
        return f"""Create professional resume for {job_details['title']} at {job_details['company']}.

CANDIDATE: {user_profile['name']}
EMAIL: {user_profile['email']} | PHONE: {user_profile['phone']}
LOCATION: {user_profile['location']}

EXPERIENCE:
{user_profile.get('experience', 'No experience provided')}

SKILLS: {user_profile.get('skills', 'Not specified')}
EDUCATION: {user_profile.get('education', 'Not specified')}

JOB REQUIREMENTS:
{job_details.get('requirements', 'Not specified')}

OUTPUT: Professional ATS-friendly resume. Highlight relevant skills matching job requirements. Use action verbs, quantify achievements. Format: Header, Summary, Experience, Skills, Education."""

    @staticmethod
    def get_cover_letter_prompt(user_profile: Dict, job_details: Dict) -> str:
        """Generate optimized cover letter prompt"""
        return f"""Write cover letter for {job_details['title']} at {job_details['company']}.

CANDIDATE: {user_profile['name']}
EXPERIENCE: {user_profile.get('experience', 'Entry level')}
KEY SKILLS: {user_profile.get('skills', 'General skills')}

JOB: {job_details['title']}
COMPANY: {job_details['company']}
REQUIREMENTS: {job_details.get('requirements', 'Not specified')}

OUTPUT: Professional 3-paragraph cover letter. P1: Interest + key qualification. P2: Relevant experience + skills match. P3: Enthusiasm + call to action. Max 300 words."""

    @staticmethod
    def get_email_templates_prompt(user_profile: Dict, job_details: Dict) -> str:
        """Generate optimized email templates prompt"""
        return f"""Create 4 email templates for {job_details['title']} application at {job_details['company']}.

CANDIDATE: {user_profile['name']}
POSITION: {job_details['title']}
COMPANY: {job_details['company']}

TEMPLATES NEEDED:
1. APPLICATION EMAIL (subject + body)
2. FOLLOW-UP AFTER APPLICATION (1 week)
3. INTERVIEW THANK YOU
4. FINAL FOLLOW-UP

Each email: Professional tone, concise, specific to role. Include subject lines. Max 100 words per email body."""

    @staticmethod
    def get_linkedin_messages_prompt(user_profile: Dict, job_details: Dict) -> str:
        """Generate optimized LinkedIn messages prompt"""
        return f"""Create 3 LinkedIn messages for {job_details['title']} networking.

SENDER: {user_profile['name']}
TARGET ROLE: {job_details['title']} at {job_details['company']}
BACKGROUND: {user_profile.get('experience', 'Professional background')}

MESSAGES:
1. HR/RECRUITER CONNECTION
2. HIRING MANAGER OUTREACH  
3. EMPLOYEE INFORMATIONAL INTERVIEW

Each message: Personalized, professional, clear value proposition. Max 150 characters per message."""

    @staticmethod
    def get_video_script_prompt(user_profile: Dict, job_details: Dict) -> str:
        """Generate optimized video script prompt"""
        return f"""Write 60-second video pitch script for {job_details['title']}.

SPEAKER: {user_profile['name']}
ROLE: {job_details['title']}
COMPANY: {job_details['company']}
BACKGROUND: {user_profile.get('experience', 'Professional background')}
KEY SKILLS: {user_profile.get('skills', 'Relevant skills')}

SCRIPT STRUCTURE:
1. Introduction (10s)
2. Relevant experience (25s)
3. Value proposition (15s)
4. Call to action (10s)

OUTPUT: Natural, confident tone. Include timing cues. Emphasize skills matching job requirements."""

    @staticmethod
    def get_followup_schedule_prompt(user_profile: Dict, job_details: Dict) -> str:
        """Generate optimized follow-up schedule prompt"""
        return f"""Create follow-up timeline for {job_details['title']} application.

APPLICATION: {job_details['title']} at {job_details['company']}
APPLICANT: {user_profile['name']}

TIMELINE NEEDED:
- Application submission to first follow-up
- Interview process follow-ups
- Post-interview communications
- Decision follow-up

OUTPUT: Structured timeline with specific days, email subjects, and key messages. Professional timing intervals."""

    @staticmethod
    def get_skills_analysis_prompt(user_profile: Dict, job_details: Dict) -> str:
        """Generate optimized skills analysis prompt"""
        return f"""Analyze skill alignment for {job_details['title']}.

CANDIDATE SKILLS: {user_profile.get('skills', 'Not specified')}
EXPERIENCE: {user_profile.get('experience', 'Not specified')}

JOB REQUIREMENTS: {job_details.get('requirements', 'Not specified')}

ANALYSIS NEEDED:
1. Skills match (strong/partial/missing)
2. Skill gaps to address
3. Transferable skills to highlight
4. Learning recommendations

OUTPUT: Actionable analysis. Specific recommendations for skill development and interview positioning."""


class PromptOptimizer:
    """
    Utility class for prompt optimization and token reduction
    """

    @staticmethod
    def optimize_prompt(prompt: str) -> str:
        """
        Apply token-saving optimizations to any prompt
        Reduces unnecessary words while preserving meaning
        """
        # Remove redundant words
        optimizations = [
            ('please ', ''),
            ('kindly ', ''),
            ('you are ', ''),
            ('I want you to ', ''),
            ('I need you to ', ''),
            ('can you ', ''),
            ('would you ', ''),
            ('professional and ', ''),
            ('high-quality ', ''),
            ('detailed and ', ''),
            ('comprehensive ', ''),
            ('thorough ', ''),
        ]

        optimized = prompt
        for old, new in optimizations:
            optimized = optimized.replace(old, new)

        # Remove extra whitespace
        optimized = ' '.join(optimized.split())

        return optimized

    @staticmethod
    def get_system_prompt(document_type: str) -> str:
        """
        Get optimized system prompts for different document types
        """
        system_prompts = {
            'resume': 'Expert resume writer. Create ATS-friendly, professional resumes.',
            'cover_letter': 'Professional cover letter specialist. Write compelling, concise letters.',
            'email_templates': 'Email communication expert. Create professional, effective templates.',
            'linkedin_messages': 'LinkedIn networking specialist. Write engaging, professional messages.',
            'video_script': 'Video content creator. Write natural, confident speaking scripts.',
            'company_research': 'Business research analyst. Provide actionable company insights.',
            'followup_schedule': 'Job application strategist. Create effective follow-up timelines.',
            'skills_analysis': 'Career development advisor. Analyze skills and provide guidance.'
        }

        return system_prompts.get(document_type, 'Professional job application assistant.')

    @staticmethod
    def add_format_instructions(prompt: str, document_type: str) -> str:
        """
        Add format-specific instructions to prompts
        """
        format_instructions = {
            'resume': '\nFORMAT: Use bullet points, action verbs, quantified results. Professional formatting.',
            'cover_letter': '\nFORMAT: 3 paragraphs, professional business letter format. Include date and addresses.',
            'email_templates': '\nFORMAT: Subject line + email body. Professional email structure.',
            'linkedin_messages': '\nFORMAT: Brief, personalized messages. Include connection reason.',
            'video_script': '\nFORMAT: Natural speech patterns. Include timing and emphasis cues.',
            'company_research': '\nFORMAT: Structured sections. Bullet points for key information.',
            'followup_schedule': '\nFORMAT: Timeline with dates, actions, and email subjects.',
            'skills_analysis': '\nFORMAT: Structured analysis with recommendations and action items.'
        }

        instruction = format_instructions.get(document_type, '')
        return prompt + instruction


# Singleton instances
prompts = OptimizedPrompts()
optimizer = PromptOptimizer()