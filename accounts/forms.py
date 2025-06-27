# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Div, Field
from crispy_forms.bootstrap import InlineCheckboxes
from .models import UserProfile
import json


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='form-group col-md-6 mb-0'),
                Column('last_name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'username',
            'email',
            'password1',
            'password2',
            Submit('submit', 'Create Account', css_class='btn btn-primary btn-block')
        )


class UserProfileForm(forms.ModelForm):
    # Flexible company size choices - users can still select common options
    COMPANY_SIZE_CHOICES = [
        ('startup', 'Startup (1-50 employees)'),
        ('small', 'Small (51-200 employees)'),
        ('medium', 'Medium (201-1000 employees)'),
        ('large', 'Large (1001-5000 employees)'),
        ('enterprise', 'Enterprise (5000+ employees)'),
        ('any', 'Any Size'),
    ]

    # Broad industry categories - but users can add custom ones too
    INDUSTRY_CHOICES = [
        ('technology', 'Technology'),
        ('finance', 'Finance & Banking'),
        ('healthcare', 'Healthcare'),
        ('education', 'Education'),
        ('retail', 'Retail & E-commerce'),
        ('consulting', 'Consulting'),
        ('manufacturing', 'Manufacturing'),
        ('media', 'Media & Entertainment'),
        ('government', 'Government'),
        ('nonprofit', 'Non-profit'),
        ('energy', 'Energy'),
        ('transportation', 'Transportation'),
        ('real_estate', 'Real Estate'),
        ('aerospace', 'Aerospace'),
        ('automotive', 'Automotive'),
        ('telecommunications', 'Telecommunications'),
        ('insurance', 'Insurance'),
        ('gaming', 'Gaming'),
        ('cybersecurity', 'Cybersecurity'),
        ('biotechnology', 'Biotechnology'),
        ('pharmaceuticals', 'Pharmaceuticals'),
        ('agriculture', 'Agriculture'),
        ('food_beverage', 'Food & Beverage'),
        ('hospitality', 'Hospitality'),
        ('sports', 'Sports & Recreation'),
        ('creative', 'Creative & Design'),
        ('legal', 'Legal'),
        ('marketing', 'Marketing & Advertising'),
        ('sales', 'Sales'),
        ('customer_service', 'Customer Service'),
        ('hr', 'Human Resources'),
        ('logistics', 'Logistics & Supply Chain'),
        ('other', 'Other'),
    ]

    # Dynamic skills field - users can type anything
    key_skills = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Add any skills relevant to your profession"
    )

    preferred_company_sizes = forms.MultipleChoiceField(
        choices=COMPANY_SIZE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Choose your preferred company sizes"
    )

    industries_of_interest = forms.MultipleChoiceField(
        choices=INDUSTRY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select industries you're interested in, or add custom ones"
    )

    class Meta:
        model = UserProfile
        fields = [
            'phone', 'location', 'linkedin_url', 'github_url', 'portfolio_url',
            'years_experience', 'education', 'current_job_title', 'current_company',
            'key_skills', 'preferred_salary_min', 'preferred_salary_max',
            'work_type_preference', 'preferred_company_sizes', 'industries_of_interest',
            'resume_file'
        ]
        widgets = {
            'phone': forms.TextInput(attrs={
                'placeholder': '+1-778-636-6294',
                'class': 'form-control'
            }),
            'location': forms.TextInput(attrs={
                'placeholder': 'Burnaby, BC, Canada (or anywhere you want to work)',
                'class': 'form-control'
            }),
            'linkedin_url': forms.URLInput(attrs={
                'placeholder': 'https://linkedin.com/in/your-profile',
                'class': 'form-control'
            }),
            'github_url': forms.URLInput(attrs={
                'placeholder': 'https://github.com/yourusername (if applicable)',
                'class': 'form-control'
            }),
            'portfolio_url': forms.URLInput(attrs={
                'placeholder': 'https://yourportfolio.com (if you have one)',
                'class': 'form-control'
            }),
            'education': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'e.g., Master\'s in Analytics from Northeastern University, Bachelor\'s in Computer Science, Self-taught, Bootcamp, etc.',
                'class': 'form-control'
            }),
            'current_job_title': forms.TextInput(attrs={
                'placeholder': 'e.g., Data Scientist, Software Engineer, Marketing Manager, Student, etc.',
                'class': 'form-control'
            }),
            'current_company': forms.TextInput(attrs={
                'placeholder': 'Your Current Company (or "Seeking Opportunities")',
                'class': 'form-control'
            }),
            'preferred_salary_min': forms.NumberInput(attrs={
                'placeholder': '50000',
                'class': 'form-control'
            }),
            'preferred_salary_max': forms.NumberInput(attrs={
                'placeholder': '100000',
                'class': 'form-control'
            }),
            'resume_file': forms.FileInput(attrs={
                'accept': '.pdf,.doc,.docx',
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h4>Contact Information</h4>'),
            Row(
                Column('phone', css_class='form-group col-md-6 mb-0'),
                Column('location', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('linkedin_url', css_class='form-group col-md-4 mb-0'),
                Column('github_url', css_class='form-group col-md-4 mb-0'),
                Column('portfolio_url', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            HTML('<hr><h4>Professional Information</h4>'),
            Row(
                Column('years_experience', css_class='form-group col-md-4 mb-0'),
                Column('current_job_title', css_class='form-group col-md-4 mb-0'),
                Column('current_company', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            'education',
            HTML('<h5>Skills & Expertise</h5>'),
            HTML('<div id="skills-input-container"></div>'),
            Field('key_skills'),
            HTML('<hr><h4>Job Preferences</h4>'),
            Row(
                Column('preferred_salary_min', css_class='form-group col-md-4 mb-0'),
                Column('preferred_salary_max', css_class='form-group col-md-4 mb-0'),
                Column('work_type_preference', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            HTML('<h5>Preferred Company Sizes</h5>'),
            InlineCheckboxes('preferred_company_sizes'),
            HTML('<h5>Industries of Interest</h5>'),
            InlineCheckboxes('industries_of_interest'),
            HTML('<hr><h4>Resume Upload</h4>'),
            'resume_file',
            Submit('submit', 'Update Profile', css_class='btn btn-primary btn-lg mt-3')
        )

        # Set help texts
        self.fields['phone'].help_text = "Include country code if outside North America"
        self.fields['location'].help_text = "Where you're located or where you want to work"
        self.fields['linkedin_url'].help_text = "Your LinkedIn profile URL (optional but recommended)"
        self.fields['github_url'].help_text = "Your GitHub profile (for technical roles)"
        self.fields['portfolio_url'].help_text = "Personal website or portfolio (if applicable)"
        self.fields['years_experience'].help_text = "Total years of professional experience"
        self.fields['education'].help_text = "Your educational background - formal or self-taught"
        self.fields['current_job_title'].help_text = "What you do now, or 'Student', 'Job Seeker', etc."
        self.fields['current_company'].help_text = "Where you work now, or 'Seeking Opportunities'"
        self.fields['preferred_salary_min'].help_text = "Minimum salary you'd accept (annual, in your currency)"
        self.fields['preferred_salary_max'].help_text = "Target salary you're aiming for (annual)"
        self.fields['work_type_preference'].help_text = "Your preferred work arrangement"
        self.fields['resume_file'].help_text = "Upload your most recent resume (PDF preferred)"

    def clean(self):
        cleaned_data = super().clean()
        salary_min = cleaned_data.get('preferred_salary_min')
        salary_max = cleaned_data.get('preferred_salary_max')

        if salary_min and salary_max and salary_min >= salary_max:
            raise forms.ValidationError("Minimum salary must be less than maximum salary.")

        return cleaned_data

    def save(self, commit=True):
        profile = super().save(commit=False)

        # Handle key_skills - convert from JSON string to list
        key_skills_data = self.cleaned_data.get('key_skills', '[]')
        try:
            if isinstance(key_skills_data, str):
                profile.key_skills = json.loads(key_skills_data) if key_skills_data else []
            else:
                profile.key_skills = key_skills_data or []
        except json.JSONDecodeError:
            profile.key_skills = []

        # Handle company sizes and industries
        if isinstance(self.cleaned_data.get('preferred_company_sizes'), list):
            profile.preferred_company_sizes = self.cleaned_data['preferred_company_sizes']
        if isinstance(self.cleaned_data.get('industries_of_interest'), list):
            profile.industries_of_interest = self.cleaned_data['industries_of_interest']

        if commit:
            profile.save()
            # Recalculate completion percentage
            profile.calculate_completion_percentage()
        return profile

# # accounts/forms.py
# from django import forms
# from django.contrib.auth.forms import UserCreationForm
# from django.contrib.auth.models import User
# from crispy_forms.helper import FormHelper
# from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Div, Field
# from crispy_forms.bootstrap import InlineCheckboxes
# from .models import UserProfile
#
#
# class CustomUserCreationForm(UserCreationForm):
#     email = forms.EmailField(required=True)
#     first_name = forms.CharField(max_length=30, required=True)
#     last_name = forms.CharField(max_length=30, required=True)
#
#     class Meta:
#         model = User
#         fields = ("username", "first_name", "last_name", "email", "password1", "password2")
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.layout = Layout(
#             Row(
#                 Column('first_name', css_class='form-group col-md-6 mb-0'),
#                 Column('last_name', css_class='form-group col-md-6 mb-0'),
#                 css_class='form-row'
#             ),
#             'username',
#             'email',
#             'password1',
#             'password2',
#             Submit('submit', 'Create Account', css_class='btn btn-primary btn-block')
#         )
#
#
# class UserProfileForm(forms.ModelForm):
#     # Predefined choices for better UX
#     SKILL_CHOICES = [
#         ('python', 'Python'),
#         ('django', 'Django'),
#         ('flask', 'Flask'),
#         ('sql', 'SQL'),
#         ('postgresql', 'PostgreSQL'),
#         ('mysql', 'MySQL'),
#         ('machine_learning', 'Machine Learning'),
#         ('data_science', 'Data Science'),
#         ('tensorflow', 'TensorFlow'),
#         ('pytorch', 'PyTorch'),
#         ('pandas', 'Pandas'),
#         ('numpy', 'NumPy'),
#         ('scikit_learn', 'Scikit-learn'),
#         ('aws', 'AWS'),
#         ('docker', 'Docker'),
#         ('kubernetes', 'Kubernetes'),
#         ('git', 'Git'),
#         ('javascript', 'JavaScript'),
#         ('react', 'React'),
#         ('html_css', 'HTML/CSS'),
#         ('data_analytics', 'Data Analytics'),
#         ('tableau', 'Tableau'),
#         ('power_bi', 'Power BI'),
#         ('excel', 'Excel'),
#         ('r', 'R'),
#         ('spark', 'Apache Spark'),
#         ('hadoop', 'Hadoop'),
#     ]
#
#     COMPANY_SIZE_CHOICES = [
#         ('startup', 'Startup (1-50 employees)'),
#         ('small', 'Small (51-200 employees)'),
#         ('medium', 'Medium (201-1000 employees)'),
#         ('large', 'Large (1001-5000 employees)'),
#         ('enterprise', 'Enterprise (5000+ employees)'),
#     ]
#
#     INDUSTRY_CHOICES = [
#         ('technology', 'Technology'),
#         ('finance', 'Finance'),
#         ('healthcare', 'Healthcare'),
#         ('education', 'Education'),
#         ('retail', 'Retail'),
#         ('manufacturing', 'Manufacturing'),
#         ('consulting', 'Consulting'),
#         ('media', 'Media & Entertainment'),
#         ('government', 'Government'),
#         ('non_profit', 'Non-profit'),
#         ('automotive', 'Automotive'),
#         ('aerospace', 'Aerospace'),
#         ('biotechnology', 'Biotechnology'),
#         ('energy', 'Energy'),
#     ]
#
#     key_skills = forms.MultipleChoiceField(
#         choices=SKILL_CHOICES,
#         widget=forms.CheckboxSelectMultiple,
#         required=False
#     )
#
#     preferred_company_sizes = forms.MultipleChoiceField(
#         choices=COMPANY_SIZE_CHOICES,
#         widget=forms.CheckboxSelectMultiple,
#         required=False
#     )
#
#     industries_of_interest = forms.MultipleChoiceField(
#         choices=INDUSTRY_CHOICES,
#         widget=forms.CheckboxSelectMultiple,
#         required=False
#     )
#
#     class Meta:
#         model = UserProfile
#         fields = [
#             'phone', 'location', 'linkedin_url', 'github_url', 'portfolio_url',
#             'years_experience', 'education', 'current_job_title', 'current_company',
#             'key_skills', 'preferred_salary_min', 'preferred_salary_max',
#             'work_type_preference', 'preferred_company_sizes', 'industries_of_interest',
#             'resume_file'
#         ]
#         widgets = {
#             'education': forms.Textarea(attrs={'rows': 3}),
#             'preferred_salary_min': forms.NumberInput(attrs={'min': 0, 'step': 1000}),
#             'preferred_salary_max': forms.NumberInput(attrs={'min': 0, 'step': 1000}),
#         }
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.layout = Layout(
#             HTML('<h4>Personal Information</h4>'),
#             Row(
#                 Column('phone', css_class='form-group col-md-6 mb-0'),
#                 Column('location', css_class='form-group col-md-6 mb-0'),
#                 css_class='form-row'
#             ),
#             Row(
#                 Column('linkedin_url', css_class='form-group col-md-4 mb-0'),
#                 Column('github_url', css_class='form-group col-md-4 mb-0'),
#                 Column('portfolio_url', css_class='form-group col-md-4 mb-0'),
#                 css_class='form-row'
#             ),
#             HTML('<hr><h4>Professional Details</h4>'),
#             Row(
#                 Column('years_experience', css_class='form-group col-md-6 mb-0'),
#                 Column('current_job_title', css_class='form-group col-md-6 mb-0'),
#                 css_class='form-row'
#             ),
#             'current_company',
#             'education',
#             HTML('<h5>Skills</h5>'),
#             InlineCheckboxes('key_skills'),
#             HTML('<hr><h4>Job Preferences</h4>'),
#             Row(
#                 Column('preferred_salary_min', css_class='form-group col-md-6 mb-0'),
#                 Column('preferred_salary_max', css_class='form-group col-md-6 mb-0'),
#                 css_class='form-row'
#             ),
#             'work_type_preference',
#             HTML('<h5>Preferred Company Sizes</h5>'),
#             InlineCheckboxes('preferred_company_sizes'),
#             HTML('<h5>Industries of Interest</h5>'),
#             InlineCheckboxes('industries_of_interest'),
#             HTML('<hr><h4>Resume</h4>'),
#             'resume_file',
#             Submit('submit', 'Save Profile', css_class='btn btn-primary')
#         )