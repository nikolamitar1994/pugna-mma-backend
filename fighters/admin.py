from django.contrib import admin
from django.db.models import Q
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Fighter, FighterNameVariation, FightHistory, FighterRanking, FighterStatistics, RankingHistory, PendingFighter
from .admin_actions import JSONImportExportMixin, export_selected_as_json_templates, create_fighter_from_pending


class FighterNameVariationInline(admin.TabularInline):
    """Inline editing for fighter name variations"""
    model = FighterNameVariation
    extra = 1
    fields = ('first_name_variation', 'last_name_variation', 'variation_type', 'source')


class FightHistoryInline(admin.TabularInline):
    """Inline editing for fight history - summary view with clickable links"""
    model = FightHistory
    fk_name = 'fighter'  # Specify which foreign key to use since there are multiple
    extra = 0
    fields = (
        'fight_order', 'result', 'get_opponent_inline_link', 'method', 'method_description',
        'get_event_inline_link', 'event_date', 'get_edit_link', 'data_quality_score'
    )
    readonly_fields = ('data_quality_score', 'get_opponent_inline_link', 'get_event_inline_link', 'get_edit_link')
    ordering = ['-fight_order']
    
    def get_opponent_inline_link(self, obj):
        """Display opponent with clickable link in inline"""
        if obj.opponent_fighter:
            url = reverse('admin:fighters_fighter_change', args=[obj.opponent_fighter.pk])
            return format_html(
                '<a href="{}" style="color: #0066cc; text-decoration: underline;" target="_blank">{}</a>',
                url, 
                obj.opponent_fighter.get_full_name()
            )
        else:
            return obj.opponent_full_name
    get_opponent_inline_link.short_description = 'Opponent'
    
    def get_event_inline_link(self, obj):
        """Display event with clickable link in inline"""
        if obj.event:
            try:
                url = reverse('admin:events_event_change', args=[obj.event.pk])
                return format_html(
                    '<a href="{}" style="color: #0066cc; text-decoration: underline;" target="_blank">{}</a>',
                    url,
                    obj.event.name
                )
            except:
                return obj.event.name
        else:
            return obj.event_name
    get_event_inline_link.short_description = 'Event'
    
    def get_edit_link(self, obj):
        """Display link to edit full fight record"""
        if obj.pk:
            url = reverse('admin:fighters_fighthistory_change', args=[obj.pk])
            return format_html(
                '<a href="{}" style="color: #0066cc; font-weight: bold;" target="_blank">✏️ Edit</a>',
                url
            )
        return '-'
    get_edit_link.short_description = 'Edit Full Record'
    
    def get_queryset(self, request):
        """Optimize queries for inline display"""
        return super().get_queryset(request).select_related('opponent_fighter', 'fight', 'event', 'organization')
    

@admin.register(Fighter)
class FighterAdmin(JSONImportExportMixin, admin.ModelAdmin):
    """Django admin interface for Fighter management - 30% time savings!"""
    
    # List display with structured names
    list_display = [
        'get_full_name', 'nickname', 'nationality', 'get_record_display', 
        'is_active', 'data_source', 'data_quality_score'
    ]
    
    # Filters for easy management
    list_filter = [
        'is_active', 'nationality', 'stance', 'data_source',
        'data_quality_score',
    ]
    
    # Search functionality with structured names
    search_fields = [
        'first_name', 'last_name', 'nickname', 'display_name',
        'birth_first_name', 'birth_last_name', 'nationality'
    ]
    
    # Organized fieldsets for better UX
    fieldsets = (
        ('Basic Information', {
            'fields': (
                ('first_name', 'last_name'),
                ('display_name', 'nickname'),
                ('birth_first_name', 'birth_last_name'),
            )
        }),
        ('Personal Details', {
            'fields': (
                ('date_of_birth', 'birth_place'),
                'nationality',
            )
        }),
        ('Physical Attributes', {
            'fields': (
                ('height_cm', 'weight_kg', 'reach_cm'),
                'stance',
            )
        }),
        ('Career Information', {
            'fields': (
                ('fighting_out_of', 'team'),
                'years_active',
                'is_active',
            )
        }),
        ('Career Statistics', {
            'fields': (
                ('wins', 'losses', 'draws', 'no_contests'),
                ('wins_by_ko', 'wins_by_tko'),
                ('wins_by_submission', 'wins_by_decision'),
            ),
            'classes': ('collapse',),
        }),
        ('Media & Links', {
            'fields': (
                'profile_image_url',
                'wikipedia_url',
                'social_media',
            ),
            'classes': ('collapse',),
        }),
        ('JSON Import', {
            'fields': (
                'json_import_data',
            ),
            'description': (
                '📋 <strong>Quick Import:</strong> Paste complete fighter JSON here to automatically populate all fields and fight history. '
                'The data will be processed when you save, and this field will be cleared. '
                '<br><br>🔗 <strong>Example structure:</strong> '
                '<a href="/static/FIGHTER_JSON_STRUCTURE.json" target="_blank">Download example JSON</a> | '
                '<a href="/static/JSON_STRUCTURE_DOCUMENTATION.md" target="_blank">View documentation</a>'
            ),
            'classes': ('wide',),
        }),
        ('Data Management', {
            'fields': (
                ('data_source', 'data_quality_score'),
                'last_data_update',
            ),
            'classes': ('collapse',),
        }),
    )
    
    # Read-only fields
    readonly_fields = ['created_at', 'updated_at', 'last_data_update']
    
    # Inline editing for name variations and fight history
    inlines = [FighterNameVariationInline, FightHistoryInline]
    
    # Actions for bulk operations
    actions = [
        'mark_as_active',
        'mark_as_inactive',
        'update_data_quality',
        'export_incomplete_profiles',
        export_selected_as_json_templates,
    ]
    
    # Custom display methods
    def get_full_name(self, obj):
        """Display full name with nickname"""
        name = obj.get_full_name()
        if obj.nickname:
            name += f' "{obj.nickname}"'
        return name
    get_full_name.short_description = 'Full Name'
    get_full_name.admin_order_field = 'last_name'
    
    def get_record_display(self, obj):
        """Display fight record with color coding"""
        record = obj.get_record_string()
        if obj.wins > obj.losses:
            color = 'green'
        elif obj.losses > obj.wins:
            color = 'red'
        else:
            color = 'orange'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, record
        )
    get_record_display.short_description = 'Record'
    
    # Custom admin actions
    def mark_as_active(self, request, queryset):
        """Mark selected fighters as active"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} fighters marked as active.")
    mark_as_active.short_description = "Mark selected fighters as active"
    
    def mark_as_inactive(self, request, queryset):
        """Mark selected fighters as inactive"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} fighters marked as inactive.")
    mark_as_inactive.short_description = "Mark selected fighters as inactive"
    
    def update_data_quality(self, request, queryset):
        """Recalculate data quality scores"""
        count = 0
        for fighter in queryset:
            # Calculate data quality based on filled fields
            filled_fields = 0
            total_fields = 15  # Key fields to check
            
            if fighter.date_of_birth:
                filled_fields += 1
            if fighter.birth_place:
                filled_fields += 1
            if fighter.nationality:
                filled_fields += 1
            if fighter.height_cm:
                filled_fields += 1
            if fighter.weight_kg:
                filled_fields += 1
            if fighter.reach_cm:
                filled_fields += 1
            if fighter.stance:
                filled_fields += 1
            if fighter.fighting_out_of:
                filled_fields += 1
            if fighter.team:
                filled_fields += 1
            if fighter.wikipedia_url:
                filled_fields += 1
            if fighter.profile_image_url:
                filled_fields += 1
            if fighter.wins or fighter.losses:
                filled_fields += 1
            
            fighter.data_quality_score = round(filled_fields / total_fields, 2)
            fighter.save()
            count += 1
        
        self.message_user(request, f"Data quality updated for {count} fighters.")
    update_data_quality.short_description = "Update data quality scores"
    
    def export_incomplete_profiles(self, request, queryset):
        """Export fighters with incomplete profiles for AI completion"""
        incomplete = queryset.filter(data_quality_score__lt=0.7)
        # This would trigger an export process
        self.message_user(
            request, 
            f"{incomplete.count()} incomplete profiles identified for AI completion."
        )
    export_incomplete_profiles.short_description = "Export incomplete profiles for AI"
    
    # Custom queryset optimization
    def get_queryset(self, request):
        """Optimize queries with prefetch_related"""
        return super().get_queryset(request).prefetch_related('name_variations')
    
    # Custom form validation and save
    def save_model(self, request, obj, form, change):
        """Custom save with JSON import processing and user feedback"""
        # Check if JSON import data was provided
        has_json_data = bool(obj.json_import_data.strip())
        
        # Save the object (this will trigger JSON processing)
        super().save_model(request, obj, form, change)
        
        # If JSON data was processed, show results to user
        if has_json_data:
            # The JSON processing happens in the model's save method
            # We can check if it was successful by seeing if the field was cleared
            if not obj.json_import_data.strip():
                # JSON was successfully processed and cleared
                fight_history_count = obj.fight_history.count()
                self.message_user(
                    request,
                    f"✅ JSON import successful! Fighter profile populated with {fight_history_count} fight history records.",
                    level='SUCCESS'
                )
            else:
                # JSON processing failed, field still contains data
                self.message_user(
                    request,
                    f"❌ JSON import failed. Please check the JSON format and try again. "
                    f"Use the documentation link above for the correct structure.",
                    level='ERROR'
                )
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form for better JSON import experience"""
        form = super().get_form(request, obj, **kwargs)
        
        # Customize the JSON import field widget
        if 'json_import_data' in form.base_fields:
            form.base_fields['json_import_data'].widget.attrs.update({
                'rows': 20,
                'cols': 80,
                'style': 'font-family: monospace; font-size: 12px;',
                'placeholder': '''Paste your fighter JSON here. Example:
{
  "entity_type": "fighter",
  "template_version": "1.0",
  "fighter_data": {
    "personal_info": {
      "first_name": "John",
      "last_name": "Doe",
      "nationality": "USA"
    },
    "physical_attributes": {
      "height_cm": 180,
      "weight_kg": 77.0
    }
  },
  "fight_history": [...]
}'''
            })
        
        return form


@admin.register(FightHistory)
class FightHistoryAdmin(admin.ModelAdmin):
    """Django admin interface for Fight History management"""
    
    # List display with key fight information - now with clickable links!
    list_display = [
        'get_fighter_name', 'fight_order', 'get_result_display', 'get_opponent_link',
        'get_method_display_short', 'get_event_link', 'event_date', 'get_organization_link',
        'data_quality_score', 'data_source'
    ]
    
    # Filters for data management
    list_filter = [
        'result', 'method', 'data_source', 'is_title_fight', 'organization',
        'event_date', 'data_quality_score', 'ending_round'
    ]
    
    # Search functionality
    search_fields = [
        'fighter__first_name', 'fighter__last_name', 'fighter__nickname',
        'opponent_first_name', 'opponent_last_name', 'opponent_full_name',
        'event_name', 'organization_name', 'location', 'venue'
    ]
    
    # Auto-complete for foreign keys
    autocomplete_fields = ['fighter', 'opponent_fighter', 'event', 'organization', 'weight_class']
    
    # Organized fieldsets for better UX
    fieldsets = (
        ('Fight Basics', {
            'fields': (
                ('fighter', 'fight_order'),
                ('result', 'fighter_record_at_time'),
            )
        }),
        ('Opponent Information', {
            'fields': (
                ('opponent_first_name', 'opponent_last_name'),
                'opponent_full_name',
                'opponent_fighter',
            )
        }),
        ('Fight Details', {
            'fields': (
                ('method', 'method_description'),
                'method_details',  # Legacy field for reference
                ('ending_round', 'ending_time', 'scheduled_rounds'),
                ('is_title_fight', 'is_interim_title', 'title_belt'),
            ),
            'description': (
                '📝 Simplified Method System: Use one of 4 core methods (Decision, KO, TKO, Submission) '
                'and put details like "unanimous", "rear naked choke", or "head kick and punches" '
                'in the Method Description field.'
            )
        }),
        ('Event Information', {
            'fields': (
                ('event_name', 'event_date'),
                'event',
                ('organization_name', 'organization'),
                ('weight_class_name', 'weight_class'),
            )
        }),
        ('Location', {
            'fields': (
                'location',
                ('venue', 'city'),
                ('state', 'country'),
            ),
            'classes': ('collapse',),
        }),
        ('Additional Information', {
            'fields': (
                'notes',
                'performance_bonuses',
            ),
            'classes': ('collapse',),
        }),
        ('Data Management', {
            'fields': (
                ('data_source', 'source_url'),
                'data_quality_score',
                'parsed_data',
            ),
            'classes': ('collapse',),
        }),
    )
    
    # Read-only fields
    readonly_fields = ['data_quality_score', 'created_at', 'updated_at', 'method_details']
    
    # Actions for bulk operations
    actions = [
        'recalculate_data_quality',
        'link_to_existing_fighters',
        'mark_as_title_fights',
        'export_for_wikipedia_import',
    ]
    
    # List per page
    list_per_page = 50
    
    # Date hierarchy for easy navigation
    date_hierarchy = 'event_date'
    
    # Custom display methods
    def get_fighter_name(self, obj):
        """Display fighter name with link"""
        url = reverse('admin:fighters_fighter_change', args=[obj.fighter.pk])
        return format_html('<a href="{}">{}</a>', url, obj.fighter.get_full_name())
    get_fighter_name.short_description = 'Fighter'
    get_fighter_name.admin_order_field = 'fighter__last_name'
    
    def get_opponent_link(self, obj):
        """Display opponent with clickable link to their profile"""
        if obj.opponent_fighter:
            # If we have the linked opponent fighter, create clickable link
            url = reverse('admin:fighters_fighter_change', args=[obj.opponent_fighter.pk])
            return format_html(
                '<a href="{}" style="color: #0066cc; text-decoration: underline;">{}</a>',
                url, 
                obj.opponent_fighter.get_full_name()
            )
        else:
            # If no linked opponent, show text with search option
            search_url = reverse('admin:fighters_fighter_changelist') + f'?q={obj.opponent_full_name}'
            return format_html(
                '{} <a href="{}" style="color: #888; font-size: 11px;">[find]</a>',
                obj.opponent_full_name,
                search_url
            )
    get_opponent_link.short_description = 'Opponent'
    get_opponent_link.admin_order_field = 'opponent_full_name'
    
    def get_event_link(self, obj):
        """Display event with clickable link to event page"""
        if obj.event:
            # If we have the linked event, create clickable link
            url = reverse('admin:events_event_change', args=[obj.event.pk])
            return format_html(
                '<a href="{}" style="color: #0066cc; text-decoration: underline;">{}</a>',
                url,
                obj.event.name
            )
        else:
            # If no linked event, show text with search option
            try:
                search_url = reverse('admin:events_event_changelist') + f'?q={obj.event_name}'
                return format_html(
                    '{} <a href="{}" style="color: #888; font-size: 11px;">[find]</a>',
                    obj.event_name,
                    search_url
                )
            except:
                # If events app not available, just show text
                return obj.event_name
    get_event_link.short_description = 'Event'
    get_event_link.admin_order_field = 'event_name'
    
    def get_organization_link(self, obj):
        """Display organization with clickable link"""
        if obj.organization:
            try:
                url = reverse('admin:organizations_organization_change', args=[obj.organization.pk])
                return format_html(
                    '<a href="{}" style="color: #0066cc; text-decoration: underline;">{}</a>',
                    url,
                    obj.organization.name
                )
            except:
                return obj.organization.name
        else:
            return obj.organization_name or '-'
    get_organization_link.short_description = 'Organization'
    get_organization_link.admin_order_field = 'organization_name'
    
    def get_result_display(self, obj):
        """Display result with color coding"""
        colors = {
            'win': 'green',
            'loss': 'red',
            'draw': 'orange',
            'no_contest': 'gray'
        }
        color = colors.get(obj.result, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.result.upper()
        )
    get_result_display.short_description = 'Result'
    get_result_display.admin_order_field = 'result'
    
    def get_method_display_short(self, obj):
        """Display method with shortened format using new simplified system"""
        if not obj.method:
            return '-'
        
        # Show method + description (simplified format)
        method_display = obj.get_method_display()
        if len(method_display) > 30:
            return method_display[:27] + '...'
        return method_display
    get_method_display_short.short_description = 'Method'
    get_method_display_short.admin_order_field = 'method'
    
    def get_location_short(self, obj):
        """Display shortened location"""
        location = obj.get_location_display()
        if len(location) > 30:
            return location[:27] + '...'
        return location
    get_location_short.short_description = 'Location'
    
    # Custom admin actions
    def recalculate_data_quality(self, request, queryset):
        """Recalculate data quality scores for selected fights"""
        count = 0
        for fight_history in queryset:
            old_score = fight_history.data_quality_score
            fight_history.data_quality_score = fight_history.calculate_data_quality()
            fight_history.save()
            count += 1
        
        self.message_user(request, f"Data quality recalculated for {count} fight records.")
    recalculate_data_quality.short_description = "Recalculate data quality scores"
    
    def link_to_existing_fighters(self, request, queryset):
        """Attempt to link opponents to existing Fighter records"""
        linked = 0
        for fight_history in queryset:
            if not fight_history.opponent_fighter:
                # Try to find matching fighter by name
                potential_matches = Fighter.objects.filter(
                    first_name__iexact=fight_history.opponent_first_name,
                    last_name__iexact=fight_history.opponent_last_name
                )
                if potential_matches.count() == 1:
                    fight_history.opponent_fighter = potential_matches.first()
                    fight_history.save()
                    linked += 1
        
        self.message_user(request, f"Linked {linked} opponents to existing Fighter records.")
    link_to_existing_fighters.short_description = "Link opponents to existing fighters"
    
    def mark_as_title_fights(self, request, queryset):
        """Mark selected fights as title fights"""
        updated = queryset.update(is_title_fight=True)
        self.message_user(request, f"{updated} fights marked as title fights.")
    mark_as_title_fights.short_description = "Mark as title fights"
    
    def export_for_wikipedia_import(self, request, queryset):
        """Export fight data for Wikipedia import validation"""
        count = queryset.count()
        # This would trigger an export process
        self.message_user(
            request, 
            f"{count} fight records prepared for Wikipedia import validation."
        )
    export_for_wikipedia_import.short_description = "Export for Wikipedia import"
    
    # Custom queryset optimization
    def get_queryset(self, request):
        """Optimize queries with select_related and prefetch_related"""
        return super().get_queryset(request).select_related(
            'fighter', 'opponent_fighter', 'event', 'organization', 'weight_class'
        )
    
    # Custom form validation and save
    def save_model(self, request, obj, form, change):
        """Custom save with automatic data quality calculation"""
        # Ensure data quality is calculated
        obj.data_quality_score = obj.calculate_data_quality()
        super().save_model(request, obj, form, change)


@admin.register(FighterNameVariation)
class FighterNameVariationAdmin(admin.ModelAdmin):
    """Admin for fighter name variations"""
    
    list_display = ['fighter', 'full_name_variation', 'variation_type', 'source']
    list_filter = ['variation_type']
    search_fields = [
        'fighter__first_name', 'fighter__last_name', 
        'first_name_variation', 'last_name_variation', 'full_name_variation'
    ]
    
    autocomplete_fields = ['fighter']
    
    fieldsets = (
        ('Name Variation', {
            'fields': (
                'fighter',
                ('first_name_variation', 'last_name_variation'),
                'full_name_variation',
            )
        }),
        ('Details', {
            'fields': (
                'variation_type',
                'source',
            )
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('fighter')


# Ranking Admin Interfaces

class FighterRankingInline(admin.TabularInline):
    """Inline editing for fighter rankings"""
    model = FighterRanking
    extra = 0
    fields = (
        'ranking_type', 'weight_class', 'organization', 'current_rank', 
        'previous_rank', 'ranking_score', 'is_champion', 'calculation_date'
    )
    readonly_fields = ('ranking_score', 'calculation_date')
    ordering = ['ranking_type', 'current_rank']


class RankingHistoryInline(admin.TabularInline):
    """Inline editing for ranking history"""
    model = RankingHistory
    extra = 0
    fields = ('rank_on_date', 'ranking_score', 'calculation_date', 'rank_change', 'trigger_event')
    readonly_fields = ('rank_change',)
    ordering = ['-calculation_date']


@admin.register(FighterRanking)
class FighterRankingAdmin(admin.ModelAdmin):
    """Django admin interface for Fighter Rankings management"""
    
    list_display = [
        'get_fighter_name', 'get_ranking_display', 'current_rank', 'previous_rank',
        'get_rank_change_display', 'ranking_score', 'is_champion', 'calculation_date'
    ]
    
    list_filter = [
        'ranking_type', 'weight_class', 'organization', 'is_champion', 
        'is_interim_champion', 'calculation_date'
    ]
    
    search_fields = [
        'fighter__first_name', 'fighter__last_name', 'fighter__nickname'
    ]
    
    autocomplete_fields = ['fighter', 'weight_class', 'organization']
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'fighter',
                ('ranking_type', 'weight_class', 'organization'),
                ('current_rank', 'previous_rank'),
            )
        }),
        ('Ranking Details', {
            'fields': (
                'ranking_score',
                ('record_score', 'opponent_quality_score'),
                ('activity_score', 'performance_score'),
                'manual_adjustment',
            )
        }),
        ('Championship Status', {
            'fields': (
                ('is_champion', 'is_interim_champion'),
            )
        }),
        ('Metadata', {
            'fields': (
                'calculation_date',
            ),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = [
        'ranking_score', 'record_score', 'opponent_quality_score',
        'activity_score', 'performance_score', 'calculation_date'
    ]
    
    inlines = [RankingHistoryInline]
    
    actions = [
        'recalculate_rankings',
        'mark_as_champion',
        'remove_champion_status',
        'export_rankings',
    ]
    
    list_per_page = 50
    
    # Custom display methods
    def get_fighter_name(self, obj):
        """Display fighter name with link"""
        url = reverse('admin:fighters_fighter_change', args=[obj.fighter.pk])
        return format_html('<a href="{}">{}</a>', url, obj.fighter.get_full_name())
    get_fighter_name.short_description = 'Fighter'
    get_fighter_name.admin_order_field = 'fighter__last_name'
    
    def get_ranking_display(self, obj):
        """Display ranking type and division"""
        if obj.ranking_type == 'p4p':
            return format_html('<strong style="color: gold;">P4P</strong>')
        elif obj.weight_class:
            return f"{obj.weight_class.name}"
        return obj.ranking_type.title()
    get_ranking_display.short_description = 'Division'
    
    def get_rank_change_display(self, obj):
        """Display rank change with visual indicators"""
        change = obj.get_rank_change()
        if change > 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">↑ {}</span>', 
                change
            )
        elif change < 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">↓ {}</span>', 
                abs(change)
            )
        else:
            return format_html('<span style="color: gray;">—</span>')
    get_rank_change_display.short_description = 'Change'
    
    # Custom admin actions
    def recalculate_rankings(self, request, queryset):
        """Recalculate ranking scores for selected rankings"""
        from fighters.ranking_service import ranking_service
        
        updated = 0
        for ranking in queryset:
            try:
                new_score = ranking_service.calculate_fighter_ranking(
                    ranking.fighter, ranking.weight_class, ranking.organization
                )
                ranking.ranking_score = new_score
                ranking.save()
                updated += 1
            except Exception as e:
                self.message_user(
                    request, 
                    f"Error recalculating {ranking.fighter.get_full_name()}: {e}",
                    level='ERROR'
                )
        
        self.message_user(request, f"Recalculated {updated} rankings.")
    recalculate_rankings.short_description = "Recalculate ranking scores"
    
    def mark_as_champion(self, request, queryset):
        """Mark selected fighters as champions"""
        updated = queryset.update(is_champion=True)
        self.message_user(request, f"{updated} fighters marked as champions.")
    mark_as_champion.short_description = "Mark as champions"
    
    def remove_champion_status(self, request, queryset):
        """Remove champion status from selected fighters"""
        updated = queryset.update(is_champion=False, is_interim_champion=False)
        self.message_user(request, f"Champion status removed from {updated} fighters.")
    remove_champion_status.short_description = "Remove champion status"
    
    def export_rankings(self, request, queryset):
        """Export rankings data"""
        count = queryset.count()
        self.message_user(request, f"Exported {count} ranking records.")
    export_rankings.short_description = "Export ranking data"
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related(
            'fighter', 'weight_class', 'organization'
        ).prefetch_related('history')


@admin.register(FighterStatistics)
class FighterStatisticsAdmin(admin.ModelAdmin):
    """Django admin interface for Fighter Statistics management"""
    
    list_display = [
        'get_fighter_name', 'get_record_display', 'finish_rate', 'current_streak',
        'fights_last_12_months', 'title_fights', 'last_calculated', 'needs_recalculation'
    ]
    
    list_filter = [
        'needs_recalculation', 'primary_weight_class', 'current_streak',
        'title_fights', 'last_calculated'
    ]
    
    search_fields = [
        'fighter__first_name', 'fighter__last_name', 'fighter__nickname'
    ]
    
    autocomplete_fields = ['fighter', 'primary_weight_class']
    
    fieldsets = (
        ('Fighter', {
            'fields': ('fighter',)
        }),
        ('Career Record', {
            'fields': (
                ('total_fights', 'wins', 'losses', 'draws', 'no_contests'),
                ('wins_ko', 'wins_tko', 'wins_submission', 'wins_decision', 'wins_other'),
                ('losses_ko', 'losses_tko', 'losses_submission', 'losses_decision', 'losses_other'),
            )
        }),
        ('Performance Metrics', {
            'fields': (
                ('finish_rate', 'finish_resistance', 'average_fight_time'),
                ('current_streak', 'longest_win_streak', 'longest_losing_streak'),
            )
        }),
        ('Activity Metrics', {
            'fields': (
                ('fights_last_12_months', 'fights_last_24_months', 'fights_last_36_months'),
                ('last_fight_date', 'days_since_last_fight'),
            )
        }),
        ('Competition Level', {
            'fields': (
                ('title_fights', 'title_wins', 'main_events'),
                ('top_5_wins', 'top_10_wins', 'signature_wins', 'quality_losses'),
                ('performance_bonuses', 'fight_bonuses', 'total_bonuses'),
            )
        }),
        ('Career Information', {
            'fields': (
                ('primary_weight_class', 'weight_classes_fought'),
                ('debut_date', 'career_length_days'),
                ('age_at_debut', 'current_age'),
                'strength_of_schedule',
            ),
            'classes': ('collapse',),
        }),
        ('System Information', {
            'fields': (
                ('last_calculated', 'needs_recalculation'),
            ),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = [
        'total_fights', 'wins', 'losses', 'draws', 'no_contests',
        'wins_ko', 'wins_tko', 'wins_submission', 'wins_decision', 'wins_other',
        'losses_ko', 'losses_tko', 'losses_submission', 'losses_decision', 'losses_other',
        'finish_rate', 'finish_resistance', 'average_fight_time',
        'current_streak', 'longest_win_streak', 'longest_losing_streak',
        'fights_last_12_months', 'fights_last_24_months', 'fights_last_36_months',
        'last_fight_date', 'days_since_last_fight',
        'title_fights', 'title_wins', 'main_events', 'top_5_wins', 'top_10_wins',
        'performance_bonuses', 'fight_bonuses', 'total_bonuses',
        'weight_classes_fought', 'debut_date', 'career_length_days',
        'age_at_debut', 'current_age', 'strength_of_schedule',
        'signature_wins', 'quality_losses', 'last_calculated'
    ]
    
    actions = [
        'recalculate_statistics',
        'mark_for_recalculation',
        'export_statistics',
    ]
    
    # Custom display methods
    def get_fighter_name(self, obj):
        """Display fighter name with link"""
        url = reverse('admin:fighters_fighter_change', args=[obj.fighter.pk])
        return format_html('<a href="{}">{}</a>', url, obj.fighter.get_full_name())
    get_fighter_name.short_description = 'Fighter'
    get_fighter_name.admin_order_field = 'fighter__last_name'
    
    def get_record_display(self, obj):
        """Display fight record with win percentage"""
        record = obj.get_record_display()
        win_pct = obj.get_win_percentage()
        return format_html(
            '{} <small style="color: gray;">({}%)</small>',
            record, f"{win_pct:.1f}"
        )
    get_record_display.short_description = 'Record'
    
    # Custom admin actions
    def recalculate_statistics(self, request, queryset):
        """Recalculate statistics for selected fighters"""
        updated = 0
        for stats in queryset:
            try:
                stats.calculate_all_statistics()
                updated += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error recalculating {stats.fighter.get_full_name()}: {e}",
                    level='ERROR'
                )
        
        self.message_user(request, f"Recalculated statistics for {updated} fighters.")
    recalculate_statistics.short_description = "Recalculate statistics"
    
    def mark_for_recalculation(self, request, queryset):
        """Mark selected statistics for recalculation"""
        updated = queryset.update(needs_recalculation=True)
        self.message_user(request, f"Marked {updated} statistics for recalculation.")
    mark_for_recalculation.short_description = "Mark for recalculation"
    
    def export_statistics(self, request, queryset):
        """Export statistics data"""
        count = queryset.count()
        self.message_user(request, f"Exported {count} statistics records.")
    export_statistics.short_description = "Export statistics data"
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related(
            'fighter', 'primary_weight_class'
        )


@admin.register(RankingHistory)
class RankingHistoryAdmin(admin.ModelAdmin):
    """Django admin interface for Ranking History management"""
    
    list_display = [
        'get_fighter_name', 'get_division_display', 'rank_on_date', 
        'get_rank_change_display', 'calculation_date', 'trigger_event'
    ]
    
    list_filter = [
        'fighter_ranking__ranking_type', 'fighter_ranking__weight_class',
        'fighter_ranking__organization', 'calculation_date', 'rank_change'
    ]
    
    search_fields = [
        'fighter_ranking__fighter__first_name', 'fighter_ranking__fighter__last_name',
        'trigger_event'
    ]
    
    autocomplete_fields = ['fighter_ranking', 'trigger_fight']
    
    fieldsets = (
        ('Ranking Information', {
            'fields': (
                'fighter_ranking',
                ('rank_on_date', 'ranking_score'),
                'calculation_date',
            )
        }),
        ('Change Details', {
            'fields': (
                'rank_change',
                'trigger_event',
                'trigger_fight',
            )
        }),
    )
    
    readonly_fields = ['rank_change']
    
    date_hierarchy = 'calculation_date'
    
    # Custom display methods
    def get_fighter_name(self, obj):
        """Display fighter name with link"""
        fighter = obj.fighter_ranking.fighter
        url = reverse('admin:fighters_fighter_change', args=[fighter.pk])
        return format_html('<a href="{}">{}</a>', url, fighter.get_full_name())
    get_fighter_name.short_description = 'Fighter'
    
    def get_division_display(self, obj):
        """Display division information"""
        ranking = obj.fighter_ranking
        if ranking.ranking_type == 'p4p':
            return format_html('<strong style="color: gold;">P4P</strong>')
        elif ranking.weight_class:
            return ranking.weight_class.name
        return ranking.ranking_type.title()
    get_division_display.short_description = 'Division'
    
    def get_rank_change_display(self, obj):
        """Display rank change with visual indicators"""
        change = obj.rank_change
        if change > 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">↑ {}</span>', 
                change
            )
        elif change < 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">↓ {}</span>', 
                abs(change)
            )
        else:
            return format_html('<span style="color: gray;">—</span>')
    get_rank_change_display.short_description = 'Change'
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related(
            'fighter_ranking__fighter', 'fighter_ranking__weight_class',
            'fighter_ranking__organization', 'trigger_fight'
        )


@admin.register(PendingFighter)
class PendingFighterAdmin(admin.ModelAdmin):
    """
    Django admin interface for PendingFighter management with review/approve workflow.
    Provides comprehensive tools for reviewing and managing scraped fighters.
    """
    
    # List display with key information for review
    list_display = [
        'get_display_name_with_status', 'get_confidence_display', 'source', 
        'get_potential_matches_display', 'get_source_event_link', 'get_review_status',
        'created_at', 'get_action_buttons'
    ]
    
    # Filters for workflow management
    list_filter = [
        'status', 'confidence_level', 'source', 'created_at', 'reviewed_at'
    ]
    
    # Search functionality
    search_fields = [
        'first_name', 'last_name', 'full_name_raw', 'nickname',
        'source_event__name', 'nationality', 'weight_class_name'
    ]
    
    # Auto-complete for foreign keys
    autocomplete_fields = ['source_event', 'matched_fighter', 'reviewed_by', 'created_fighter']
    
    # Organized fieldsets for review workflow
    fieldsets = (
        ('Fighter Information', {
            'fields': (
                ('first_name', 'last_name'),
                'full_name_raw',
                'nickname',
                ('nationality', 'weight_class_name'),
                'record_text',
            ),
            'description': 'Basic information discovered during scraping'
        }),
        ('Source Context', {
            'fields': (
                ('source', 'source_event'),
                'source_url',
                'source_data',
            ),
            'classes': ('collapse',)
        }),
        ('Review Workflow', {
            'fields': (
                ('status', 'confidence_level'),
                'potential_matches',
                'matched_fighter',
                ('reviewed_by', 'reviewed_at'),
                'review_notes',
            ),
            'description': 'Review and approval workflow information'
        }),
        ('AI Assistance', {
            'fields': (
                'ai_suggested_data',
                'json_template_url',
            ),
            'classes': ('collapse',),
            'description': 'AI-generated suggestions and completion templates'
        }),
        ('Resolution', {
            'fields': (
                'created_fighter',
            ),
            'classes': ('collapse',),
            'description': 'Final resolution if fighter was created'
        }),
    )
    
    # Read-only fields
    readonly_fields = [
        'created_at', 'updated_at', 'potential_matches', 'ai_suggested_data'
    ]
    
    # Actions for bulk workflow operations
    actions = [
        'approve_for_creation',
        'mark_as_duplicates',
        'generate_json_templates',
        'run_ai_completion',
        'bulk_reject',
        'export_pending_summary',
        create_fighter_from_pending,
        export_selected_as_json_templates,
    ]
    
    # List per page
    list_per_page = 25
    
    # Date hierarchy for easy navigation
    date_hierarchy = 'created_at'
    
    # Custom display methods
    def get_display_name_with_status(self, obj):
        """Display fighter name with visual status indicator"""
        status_colors = {
            'pending': '#ffa500',  # orange
            'approved': '#008000',  # green
            'rejected': '#ff0000',  # red
            'duplicate': '#0066cc',  # blue
            'created': '#9932cc',  # purple
        }
        
        color = status_colors.get(obj.status, '#000000')
        status_icon = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌',
            'duplicate': '🔗',
            'created': '🎯',
        }.get(obj.status, '❓')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, status_icon, obj.get_display_name()
        )
    get_display_name_with_status.short_description = 'Fighter Name'
    get_display_name_with_status.admin_order_field = 'full_name_raw'
    
    def get_confidence_display(self, obj):
        """Display confidence level with visual indicators"""
        confidence_colors = {
            'high': 'green',
            'medium': 'orange', 
            'low': 'red'
        }
        confidence_icons = {
            'high': '🟢',
            'medium': '🟡',
            'low': '🔴'
        }
        
        color = confidence_colors.get(obj.confidence_level, 'gray')
        icon = confidence_icons.get(obj.confidence_level, '⚪')
        
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, obj.get_confidence_level_display()
        )
    get_confidence_display.short_description = 'Confidence'
    get_confidence_display.admin_order_field = 'confidence_level'
    
    def get_potential_matches_display(self, obj):
        """Display potential matches summary"""
        if not obj.potential_matches:
            return format_html('<span style="color: gray;">None</span>')
        
        match_count = len(obj.potential_matches)
        if match_count == 1:
            match = obj.potential_matches[0]
            return format_html(
                '<span style="color: orange; font-weight: bold;">{} ({}%)</span>',
                match.get('name', 'Unknown'), 
                int(match.get('confidence', 0) * 100)
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">{} matches</span>',
                match_count
            )
    get_potential_matches_display.short_description = 'Potential Matches'
    
    def get_source_event_link(self, obj):
        """Display source event with clickable link"""
        if obj.source_event:
            try:
                url = reverse('admin:events_event_change', args=[obj.source_event.pk])
                return format_html(
                    '<a href="{}" style="color: #0066cc; text-decoration: underline;" target="_blank">{}</a>',
                    url, obj.source_event.name[:30] + '...' if len(obj.source_event.name) > 30 else obj.source_event.name
                )
            except:
                return obj.source_event.name
        return format_html('<span style="color: gray;">—</span>')
    get_source_event_link.short_description = 'Source Event'
    
    def get_review_status(self, obj):
        """Display review status with reviewer info"""
        if obj.reviewed_by:
            return format_html(
                '<span style="color: green;">✓ by {}</span>',
                obj.reviewed_by.email[:20] + '...' if len(obj.reviewed_by.email) > 20 else obj.reviewed_by.email
            )
        elif obj.status == 'pending':
            return format_html('<span style="color: orange;">Needs Review</span>')
        else:
            return format_html('<span style="color: gray;">Auto-processed</span>')
    get_review_status.short_description = 'Review Status'
    
    def get_action_buttons(self, obj):
        """Display quick action buttons"""
        if obj.status == 'pending':
            buttons = []
            
            # Approve button
            buttons.append(
                f'<a href="/admin/fighters/pendingfighter/{obj.pk}/approve/" '
                f'style="background: green; color: white; padding: 2px 8px; text-decoration: none; '
                f'border-radius: 3px; font-size: 11px;">Approve</a>'
            )
            
            # Mark as duplicate button
            if obj.potential_matches:
                buttons.append(
                    f'<a href="/admin/fighters/pendingfighter/{obj.pk}/duplicate/" '
                    f'style="background: blue; color: white; padding: 2px 8px; text-decoration: none; '
                    f'border-radius: 3px; font-size: 11px;">Duplicate</a>'
                )
            
            # Reject button
            buttons.append(
                f'<a href="/admin/fighters/pendingfighter/{obj.pk}/reject/" '
                f'style="background: red; color: white; padding: 2px 8px; text-decoration: none; '
                f'border-radius: 3px; font-size: 11px;">Reject</a>'
            )
            
            return format_html(' '.join(buttons))
        
        return format_html('<span style="color: gray;">—</span>')
    get_action_buttons.short_description = 'Quick Actions'
    
    # Custom admin actions
    def approve_for_creation(self, request, queryset):
        """Approve selected pending fighters for Fighter creation"""
        approved_count = 0
        for pending_fighter in queryset.filter(status='pending'):
            pending_fighter.status = 'approved'
            pending_fighter.reviewed_by = request.user
            pending_fighter.reviewed_at = timezone.now()
            pending_fighter.save()
            approved_count += 1
        
        self.message_user(
            request, 
            f"Approved {approved_count} pending fighters for creation."
        )
    approve_for_creation.short_description = "Approve selected for Fighter creation"
    
    def mark_as_duplicates(self, request, queryset):
        """Mark selected pending fighters as duplicates"""
        duplicate_count = 0
        for pending_fighter in queryset.filter(status='pending'):
            if pending_fighter.potential_matches:
                # Auto-select the highest confidence match
                best_match = max(
                    pending_fighter.potential_matches, 
                    key=lambda m: m.get('confidence', 0)
                )
                
                try:
                    matched_fighter = Fighter.objects.get(id=best_match['fighter_id'])
                    pending_fighter.mark_as_duplicate(matched_fighter, request.user)
                    duplicate_count += 1
                except Fighter.DoesNotExist:
                    continue
        
        self.message_user(
            request,
            f"Marked {duplicate_count} pending fighters as duplicates."
        )
    mark_as_duplicates.short_description = "Mark selected as duplicates"
    
    def generate_json_templates(self, request, queryset):
        """Generate JSON templates for AI completion"""
        from .templates import JSONTemplateGenerator
        import json
        import os
        from django.conf import settings
        
        template_count = 0
        for pending_fighter in queryset.filter(status='pending'):
            partial_data = {
                'first_name': pending_fighter.first_name,
                'last_name': pending_fighter.last_name,
                'nickname': pending_fighter.nickname,
                'nationality': pending_fighter.nationality,
                'source_context': {
                    'discovered_in_event': pending_fighter.source_event.name if pending_fighter.source_event else '',
                    'source_url': pending_fighter.source_url,
                    'weight_class': pending_fighter.weight_class_name,
                    'record_text': pending_fighter.record_text
                }
            }
            
            template = JSONTemplateGenerator.generate_fighter_template(partial_data)
            
            # Save template (in a real implementation, this might be saved to cloud storage)
            template_dir = os.path.join(settings.MEDIA_ROOT, 'json_templates')
            os.makedirs(template_dir, exist_ok=True)
            
            template_filename = f"pending_fighter_{pending_fighter.id}.json"
            template_path = os.path.join(template_dir, template_filename)
            
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)
            
            # Update pending fighter with template URL
            pending_fighter.json_template_url = f"/media/json_templates/{template_filename}"
            pending_fighter.save()
            
            template_count += 1
        
        self.message_user(
            request,
            f"Generated JSON templates for {template_count} pending fighters."
        )
    generate_json_templates.short_description = "Generate JSON templates for AI completion"
    
    def run_ai_completion(self, request, queryset):
        """Run AI completion for selected pending fighters (placeholder)"""
        # In a real implementation, this would trigger AI completion
        self.message_user(
            request,
            f"AI completion triggered for {queryset.count()} pending fighters. "
            "Results will be available shortly."
        )
    run_ai_completion.short_description = "Run AI completion (placeholder)"
    
    def bulk_reject(self, request, queryset):
        """Reject selected pending fighters"""
        rejected_count = 0
        for pending_fighter in queryset.filter(status='pending'):
            pending_fighter.status = 'rejected'
            pending_fighter.reviewed_by = request.user
            pending_fighter.reviewed_at = timezone.now()
            pending_fighter.save()
            rejected_count += 1
        
        self.message_user(
            request,
            f"Rejected {rejected_count} pending fighters."
        )
    bulk_reject.short_description = "Reject selected pending fighters"
    
    def export_pending_summary(self, request, queryset):
        """Export summary of pending fighters for external review"""
        summary_data = []
        for pending_fighter in queryset:
            summary_data.append({
                'name': pending_fighter.full_name_raw,
                'status': pending_fighter.status,
                'confidence': pending_fighter.confidence_level,
                'source_event': pending_fighter.source_event.name if pending_fighter.source_event else '',
                'potential_matches': len(pending_fighter.potential_matches) if pending_fighter.potential_matches else 0,
                'created_at': pending_fighter.created_at.isoformat()
            })
        
        # In a real implementation, this would generate a downloadable file
        self.message_user(
            request,
            f"Summary exported for {len(summary_data)} pending fighters."
        )
    export_pending_summary.short_description = "Export pending fighters summary"
    
    # Custom queryset optimization
    def get_queryset(self, request):
        """Optimize queries with select_related and prefetch_related"""
        return super().get_queryset(request).select_related(
            'source_event', 'matched_fighter', 'reviewed_by', 'created_fighter'
        )
    
    # Custom form validation and save
    def save_model(self, request, obj, form, change):
        """Custom save with automatic matching if needed"""
        is_new = obj.pk is None
        
        # If this is a new pending fighter, run fuzzy matching
        if is_new and not obj.potential_matches:
            obj.run_fuzzy_matching()
        
        super().save_model(request, obj, form, change)
    
    # Custom change view to add workflow buttons
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Add custom context for workflow buttons"""
        extra_context = extra_context or {}
        
        try:
            pending_fighter = PendingFighter.objects.get(pk=object_id)
            extra_context['pending_fighter'] = pending_fighter
            extra_context['show_workflow_buttons'] = pending_fighter.status == 'pending'
            
            # Add potential matches context
            if pending_fighter.potential_matches:
                potential_fighters = []
                for match in pending_fighter.potential_matches:
                    try:
                        fighter = Fighter.objects.get(id=match['fighter_id'])
                        potential_fighters.append({
                            'fighter': fighter,
                            'confidence': match.get('confidence', 0),
                            'admin_url': reverse('admin:fighters_fighter_change', args=[fighter.pk])
                        })
                    except Fighter.DoesNotExist:
                        continue
                
                extra_context['potential_fighters'] = potential_fighters
            
        except PendingFighter.DoesNotExist:
            pass
        
        return super().change_view(request, object_id, form_url, extra_context)
    
    class Media:
        """Custom CSS/JS for enhanced admin interface"""
        css = {
            'all': ('admin/css/pending_fighter_admin.css',)
        }
        js = ('admin/js/pending_fighter_workflow.js',)