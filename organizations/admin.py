from django.contrib import admin
from .models import Organization, WeightClass


class WeightClassInline(admin.TabularInline):
    """Inline editing for weight classes within organizations"""
    model = WeightClass
    extra = 1
    fields = ('name', 'weight_limit_lbs', 'weight_limit_kg', 'gender', 'is_active')


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Admin interface for MMA organizations"""
    
    list_display = ['name', 'abbreviation', 'founded_date', 'headquarters', 'is_active']
    list_filter = ['is_active', 'founded_date']
    search_fields = ['name', 'abbreviation', 'headquarters']
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                ('name', 'abbreviation'),
                'founded_date',
                'headquarters',
            )
        }),
        ('Online Presence', {
            'fields': (
                'website',
                'logo_url',
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
            )
        }),
    )
    
    inlines = [WeightClassInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(WeightClass)
class WeightClassAdmin(admin.ModelAdmin):
    """Admin interface for weight classes"""
    
    list_display = ['name', 'organization', 'weight_limit_lbs', 'weight_limit_kg', 'gender', 'is_active']
    list_filter = ['organization', 'gender', 'is_active']
    search_fields = ['name', 'organization__name']
    
    fieldsets = (
        ('Weight Class Details', {
            'fields': (
                'organization',
                'name',
                ('weight_limit_lbs', 'weight_limit_kg'),
                'gender',
                'is_active',
            )
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization')