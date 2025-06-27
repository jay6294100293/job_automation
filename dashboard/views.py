import json
import os
import zipfile
from datetime import date
from datetime import datetime, timedelta
from datetime import time
from io import BytesIO

import openai
import requests
from celery import canvas
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import HttpResponse
# ADD THESE IMPORTS TO dashboard/views.py
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView, View

from accounts.models import UserProfile
from api.exceptions import logger

from documents.models import GeneratedDocument
from documents.tasks import generate_company_research as generate_company_research_task

from followups.models import FollowUpHistory
from job_automation import settings
from jobs.models import JobApplication, JobSearchConfig
from .forms import QuickSearchForm
from .models import UserNotification, DashboardSettings, DashboardActivity



class SkillsAnalysisView(LoginRequiredMixin, TemplateView):
    """Skills analysis and development recommendations"""
    template_name = 'dashboard/skills_analysis.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get user's applications and their requirements
        applications = JobApplication.objects.filter(user=user)

        # Analyze skills from job requirements
        required_skills = {}
        user_skills = user.userprofile.key_skills.split(',') if user.userprofile.key_skills else []

        for app in applications:
            if app.job_requirements:
                # Extract skills from job requirements (simplified logic)
                skills = app.job_requirements.lower().split()
                for skill in ['python', 'django', 'react', 'sql', 'aws', 'docker', 'kubernetes']:
                    if skill in ' '.join(skills):
                        required_skills[skill] = required_skills.get(skill, 0) + 1

        # Calculate skill gaps
        skills_you_have = [skill.strip().lower() for skill in user_skills]
        skills_to_highlight = []
        skills_to_develop = []

        for skill, count in required_skills.items():
            if skill in skills_you_have:
                skills_to_highlight.append({'skill': skill, 'demand': count})
            else:
                skills_to_develop.append({'skill': skill, 'demand': count})

        # Get recommended certifications
        certifications = self._get_recommended_certifications(skills_to_develop)

        context.update({
            'skills_you_have': skills_to_highlight,
            'skills_to_develop': sorted(skills_to_develop, key=lambda x: x['demand'], reverse=True)[:10],
            'recommended_certifications': certifications,
            'total_applications_analyzed': applications.count(),
        })

        return context

    def _get_recommended_certifications(self, skills_to_develop):
        """Get recommended certifications based on missing skills"""
        cert_mapping = {
            'aws': ['AWS Solutions Architect', 'AWS Developer Associate'],
            'docker': ['Docker Certified Associate', 'Kubernetes Administrator'],
            'python': ['Python Institute Certifications', 'Django Developer Certification'],
            'react': ['React Developer Certification', 'Frontend Developer Certification'],
        }

        recommendations = []
        for skill_data in skills_to_develop[:5]:  # Top 5 skills
            skill = skill_data['skill']
            if skill in cert_mapping:
                recommendations.extend(cert_mapping[skill])

        return list(set(recommendations))  # Remove duplicates





def generate_company_questions(application):
    """
    Generate company-specific interview questions using AI
    """
    try:
        openai.api_key = settings.OPENAI_API_KEY

        prompt = f"""
        Generate 5 company-specific interview questions for a {application.job_title} position at {application.company_name}.
        Consider the job description: {application.job_description[:500] if application.job_description else 'No description available'}

        Focus on:
        - Company values and culture
        - Industry-specific challenges
        - Role-specific responsibilities

        Return only the questions, one per line.
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert interview coach."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )

        questions = response.choices[0].message.content.strip().split('\n')
        return [q.strip() for q in questions if q.strip()]

    except Exception as e:
        # Fallback questions if AI generation fails
        return [
            f"Why do you want to work at {application.company_name}?",
            f"What do you know about {application.company_name}'s mission?",
            "How would you contribute to our team?",
            "What interests you most about this role?",
            "How do you handle workplace challenges?"
        ]


def generate_technical_questions(application):
    """
    Generate technical questions based on job requirements
    """
    try:
        openai.api_key = settings.OPENAI_API_KEY

        prompt = f"""
        Generate 4 technical interview questions for a {application.job_title} position.
        Job description: {application.job_description[:500] if application.job_description else 'No description available'}

        Focus on:
        - Core technical skills required
        - Problem-solving scenarios
        - Best practices in the field

        Return only the questions, one per line.
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a technical interview expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250,
            temperature=0.7
        )

        questions = response.choices[0].message.content.strip().split('\n')
        return [q.strip() for q in questions if q.strip()]

    except Exception as e:
        # Fallback technical questions
        job_title_lower = application.job_title.lower() if application.job_title else ""

        if 'developer' in job_title_lower or 'engineer' in job_title_lower:
            return [
                "Explain your approach to debugging complex issues",
                "How do you ensure code quality in your projects?",
                "Describe your experience with version control",
                "What testing strategies do you prefer?"
            ]
        elif 'data' in job_title_lower:
            return [
                "How do you handle missing data in datasets?",
                "Explain your data validation process",
                "What visualization tools do you prefer?",
                "How do you ensure data accuracy?"
            ]
        else:
            return [
                "Describe your problem-solving approach",
                "How do you stay updated in your field?",
                "What tools do you use for productivity?",
                "How do you handle tight deadlines?"
            ]


# dashboard/views.py (Add MarketIntelligenceView)

class MarketIntelligenceView(LoginRequiredMixin, TemplateView):
    """Market intelligence and trends analysis"""
    template_name = 'dashboard/market_intelligence.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get user's applications for analysis
        user_applications = JobApplication.objects.filter(
            user=self.request.user
        )

        # Extract job titles and categories
        job_titles = user_applications.values_list('job_title', flat=True).distinct()
        job_categories = []
        for app in user_applications:
            if hasattr(app, 'job_categories') and app.job_categories:
                categories = app.job_categories.split(',')
                job_categories.extend([cat.strip() for cat in categories])

        job_categories = list(set(job_categories))

        # Get data for market insights
        context.update({
            'job_titles': job_titles,
            'job_categories': job_categories,
            'selected_title': self.request.GET.get('job_title', ''),
            'selected_category': self.request.GET.get('job_category', ''),
            'time_period': self.request.GET.get('time_period', '30')
        })

        # If a specific title or category is selected, fetch market data
        if context['selected_title'] or context['selected_category']:
            context.update(self._get_market_data(
                context['selected_title'],
                context['selected_category'],
                int(context['time_period'])
            ))

        return context

    def _get_market_data(self, job_title, job_category, days):
        """Get market intelligence data for the selected filters"""
        try:
            # Prepare data to send to n8n
            webhook_data = {
                'user_id': self.request.user.id,
                'job_title': job_title,
                'job_category': job_category,
                'days': days
            }

            # Call n8n webhook to get market data
            response = requests.post(
                f"{settings.N8N_WEBHOOK_URL}/market-intelligence",
                json=webhook_data,
                headers={'Authorization': f'Bearer {settings.N8N_API_TOKEN}'}
            )

            if response.status_code == 200:
                market_data = response.json()

                # Process the data for display
                return {
                    'market_data': market_data,
                    'salary_data': self._process_salary_data(market_data.get('salary_data', [])),
                    'skills_data': self._process_skills_data(market_data.get('skills_data', [])),
                    'location_data': self._process_location_data(market_data.get('location_data', [])),
                    'trend_data': self._process_trend_data(market_data.get('trend_data', [])),
                    'top_companies': market_data.get('top_companies', [])[:10],
                    'market_insights': market_data.get('insights', [])
                }
            else:
                # If n8n call fails, generate some demo data
                return self._generate_demo_data(job_title, job_category)

        except Exception as e:
            logger.error(f"Error fetching market intelligence: {str(e)}")
            # Return fallback demo data
            return self._generate_demo_data(job_title, job_category)

    def _process_salary_data(self, salary_data):
        """Process salary data for chart display"""
        if not salary_data:
            return None

        return {
            'labels': ['10th', '25th', 'Median', '75th', '90th'],
            'datasets': [{
                'label': 'Salary Range (USD)',
                'data': [
                    salary_data.get('percentile_10', 0),
                    salary_data.get('percentile_25', 0),
                    salary_data.get('median', 0),
                    salary_data.get('percentile_75', 0),
                    salary_data.get('percentile_90', 0)
                ],
                'backgroundColor': 'rgba(79, 70, 229, 0.8)'
            }]
        }

    def _process_skills_data(self, skills_data):
        """Process skills data for chart display"""
        if not skills_data:
            return None

        # Sort by demand score
        sorted_skills = sorted(skills_data, key=lambda x: x.get('demand_score', 0), reverse=True)[:10]

        return {
            'labels': [skill.get('name', '') for skill in sorted_skills],
            'datasets': [{
                'label': 'Demand Score',
                'data': [skill.get('demand_score', 0) for skill in sorted_skills],
                'backgroundColor': 'rgba(16, 185, 129, 0.8)'
            }]
        }

    def _process_location_data(self, location_data):
        """Process location data for chart display"""
        if not location_data:
            return None

        # Sort by job count
        sorted_locations = sorted(location_data, key=lambda x: x.get('job_count', 0), reverse=True)[:8]

        return {
            'labels': [loc.get('name', '') for loc in sorted_locations],
            'datasets': [{
                'label': 'Job Openings',
                'data': [loc.get('job_count', 0) for loc in sorted_locations],
                'backgroundColor': 'rgba(14, 165, 233, 0.8)'
            }]
        }

    def _process_trend_data(self, trend_data):
        """Process trend data for chart display"""
        if not trend_data:
            return None

        # Sort by date
        sorted_trends = sorted(trend_data, key=lambda x: x.get('date', ''))

        return {
            'labels': [item.get('date', '') for item in sorted_trends],
            'datasets': [{
                'label': 'Job Postings',
                'data': [item.get('job_count', 0) for item in sorted_trends],
                'borderColor': 'rgba(79, 70, 229, 1)',
                'backgroundColor': 'rgba(79, 70, 229, 0.1)',
                'tension': 0.4,
                'fill': True
            }]
        }

        # dashboard/views.py (Continue MarketIntelligenceView)

        def _generate_demo_data(self, job_title, job_category):
            """Generate demo data for display when API is unavailable"""
            title = job_title if job_title else job_category if job_category else "Data Scientist"

            # Sample data for demonstration
            return {
                'salary_data': {
                    'labels': ['10th', '25th', 'Median', '75th', '90th'],
                    'datasets': [{
                        'label': 'Salary Range (USD)',
                        'data': [75000, 90000, 110000, 130000, 150000],
                        'backgroundColor': 'rgba(79, 70, 229, 0.8)'
                    }]
                },
                'skills_data': {
                    'labels': ['Python', 'SQL', 'Machine Learning', 'Data Analysis', 'TensorFlow', 'PyTorch', 'AWS',
                               'Spark', 'Docker', 'Git'],
                    'datasets': [{
                        'label': 'Demand Score',
                        'data': [95, 88, 82, 78, 72, 68, 65, 60, 55, 52],
                        'backgroundColor': 'rgba(16, 185, 129, 0.8)'
                    }]
                },
                'location_data': {
                    'labels': ['San Francisco', 'New York', 'Seattle', 'Boston', 'Austin', 'Toronto', 'Vancouver',
                               'Remote'],
                    'datasets': [{
                        'label': 'Job Openings',
                        'data': [580, 520, 420, 310, 280, 260, 210, 850],
                        'backgroundColor': 'rgba(14, 165, 233, 0.8)'
                    }]
                },
                'trend_data': {
                    'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    'datasets': [{
                        'label': 'Job Postings',
                        'data': [1200, 1350, 1100, 1500, 1700, 1600],
                        'borderColor': 'rgba(79, 70, 229, 1)',
                        'backgroundColor': 'rgba(79, 70, 229, 0.1)',
                        'tension': 0.4,
                        'fill': True
                    }]
                },
                'top_companies': [
                    {'name': 'Google', 'job_count': 125, 'avg_salary': 145000},
                    {'name': 'Microsoft', 'job_count': 110, 'avg_salary': 140000},
                    {'name': 'Amazon', 'job_count': 95, 'avg_salary': 135000},
                    {'name': 'Facebook', 'job_count': 85, 'avg_salary': 150000},
                    {'name': 'Apple', 'job_count': 75, 'avg_salary': 142000},
                    {'name': 'Netflix', 'job_count': 45, 'avg_salary': 155000},
                    {'name': 'IBM', 'job_count': 70, 'avg_salary': 125000},
                    {'name': 'Adobe', 'job_count': 65, 'avg_salary': 130000},
                    {'name': 'Oracle', 'job_count': 60, 'avg_salary': 128000},
                    {'name': 'Salesforce', 'job_count': 55, 'avg_salary': 132000}
                ],
                'market_insights': [
                    f"Demand for {title} roles has increased by 18% in the last 6 months.",
                    f"The average time to fill a {title} position is currently 32 days.",
                    f"Remote work options are available for 65% of {title} positions.",
                    f"The most in-demand certification for {title} roles is AWS Certified Solutions Architect.",
                    f"Companies are increasingly looking for {title}s with experience in cloud technologies.",
                    f"Strong communication skills are mentioned in 78% of {title} job descriptions."
                ]
            }

class WeeklyReportView(LoginRequiredMixin, TemplateView):
    """Weekly performance report"""
    template_name = 'dashboard/weekly_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Calculate week boundaries
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        # Get this week's data
        this_week_apps = JobApplication.objects.filter(
            user=user,
            created_at__date__range=[week_start, week_end]
        )

        # Get last week's data for comparison
        last_week_start = week_start - timedelta(days=7)
        last_week_end = week_start - timedelta(days=1)
        last_week_apps = JobApplication.objects.filter(
            user=user,
            created_at__date__range=[last_week_start, last_week_end]
        )

        # Calculate metrics
        this_week_metrics = {
            'applications': this_week_apps.count(),
            'responses': this_week_apps.filter(
                application_status__in=['responded', 'interview', 'offer']
            ).count(),
            'interviews': this_week_apps.filter(application_status='interview').count(),
            'offers': this_week_apps.filter(application_status='offer').count(),
        }

        last_week_metrics = {
            'applications': last_week_apps.count(),
            'responses': last_week_apps.filter(
                application_status__in=['responded', 'interview', 'offer']
            ).count(),
            'interviews': last_week_apps.filter(application_status='interview').count(),
            'offers': last_week_apps.filter(application_status='offer').count(),
        }

        # Calculate percentage changes
        changes = {}
        for metric in this_week_metrics:
            if last_week_metrics[metric] > 0:
                change = ((this_week_metrics[metric] - last_week_metrics[metric]) /
                          last_week_metrics[metric]) * 100
                changes[metric] = round(change, 1)
            else:
                changes[metric] = 100 if this_week_metrics[metric] > 0 else 0

        # Get weekly goals and achievements
        goals = self._get_weekly_goals(user)
        achievements = self._calculate_achievements(this_week_metrics, goals)

        context.update({
            'week_start': week_start,
            'week_end': week_end,
            'this_week': this_week_metrics,
            'last_week': last_week_metrics,
            'changes': changes,
            'goals': goals,
            'achievements': achievements,
            'weekly_applications': this_week_apps.order_by('-created_at'),
            'top_companies': self._get_top_companies(this_week_apps),
        })

        return context

    def _get_weekly_goals(self, user):
        """Get or create weekly goals for user"""
        # This could be stored in user preferences or a separate model
        return {
            'applications': 20,
            'responses': 5,
            'interviews': 2,
            'offers': 1,
        }

    def _calculate_achievements(self, metrics, goals):
        """Calculate goal achievements"""
        achievements = {}
        for metric, goal in goals.items():
            if goal > 0:
                achievement = (metrics[metric] / goal) * 100
                achievements[metric] = min(round(achievement, 1), 100)
            else:
                achievements[metric] = 0
        return achievements

    def _get_top_companies(self, applications):
        """Get top companies applied to this week"""
        return applications.values('company_name').annotate(
            count=Count('id')
        ).order_by('-count')[:5]


# dashboard/views.py (Update the BulkDocumentDownloadView)

class BulkDocumentDownloadView(LoginRequiredMixin, TemplateView):
    """Bulk document download functionality"""
    template_name = 'dashboard/bulk_download.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get user's applications with documents
        applications = JobApplication.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

        # Count documents for each application
        for app in applications:
            app.document_count = GeneratedDocument.objects.filter(
                application=app
            ).count()

        # Filter to only show applications with documents
        applications_with_docs = [app for app in applications if app.document_count > 0]

        # Group documents by type
        document_types = GeneratedDocument.objects.filter(
            application__user=self.request.user
        ).values('document_type').annotate(
            count=Count('id')
        ).order_by('document_type')

        context['applications'] = applications_with_docs
        context['document_types'] = document_types
        context['total_documents'] = GeneratedDocument.objects.filter(
            application__user=self.request.user
        ).count()

        return context

    def post(self, request):
        """Handle bulk document download requests"""
        try:
            download_type = request.POST.get('download_type')

            if download_type == 'all_documents':
                # Download all documents
                return self._download_all_documents()

            elif download_type == 'selected_applications':
                # Download documents for selected applications
                application_ids = request.POST.getlist('application_ids')
                if not application_ids:
                    messages.error(request, 'Please select at least one application.')
                    return redirect('dashboard:bulk_download')

                return self._download_selected_applications(application_ids)

            elif download_type == 'selected_document_types':
                # Download specific document types across all applications
                document_types = request.POST.getlist('document_types')
                if not document_types:
                    messages.error(request, 'Please select at least one document type.')
                    return redirect('dashboard:bulk_download')

                return self._download_selected_document_types(document_types)

            elif download_type == 'date_range':
                # Download documents within a date range
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')

                if not start_date or not end_date:
                    messages.error(request, 'Please specify both start and end dates.')
                    return redirect('dashboard:bulk_download')

                try:
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

                    if start_date > end_date:
                        messages.error(request, 'Start date cannot be after end date.')
                        return redirect('dashboard:bulk_download')

                    return self._download_date_range(start_date, end_date)
                except ValueError:
                    messages.error(request, 'Invalid date format. Please use YYYY-MM-DD.')
                    return redirect('dashboard:bulk_download')

            else:
                messages.error(request, 'Invalid download type.')
                return redirect('dashboard:bulk_download')

        except Exception as e:
            messages.error(request, f'Error processing download: {str(e)}')
            return redirect('dashboard:bulk_download')

    def _download_all_documents(self):
        """Download all documents for the user"""
        try:
            documents = GeneratedDocument.objects.filter(
                application__user=self.request.user
            )

            if not documents.exists():
                messages.error(self.request, 'No documents found to download.')
                return redirect('dashboard:bulk_download')

            # Create a zip file
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for document in documents:
                    filename = f"{document.application.company_name}_{document.application.job_title}_{document.document_type}.pdf".replace(
                        ' ', '_')

                    # Get the document content (assuming PDF)
                    if document.file_path and os.path.exists(document.file_path):
                        # File exists on disk
                        with open(document.file_path, 'rb') as file:
                            zip_file.writestr(filename, file.read())
                    else:
                        # Generate PDF from content
                        pdf_content = self._generate_pdf_from_content(document.content)
                        zip_file.writestr(filename, pdf_content)

            # Prepare response
            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="all_documents.zip"'

            return response

        except Exception as e:
            messages.error(self.request, f'Error creating zip file: {str(e)}')
            return redirect('dashboard:bulk_download')

    # dashboard/views.py (Continue BulkDocumentDownloadView)

    def _download_selected_document_types(self, document_types):
        """Download specific document types across all applications"""
        try:
            documents = GeneratedDocument.objects.filter(
                application__user=self.request.user,
                document_type__in=document_types
            )

            if not documents.exists():
                messages.error(self.request, 'No documents found for the selected types.')
                return redirect('dashboard:bulk_download')

            # Create a zip file
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for document in documents:
                    filename = f"{document.application.company_name}_{document.application.job_title}_{document.document_type}.pdf".replace(
                        ' ', '_')

                    # Get the document content (assuming PDF)
                    if document.file_path and os.path.exists(document.file_path):
                        # File exists on disk
                        with open(document.file_path, 'rb') as file:
                            zip_file.writestr(filename, file.read())
                    else:
                        # Generate PDF from content
                        pdf_content = self._generate_pdf_from_content(document.content)
                        zip_file.writestr(filename, pdf_content)

            # Prepare response
            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="selected_document_types.zip"'

            return response

        except Exception as e:
            messages.error(self.request, f'Error creating zip file: {str(e)}')
            return redirect('dashboard:bulk_download')

    def _download_date_range(self, start_date, end_date):
        """Download documents within a date range"""
        try:
            # Convert end_date to include the entire day
            end_date = datetime.combine(end_date, time.max)

            documents = GeneratedDocument.objects.filter(
                application__user=self.request.user,
                generated_at__gte=start_date,
                generated_at__lte=end_date
            )

            if not documents.exists():
                messages.error(self.request, 'No documents found in the specified date range.')
                return redirect('dashboard:bulk_download')

            # Create a zip file
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for document in documents:
                    filename = f"{document.application.company_name}_{document.application.job_title}_{document.document_type}.pdf".replace(
                        ' ', '_')

                    # Get the document content (assuming PDF)
                    if document.file_path and os.path.exists(document.file_path):
                        # File exists on disk
                        with open(document.file_path, 'rb') as file:
                            zip_file.writestr(filename, file.read())
                    else:
                        # Generate PDF from content
                        pdf_content = self._generate_pdf_from_content(document.content)
                        zip_file.writestr(filename, pdf_content)

            # Prepare response
            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer, content_type='application/zip')
            response[
                'Content-Disposition'] = f'attachment; filename="documents_{start_date.strftime("%Y-%m-%d")}_to_{end_date.strftime("%Y-%m-%d")}.zip"'

            return response

        except Exception as e:
            messages.error(self.request, f'Error creating zip file: {str(e)}')
            return redirect('dashboard:bulk_download')

    def _generate_pdf_from_content(self, content):
        """Generate a PDF from text content"""
        # Create a file-like buffer to receive PDF data
        buffer = BytesIO()

        # Create the PDF object using the buffer as its "file"
        p = canvas.Canvas(buffer)

        # Set up the PDF document
        p.setFont("Helvetica", 12)

        # Write the content to the PDF
        y = 800  # Starting y position
        for line in content.split('\n'):
            if y < 50:  # If we're near the bottom of the page
                p.showPage()  # Start a new page
                p.setFont("Helvetica", 12)
                y = 800  # Reset y position

            p.drawString(50, y, line)
            y -= 15  # Move down to the next line

        # Close the PDF object cleanly
        p.showPage()
        p.save()

        # Get the value of the BytesIO buffer and return it
        buffer.seek(0)
        return buffer.read()



class PipelineVisualizationView(LoginRequiredMixin, TemplateView):
    """Enhanced pipeline visualization"""
    template_name = 'dashboard/pipeline_visualization.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get pipeline data
        pipeline_stages = [
            'found', 'applied', 'responded', 'interview', 'offer', 'hired', 'rejected'
        ]

        pipeline_data = {}
        total_applications = 0

        for stage in pipeline_stages:
            count = JobApplication.objects.filter(
                user=user,
                application_status=stage
            ).count()
            pipeline_data[stage] = count
            total_applications += count

        # Calculate conversion rates
        conversion_rates = {}
        for i, stage in enumerate(pipeline_stages[1:], 1):
            previous_stage = pipeline_stages[i - 1]
            if pipeline_data[previous_stage] > 0:
                rate = (pipeline_data[stage] / pipeline_data[previous_stage]) * 100
                conversion_rates[f"{previous_stage}_to_{stage}"] = round(rate, 1)

        # Get applications by stage for detailed view
        applications_by_stage = {}
        for stage in pipeline_stages:
            applications_by_stage[stage] = JobApplication.objects.filter(
                user=user,
                application_status=stage
            ).order_by('-updated_at')[:5]  # Latest 5 per stage

        context.update({
            'pipeline_data': pipeline_data,
            'conversion_rates': conversion_rates,
            'applications_by_stage': applications_by_stage,
            'total_applications': total_applications,
            'pipeline_stages': pipeline_stages,
        })

        return context


# ==============================================
# ADD THESE AJAX ENDPOINTS FOR REAL-TIME UPDATES
# ==============================================

class QuickStatsAPIView(LoginRequiredMixin, View):
    """Quick statistics API for real-time updates"""

    def get(self, request):
        user = request.user

        # Calculate quick stats
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())

        stats = {
            'applications_today': JobApplication.objects.filter(
                user=user,
                created_at__date=today
            ).count(),
            'applications_this_week': JobApplication.objects.filter(
                user=user,
                created_at__date__gte=week_start
            ).count(),
            'pending_followups': FollowUpHistory.objects.filter(
                application__user=user,
                scheduled_date__lte=today,
                sent_date__isnull=True
            ).count(),
            'upcoming_interviews': JobApplication.objects.filter(
                user=user,
                application_status='interview',
                interview_date__gte=today
            ).count(),
        }

        return JsonResponse(stats)


class ApplicationTimelineAPIView(LoginRequiredMixin, View):
    """Application timeline data for charts"""

    def get(self, request):
        user = request.user
        days = int(request.GET.get('days', 30))

        # Get applications over time
        start_date = timezone.now().date() - timedelta(days=days)

        timeline_data = []
        for i in range(days + 1):
            date = start_date + timedelta(days=i)
            count = JobApplication.objects.filter(
                user=user,
                created_at__date=date
            ).count()
            timeline_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'applications': count
            })

        return JsonResponse({'timeline': timeline_data})
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        context['profile'] = profile

        # Application statistics
        applications = JobApplication.objects.filter(user=user)
        context['total_applications'] = applications.count()
        context['applications_this_week'] = applications.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        context['applications_this_month'] = applications.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()

        # Response rate calculation
        applied_count = applications.filter(application_status='applied').count()
        responded_count = applications.filter(
            application_status__in=['responded', 'interview', 'offer']
        ).count()
        context['response_rate'] = (responded_count / applied_count * 100) if applied_count > 0 else 0

        # Interview statistics
        context['interviews_scheduled'] = applications.filter(
            application_status='interview'
        ).count()

        # Applications by status for pipeline
        context['pipeline_data'] = {
            'found': applications.filter(application_status='found').count(),
            'applied': applications.filter(application_status='applied').count(),
            'responded': applications.filter(application_status='responded').count(),
            'interview': applications.filter(application_status='interview').count(),
            'offer': applications.filter(application_status='offer').count(),
        }

        # Recent applications
        context['recent_applications'] = applications.order_by('-created_at')[:5]

        # Due follow-ups

        context['due_followups'] = applications.filter(
            next_follow_up_date__lte=timezone.now().date(),
            application_status__in=['applied', 'responded']
        ).count()

        # Search configurations
        context['search_configs'] = JobSearchConfig.objects.filter(
            user=user, is_active=True
        )

        return context


class AnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Monthly application trends
        applications = JobApplication.objects.filter(user=user)
        monthly_data = []
        for i in range(6):
            month_start = timezone.now() - timedelta(days=30 * i)
            month_end = month_start + timedelta(days=30)
            count = applications.filter(
                created_at__gte=month_start,
                created_at__lt=month_end
            ).count()
            monthly_data.append({
                'month': month_start.strftime('%B'),
                'applications': count
            })

        context['monthly_data'] = list(reversed(monthly_data))

        # Success metrics
        total_apps = applications.count()
        total_responses = applications.filter(
            application_status__in=['responded', 'interview', 'offer']
        ).count()
        total_interviews = applications.filter(application_status='interview').count()
        total_offers = applications.filter(application_status='offer').count()

        context['success_metrics'] = {
            'total_applications': total_apps,
            'response_rate': (total_responses / total_apps * 100) if total_apps > 0 else 0,
            'interview_rate': (total_interviews / total_apps * 100) if total_apps > 0 else 0,
            'offer_rate': (total_offers / total_apps * 100) if total_apps > 0 else 0,
        }

        return context


# dashboard/views.py (Update the QuickSearchView)

class QuickSearchView(LoginRequiredMixin, TemplateView):
    """Emergency job search functionality"""
    template_name = 'dashboard/quick_search.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get user's search configurations
        search_configs = JobSearchConfig.objects.filter(
            user=self.request.user,
            is_active=True
        ).order_by('-created_at')

        context['search_configs'] = search_configs
        context['form'] = QuickSearchForm(user=self.request.user)

        return context

    def post(self, request):
        form = QuickSearchForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                # Get form data
                search_type = form.cleaned_data['search_type']
                config = form.cleaned_data['config']
                job_categories = form.cleaned_data['job_categories']
                locations = form.cleaned_data['locations']
                remote_only = form.cleaned_data['remote_only']
                salary_min = form.cleaned_data['salary_min']
                urgency = form.cleaned_data['urgency']
                generate_documents = form.cleaned_data['generate_documents']

                # Create webhook data for n8n integration
                webhook_data = {
                    'user_id': request.user.id,
                    'config_id': config.id if config else None,
                    'search_type': search_type,
                    'job_categories': job_categories,
                    'locations': locations,
                    'remote_only': remote_only,
                    'salary_min': salary_min,
                    'urgency': urgency,
                    'generate_documents': generate_documents,
                    'is_emergency': True
                }

                # Send to n8n webhook
                response = requests.post(
                    f"{settings.N8N_WEBHOOK_URL}/job-search",
                    json=webhook_data,
                    headers={'Authorization': f'Bearer {settings.N8N_API_TOKEN}'}
                )

                if response.status_code == 200:
                    # Create activity record
                    DashboardActivity.objects.create(
                        user=request.user,
                        activity_type='search',
                        description=f'Performed a {search_type} job search'
                    )

                    messages.success(request,
                                     'Emergency job search started! Results will appear in your dashboard shortly.')
                else:
                    messages.error(request, 'Failed to start job search. Please try again.')

                return redirect('dashboard:dashboard')

            except Exception as e:
                messages.error(request, f'Error starting job search: {str(e)}')
                return render(request, self.template_name, {'form': form})
        else:
            messages.error(request, 'Please correct the errors in the form.')
            return render(request, self.template_name, {'form': form})


class ProfileHealthCheckView(LoginRequiredMixin, View):
    """Analyze profile completeness and provide recommendations"""

    def post(self, request):
        try:
            from accounts.models import UserProfile

            # Get user profile
            try:
                profile = UserProfile.objects.get(user=request.user)
            except UserProfile.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Profile not found. Please create your profile first.',
                    'redirect_url': '/accounts/profile/'
                })

            # Analyze profile completeness
            analysis = self._analyze_profile_health(profile)

            # Log activity
            DashboardActivity.log_activity(
                user=request.user,
                activity_type='profile_updated',
                description='Profile health check performed',
                metadata=analysis,
                request=request
            )

            return JsonResponse({
                'success': True,
                'analysis': analysis
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error analyzing profile: {str(e)}'
            })

    def _analyze_profile_health(self, profile):
        """Perform detailed profile analysis"""
        issues = []
        recommendations = []
        score = 0
        max_score = 100

        # Check basic information
        if not profile.phone:
            issues.append("Missing phone number")
            recommendations.append("Add your phone number for better recruiter contact")
        else:
            score += 10

        if not profile.location:
            issues.append("Missing location information")
            recommendations.append("Add your location to help with location-based job searches")
        else:
            score += 10

        # Check professional details
        if not profile.current_job_title:
            issues.append("Missing current job title")
            recommendations.append("Add your current or most recent job title")
        else:
            score += 15

        if not profile.years_experience:
            issues.append("Missing years of experience")
            recommendations.append("Specify your years of professional experience")
        else:
            score += 10

        # Check skills
        if not profile.key_skills:
            issues.append("No skills listed")
            recommendations.append("Add your key technical and professional skills")
        else:
            skills_count = len(profile.key_skills) if isinstance(profile.key_skills, list) else 0
            if skills_count < 5:
                issues.append(f"Only {skills_count} skills listed")
                recommendations.append("Add more skills (aim for 8-12 key skills)")
                score += 5
            else:
                score += 15

        # Check social profiles
        if not profile.linkedin_url:
            issues.append("Missing LinkedIn profile")
            recommendations.append("Add your LinkedIn profile URL")
        else:
            score += 10

        if not profile.github_url and 'developer' in (profile.current_job_title or '').lower():
            recommendations.append("Consider adding your GitHub profile for developer roles")
        elif profile.github_url:
            score += 5

        # Check salary preferences
        if not profile.preferred_salary_min or not profile.preferred_salary_max:
            issues.append("Missing salary preferences")
            recommendations.append("Set your salary expectations to get better job matches")
        else:
            score += 10

        # Check work preferences
        if not profile.work_type_preference:
            issues.append("Missing work type preference")
            recommendations.append("Specify if you prefer remote, hybrid, or on-site work")
        else:
            score += 5

        # Check industries of interest
        if not profile.industries_of_interest:
            recommendations.append("Specify industries you're interested in for better job matching")
        else:
            score += 5

        # ATS compatibility check
        ats_score = self._calculate_ats_score(profile)

        return {
            'overall_score': min(score, max_score),
            'ats_compatibility_score': ats_score,
            'completion_percentage': profile.profile_completion_percentage,
            'issues_count': len(issues),
            'issues': issues,
            'recommendations': recommendations,
            'next_steps': self._generate_next_steps(issues, recommendations),
            'strengths': self._identify_strengths(profile)
        }

    def _calculate_ats_score(self, profile):
        """Calculate ATS (Applicant Tracking System) compatibility score"""
        score = 0

        # Keywords in job title
        if profile.current_job_title and len(profile.current_job_title.split()) >= 2:
            score += 20

        # Skills listed
        if profile.key_skills:
            skills_count = len(profile.key_skills) if isinstance(profile.key_skills, list) else 0
            score += min(skills_count * 5, 30)

        # Years of experience specified
        if profile.years_experience:
            score += 15

        # Education information
        if profile.education:
            score += 10

        # Location specified
        if profile.location:
            score += 10

        # Professional email format (check user email)
        email = profile.user.email
        if email and '@' in email and '.' in email.split('@')[1]:
            score += 10

        # Phone number format
        if profile.phone and len(profile.phone.replace(' ', '').replace('-', '')) >= 10:
            score += 5

        return min(score, 100)

    def _generate_next_steps(self, issues, recommendations):
        """Generate prioritized next steps"""
        if not issues and not recommendations:
            return ["Your profile looks great! Consider reviewing and updating it monthly."]

        next_steps = []

        # Prioritize critical missing information
        if "Missing phone number" in issues:
            next_steps.append("Add your phone number immediately")

        if "Missing current job title" in issues:
            next_steps.append("Update your current job title")

        if "No skills listed" in issues:
            next_steps.append("Add at least 5-8 key skills")

        if "Missing LinkedIn profile" in issues:
            next_steps.append("Add your LinkedIn profile URL")

        # Add other recommendations
        for rec in recommendations[:3]:  # Limit to top 3
            if len(next_steps) < 5:
                next_steps.append(rec)

        return next_steps

    def _identify_strengths(self, profile):
        """Identify profile strengths"""
        strengths = []

        if profile.linkedin_url:
            strengths.append("LinkedIn profile connected")

        if profile.github_url:
            strengths.append("GitHub profile available")

        if profile.portfolio_url:
            strengths.append("Portfolio website linked")

        if profile.key_skills and len(profile.key_skills) >= 8:
            strengths.append("Comprehensive skills list")

        if profile.preferred_salary_min and profile.preferred_salary_max:
            strengths.append("Clear salary expectations")

        if profile.years_experience and profile.years_experience >= 3:
            strengths.append("Experienced professional")

        if profile.education:
            strengths.append("Education information complete")

        return strengths


class PipelineUpdateView(LoginRequiredMixin, View):
    """Update application status via drag-drop"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            application_id = data.get('application_id')
            new_status = data.get('new_status')
            notes = data.get('notes', '')

            # Validate inputs
            if not application_id or not new_status:
                return JsonResponse({
                    'success': False,
                    'message': 'Application ID and new status are required'
                })

            # Get application
            application = get_object_or_404(
                JobApplication,
                id=application_id,
                user=request.user
            )

            # Validate status
            valid_statuses = [choice[0] for choice in JobApplication.STATUS_CHOICES]
            if new_status not in valid_statuses:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid status'
                })

            # Update application
            old_status = application.application_status
            application.application_status = new_status

            if notes:
                application.notes = notes

            # Update status-specific fields
            if new_status == 'applied' and not application.applied_date:
                application.applied_date = date.today()

            application.save()

            # Log activity
            DashboardActivity.log_activity(
                user=request.user,
                activity_type='application_status_changed',
                description=f'Status changed from {old_status} to {new_status}',
                metadata={
                    'application_id': application_id,
                    'old_status': old_status,
                    'new_status': new_status,
                    'company': application.company_name,
                    'job_title': application.job_title
                },
                request=request
            )

            # Create notification for significant status changes
            if new_status in ['responded', 'interview', 'offer']:
                UserNotification.objects.create(
                    user=request.user,
                    notification_type='success',
                    title='Application Status Updated',
                    message=f'{application.job_title} at {application.company_name} is now "{new_status.title()}"',
                    related_application=application,
                    priority='high' if new_status == 'offer' else 'normal'
                )

            return JsonResponse({
                'success': True,
                'message': f'Status updated to {new_status}',
                'application': {
                    'id': application.id,
                    'job_title': application.job_title,
                    'company_name': application.company_name,
                    'status': application.application_status,
                    'updated_at': application.updated_at.isoformat()
                }
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error updating status: {str(e)}'
            })


class DashboardAPIView(LoginRequiredMixin, View):
    """Real-time dashboard data API"""

    def get(self, request):
        try:
            # Get fresh dashboard statistics
            applications = JobApplication.objects.filter(user=request.user)

            # Basic stats
            stats = {
                'total_applications': applications.count(),
                'applications_this_week': applications.filter(
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).count(),
                'applications_this_month': applications.filter(
                    created_at__gte=timezone.now() - timedelta(days=30)
                ).count(),
            }

            # Response rate
            applied_count = applications.filter(application_status='applied').count()
            responded_count = applications.filter(
                application_status__in=['responded', 'interview', 'offer']
            ).count()
            stats['response_rate'] = (responded_count / applied_count * 100) if applied_count > 0 else 0

            # Interview statistics
            stats['interviews_scheduled'] = applications.filter(
                application_status='interview'
            ).count()

            # Pipeline data
            stats['pipeline_data'] = {
                'found': applications.filter(application_status='found').count(),
                'applied': applications.filter(application_status='applied').count(),
                'responded': applications.filter(application_status='responded').count(),
                'interview': applications.filter(application_status='interview').count(),
                'offer': applications.filter(application_status='offer').count(),
            }

            # Due follow-ups
            stats['due_followups'] = applications.filter(
                next_follow_up_date__lte=timezone.now().date(),
                application_status__in=['applied', 'responded']
            ).count()

            # Recent activity
            recent_activity = DashboardActivity.objects.filter(
                user=request.user
            ).order_by('-created_at')[:5]

            stats['recent_activity'] = [
                {
                    'type': activity.activity_type,
                    'description': activity.description,
                    'created_at': activity.created_at.isoformat()
                }
                for activity in recent_activity
            ]

            # Unread notifications
            unread_notifications = UserNotification.objects.filter(
                user=request.user,
                is_read=False,
                is_dismissed=False
            ).count()

            stats['unread_notifications'] = unread_notifications

            return JsonResponse({
                'success': True,
                'stats': stats,
                'last_updated': timezone.now().isoformat()
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


# dashboard/views.py - FIXED NotificationView

class NotificationView(LoginRequiredMixin, View):
    """Dashboard notifications management"""

    def get(self, request):
        """Get user notifications"""
        try:
            # Get base queryset WITHOUT slicing first
            base_notifications = UserNotification.objects.filter(
                user=request.user,
                is_dismissed=False
            )

            # Calculate counts BEFORE slicing
            total_count = base_notifications.count()
            unread_count = base_notifications.filter(is_read=False).count()

            # Now get the actual notifications with slicing
            notifications = base_notifications.order_by('-created_at')[:20]

            notifications_data = []
            for notification in notifications:
                notifications_data.append({
                    'id': notification.id,
                    'type': notification.notification_type,
                    'title': notification.title,
                    'message': notification.message,
                    'priority': notification.priority,
                    'is_read': notification.is_read,
                    'action_url': notification.action_url,
                    'action_text': notification.action_text,
                    'created_at': notification.created_at.isoformat(),
                    'expires_at': notification.expires_at.isoformat() if notification.expires_at else None,
                    'related_application_id': notification.related_application.id if notification.related_application else None
                })

            return JsonResponse({
                'success': True,
                'notifications': notifications_data,
                'total_count': total_count,
                'unread_count': unread_count,
                'displayed_count': len(notifications_data)
            })

        except Exception as e:
            logger.error(f"Error getting notifications: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

    def post(self, request):
        """Update notifications (mark as read/dismissed)"""
        try:
            data = json.loads(request.body)
            action = data.get('action')
            notification_ids = data.get('notification_ids', [])

            if action == 'mark_read':
                count = UserNotification.objects.filter(
                    user=request.user,
                    id__in=notification_ids
                ).update(is_read=True)

                return JsonResponse({
                    'success': True,
                    'message': f'Marked {count} notifications as read'
                })

            elif action == 'mark_all_read':
                count = UserNotification.objects.filter(
                    user=request.user,
                    is_read=False
                ).update(is_read=True)

                return JsonResponse({
                    'success': True,
                    'message': f'Marked {count} notifications as read'
                })

            elif action == 'dismiss':
                count = UserNotification.objects.filter(
                    user=request.user,
                    id__in=notification_ids
                ).update(is_dismissed=True)

                return JsonResponse({
                    'success': True,
                    'message': f'Dismissed {count} notifications'
                })

            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action'
                })

        except Exception as e:
            logger.error(f"Error processing notifications: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error processing notifications: {str(e)}'
            })

class DashboardSettingsView(LoginRequiredMixin, View):
    """Dashboard settings and customization"""

    def get(self, request):
        """Get user dashboard settings"""
        settings = DashboardSettings.get_for_user(request.user)

        return JsonResponse({
            'success': True,
            'settings': {
                'theme': settings.theme,
                'layout_density': settings.layout_density,
                'auto_refresh_enabled': settings.auto_refresh_enabled,
                'auto_refresh_interval': settings.auto_refresh_interval,
                'email_notifications': settings.email_notifications,
                'browser_notifications': settings.browser_notifications,
                'follow_up_reminders': settings.follow_up_reminders,
                'job_alert_notifications': settings.job_alert_notifications,
            }
        })

    def post(self, request):
        """Update dashboard settings"""
        try:
            data = json.loads(request.body)
            settings = DashboardSettings.get_for_user(request.user)

            # Update settings
            for key, value in data.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)

            settings.save()

            return JsonResponse({
                'success': True,
                'message': 'Dashboard settings updated successfully'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error updating settings: {str(e)}'
            })


# Add this to your views.py
@login_required
@require_http_methods(["POST"])
def save_notes(request, application_id):
    try:
        application = get_object_or_404(JobApplication, id=application_id, user=request.user)
        data = json.loads(request.body)
        application.notes = data.get('notes', '')
        application.save()

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def interview_prep_detail_view(request, application_id):
    """
    Detailed view for specific interview preparation
    """
    application = get_object_or_404(JobApplication, id=application_id, user=request.user)

    # Generate comprehensive preparation materials
    company_questions = generate_company_questions(application)
    technical_questions = generate_technical_questions(application)

    # Generate company research points
    company_research = generate_company_research(application)

    # Calculate days until interview
    days_until = None
    if application.interview_scheduled_date:
        days_until = (application.interview_scheduled_date.date() - timezone.now().date()).days

    context = {
        'application': application,
        'company_questions': company_questions,
        'technical_questions': technical_questions,
        'company_research': company_research,
        'days_until_interview': days_until,
    }

    return render(request, 'dashboard/interview_prep_detail.html', context)

@login_required
def get_practice_questions(request, application_id):
    """
    API endpoint to get practice questions for an application
    """
    application = get_object_or_404(JobApplication, id=application_id, user=request.user)

    company_questions = generate_company_questions(application)
    technical_questions = generate_technical_questions(application)

    # Common behavioral questions
    behavioral_questions = [
        "Tell me about yourself",
        "Why do you want this job?",
        "What are your strengths?",
        "Describe a challenging situation you faced",
        "Why should we hire you?",
    ]

    # Combine all questions
    all_questions = company_questions + technical_questions + behavioral_questions

    return JsonResponse({
        'questions': all_questions,
        'company_name': application.company_name,
        'job_title': application.job_title
    })


@login_required
@require_http_methods(["POST"])
def generate_additional_questions(request, application_id):
    """
    API endpoint to generate additional interview questions
    """
    try:
        application = get_object_or_404(JobApplication, id=application_id, user=request.user)

        # Generate new questions
        new_company_questions = generate_company_questions(application)
        new_technical_questions = generate_technical_questions(application)

        return JsonResponse({
            'success': True,
            'company_questions': new_company_questions,
            'technical_questions': new_technical_questions
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# ✅ ADD these functions to your dashboard/views.py to integrate with your existing system

# Add this import at the top of your views.py




def generate_company_research(application):
    """
    Generate company research points for interview preparation
    This function adapts your existing Celery task for synchronous use in the interview prep view
    """
    try:
        # Try to get existing company research from GeneratedDocument
        from documents.models import GeneratedDocument

        existing_research = GeneratedDocument.objects.filter(
            application=application,
            document_type='company_research'
        ).first()

        if existing_research and existing_research.content:
            # Parse the existing research content into bullet points
            research_content = existing_research.content

            # Extract key points from the research (simplified parsing)
            lines = research_content.split('\n')
            research_points = []

            for line in lines:
                line = line.strip()
                if line and len(line) > 20 and not line.isupper():
                    # Clean up the line
                    if line.startswith('-') or line.startswith('•'):
                        line = line[1:].strip()
                    elif line.startswith(tuple('123456789')):
                        line = line.split('.', 1)[-1].strip()

                    if len(line) > 10:
                        research_points.append(line)

                    if len(research_points) >= 8:
                        break

            if research_points:
                return research_points

        # If no existing research, generate new simplified research points
        return generate_quick_company_research(application)

    except Exception as e:
        print(f"Error getting company research: {e}")
        return generate_quick_company_research(application)


def generate_quick_company_research(application):
    """
    Generate quick company research points when full research isn't available
    """
    company_name = application.company_name

    # Use AI to generate quick research points
    try:
        import openai
        from django.conf import settings

        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY

            prompt = f"""
            Generate 6 key research points about {company_name} for job interview preparation.

            Focus on:
            - Company mission and recent news
            - Industry position and competitors
            - Company culture and values
            - Growth and future plans

            Return ONLY a simple numbered list, each point should be 1-2 sentences maximum.
            """

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a career research expert."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )

            # Parse the response into individual points
            research_text = response.choices[0].message.content.strip()
            research_points = []

            for line in research_text.split('\n'):
                line = line.strip()
                if line and len(line) > 20:
                    # Clean up numbering
                    if line.startswith(tuple('123456789')):
                        line = line.split('.', 1)[-1].strip()
                    research_points.append(line)

            return research_points[:6]

    except Exception as e:
        print(f"Error generating AI research: {e}")

    # Fallback research points
    return [
        f"Research {company_name}'s mission statement and core values",
        f"Review {company_name}'s recent news and press releases from the last 6 months",
        f"Understand {company_name}'s main products, services, and target market",
        f"Learn about {company_name}'s company culture and work environment",
        f"Research {company_name}'s key competitors and market position",
        f"Look up {company_name}'s recent achievements, awards, or major milestones"
    ]


# ✅ ADD these API endpoints that your template needs

@login_required
@require_http_methods(["POST"])
def track_practice_session(request):
    """
    API endpoint to track practice sessions for analytics
    """
    try:
        data = json.loads(request.body)

        # You can save this data to a new model or existing UserNotification
        # For now, we'll just log it and return success
        question_type = data.get('question_type', 'general')
        duration = data.get('duration', 0)
        completed = data.get('completed', False)

        # Log the practice session (you can extend this to save to database)
        logger.info(
            f"Practice session: User {request.user.id}, Type: {question_type}, Duration: {duration}s, Completed: {completed}")

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_practice_analytics(request):
    """
    API endpoint to get practice analytics
    """
    try:
        # You can extend this to get real analytics from database
        # For now, return mock data
        analytics = {
            'total_questions': 45,
            'completion_rate': '78%',
            'average_time': '2.5 min'
        }
        return JsonResponse({'success': True, 'analytics': analytics})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def export_prep_materials(request, application_id):
    """
    API endpoint to export preparation materials as PDF
    """
    try:
        application = get_object_or_404(JobApplication, id=application_id, user=request.user)

        # For now, return a simple response
        # You can extend this to generate actual PDF using your existing document generation system
        return JsonResponse({
            'success': True,
            'message': 'PDF export feature coming soon!',
            'download_url': '#'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ✅ UPDATE your existing interview_prep_view to work better with your system

def interview_prep_view(request):
    """
    Enhanced interview preparation dashboard view that integrates with your document system
    """
    # Get upcoming interviews (next 30 days)
    upcoming_date_threshold = timezone.now() + timedelta(days=30)
    upcoming_interviews = JobApplication.objects.filter(
        user=request.user,
        interview_scheduled_date__isnull=False,
        interview_scheduled_date__gte=timezone.now(),
        interview_scheduled_date__lte=upcoming_date_threshold
    ).order_by('interview_scheduled_date')

    # Get total interviews count
    total_interviews = JobApplication.objects.filter(
        user=request.user,
        interview_scheduled_date__isnull=False
    ).count()

    # Generate interview preparation data
    interview_prep_data = []

    for application in upcoming_interviews:
        # Calculate days until interview
        days_until = (application.interview_scheduled_date.date() - timezone.now().date()).days

        # Check if documents already exist for this application
        from documents.models import GeneratedDocument
        has_documents = GeneratedDocument.objects.filter(application=application).exists()

        # Generate preparation questions
        prep_data = {
            'application': application,
            'days_until_interview': days_until,
            'company_questions': generate_company_questions(application),
            'technical_questions': generate_technical_questions(application),
            'has_generated_documents': has_documents,  # New field
        }
        interview_prep_data.append(prep_data)

    # Common behavioral questions
    behavioral_questions = [
        "Tell me about yourself",
        "Why do you want this job?",
        "What are your strengths?",
        "What are your weaknesses?",
        "Describe a challenging situation you faced",
        "Where do you see yourself in 5 years?",
        "Why should we hire you?",
        "Tell me about a time you failed",
    ]

    context = {
        'upcoming_interviews': upcoming_interviews,
        'total_interviews': total_interviews,
        'interview_prep_data': interview_prep_data,
        'behavioral_questions': behavioral_questions,
    }

    return render(request, 'dashboard/interview_prep.html', context)


# ✅ ADD this helper function to generate documents if they don't exist

@login_required
@require_http_methods(["POST"])
def trigger_document_generation(request, application_id):
    """
    Trigger document generation for an application
    """
    try:
        application = get_object_or_404(JobApplication, id=application_id, user=request.user)

        # Import your Celery task
        from documents.tasks import generate_all_documents

        # Start the document generation process
        task = generate_all_documents.delay(application_id)

        return JsonResponse({
            'success': True,
            'message': 'Document generation started!',
            'task_id': task.id
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
