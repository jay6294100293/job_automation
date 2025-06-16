from django.contrib import admin

# Register your models here.
# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = (
        'phone', 'location', 'linkedin_url', 'github_url', 'portfolio_url',
        'years_experience', 'education', 'current_job_title', 'current_company',
        'preferred_salary_min', 'preferred_salary_max', 'work_type_preference',
        'profile_completion_percentage'
    )
    readonly_fields = ('profile_completion_percentage',)


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_completion_percentage')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')

    def get_completion_percentage(self, obj):
        try:
            return f"{obj.userprofile.profile_completion_percentage}%"
        except UserProfile.DoesNotExist:
            return "No Profile"

    get_completion_percentage.short_description = 'Profile Completion'


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'years_experience', 'current_job_title', 'profile_completion_percentage')
    list_filter = ('work_type_preference', 'years_experience', 'profile_completion_percentage')
    search_fields = ('user__username', 'user__email', 'current_job_title', 'current_company')
    readonly_fields = ('profile_completion_percentage', 'created_at', 'updated_at')

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'discord_user_id', 'phone', 'location')
        }),
        ('Professional Details', {
            'fields': ('years_experience', 'education', 'current_job_title', 'current_company', 'key_skills')
        }),
        ('Job Preferences', {
            'fields': ('preferred_salary_min', 'preferred_salary_max', 'work_type_preference',
                       'preferred_company_sizes', 'industries_of_interest')
        }),
        ('URLs', {
            'fields': ('linkedin_url', 'github_url', 'portfolio_url')
        }),
        ('Resume & Completion', {
            'fields': ('resume_file', 'profile_completion_percentage')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
