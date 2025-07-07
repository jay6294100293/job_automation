# Create your views here.
# accounts/views.py


# accounts/views.py
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse  # Keep JsonResponse for the API view if you plan to use it
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, UpdateView, TemplateView
from django.contrib.auth import views as auth_views
from .forms import CustomUserCreationForm, UserProfileForm
from .models import UserProfile  # Ensure UserProfile is imported


class ProfileCompletionView(LoginRequiredMixin, View):
    def get(self, request):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        completion = profile.calculate_completion_percentage()

        # Get missing fields
        missing_fields = []
        if not request.user.first_name or not request.user.last_name:
            missing_fields.append('Full Name')
        if not profile.phone:
            missing_fields.append('Phone Number')
        if not profile.location:
            missing_fields.append('Location')
        if profile.years_experience is None:
            missing_fields.append('Years of Experience')
        if not profile.education:
            missing_fields.append('Education')
        if not profile.current_job_title:
            missing_fields.append('Current Job Title')
        if not profile.key_skills:
            missing_fields.append('Key Skills')
        if not profile.resume_file:
            missing_fields.append('Resume')
        if not profile.industries_of_interest:
            missing_fields.append('Industries of Interest')
        if not profile.preferred_salary_min or not profile.preferred_salary_max:
            missing_fields.append('Salary Range')
        print(completion)
        return JsonResponse({
            'completion_percentage': completion,
            'missing_fields': missing_fields[:3],  # Show top 3 missing fields
            'total_missing': len(missing_fields)
        })



class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    form_class = UserProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['completion_percentage'] = self.object.calculate_completion_percentage()
        return context



# This API view can be used for fetching completion percentage dynamically via AJAX
# if you want to update progress bars without a full page reload.
# It's currently not directly used by the provided HTML templates for display,
# but it's a good utility to keep.
class ProfileCompletionApiView(LoginRequiredMixin, View):
    def get(self, request):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        completion = profile.calculate_completion_percentage()

        # Get missing fields (simplified for example)
        missing_fields_list = []
        if not request.user.first_name or not request.user.last_name:
            missing_fields_list.append('Full Name')
        if not profile.phone:
            missing_fields_list.append('Phone Number')
        if not profile.location:
            missing_fields_list.append('Location')
        if profile.years_experience is None:
            missing_fields_list.append('Years of Experience')
        if not profile.education:
            missing_fields_list.append('Education')
        if not profile.current_job_title:
            missing_fields_list.append('Current Job Title')
        if not profile.key_skills:
            missing_fields_list.append('Key Skills')
        if not profile.resume_file:
            missing_fields_list.append('Resume')
        if not profile.industries_of_interest:
            missing_fields_list.append('Industries of Interest')
        if not profile.preferred_salary_min or not profile.preferred_salary_max:
            missing_fields_list.append('Salary Range')

        return JsonResponse({
            'completion_percentage': completion,
            'missing_fields': missing_fields_list[:3],  # Show top 3 missing fields
            'total_missing': len(missing_fields_list)
        })


class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:profile_completion')  # Redirect to profile completion after registration

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.save()
        login(self.request, user)
        # Create profile for new user
        UserProfile.objects.create(user=user)
        messages.success(self.request, 'Account created successfully! Please complete your profile.')
        return response


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    form_class = UserProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')  # Stays on the profile page after update

    def get_object(self):
        # Ensure a UserProfile exists for the current user
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        # Save user fields (first_name, last_name, email)
        user = self.request.user
        user.first_name = self.request.POST.get('first_name', user.first_name)
        user.last_name = self.request.POST.get('last_name', user.last_name)
        user.email = self.request.POST.get('email', user.email)
        user.save()

        # Save profile fields
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_object()  # Get the profile instance
        context['profile'] = profile
        context['completion_percentage'] = profile.calculate_completion_percentage()

        # Add counts for sidebar stats (dummy data or link to actual counts)
        context['applications_count'] = 0  # Replace with actual count from your models if available
        context['followups_count'] = 0  # Replace with actual count
        context['active_searches_count'] = 0  # Replace with actual count

        # Add a current_step for the profile completion logic if needed,
        # otherwise, it can be derived from the form submission.
        # For simplicity, we'll let the JS handle initial section display.

        # Pass initial skills data as JSON string
        context['initial_key_skills'] = profile.key_skills  # This will be JSONField, so it's already a list/dict

        return context


class ProfileCompletionView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile_completion.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)

        # Calculate completion for each section
        personal_completed = all([
            self.request.user.first_name,
            self.request.user.last_name,
            self.request.user.email,
            profile.phone,
            profile.location,
            profile.linkedin_url
        ])

        professional_completed = all([
            profile.years_experience is not None,
            profile.current_job_title,
            profile.education,
            profile.key_skills  # Assuming key_skills is a list that needs to be non-empty
        ])
        if profile.key_skills and isinstance(profile.key_skills, list) and len(profile.key_skills) == 0:
            professional_completed = False

        preferences_completed = all([
            profile.preferred_salary_min is not None,
            profile.preferred_salary_max is not None,
            profile.work_type_preference
        ])

        # For 'Job Search Setup', let's assume it's completed if there's at least one search config.
        # You'll need to import the JobSearchConfig model and query it.
        # For now, let's use a placeholder.
        # from jobs.models import JobSearchConfig # Uncomment and adjust if you have this model
        search_configs_count = 0  # JobSearchConfig.objects.filter(user=self.request.user).count() if 'jobs' in globals() else 0
        search_setup_completed = search_configs_count > 0

        # Calculate fields missing per section
        personal_fields_missing = sum([
            1 for field in
            [self.request.user.first_name, self.request.user.last_name, self.request.user.email, profile.phone,
             profile.location, profile.linkedin_url] if not field
        ])
        professional_fields_missing = sum([
            1 for field in [profile.years_experience, profile.current_job_title, profile.education] if not field
        ])
        if not profile.key_skills or (isinstance(profile.key_skills, list) and len(profile.key_skills) == 0):
            professional_fields_missing += 1

        preferences_fields_missing = sum([
            1 for field in [profile.preferred_salary_min, profile.preferred_salary_max, profile.work_type_preference] if
            not field
        ])

        completed_steps = 0
        if personal_completed: completed_steps += 1
        if professional_completed: completed_steps += 1
        if preferences_completed: completed_steps += 1
        if search_setup_completed: completed_steps += 1

        total_steps = 4
        completion_percentage = int((completed_steps / total_steps) * 100)

        context['profile'] = profile
        context['completed_steps'] = completed_steps
        context['completion_percentage'] = completion_percentage

        context['personal_completed'] = personal_completed
        context['personal_fields_missing'] = personal_fields_missing if not personal_completed else 0

        context['professional_completed'] = professional_completed
        context['professional_fields_missing'] = professional_fields_missing if not professional_completed else 0

        context['preferences_completed'] = preferences_completed
        context['preferences_fields_missing'] = preferences_fields_missing if not preferences_completed else 0

        context['search_setup_completed'] = search_setup_completed
        context['search_configs_count'] = search_configs_count

        # Determine current step to highlight (simple logic for demonstration)
        if not personal_completed:
            context['current_step'] = 'personal'
        elif not professional_completed:
            context['current_step'] = 'professional'
        elif not preferences_completed:
            context['current_step'] = 'preferences'
        elif not search_setup_completed:
            context['current_step'] = 'search'
        else:
            context['current_step'] = 'all_completed'  # Or null, as all are done

        return context


class CustomLogoutView(auth_views.LogoutView):
    """Custom logout view that handles both GET and POST"""
    http_method_names = ['get', 'post']
    next_page = 'accounts:login'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.success(request, f'Goodbye {request.user.username}! You have been logged out successfully.')
        return super().dispatch(request, *args, **kwargs)
