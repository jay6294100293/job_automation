# dashboard/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import DashboardWidget, UserNotification, DashboardSettings, DashboardActivity


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ('user', 'widget_type', 'title', 'position_display', 'size_display', 'is_visible', 'updated_at')
    list_filter = ('widget_type', 'is_visible', 'created_at')
    search_fields = ('user__username', 'user__email', 'title')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Widget Information', {
            'fields': ('user', 'widget_type', 'title', 'is_visible')
        }),
        ('Position & Size', {
            'fields': ('position_x', 'position_y', 'width', 'height'),
            'description': 'Widget position and size on the dashboard grid'
        }),
        ('Settings', {
            'fields': ('settings',),
            'classes': ('collapse',),
            'description': 'Widget-specific configuration in JSON format'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def position_display(self, obj):
        return f"({obj.position_x}, {obj.position_y})"

    position_display.short_description = "Position (X, Y)"

    def size_display(self, obj):
        return f"{obj.width}×{obj.height}"

    size_display.short_description = "Size (W×H)"

    actions = ['reset_positions', 'hide_widgets', 'show_widgets']

    def reset_positions(self, request, queryset):
        """Reset widget positions to default grid layout"""
        for i, widget in enumerate(queryset):
            widget.position_x = i % 3
            widget.position_y = i // 3
            widget.save()
        self.message_user(request, f'Reset positions for {queryset.count()} widgets.')

    reset_positions.short_description = "Reset widget positions"

    def hide_widgets(self, request, queryset):
        queryset.update(is_visible=False)
        self.message_user(request, f'Hidden {queryset.count()} widgets.')

    hide_widgets.short_description = "Hide selected widgets"

    def show_widgets(self, request, queryset):
        queryset.update(is_visible=True)
        self.message_user(request, f'Shown {queryset.count()} widgets.')

    show_widgets.short_description = "Show selected widgets"


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'priority', 'is_read', 'is_dismissed', 'created_at')
    list_filter = ('notification_type', 'priority', 'is_read', 'is_dismissed', 'created_at')
    search_fields = ('user__username', 'user__email', 'title', 'message')
    readonly_fields = ('created_at', 'read_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Notification Details', {
            'fields': ('user', 'notification_type', 'title', 'message', 'priority')
        }),
        ('Related Objects', {
            'fields': ('related_application', 'related_search_config'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read', 'is_dismissed', 'read_at')
        }),
        ('Action', {
            'fields': ('action_url', 'action_text'),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': ('created_at', 'expires_at'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'related_application', 'related_search_config'
        )

    actions = ['mark_as_read', 'mark_as_unread', 'dismiss_notifications', 'delete_expired']

    def mark_as_read(self, request, queryset):
        count = queryset.filter(is_read=False).count()
        queryset.update(is_read=True)
        self.message_user(request, f'Marked {count} notifications as read.')

    mark_as_read.short_description = "Mark selected notifications as read"

    def mark_as_unread(self, request, queryset):
        count = queryset.filter(is_read=True).count()
        queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'Marked {count} notifications as unread.')

    mark_as_unread.short_description = "Mark selected notifications as unread"

    def dismiss_notifications(self, request, queryset):
        count = queryset.filter(is_dismissed=False).count()
        queryset.update(is_dismissed=True)
        self.message_user(request, f'Dismissed {count} notifications.')

    dismiss_notifications.short_description = "Dismiss selected notifications"

    def delete_expired(self, request, queryset):
        from django.utils import timezone
        expired = queryset.filter(expires_at__lt=timezone.now())
        count = expired.count()
        expired.delete()
        self.message_user(request, f'Deleted {count} expired notifications.')

    delete_expired.short_description = "Delete expired notifications"


@admin.register(DashboardSettings)
class DashboardSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'theme', 'layout_density', 'auto_refresh_enabled', 'email_notifications', 'updated_at')
    list_filter = ('theme', 'layout_density', 'auto_refresh_enabled', 'email_notifications', 'browser_notifications')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Appearance', {
            'fields': ('theme', 'layout_density')
        }),
        ('Behavior', {
            'fields': ('auto_refresh_enabled', 'auto_refresh_interval', 'show_welcome_message')
        }),
        ('Notifications', {
            'fields': ('email_notifications', 'browser_notifications', 'follow_up_reminders', 'job_alert_notifications')
        }),
        ('Customization', {
            'fields': ('default_widget_layout', 'hidden_widgets', 'favorite_actions'),
            'classes': ('collapse',),
            'description': 'Advanced customization settings'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['reset_to_defaults', 'enable_notifications', 'disable_notifications']

    def reset_to_defaults(self, request, queryset):
        """Reset settings to default values"""
        for settings in queryset:
            settings.theme = 'light'
            settings.layout_density = 'comfortable'
            settings.auto_refresh_enabled = True
            settings.auto_refresh_interval = 30
            settings.email_notifications = True
            settings.browser_notifications = True
            settings.follow_up_reminders = True
            settings.job_alert_notifications = True
            settings.default_widget_layout = {}
            settings.hidden_widgets = []
            settings.favorite_actions = []
            settings.save()
        self.message_user(request, f'Reset {queryset.count()} settings to defaults.')

    reset_to_defaults.short_description = "Reset settings to defaults"

    def enable_notifications(self, request, queryset):
        queryset.update(
            email_notifications=True,
            browser_notifications=True,
            follow_up_reminders=True,
            job_alert_notifications=True
        )
        self.message_user(request, f'Enabled all notifications for {queryset.count()} users.')

    enable_notifications.short_description = "Enable all notifications"

    def disable_notifications(self, request, queryset):
        queryset.update(
            email_notifications=False,
            browser_notifications=False,
            follow_up_reminders=False,
            job_alert_notifications=False
        )
        self.message_user(request, f'Disabled all notifications for {queryset.count()} users.')

    disable_notifications.short_description = "Disable all notifications"


@admin.register(DashboardActivity)
class DashboardActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'description', 'ip_address', 'created_at')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('user__username', 'user__email', 'description', 'ip_address')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Activity Information', {
            'fields': ('user', 'activity_type', 'description')
        }),
        ('Session Details', {
            'fields': ('session_id', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',),
            'description': 'Additional activity data in JSON format'
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        })
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    def has_add_permission(self, request):
        """Disable adding activities through admin"""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable editing activities through admin"""
        return False

    actions = ['delete_old_activities']

    def delete_old_activities(self, request, queryset):
        """Delete activities older than 90 days"""
        from datetime import timedelta
        from django.utils import timezone

        cutoff_date = timezone.now() - timedelta(days=90)
        old_activities = queryset.filter(created_at__lt=cutoff_date)
        count = old_activities.count()
        old_activities.delete()

        self.message_user(request, f'Deleted {count} activities older than 90 days.')

    delete_old_activities.short_description = "Delete activities older than 90 days"


# Admin site customization
admin.site.site_header = "Job Automation Dashboard Admin"
admin.site.site_title = "Dashboard Admin"
admin.site.index_title = "Dashboard Administration"