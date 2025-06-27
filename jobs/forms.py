# jobs/forms.py
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Div, Field, Fieldset
from crispy_forms.bootstrap import InlineCheckboxes
from .models import JobSearchConfig, JobApplication


class JobSearchConfigForm(forms.ModelForm):
    JOB_CATEGORY_CHOICES = [
        ('data_scientist', 'Data Scientist'),
        ('ml_engineer', 'Machine Learning Engineer'),
        ('data_analyst', 'Data Analyst'),
        ('python_developer', 'Python Developer'),
        ('django_developer', 'Django Developer'),
        ('backend_developer', 'Backend Developer'),
        ('full_stack_developer', 'Full Stack Developer'),
        ('software_engineer', 'Software Engineer'),
        ('data_engineer', 'Data Engineer'),
        ('ai_engineer', 'AI Engineer'),
        ('research_scientist', 'Research Scientist'),
        ('business_analyst', 'Business Analyst'),
        ('product_analyst', 'Product Analyst'),
        ('quantitative_analyst', 'Quantitative Analyst'),
    ]

    LOCATION_CHOICES = [
        ('remote', 'Remote'),
        ('toronto_on', 'Toronto, ON'),
        ('vancouver_bc', 'Vancouver, BC'),
        ('montreal_qc', 'Montreal, QC'),
        ('calgary_ab', 'Calgary, AB'),
        ('ottawa_on', 'Ottawa, ON'),
        ('seattle_wa', 'Seattle, WA'),
        ('san_francisco_ca', 'San Francisco, CA'),
        ('new_york_ny', 'New York, NY'),
        ('boston_ma', 'Boston, MA'),
        ('chicago_il', 'Chicago, IL'),
    ]

    job_categories = forms.MultipleChoiceField(
        choices=JOB_CATEGORY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    target_locations = forms.MultipleChoiceField(
        choices=LOCATION_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    class Meta:
        model = JobSearchConfig
        fields = [
            'config_name', 'job_categories', 'target_locations',
            'remote_preference', 'salary_min', 'salary_max',
            'auto_follow_up_enabled'
        ]
        widgets = {
            'salary_min': forms.NumberInput(attrs={'min': 0, 'step': 1000}),
            'salary_max': forms.NumberInput(attrs={'min': 0, 'step': 1000}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'config_name',
            HTML('<h5>Job Categories</h5>'),
            InlineCheckboxes('job_categories'),
            HTML('<h5>Target Locations</h5>'),
            InlineCheckboxes('target_locations'),
            Row(
                Column('remote_preference', css_class='form-group col-md-4 mb-0'),
                Column('salary_min', css_class='form-group col-md-4 mb-0'),
                Column('salary_max', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Field('auto_follow_up_enabled'),
            Submit('submit', 'Save Configuration', css_class='btn btn-primary')
        )


class JobApplicationUpdateForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = [
            'application_status',
            'urgency_level',
            'notes',
            'interview_scheduled_date',
            'offer_received',
            'offer_amount',
            'rejection_received',
            'rejection_reason'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Add any notes about this application...'
            }),
            'interview_scheduled_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'offer_amount': forms.NumberInput(attrs={
                'min': 0,
                'step': 1000,
                'placeholder': 'Enter offer amount'
            }),
            'rejection_reason': forms.TextInput(attrs={
                'placeholder': 'Reason for rejection (optional)'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('application_status', css_class='form-group col-md-6 mb-0'),
                Column('urgency_level', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'notes',
            Fieldset(
                'Interview & Offer Details',
                Row(
                    Column('interview_scheduled_date', css_class='form-group col-md-6 mb-0'),
                    Column('offer_received', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                Row(
                    Column('offer_amount', css_class='form-group col-md-6 mb-0'),
                    Column('rejection_received', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                'rejection_reason',
                css_class='collapse',
                css_id='advancedFields'
            ),
            Submit('submit', 'Update Application', css_class='btn btn-primary')
        )

        # Add some styling
        self.fields['application_status'].widget.attrs.update({'class': 'form-select'})
        self.fields['urgency_level'].widget.attrs.update({'class': 'form-select'})
        self.fields['offer_received'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['rejection_received'].widget.attrs.update({'class': 'form-check-input'})


class BulkApplicationForm(forms.Form):
    applications = forms.ModelMultipleChoiceField(
        queryset=JobApplication.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    action = forms.ChoiceField(
        choices=[
            ('send_followup', 'Send Follow-up'),
            ('mark_applied', 'Mark as Applied'),
            ('update_status', 'Update Status'),
            ('download_docs', 'Download Documents'),
        ],
        required=True
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['applications'].queryset = JobApplication.objects.filter(user=user)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'action',
            InlineCheckboxes('applications'),
            Submit('submit', 'Execute Action', css_class='btn btn-primary')
        )