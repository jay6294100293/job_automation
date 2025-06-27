from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from accounts.models import UserProfile
from followups.models import FollowUpTemplate


class Command(BaseCommand):
    help = 'Setup initial data for the job automation system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email for the initial user account',
            default='mrityunjay.100293@gmail.com'
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Username for the initial user account',
            default='mrityunjay'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password for the initial user account',
            default='admin123'
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            # Create initial user
            user, created = User.objects.get_or_create(
                username=options['username'],
                defaults={
                    'email': options['email'],
                    'first_name': 'Mrityunjay',
                    'last_name': 'Gupta',
                    'is_staff': True,
                    'is_superuser': True,
                }
            )

            if created:
                user.set_password(options['password'])
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created superuser: {user.username}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User {user.username} already exists')
                )

            # Create user profile
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'phone': '778-636-6294',
                    'location': 'Burnaby, BC, Canada',
                    'linkedin_url': 'https://linkedin.com/in/gupta-mrityunjay',
                    'years_experience': 5,
                    'education': "Master's in Analytics (AI/ML) from Northeastern University",
                    'current_job_title': 'Data Scientist',
                    'current_company': 'Tech Company',
                    'key_skills': [
                        'python', 'django', 'machine_learning', 'data_science',
                        'sql', 'aws', 'docker', 'tensorflow', 'pandas'
                    ],
                    'preferred_salary_min': 80000,
                    'preferred_salary_max': 120000,
                    'work_type_preference': 'remote',
                    'preferred_company_sizes': ['startup', 'medium', 'large'],
                    'industries_of_interest': ['technology', 'finance', 'healthcare']
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created profile for {user.username}')
                )
                profile.calculate_completion_percentage()

            # Create default follow-up templates
            self.create_default_templates(user)

            self.stdout.write(
                self.style.SUCCESS('Initial data setup completed successfully!')
            )

    def create_default_templates(self, user):
        templates = [
            {
                'template_name': 'Professional Follow-up (1 Week)',
                'template_type': '1_week',
                'subject_template': 'Following up on {{job_title}} Application - {{user_name}}',
                'body_template': '''Dear Hiring Manager,

I hope this email finds you well. I wanted to follow up on my application for the {{job_title}} position at {{company_name}} that I submitted {{days_since_application}} days ago.

I remain very interested in this opportunity and believe my {{years_experience}} years of experience in data science and machine learning would be valuable to your team. I'm particularly excited about the possibility of contributing to {{company_name}}'s innovative projects.

I would welcome the opportunity to discuss how my background in Python, Django, machine learning, and cloud technologies aligns with your needs. Please let me know if you require any additional information.

Thank you for your time and consideration. I look forward to hearing from you.

Best regards,
{{user_name}}
{{current_title}}
Phone: 778-636-6294
Email: mrityunjay.100293@gmail.com
LinkedIn: linkedin.com/in/gupta-mrityunjay''',
                'days_after_application': 7,
                'is_default': True,
            },
            {
                'template_name': 'Second Follow-up (2 Weeks)',
                'template_type': '2_week',
                'subject_template': 'Continued Interest in {{job_title}} Position - {{user_name}}',
                'body_template': '''Dear {{hiring_manager}},

I hope you're doing well. I wanted to reach out once more regarding the {{job_title}} position at {{company_name}}. I understand you're likely reviewing many qualified candidates, and I appreciate the time required for a thorough evaluation process.

Since my last email, I've been following {{company_name}}'s recent developments and am even more excited about the opportunity to contribute to your team. My experience with machine learning, data analytics, and full-stack development using Django and Python would allow me to make immediate contributions while continuing to grow with the organization.

I'm still very enthusiastic about this role and would be happy to provide any additional information you might need. Would it be possible to schedule a brief conversation to discuss how my background aligns with your current needs?

Thank you again for your consideration. I look forward to the possibility of contributing to {{company_name}}'s success.

Best regards,
{{user_name}}''',
                'days_after_application': 14,
            },
            {
                'template_name': 'Final Follow-up (1 Month)',
                'template_type': '1_month',
                'subject_template': 'Final Follow-up: {{job_title}} Application - {{user_name}}',
                'body_template': '''Dear Hiring Team,

I hope this message finds you well. This will be my final follow-up regarding the {{job_title}} position at {{company_name}}.

I understand that hiring decisions take time, and I respect your thorough evaluation process. I remain interested in the opportunity and believe that my skills in data science, machine learning, and software development would be valuable to your team.

If the position is still available and you'd like to discuss my qualifications further, I'm available at your convenience. If you've moved forward with other candidates, I completely understand and wish you success with your selection.

I would appreciate being considered for future opportunities that align with my background in AI/ML, Python development, and data analytics.

Thank you once again for your time and consideration throughout this process.

Best regards,
{{user_name}}
Mrityunjay Gupta
Data Scientist & ML Engineer
Phone: 778-636-6294
Email: mrityunjay.100293@gmail.com''',
                'days_after_application': 30,
            },
            {
                'template_name': 'Thank You After Interview',
                'template_type': 'thank_you',
                'subject_template': 'Thank you for the {{job_title}} interview - {{user_name}}',
                'body_template': '''Dear {{hiring_manager}},

Thank you for taking the time to meet with me today to discuss the {{job_title}} position at {{company_name}}. I thoroughly enjoyed our conversation and learning more about your team's exciting projects and goals.

Our discussion reinforced my enthusiasm for this opportunity. I'm particularly excited about [specific project or responsibility discussed] and how my experience with machine learning, Python development, and data analytics can contribute to {{company_name}}'s continued innovation.

I was impressed by [specific aspect of company/team mentioned in interview] and am confident that my technical skills and collaborative approach would make me a valuable addition to your team.

Please don't hesitate to reach out if you have any additional questions or need clarification on any aspect of my background. I'm very much looking forward to the next steps in the process.

Thank you again for your time and consideration.

Best regards,
{{user_name}}''',
                'days_after_application': 1,
            },
            {
                'template_name': 'LinkedIn Connection Request',
                'template_type': 'custom',
                'subject_template': 'Connecting regarding {{job_title}} opportunity',
                'body_template': '''Hi {{hiring_manager}},

I recently applied for the {{job_title}} position at {{company_name}} and would love to connect. I'm excited about the opportunity to contribute to your team with my background in data science and machine learning.

Best regards,
{{user_name}}''',
                'days_after_application': 3,
            }
        ]

        created_count = 0
        for template_data in templates:
            template, created = FollowUpTemplate.objects.get_or_create(
                user=user,
                template_name=template_data['template_name'],
                defaults=template_data
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Created {created_count} follow-up templates')
        )

