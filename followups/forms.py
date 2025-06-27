# followups/forms.py
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, HTML
from django import forms
from django.utils import timezone

from jobs.models import JobApplication
from .models import FollowUpTemplate


# followups/forms.py (Add this file if it doesn't exist)


class BulkFollowUpForm(forms.Form):
    """Form for sending bulk follow-ups"""

    applications = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
        help_text="Select applications to send follow-ups"
    )

    template = forms.ModelChoiceField(
        queryset=FollowUpTemplate.objects.none(),
        required=True,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text="Select a follow-up template to use"
    )

    custom_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add a personal touch to your follow-ups (optional)'
        }),
        help_text="Optional custom message to append to the template"
    )

    send_now = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Send immediately (or schedule for later)"
    )

    scheduled_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        help_text="When to send the follow-up (if not sending immediately)"
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if user:
            # Get applications needing follow-up
            followup_candidates = JobApplication.objects.filter(
                user=user,
                application_status__in=['applied', 'responded', 'interview'],
                created_at__lte=timezone.now() - timezone.timedelta(days=5)
            ).order_by('-created_at')

            self.fields['applications'].choices = [
                (app.id, f"{app.job_title} at {app.company_name} (Applied: {app.created_at.strftime('%b %d, %Y')})")
                for app in followup_candidates
            ]

            # Get templates
            self.fields['template'].queryset = FollowUpTemplate.objects.filter(
                user=user,
                is_active=True
            )

        # Setup crispy form
        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h5><i class="fas fa-paper-plane"></i> Bulk Follow-up</h5>'),
            HTML('<div class="form-section">'),
            HTML('<h6 class="form-section-title"><i class="fas fa-briefcase"></i> 1. Select Applications</h6>'),
            HTML('<div class="select-actions mb-2">'),
            HTML('<button type="button" class="select-action-btn" id="select-all">Select All</button>'),
            HTML('<button type="button" class="select-action-btn" id="deselect-all">Deselect All</button>'),
            HTML('</div>'),
            'applications',
            HTML('</div>'),

            HTML('<div class="form-section">'),
            HTML('<h6 class="form-section-title"><i class="fas fa-envelope"></i> 2. Choose Template</h6>'),
            'template',
            HTML('</div>'),

            HTML('<div class="form-section">'),
            HTML('<h6 class="form-section-title"><i class="fas fa-edit"></i> 3. Customize (Optional)</h6>'),
            'custom_message',
            HTML('</div>'),

            HTML('<div class="form-section">'),
            HTML('<h6 class="form-section-title"><i class="fas fa-clock"></i> 4. Timing</h6>'),
            Row(
                Column('send_now', css_class='col-md-6'),
                Column('scheduled_date', css_class='col-md-6'),
            ),
            HTML('</div>'),

            HTML('<div class="mt-4">'),
            Submit('submit', 'Send Follow-ups', css_class='btn btn-primary btn-lg'),
            HTML('</div>')
        )

    def clean(self):
        cleaned_data = super().clean()
        send_now = cleaned_data.get('send_now')
        scheduled_date = cleaned_data.get('scheduled_date')

        if not send_now and not scheduled_date:
            raise forms.ValidationError("Please either select 'Send Now' or specify a schedule date.")

        if not send_now and scheduled_date and scheduled_date < timezone.now():
            raise forms.ValidationError("Scheduled date cannot be in the past.")

        return cleaned_data

class FollowUpTemplateForm(forms.ModelForm):
    class Meta:
        model = FollowUpTemplate
        fields = [
            'template_name', 'template_type', 'subject_template',
            'body_template', 'days_after_application', 'is_default'
        ]
        widgets = {
            'subject_template': forms.TextInput(attrs={'placeholder': 'Follow-up regarding {{job_title}} position'}),
            'body_template': forms.Textarea(attrs={
                'rows': 8,
                'placeholder': 'Dear {{hiring_manager}},\n\nI hope this email finds you well...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'template_name',
            'template_type',
            'days_after_application',
            'is_default',
            HTML('<h5>Email Template</h5>'),
            'subject_template',
            HTML(
                '<small class="form-text text-muted">Available variables: {{user_name}}, {{company_name}}, {{job_title}}, {{hiring_manager}}, {{days_since_application}}</small>'),
            'body_template',
            Submit('submit', 'Save Template', css_class='btn btn-primary')
        )


class ScheduleFollowUpForm(forms.Form):
    follow_up_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True
    )
    template = forms.ModelChoiceField(
        queryset=FollowUpTemplate.objects.none(),
        required=True
    )
    custom_message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False,
        help_text="Optional: Add a custom message to append to the template"
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['template'].queryset = FollowUpTemplate.objects.filter(
            user=user, is_active=True
        )
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'follow_up_date',
            'template',
            'custom_message',
            Submit('submit', 'Schedule Follow-up', css_class='btn btn-primary')
        )


class QuickFollowUpForm(forms.Form):
    template = forms.ModelChoiceField(
        queryset=FollowUpTemplate.objects.none(),
        required=True,
        empty_label="Select a template"
    )
    send_immediately = forms.BooleanField(
        initial=True,
        required=False,
        help_text="Uncheck to schedule for later"
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['template'].queryset = FollowUpTemplate.objects.filter(
            user=user, is_active=True
        )
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'template',
            'send_immediately',
            Submit('submit', 'Send Follow-up', css_class='btn btn-success')
        )