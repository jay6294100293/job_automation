from django.contrib import admin

# Register your models here.
# followups/admin.py
from django.contrib import admin

from documents.models import GeneratedDocument, DocumentGenerationJob
from .models import FollowUpTemplate, FollowUpHistory


@admin.register(FollowUpTemplate)
class FollowUpTemplateAdmin(admin.ModelAdmin):
    list_display = ('template_name', 'user', 'template_type', 'days_after_application',
                    'is_default', 'is_active', 'success_rate', 'times_used')
    list_filter = ('template_type', 'is_default', 'is_active', 'created_at')
    search_fields = ('template_name', 'user__username', 'subject_template')
    readonly_fields = ('success_rate', 'times_used', 'responses_received', 'created_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'template_name', 'template_type', 'is_default', 'is_active')
        }),
        ('Template Content', {
            'fields': ('subject_template', 'body_template', 'days_after_application')
        }),
        ('Analytics', {
            'fields': ('success_rate', 'times_used', 'responses_received'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

    actions = ['duplicate_template', 'activate_templates', 'deactivate_templates']

    def duplicate_template(self, request, queryset):
        for template in queryset:
            template.pk = None
            template.template_name += ' (Copy)'
            template.is_default = False
            template.save()
        self.message_user(request, f'{queryset.count()} templates duplicated.')

    duplicate_template.short_description = "Duplicate selected templates"


@admin.register(FollowUpHistory)
class FollowUpHistoryAdmin(admin.ModelAdmin):
    list_display = ('application', 'template', 'sent_date', 'response_received', 'response_type')
    list_filter = ('response_received', 'response_type', 'sent_date')
    search_fields = ('application__job_title', 'application__company_name',
                     'application__user__username', 'subject')
    readonly_fields = ('sent_date',)
    date_hierarchy = 'sent_date'

    fieldsets = (
        ('Follow-up Information', {
            'fields': ('application', 'template', 'sent_date')
        }),
        ('Email Content', {
            'fields': ('subject', 'body')
        }),
        ('Response Tracking', {
            'fields': ('response_received', 'response_date', 'response_type', 'notes')
        })
    )

