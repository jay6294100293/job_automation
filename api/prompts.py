from jobs.models import JobApplication
from django.db.models import Q, Avg
from datetime import datetime, timedelta


prompt  = f"""
Analyze this job posting and score it (0-100) for the user:

JOB:
Title: {job.job_title}
Company: {job.company_name}
Location: {job.location}
Salary: {job.salary_range}
Type: {job.employment_type}
Description: {job.job_description[:800]}...

USER:
Skills: {', '.join(user_context['skills'])}
Experience: {user_context['experience_years']} years
Current Role: {user_context['current_position']}
Target Salary: ${user_context['target_salary']}

Return JSON only:
{{
    "overall_score": 78,
    "skill_match": 85,
    "experience_match": 75,
    "location_match": 90,
    "salary_match": 70,
    "strengths": ["Python experience", "Remote friendly", "Good salary"],
    "concerns": ["Requires 5+ years", "Startup environment"],
    "recommendation": "recommended",
    "reasoning": "Strong technical match but experience gap"
}}
"""