# documents/research.py - HYBRID RESEARCH SYSTEM
import requests
import json
import logging
from typing import Dict, Any, List
from django.conf import settings
from .ai_services import ai_service
from .models import CompanyResearch

logger = logging.getLogger('documents.ai_services')


class CompanyResearchService:
    """
    Hybrid research system combining web search with AI analysis
    Uses Serper API for real-time data + AI for analysis
    """

    def __init__(self):
        self.serper_api_key = settings.SERPER_API_KEY
        self.serper_settings = settings.SERPER_SETTINGS

    def research_company(self, application_id: int, company_name: str, job_title: str = "") -> Dict[str, Any]:
        """
        Complete company research workflow
        Returns comprehensive research data or fallback analysis
        """
        try:
            # Step 1: Search for company information
            search_results = self._search_company_info(company_name, job_title)

            if search_results['success']:
                # Step 2: AI analysis of search results
                analysis = self._analyze_search_results(
                    company_name, job_title, search_results['data']
                )

                if analysis['success']:
                    # Step 3: Save research to database
                    research_data = self._save_research(application_id, analysis['data'])

                    return {
                        'success': True,
                        'data': research_data,
                        'source': 'web_search_ai_analysis'
                    }

            # Fallback: AI-only research
            logger.warning(f"Web search failed for {company_name}, using AI fallback")
            fallback_analysis = self._ai_only_research(company_name, job_title)

            if fallback_analysis['success']:
                research_data = self._save_research(application_id, fallback_analysis['data'])
                return {
                    'success': True,
                    'data': research_data,
                    'source': 'ai_knowledge_base'
                }

            return {
                'success': False,
                'error': 'All research methods failed',
                'data': self._get_generic_research(company_name, job_title)
            }

        except Exception as e:
            logger.error(f"Company research error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': self._get_generic_research(company_name, job_title)
            }

    def _search_company_info(self, company_name: str, job_title: str = "") -> Dict[str, Any]:
        """Search for company information using Serper API"""

        if not self.serper_api_key:
            return {'success': False, 'error': 'Serper API key not configured'}

        try:
            # Construct search queries
            queries = [
                f"{company_name} company news 2024 2025",
                f"{company_name} about company culture values",
                f"{company_name} recent developments hiring",
            ]

            if job_title:
                queries.append(f"{company_name} {job_title} job requirements")

            all_results = []

            for query in queries:
                headers = {
                    'X-API-KEY': self.serper_api_key,
                    'Content-Type': 'application/json'
                }

                data = {
                    'q': query,
                    'gl': self.serper_settings.get('GL', 'ca'),
                    'hl': self.serper_settings.get('HL', 'en'),
                    'num': self.serper_settings.get('NUM_RESULTS', 10),
                }

                response = requests.post(
                    'https://google.serper.dev/search',
                    headers=headers,
                    json=data,
                    timeout=10
                )

                if response.status_code == 200:
                    results = response.json()
                    if 'organic' in results:
                        all_results.extend(results['organic'][:3])  # Top 3 results per query

                # Rate limiting - small delay between requests
                import time
                time.sleep(0.5)

            if all_results:
                return {
                    'success': True,
                    'data': {
                        'search_results': all_results,
                        'total_results': len(all_results),
                        'company_name': company_name
                    }
                }
            else:
                return {'success': False, 'error': 'No search results found'}

        except Exception as e:
            logger.error(f"Serper API error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _analyze_search_results(self, company_name: str, job_title: str, search_data: Dict) -> Dict[str, Any]:
        """Use AI to analyze search results and create structured research"""

        # Prepare search results for AI analysis
        search_summary = ""
        for result in search_data.get('search_results', []):
            search_summary += f"Title: {result.get('title', '')}\n"
            search_summary += f"Snippet: {result.get('snippet', '')}\n"
            search_summary += f"Link: {result.get('link', '')}\n\n"

        analysis_prompt = f"""
Analyze the following search results about {company_name} and create a comprehensive company research report for a {job_title} position.

Search Results:
{search_summary}

Please provide a structured analysis with the following sections:

1. COMPANY OVERVIEW (2-3 sentences)
Brief description of what the company does, size, and industry position.

2. RECENT DEVELOPMENTS (3-4 bullet points)
Key recent news, changes, or developments from the search results.

3. INTERVIEW TALKING POINTS (4-5 bullet points)
Specific topics and achievements to mention during interviews based on the research.

4. SMART QUESTIONS TO ASK (3-4 questions)
Thoughtful questions to ask the interviewer based on company insights.

5. INDUSTRY CONTEXT (2-3 sentences)
Where the company fits in the industry and current market trends.

Format your response as clear, actionable insights for job interview preparation.
Keep it professional and specific to the information found in the search results.
"""

        try:
            # Use AI service to analyze search results
            analysis_result = ai_service.generate_content(
                prompt=analysis_prompt,
                document_type="company_research",
                user_id=1  # System user for research
            )

            if analysis_result['success']:
                # Parse AI response into structured format
                content = analysis_result['content']

                # Simple parsing - in production, you might use more sophisticated parsing
                research_data = {
                    'company_overview': self._extract_section(content, "COMPANY OVERVIEW"),
                    'recent_news': self._extract_section(content, "RECENT DEVELOPMENTS"),
                    'interview_talking_points': self._extract_section(content, "INTERVIEW TALKING POINTS"),
                    'questions_to_ask': self._extract_section(content, "SMART QUESTIONS TO ASK"),
                    'industry_context': self._extract_section(content, "INDUSTRY CONTEXT"),
                    'full_analysis': content,
                    'ai_provider': analysis_result['provider'],
                    'tokens_used': analysis_result.get('tokens_used', 0),
                    'cost': float(analysis_result.get('cost', 0))
                }

                return {
                    'success': True,
                    'data': research_data
                }
            else:
                return {
                    'success': False,
                    'error': analysis_result.get('error', 'AI analysis failed')
                }

        except Exception as e:
            logger.error(f"AI analysis error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _ai_only_research(self, company_name: str, job_title: str) -> Dict[str, Any]:
        """Fallback: Use AI knowledge base for company research"""

        fallback_prompt = f"""
Create a company research report for {company_name} for a {job_title} position using your knowledge base.

Please provide:

1. COMPANY OVERVIEW
What you know about {company_name} - industry, business model, size, reputation.

2. GENERAL TALKING POINTS
Common achievements, values, and aspects to highlight in interviews.

3. TYPICAL QUESTIONS TO ASK
Standard but thoughtful questions for this type of company/role.

4. INDUSTRY INSIGHTS
General trends and challenges in their industry.

5. PREPARATION TIPS
Specific advice for interviewing at this type of company.

Be honest about limitations of knowledge and provide general but useful guidance.
"""

        try:
            analysis_result = ai_service.generate_content(
                prompt=fallback_prompt,
                document_type="company_research_fallback",
                user_id=1
            )

            if analysis_result['success']:
                content = analysis_result['content']

                research_data = {
                    'company_overview': self._extract_section(content, "COMPANY OVERVIEW"),
                    'recent_news': "Limited recent information available",
                    'interview_talking_points': self._extract_section(content, "GENERAL TALKING POINTS"),
                    'questions_to_ask': self._extract_section(content, "TYPICAL QUESTIONS TO ASK"),
                    'industry_context': self._extract_section(content, "INDUSTRY INSIGHTS"),
                    'full_analysis': content,
                    'ai_provider': analysis_result['provider'],
                    'tokens_used': analysis_result.get('tokens_used', 0),
                    'cost': float(analysis_result.get('cost', 0))
                }

                return {
                    'success': True,
                    'data': research_data
                }
            else:
                return {
                    'success': False,
                    'error': analysis_result.get('error', 'AI fallback failed')
                }

        except Exception as e:
            logger.error(f"AI fallback error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _extract_section(self, content: str, section_name: str) -> str:
        """Extract a specific section from AI-generated content"""
        try:
            lines = content.split('\n')
            section_content = []
            capturing = False

            for line in lines:
                if section_name.upper() in line.upper() and any(
                        char in line for char in ['1.', '2.', '3.', '4.', '5.', '#']):
                    capturing = True
                    continue
                elif capturing and any(char in line for char in ['1.', '2.', '3.', '4.', '5.',
                                                                 '#']) and section_name.upper() not in line.upper():
                    break
                elif capturing:
                    section_content.append(line.strip())

            result = '\n'.join(section_content).strip()
            return result if result else "Information not available"

        except Exception as e:
            logger.error(f"Section extraction error: {e}")
            return "Information not available"

    def _save_research(self, application_id: int, research_data: Dict) -> Dict[str, Any]:
        """Save research data to database"""
        try:
            from jobs.models import JobApplication

            application = JobApplication.objects.get(id=application_id)

            # Create or update company research
            research, created = CompanyResearch.objects.update_or_create(
                application=application,
                defaults={
                    'company_overview': research_data.get('company_overview', ''),
                    'recent_news': research_data.get('recent_news', ''),
                    'interview_talking_points': research_data.get('interview_talking_points', ''),
                    'questions_to_ask': research_data.get('questions_to_ask', ''),
                    'industry_context': research_data.get('industry_context', ''),
                    'research_source': 'serper_ai'
                }
            )

            logger.info(f"Saved research for {application.company_name}")

            return {
                'id': research.id,
                'company_name': application.company_name,
                'overview': research.company_overview,
                'recent_news': research.recent_news,
                'talking_points': research.interview_talking_points,
                'questions': research.questions_to_ask,
                'industry_context': research.industry_context,
                'created': created,
                'research_date': research.research_date
            }

        except Exception as e:
            logger.error(f"Failed to save research: {e}")
            raise e

    def _get_generic_research(self, company_name: str, job_title: str) -> Dict[str, Any]:
        """Return generic research template as last resort"""
        return {
            'id': None,
            'company_name': company_name,
            'overview': f"Research {company_name} online before your interview to understand their business model, values, and recent developments.",
            'recent_news': "Check their website, LinkedIn, and recent news articles for current information.",
            'talking_points': f"Highlight your relevant skills for the {job_title} role and express genuine interest in their company mission.",
            'questions': "Ask about team structure, growth opportunities, and company culture during your interview.",
            'industry_context': "Research current trends and challenges in their industry to demonstrate market awareness.",
            'research_date': None
        }

    def get_research_by_application(self, application_id: int) -> Dict[str, Any]:
        """Retrieve existing research for an application"""
        try:
            research = CompanyResearch.objects.get(application_id=application_id)

            return {
                'success': True,
                'data': {
                    'id': research.id,
                    'company_name': research.application.company_name,
                    'overview': research.company_overview,
                    'recent_news': research.recent_news,
                    'talking_points': research.interview_talking_points,
                    'questions': research.questions_to_ask,
                    'industry_context': research.industry_context,
                    'research_date': research.research_date,
                    'source': research.research_source
                }
            }

        except CompanyResearch.DoesNotExist:
            return {
                'success': False,
                'error': 'No research found for this application'
            }
        except Exception as e:
            logger.error(f"Error retrieving research: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Singleton instance
research_service = CompanyResearchService()