from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from followups.models import FollowUpTemplate


class Command(BaseCommand):
    help = 'Create default follow-up templates for users'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, help='Specific user ID')

    def handle(self, *args, **options):
        users = [User.objects.get(id=options['user_id'])] if options['user_id'] else User.objects.all()

        templates_data = [
            {
                'template_name': 'Initial Follow-up (1 Week)',
                'template_type': '1_week',
                'subject_template': 'Following up on {{job_title}} Application - {{user_name}}',
                'body_template': '''Dear Hiring Manager,

I hope this email finds you well. I wanted to follow up on my application for the {{job_title}} position at {{company_name}} that I submitted {{days_since_application}} days ago.

I remain very interested in this opportunity and would welcome the chance to discuss how my {{years_experience}} years of experience can contribute to your team's success.

Please let me know if you need any additional information from me. I look forward to hearing from you.

Best regards,
{{user_name}}''',
                'days_after_application': 7,
                'is_default': True,
            },
            {
                'template_name': 'Second Follow-up (2 Weeks)',
                'template_type': '2_week',
                'subject_template': 'Continued Interest in {{job_title}} Position',
                'body_template': '''Dear {{hiring_manager}},

I wanted to reach out once more regarding the {{job_title}} position at {{company_name}}. I understand you're likely reviewing many qualified candidates.

I'm still very enthusiastic about the opportunity to join your team and contribute to {{company_name}}'s continued success. My background in {{current_title}} has prepared me well for this role.

Would it be possible to schedule a brief conversation about next steps? I'm happy to work around your schedule.

Thank you for your time and consideration.

Best regards,
{{user_name}}''',
                'days_after_application': 14,
            },
            {
                'template_name': 'Final Follow-up (1 Month)',
                'template_type': '1_month',
                'subject_template': 'Final Follow-up: {{job_title}} Application',
                'body_template': '''Dear Hiring Team,

I hope you're doing well. This will be my final follow-up regarding the {{job_title}} position at {{company_name}}.

I understand that hiring decisions take time, and I respect your process. If the position is still available and you'd like to discuss my qualifications, I remain interested and available.

If you've moved forward with other candidates, I completely understand and wish you the best with your selection.

Thank you again for considering my application.

Best regards,
{{user_name}}''',
                'days_after_application': 30,
            },
            {
                'template_name': 'Thank You After Interview',
                'template_type': 'thank_you',
                'subject_template': 'Thank you for the {{job_title}} interview',
                'body_template': '''Dear {{hiring_manager}},

Thank you for taking the time to meet with me yesterday to discuss the {{job_title}} position at {{company_name}}. I enjoyed our conversation and learning more about your team's goals.

Our discussion reinforced my enthusiasm for this opportunity. I'm particularly excited about [specific detail from interview] and how I can contribute to [specific project/goal mentioned].

Please don't hesitate to reach out if you have any additional questions. I look forward to the next steps in the process.

Best regards,
{{user_name}}''',
                'days_after_application': 1,
            }
        ]

        created_count = 0
        for user in users:
            for template_data in templates_data:
                template, created = FollowUpTemplate.objects.get_or_create(
                    user=user,
                    template_name=template_data['template_name'],
                    defaults=template_data
                )
                if created:
                    created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} default templates')
        )