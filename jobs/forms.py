# jobs/forms.py - Enhanced Universal Version
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Div, Field, Fieldset
from crispy_forms.bootstrap import InlineCheckboxes
from .models import JobSearchConfig, JobApplication


class UniversalJobSearchConfigForm(forms.ModelForm):
    """Universal job search configuration form that works for any industry"""

    # Instead of limited choices, use flexible text areas with suggestions
    job_categories = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Enter job titles/roles (one per line):\nData Scientist\nSoftware Engineer\nProduct Manager\nMarketing Specialist\nSales Representative',
            'class': 'form-control job-categories-input'
        }),
        help_text='Enter job titles or roles you\'re interested in, one per line. Be as specific or general as you want.',
        required=True,
        label='Job Categories/Titles'
    )

    target_locations = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Enter locations (one per line):\nRemote\nToronto, ON\nVancouver, BC\nNew York, NY\nLondon, UK',
            'class': 'form-control locations-input'
        }),
        help_text='Enter cities, provinces/states, countries, or "Remote". One per line.',
        required=True,
        label='Target Locations'
    )

    # Additional flexible fields
    excluded_companies = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 2,
            'placeholder': 'Companies to avoid (one per line):\nCompany A\nCompany B',
            'class': 'form-control'
        }),
        required=False,
        help_text='Optional: Companies you don\'t want to work for.',
        label='Excluded Companies'
    )

    required_keywords = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 2,
            'placeholder': 'Must-have keywords (one per line):\nPython\nRemote\nFlexible hours',
            'class': 'form-control'
        }),
        required=False,
        help_text='Jobs must contain these keywords to be included.',
        label='Required Keywords'
    )

    excluded_keywords = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 2,
            'placeholder': 'Keywords to avoid (one per line):\nUnpaid\nCommission only\nDoor-to-door',
            'class': 'form-control'
        }),
        required=False,
        help_text='Jobs containing these keywords will be excluded.',
        label='Excluded Keywords'
    )

    # Currency and salary (universal)
    salary_currency = forms.ChoiceField(
        choices=[
            ('CAD', 'CAD ($)'),
            ('USD', 'USD ($)'),
            ('EUR', 'EUR (€)'),
            ('GBP', 'GBP (£)'),
            ('AUD', 'AUD ($)'),
            ('INR', 'INR (₹)'),
            ('OTHER', 'Other'),
        ],
        initial='CAD',
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )

    class Meta:
        model = JobSearchConfig
        fields = [
            'config_name', 'job_categories', 'target_locations',
            'remote_preference', 'salary_min', 'salary_max', 'salary_currency',
            'required_keywords', 'excluded_keywords', 'excluded_companies',
            'auto_follow_up_enabled'
        ]
        widgets = {
            'config_name': forms.TextInput(attrs={
                'placeholder': 'E.g., Data Science Jobs Canada, Marketing Remote, Entry Level Sales',
                'class': 'form-control'
            }),
            'salary_min': forms.NumberInput(attrs={
                'min': 0,
                'step': 1000,
                'placeholder': '50000',
                'class': 'form-control'
            }),
            'salary_max': forms.NumberInput(attrs={
                'min': 0,
                'step': 1000,
                'placeholder': '100000',
                'class': 'form-control'
            }),
            'remote_preference': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Convert stored JSON back to text for editing
        if self.instance and self.instance.pk:
            if isinstance(self.instance.job_categories, list):
                self.fields['job_categories'].initial = '\n'.join(self.instance.job_categories)
            if isinstance(self.instance.target_locations, list):
                self.fields['target_locations'].initial = '\n'.join(self.instance.target_locations)

            # Handle additional fields
            for field_name in ['required_keywords', 'excluded_keywords', 'excluded_companies']:
                field_value = getattr(self.instance, field_name, None)
                if field_value and isinstance(field_value, list):
                    self.fields[field_name].initial = '\n'.join(field_value)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('config_name', css_class='form-group col-12 mb-3'),
                css_class='form-row'
            ),

            HTML(
                '<div class="alert alert-info"><i class="fas fa-info-circle"></i> <strong>Tip:</strong> Be specific with job titles for better results. You can include variations like "Software Developer", "Software Engineer", "Full Stack Developer".</div>'),

            'job_categories',

            HTML(
                '<div class="mb-3"><small class="text-muted"><i class="fas fa-lightbulb"></i> You can include "Remote", specific cities, or entire countries/regions.</small></div>'),

            'target_locations',

            Fieldset(
                'Salary Requirements',
                Row(
                    Column('salary_currency', css_class='form-group col-md-4 mb-0'),
                    Column('salary_min', css_class='form-group col-md-4 mb-0'),
                    Column('salary_max', css_class='form-group col-md-4 mb-0'),
                    css_class='form-row'
                ),
                Row(
                    Column('remote_preference', css_class='form-group col-12 mb-0'),
                    css_class='form-row'
                ),
            ),

            Fieldset(
                'Advanced Filters (Optional)',
                'required_keywords',
                'excluded_keywords',
                'excluded_companies',
                css_class='advanced-filters',
                css_id='advancedFilters'
            ),

            HTML('<div class="card border-success mb-3"><div class="card-body"><div class="form-check form-switch">'),
            Field('auto_follow_up_enabled'),
            HTML(
                '</div><small class="text-muted">Automatically send follow-up emails to increase response rates by 3-5x</small></div></div>'),

            Row(
                Column(
                    Submit('submit', 'Save Configuration', css_class='btn btn-primary btn-lg'),
                    css_class='col-md-6'
                ),
                Column(
                    HTML(
                        '<button type="button" class="btn btn-outline-success btn-lg" onclick="testConfiguration()"><i class="fas fa-search"></i> Test & Save</button>'),
                    css_class='col-md-6 text-end'
                ),
                css_class='form-row mt-4'
            )
        )

    def clean_job_categories(self):
        """Convert textarea input to list"""
        categories_text = self.cleaned_data['job_categories']
        if categories_text:
            categories = [cat.strip() for cat in categories_text.split('\n') if cat.strip()]
            if not categories:
                raise forms.ValidationError('Please enter at least one job category.')
            return categories
        raise forms.ValidationError('Job categories are required.')

    def clean_target_locations(self):
        """Convert textarea input to list"""
        locations_text = self.cleaned_data['target_locations']
        if locations_text:
            locations = [loc.strip() for loc in locations_text.split('\n') if loc.strip()]
            if not locations:
                raise forms.ValidationError('Please enter at least one target location.')
            return locations
        raise forms.ValidationError('Target locations are required.')

    def clean_required_keywords(self):
        keywords_text = self.cleaned_data.get('required_keywords', '')
        if keywords_text:
            return [kw.strip() for kw in keywords_text.split('\n') if kw.strip()]
        return []

    def clean_excluded_keywords(self):
        keywords_text = self.cleaned_data.get('excluded_keywords', '')
        if keywords_text:
            return [kw.strip() for kw in keywords_text.split('\n') if kw.strip()]
        return []

    def clean_excluded_companies(self):
        companies_text = self.cleaned_data.get('excluded_companies', '')
        if companies_text:
            return [comp.strip() for comp in companies_text.split('\n') if comp.strip()]
        return []

    def clean(self):
        cleaned_data = super().clean()
        salary_min = cleaned_data.get('salary_min')
        salary_max = cleaned_data.get('salary_max')

        if salary_min and salary_max and salary_min >= salary_max:
            raise forms.ValidationError('Maximum salary must be greater than minimum salary.')

        return cleaned_data


class JobApplicationUpdateForm(forms.ModelForm):
    """Enhanced form for updating job applications"""

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
                'placeholder': 'Add any notes about this application, interview feedback, or next steps...',
                'class': 'form-control'
            }),
            'interview_scheduled_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'offer_amount': forms.NumberInput(attrs={
                'min': 0,
                'step': 1000,
                'placeholder': 'Enter offer amount',
                'class': 'form-control'
            }),
            'rejection_reason': forms.TextInput(attrs={
                'placeholder': 'Optional: Reason provided for rejection',
                'class': 'form-control'
            }),
            'application_status': forms.Select(attrs={'class': 'form-select'}),
            'urgency_level': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('application_status', css_class='form-group col-md-6 mb-3'),
                Column('urgency_level', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            'notes',
            Fieldset(
                'Interview & Offer Details',
                Row(
                    Column('interview_scheduled_date', css_class='form-group col-md-6 mb-3'),
                    Column(
                        HTML('<div class="form-check form-switch mt-4">'),
                        'offer_received',
                        HTML('</div>'),
                        css_class='form-group col-md-6 mb-3'
                    ),
                    css_class='form-row'
                ),
                Row(
                    Column('offer_amount', css_class='form-group col-md-6 mb-3'),
                    Column(
                        HTML('<div class="form-check form-switch mt-4">'),
                        'rejection_received',
                        HTML('</div>'),
                        css_class='form-group col-md-6 mb-3'
                    ),
                    css_class='form-row'
                ),
                'rejection_reason',
                css_class='advanced-fields border rounded p-3 bg-light'
            ),
            Submit('submit', 'Update Application', css_class='btn btn-primary btn-lg mt-3')
        )


class BulkApplicationForm(forms.Form):
    """Enhanced bulk action form"""

    BULK_ACTIONS = [
        ('send_followup', 'Send Follow-up Emails'),
        ('mark_applied', 'Mark as Applied'),
        ('update_status', 'Update Status'),
        ('download_docs', 'Download Documents'),
        ('schedule_interview', 'Schedule Interview Reminders'),
        ('add_to_calendar', 'Add to Calendar'),
    ]

    applications = forms.ModelMultipleChoiceField(
        queryset=JobApplication.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'bulk-checkbox'}),
        required=True,
        label='Select Applications'
    )

    action = forms.ChoiceField(
        choices=BULK_ACTIONS,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Bulk Action'
    )

    # Optional fields for specific actions
    new_status = forms.ChoiceField(
        choices=JobApplication.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='New Status (for Update Status action)'
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['applications'].queryset = JobApplication.objects.filter(user=user)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'action',
            'new_status',
            HTML('<div class="applications-grid mt-3">'),
            'applications',
            HTML('</div>'),
            Submit('submit', 'Execute Bulk Action', css_class='btn btn-warning btn-lg mt-3')
        )