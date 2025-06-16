# followups/forms.py
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, HTML
from .models import FollowUpTemplate


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