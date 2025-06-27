# dashboard/forms.py
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, HTML, Div
from .models import DashboardWidget, DashboardSettings
from jobs.models import JobSearchConfig, JobApplication


class QuickSearchForm(forms.Form):
    """Quick search configuration form"""

    SEARCH_TYPES = [
        ('normal', 'Normal Search (15 jobs)'),
        ('emergency', 'Emergency Search (10 urgent jobs)'),
        ('extensive', 'Extensive Search (25 jobs)'),
    ]

    URGENCY_LEVELS = [
        ('normal', 'Normal Priority'),
        ('high', 'High Priority'),
        ('urgent', 'Urgent (Premium Processing)'),
    ]

    search_type = forms.ChoiceField(
        choices=SEARCH_TYPES,
        initial='normal',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text="Choose search intensity based on your needs"
    )

    config = forms.ModelChoiceField(
        queryset=JobSearchConfig.objects.none(),
        empty_label="Use default configuration",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Override default search configuration"
    )

    job_categories = forms.MultipleChoiceField(
        choices=[
            ('data_scientist', 'Data Scientist'),
            ('ml_engineer', 'ML Engineer'),
            ('software_engineer', 'Software Engineer'),
            ('python_developer', 'Python Developer'),
            ('data_analyst', 'Data Analyst'),
            ('backend_developer', 'Backend Developer'),
            ('full_stack_developer', 'Full Stack Developer'),
            ('devops_engineer', 'DevOps Engineer'),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text="Override job categories for this search"
    )

    locations = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Toronto, ON; Vancouver, BC; Remote'
        }),
        help_text="Comma-separated list of locations"
    )

    remote_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Search only for remote positions"
    )

    salary_min = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '80000'
        }),
        help_text="Minimum salary requirement"
    )

    urgency = forms.ChoiceField(
        choices=URGENCY_LEVELS,
        initial='normal',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Processing priority level"
    )

    generate_documents = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Automatically generate application documents"
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['config'].queryset = JobSearchConfig.objects.filter(
                user=user, is_active=True
            )

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h5><i class="fas fa-rocket"></i> Quick Job Search</h5>'),
            'search_type',
            Row(
                Column('config', css_class='col-md-6'),
                Column('urgency', css_class='col-md-6'),
            ),
            HTML('<hr><h6><i class="fas fa-filter"></i> Search Filters (Optional)</h6>'),
            'job_categories',
            Row(
                Column('locations', css_class='col-md-8'),
                Column('remote_only', css_class='col-md-4 d-flex align-items-end'),
            ),
            'salary_min',
            HTML('<hr><h6><i class="fas fa-cog"></i> Options</h6>'),
            'generate_documents',
            HTML('<div class="mt-3">'),
            Submit('submit', 'Start Job Search', css_class='btn btn-primary btn-lg'),
            HTML('</div>')
        )


class DashboardSettingsForm(forms.ModelForm):
    """Dashboard customization form"""

    class Meta:
        model = DashboardSettings
        fields = [
            'theme', 'layout_density', 'auto_refresh_enabled',
            'auto_refresh_interval', 'email_notifications',
            'browser_notifications', 'follow_up_reminders',
            'job_alert_notifications'
        ]
        widgets = {
            'theme': forms.Select(attrs={'class': 'form-select'}),
            'layout_density': forms.Select(attrs={'class': 'form-select'}),
            'auto_refresh_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_refresh_interval': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 300}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'browser_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'follow_up_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'job_alert_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h5><i class="fas fa-palette"></i> Appearance</h5>'),
            Row(
                Column('theme', css_class='col-md-6'),
                Column('layout_density', css_class='col-md-6'),
            ),
            HTML('<hr><h5><i class="fas fa-sync"></i> Auto-Refresh</h5>'),
            Row(
                Column('auto_refresh_enabled', css_class='col-md-6'),
                Column('auto_refresh_interval', css_class='col-md-6'),
            ),
            HTML('<small class="form-text text-muted">Auto-refresh interval in seconds (10-300)</small>'),
            HTML('<hr><h5><i class="fas fa-bell"></i> Notifications</h5>'),
            Row(
                Column('email_notifications', css_class='col-md-6'),
                Column('browser_notifications', css_class='col-md-6'),
            ),
            Row(
                Column('follow_up_reminders', css_class='col-md-6'),
                Column('job_alert_notifications', css_class='col-md-6'),
            ),
            HTML('<div class="mt-4">'),
            Submit('submit', 'Save Settings', css_class='btn btn-primary'),
            HTML('</div>')
        )


class WidgetCustomizationForm(forms.ModelForm):
    """Widget customization form"""

    class Meta:
        model = DashboardWidget
        fields = ['title', 'position_x', 'position_y', 'width', 'height', 'is_visible']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'position_x': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'position_y': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'width': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 12}),
            'height': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
            'is_visible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    widget_settings = forms.JSONField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': '{"key": "value"}'
        }),
        help_text="Advanced widget settings in JSON format"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h5><i class="fas fa-cube"></i> Widget Configuration</h5>'),
            'title',
            'is_visible',
            HTML('<hr><h6><i class="fas fa-arrows-alt"></i> Position & Size</h6>'),
            Row(
                Column('position_x', css_class='col-md-3'),
                Column('position_y', css_class='col-md-3'),
                Column('width', css_class='col-md-3'),
                Column('height', css_class='col-md-3'),
            ),
            HTML(
                '<small class="form-text text-muted">Position is in grid units (0-11 for X, 0+ for Y). Size: width (1-12), height (1-6)</small>'),
            HTML('<hr><h6><i class="fas fa-cogs"></i> Advanced Settings</h6>'),
            'widget_settings',
            HTML('<div class="mt-3">'),
            Submit('submit', 'Update Widget', css_class='btn btn-primary'),
            HTML('</div>')
        )


class BulkActionForm(forms.Form):
    """Bulk actions form for dashboard operations"""

    ACTIONS = [
        ('mark_applied', 'Mark as Applied'),
        ('send_followup', 'Send Follow-up'),
        ('update_status', 'Update Status'),
        ('download_documents', 'Download Documents'),
        ('delete_applications', 'Delete Applications'),
        ('export_data', 'Export Data'),
    ]

    STATUS_CHOICES = [
        ('found', 'Found'),
        ('applied', 'Applied'),
        ('responded', 'Responded'),
        ('interview', 'Interview'),
        ('offer', 'Offer'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
    ]

    action = forms.ChoiceField(
        choices=ACTIONS,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Select action to perform on selected items"
    )

    applications = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text="Select applications to perform action on"
    )

    new_status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Required for status update action"
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional notes for this bulk action'
        }),
        help_text="Optional notes to add to all selected applications"
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if user:
            # Populate applications choices
            applications = JobApplication.objects.filter(user=user).order_by('-created_at')
            self.fields['applications'].choices = [
                (app.id, f"{app.job_title} at {app.company_name}")
                for app in applications
            ]

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h5><i class="fas fa-tasks"></i> Bulk Actions</h5>'),
            'action',
            'applications',
            Row(
                Column('new_status', css_class='col-md-6'),
                Column(HTML('<div class="form-text">Only required for status updates</div>'), css_class='col-md-6'),
            ),
            'notes',
            HTML('<div class="mt-3">'),
            Submit('submit', 'Execute Action', css_class='btn btn-warning'),
            HTML('</div>')
        )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        new_status = cleaned_data.get('new_status')

        if action == 'update_status' and not new_status:
            raise forms.ValidationError("New status is required for status update action.")

        return cleaned_data


class ProfileHealthForm(forms.Form):
    """Profile health analysis form"""

    ANALYSIS_TYPES = [
        ('basic', 'Basic Analysis'),
        ('detailed', 'Detailed Analysis'),
        ('ats_compatibility', 'ATS Compatibility Check'),
        ('market_analysis', 'Market Competitiveness'),
    ]

    analysis_type = forms.ChoiceField(
        choices=ANALYSIS_TYPES,
        initial='detailed',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text="Choose the type of analysis to perform"
    )

    include_recommendations = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Include improvement recommendations"
    )

    compare_to_market = forms.BooleanField(
        initial=False,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Compare profile to market standards"
    )

    target_roles = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Data Scientist, Software Engineer'
        }),
        help_text="Comma-separated list of target roles for analysis"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h5><i class="fas fa-user-md"></i> Profile Health Check</h5>'),
            'analysis_type',
            HTML('<hr><h6><i class="fas fa-clipboard-check"></i> Options</h6>'),
            'include_recommendations',
            'compare_to_market',
            'target_roles',
            HTML('<div class="mt-3">'),
            Submit('submit', 'Analyze Profile', css_class='btn btn-info'),
            HTML('</div>')
        )