from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import JobSearchConfig, JobApplication


@admin.register(JobSearchConfig)
class JobSearchConfigAdmin(admin.ModelAdmin):
    list_display = ('user', 'config_name', 'is_active', 'last_search_date', 'auto_follow_up_enabled')
    list_filter = ('is_active', 'auto_follow_up_enabled', 'remote_preference', 'created_at')
    search_fields = ('user__username', 'config_name', 'job_categories', 'target_locations')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'config_name', 'is_active')
        }),
        ('Search Criteria', {
            'fields': ('job_categories', 'target_locations', 'remote_preference')
        }),
        ('Salary & Preferences', {
            'fields': ('salary_min', 'salary_max', 'company_size_preference')
        }),
        ('Automation', {
            'fields': ('auto_follow_up_enabled', 'last_search_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('job_title', 'company_name', 'user', 'application_status', 'urgency_level',
                    'applied_date', 'documents_generated', 'match_percentage')
    list_filter = ('application_status', 'urgency_level', 'documents_generated', 'remote_option',
                   'follow_up_sequence_active', 'created_at')
    search_fields = ('job_title', 'company_name', 'user__username', 'location')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Job Information', {
            'fields': ('user', 'search_config', 'job_title', 'company_name', 'job_url')
        }),
        ('Job Details', {
            'fields': ('job_description', 'salary_range', 'location', 'remote_option')
        }),
        ('Application Status', {
            'fields': ('application_status', 'applied_date', 'urgency_level', 'notes')
        }),
        ('Follow-up Management', {
            'fields': ('last_follow_up_date', 'follow_up_count', 'next_follow_up_date',
                       'follow_up_sequence_active')
        }),
        ('Interview & Offer', {
            'fields': ('interview_scheduled_date', 'offer_received', 'offer_amount',
                       'rejection_received', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('company_rating', 'glassdoor_rating', 'match_percentage', 'skills_match_analysis'),
            'classes': ('collapse',)
        }),
        ('Documents', {
            'fields': ('documents_generated', 'documents_folder_path')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['mark_as_applied', 'enable_follow_up_sequence', 'generate_documents']

    def mark_as_applied(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            application_status='applied',
            applied_date=timezone.now()
        )
        self.message_user(request, f'{updated} applications marked as applied.')

    mark_as_applied.short_description = "Mark selected applications as applied"

    def enable_follow_up_sequence(self, request, queryset):
        updated = queryset.update(follow_up_sequence_active=True)
        self.message_user(request, f'Follow-up sequence enabled for {updated} applications.')

    enable_follow_up_sequence.short_description = "Enable follow-up sequence"

    def generate_documents(self, request, queryset):
        from documents.tasks import generate_all_documents
        count = 0
        for application in queryset:
            generate_all_documents.delay(application.id)
            count += 1
        self.message_user(request, f'Document generation started for {count} applications.')

    generate_documents.short_description = "Generate documents for selected applications"
