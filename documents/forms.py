# documents/forms.py
from django import forms
from .models import GeneratedDocument


class DocumentRegenerationForm(forms.Form):
    """Form for document regeneration options"""

    REGENERATION_OPTIONS = [
        ('current_profile', 'Use Current Profile Data'),
        ('custom_prompt', 'Use Custom Instructions'),
        ('enhanced_mode', 'Enhanced AI Mode (Slower but Better)'),
    ]

    regeneration_option = forms.ChoiceField(
        choices=REGENERATION_OPTIONS,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='current_profile',
        help_text="Choose how to regenerate the document"
    )

    custom_instructions = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter specific instructions for document generation (optional)'
        }),
        required=False,
        help_text="Provide specific instructions or requirements for the document"
    )

    priority_level = forms.ChoiceField(
        choices=[
            ('normal', 'Normal Priority'),
            ('high', 'High Priority (Faster Processing)'),
            ('urgent', 'Urgent (Premium Processing)')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='normal'
    )

    include_keywords = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Keywords to emphasize (comma-separated)'
        }),
        required=False,
        help_text="Keywords to emphasize in the document"
    )


class BulkDocumentForm(forms.Form):
    """Form for bulk document operations"""

    BULK_ACTIONS = [
        ('download', 'Download Selected'),
        ('regenerate', 'Regenerate Selected'),
        ('delete', 'Delete Selected'),
        ('export_zip', 'Export as ZIP'),
        ('email', 'Email Documents'),
    ]

    action = forms.ChoiceField(
        choices=BULK_ACTIONS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    selected_documents = forms.ModelMultipleChoiceField(
        queryset=GeneratedDocument.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True
    )

    email_address = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        }),
        required=False,
        help_text="Required only for email action"
    )

    zip_filename = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'documents_export'
        }),
        required=False,
        initial='job_documents',
        help_text="Filename for ZIP export (without extension)"
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['selected_documents'].queryset = GeneratedDocument.objects.filter(
                application__user=user
            )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        email_address = cleaned_data.get('email_address')

        if action == 'email' and not email_address:
            raise forms.ValidationError("Email address is required for email action.")

        return cleaned_data


class DocumentFilterForm(forms.Form):
    """Form for filtering documents"""

    DOCUMENT_TYPE_CHOICES = [('', 'All Types')] + GeneratedDocument.DOCUMENT_TYPES

    DATE_RANGE_CHOICES = [
        ('', 'All Time'),
        ('today', 'Today'),
        ('week', 'This Week'),
        ('month', 'This Month'),
        ('quarter', 'This Quarter'),
        ('year', 'This Year'),
    ]

    search_query = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search documents...'
        }),
        required=False
    )

    document_type = forms.ChoiceField(
        choices=DOCUMENT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )

    date_range = forms.ChoiceField(
        choices=DATE_RANGE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )

    application_status = forms.ChoiceField(
        choices=[
            ('', 'All Applications'),
            ('found', 'Found'),
            ('applied', 'Applied'),
            ('responded', 'Responded'),
            ('interview', 'Interview'),
            ('offer', 'Offer'),
            ('hired', 'Hired'),
            ('rejected', 'Rejected'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )

    has_content = forms.ChoiceField(
        choices=[
            ('', 'All Documents'),
            ('yes', 'With Content'),
            ('no', 'File Only'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )


class DocumentPreferencesForm(forms.Form):
    """Form for user document generation preferences"""

    TONE_CHOICES = [
        ('professional', 'Professional'),
        ('friendly', 'Friendly'),
        ('enthusiastic', 'Enthusiastic'),
        ('formal', 'Formal'),
        ('conversational', 'Conversational'),
    ]

    LENGTH_CHOICES = [
        ('concise', 'Concise'),
        ('standard', 'Standard'),
        ('detailed', 'Detailed'),
        ('comprehensive', 'Comprehensive'),
    ]

    default_tone = forms.ChoiceField(
        choices=TONE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='professional'
    )

    default_length = forms.ChoiceField(
        choices=LENGTH_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='standard'
    )

    auto_generate = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False,
        initial=True,
        help_text="Automatically generate documents when new jobs are found"
    )

    include_skills_analysis = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False,
        initial=True
    )

    include_company_research = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False,
        initial=True
    )

    include_followup_schedule = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False,
        initial=True
    )

    custom_signature = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Your email signature for follow-ups'
        }),
        required=False
    )

    preferred_ai_model = forms.ChoiceField(
        choices=[
            ('gpt-4', 'GPT-4 (Best Quality)'),
            ('gpt-3.5', 'GPT-3.5 (Faster)'),
            ('gemini', 'Google Gemini'),
            ('mixed', 'Mixed Models (Optimized)'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='mixed'
    )