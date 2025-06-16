# documents/admin.py
from django.contrib import admin
from .models import GeneratedDocument, DocumentGenerationJob


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ('application', 'document_type', 'generated_at', 'file_size')
    list_filter = ('document_type', 'generated_at')
    search_fields = ('application__job_title', 'application__company_name',
                     'application__user__username')
    readonly_fields = ('generated_at', 'file_size')

    fieldsets = (
        ('Document Information', {
            'fields': ('application', 'document_type', 'file_path', 'file_size')
        }),
        ('Content Preview', {
            'fields': ('content',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('generated_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(DocumentGenerationJob)
class DocumentGenerationJobAdmin(admin.ModelAdmin):
    list_display = ('application', 'status', 'started_at', 'completed_at')
    list_filter = ('status', 'started_at')
    search_fields = ('application__job_title', 'application__company_name')
    readonly_fields = ('started_at', 'completed_at')

    fieldsets = (
        ('Job Information', {
            'fields': ('application', 'status')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at')
        }),
        ('Error Details', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        })
    )
