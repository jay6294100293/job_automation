# Create your views here.
# accounts/views.py
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, TemplateView

from .forms import CustomUserCreationForm, UserProfileForm
from .models import UserProfile


class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:profile')

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


class ProfileCompletionView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile_completion.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        context['profile'] = profile
        context['completion_percentage'] = profile.calculate_completion_percentage()

        # Completion suggestions
        suggestions = []
        if not self.request.user.first_name:
            suggestions.append('Add your first name')
        if not profile.phone:
            suggestions.append('Add your phone number')
        if not profile.linkedin_url:
            suggestions.append('Add your LinkedIn profile')
        if not profile.resume_file:
            suggestions.append('Upload your resume')
        if not profile.key_skills:
            suggestions.append('Add your key skills')

        context['suggestions'] = suggestions
        return context
