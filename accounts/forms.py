# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Div, Field
from crispy_forms.bootstrap import InlineCheckboxes
from .models import UserProfile


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
    # Predefined choices for better UX
    SKILL_CHOICES = [
        ('python', 'Python'),
        ('django', 'Django'),
        ('flask', 'Flask'),
        ('sql', 'SQL'),
        ('postgresql', 'PostgreSQL'),
        ('mysql', 'MySQL'),
        ('machine_learning', 'Machine Learning'),
        ('data_science', 'Data Science'),
        ('tensorflow', 'TensorFlow'),
        ('pytorch', 'PyTorch'),
        ('pandas', 'Pandas'),
        ('numpy', 'NumPy'),
        ('scikit_learn', 'Scikit-learn'),
        ('aws', 'AWS'),
        ('docker', 'Docker'),
        ('kubernetes', 'Kubernetes'),
        ('git', 'Git'),
        ('javascript', 'JavaScript'),
        ('react', 'React'),
        ('html_css', 'HTML/CSS'),
        ('data_analytics', 'Data Analytics'),
        ('tableau', 'Tableau'),
        ('power_bi', 'Power BI'),
        ('excel', 'Excel'),
        ('r', 'R'),
        ('spark', 'Apache Spark'),
        ('hadoop', 'Hadoop'),
    ]

    COMPANY_SIZE_CHOICES = [
        ('startup', 'Startup (1-50 employees)'),
        ('small', 'Small (51-200 employees)'),
        ('medium', 'Medium (201-1000 employees)'),
        ('large', 'Large (1001-5000 employees)'),
        ('enterprise', 'Enterprise (5000+ employees)'),
    ]

    INDUSTRY_CHOICES = [
        ('technology', 'Technology'),
        ('finance', 'Finance'),
        ('healthcare', 'Healthcare'),
        ('education', 'Education'),
        ('retail', 'Retail'),
        ('manufacturing', 'Manufacturing'),
        ('consulting', 'Consulting'),
        ('media', 'Media & Entertainment'),
        ('government', 'Government'),
        ('non_profit', 'Non-profit'),
        ('automotive', 'Automotive'),
        ('aerospace', 'Aerospace'),
        ('biotechnology', 'Biotechnology'),
        ('energy', 'Energy'),
    ]

    key_skills = forms.MultipleChoiceField(
        choices=SKILL_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    preferred_company_sizes = forms.MultipleChoiceField(
        choices=COMPANY_SIZE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    industries_of_interest = forms.MultipleChoiceField(
        choices=INDUSTRY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
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
            'education': forms.Textarea(attrs={'rows': 3}),
            'preferred_salary_min': forms.NumberInput(attrs={'min': 0, 'step': 1000}),
            'preferred_salary_max': forms.NumberInput(attrs={'min': 0, 'step': 1000}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h4>Personal Information</h4>'),
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
            HTML('<hr><h4>Professional Details</h4>'),
            Row(
                Column('years_experience', css_class='form-group col-md-6 mb-0'),
                Column('current_job_title', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'current_company',
            'education',
            HTML('<h5>Skills</h5>'),
            InlineCheckboxes('key_skills'),
            HTML('<hr><h4>Job Preferences</h4>'),
            Row(
                Column('preferred_salary_min', css_class='form-group col-md-6 mb-0'),
                Column('preferred_salary_max', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'work_type_preference',
            HTML('<h5>Preferred Company Sizes</h5>'),
            InlineCheckboxes('preferred_company_sizes'),
            HTML('<h5>Industries of Interest</h5>'),
            InlineCheckboxes('industries_of_interest'),
            HTML('<hr><h4>Resume</h4>'),
            'resume_file',
            Submit('submit', 'Save Profile', css_class='btn btn-primary')
        )