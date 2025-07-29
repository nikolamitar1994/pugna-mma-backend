from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, EditorialWorkflowLog, AssignmentNotification


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model"""
    
    list_display = ('email', 'get_full_name', 'is_staff', 'is_active', 'last_active')
    list_filter = ('is_staff', 'is_active', 'groups')
    search_fields = ('email', 'first_name', 'last_name', 'username')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'username', 'bio', 'avatar', 'website')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Settings', {'fields': ('email_notifications',)}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'last_active')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile model"""
    
    list_display = ('user', 'editorial_role', 'articles_authored', 'articles_published', 'last_article_date')
    list_filter = ('editorial_role', 'notify_on_status_change', 'notify_on_comment')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    raw_id_fields = ('user', 'default_category')
    
    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Editorial Role', {'fields': ('editorial_role', 'default_category')}),
        ('Statistics', {'fields': ('articles_authored', 'articles_edited', 'articles_published', 'last_article_date')}),
        ('Notifications', {'fields': ('notify_on_article_assignment', 'notify_on_status_change', 'notify_on_comment')}),
    )
    
    readonly_fields = ('articles_authored', 'articles_edited', 'articles_published', 'last_article_date')


@admin.register(EditorialWorkflowLog)
class EditorialWorkflowLogAdmin(admin.ModelAdmin):
    """Admin configuration for EditorialWorkflowLog model"""
    
    list_display = ('article', 'user', 'action', 'from_status', 'to_status', 'created_at')
    list_filter = ('action', 'from_status', 'to_status', 'created_at')
    search_fields = ('article__title', 'user__email', 'notes')
    raw_id_fields = ('article', 'user')
    
    fieldsets = (
        ('Action', {'fields': ('article', 'user', 'action')}),
        ('Status Change', {'fields': ('from_status', 'to_status')}),
        ('Details', {'fields': ('notes', 'metadata')}),
        ('Timestamp', {'fields': ('created_at',)}),
    )
    
    readonly_fields = ('created_at',)


@admin.register(AssignmentNotification)
class AssignmentNotificationAdmin(admin.ModelAdmin):
    """Admin configuration for AssignmentNotification model"""
    
    list_display = ('title', 'recipient', 'notification_type', 'status', 'email_sent', 'created_at')
    list_filter = ('notification_type', 'status', 'email_sent', 'created_at')
    search_fields = ('title', 'recipient__email', 'article__title')
    raw_id_fields = ('recipient', 'article')
    
    fieldsets = (
        ('Notification', {'fields': ('recipient', 'article', 'notification_type')}),
        ('Content', {'fields': ('title', 'message')}),
        ('Status', {'fields': ('status', 'email_sent', 'email_sent_at', 'read_at')}),
        ('Timestamp', {'fields': ('created_at',)}),
    )
    
    readonly_fields = ('created_at', 'email_sent_at', 'read_at')