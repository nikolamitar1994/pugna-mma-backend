from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Event, Fight, FightParticipant, FightStatistics, 
    RoundStatistics, Scorecard, RoundScore, FightStoryline,
    EventNameVariation
)


class EventNameVariationInline(admin.TabularInline):
    """Inline editing for event name variations"""
    model = EventNameVariation
    extra = 1
    fields = ('name_variation', 'variation_type', 'source')
    

class FightParticipantInline(admin.TabularInline):
    """Inline editing for fight participants"""
    model = FightParticipant
    extra = 2
    max_num = 2
    fields = ('fighter', 'corner', 'result', 'weigh_in_weight', 'purse')
    autocomplete_fields = ['fighter']




class FightInline(admin.StackedInline):
    """Detailed inline editing for individual fights"""
    model = Fight
    extra = 1
    fields = (
        ('fight_order', 'is_main_event', 'is_title_fight'),
        ('weight_class', 'scheduled_rounds'),
        ('status', 'method'),
        ('winner', 'ending_round', 'ending_time'),
        'referee',
    )
    autocomplete_fields = ['weight_class', 'winner']
    classes = ['collapse']  # Collapsed by default since we have the overview


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Admin interface for MMA events"""
    
    list_display = [
        'name', 'organization', 'date', 'location', 'status', 
        'get_fight_count', 'attendance'
    ]
    
    list_filter = [
        'organization', 'status', 'date', 'country'
    ]
    
    search_fields = [
        'name', 'location', 'venue', 'city'
    ]
    
    fieldsets = (
        ('Event Details', {
            'fields': (
                ('organization', 'event_number'),
                'name',
                'date',
                'status',
            )
        }),
        ('Event Name Variations', {
            'fields': ('get_name_variations_info',),
            'description': 'Manage event name variations below to aid in scraping and matching from different sources.',
        }),
        ('Location', {
            'fields': (
                'location',
                ('venue', 'city'),
                ('state', 'country'),
            )
        }),
        ('Fight Card Overview', {
            'fields': (
                'get_fight_card_overview',
            ),
            'classes': ('wide',),
        }),
        ('Event Metrics', {
            'fields': (
                ('attendance', 'gate_revenue'),
                'ppv_buys',
                'broadcast_info',
            ),
            'classes': ('collapse',),
        }),
        ('Media', {
            'fields': (
                'poster_url',
                'wikipedia_url',
            ),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['get_fight_card_overview', 'get_name_variations_info']
    inlines = [EventNameVariationInline, FightInline]
    date_hierarchy = 'date'
    
    def get_fight_card_overview(self, obj=None):
        """Display Wikipedia-style fight card table"""
        if not obj or not obj.pk:
            return "Save event first to view fight card overview"
        
        # Get all fights for this event ordered by fight_order
        fights = obj.fights.all().order_by('fight_order')
        
        if not fights:
            return "No fights scheduled for this event"
        
        # Organize fights by card position
        main_card = []
        prelims = []
        early_prelims = []
        
        for fight in fights:
            if fight.is_main_event or fight.fight_order <= 5:
                main_card.append(fight)
            elif fight.fight_order <= 9:
                prelims.append(fight)
            else:
                early_prelims.append(fight)
        
        def generate_fight_table(fights_list, card_name):
            """Generate Wikipedia-style table for fight card section"""
            if not fights_list:
                return ""
            
            html = f'''
            <h4 style="margin: 20px 0 10px 0; color: #333; border-bottom: 2px solid #333; padding-bottom: 5px;">
                {card_name}
            </h4>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 20px;">
                <thead>
                    <tr style="background: #f0f0f0;">
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Weight class</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;" colspan="3">Result</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Method</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Method Description</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: center;">Round</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: center;">Time</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: center;">Action</th>
                    </tr>
                </thead>
                <tbody>
            '''
            
            for fight in fights_list:
                participants = fight.participants.all()
                
                # Weight class
                weight_class = fight.weight_class.name if fight.weight_class else 'TBA'
                
                # Fighter names and result with clickable links
                if len(participants) >= 2:
                    fighter1 = participants[0].fighter
                    fighter2 = participants[1].fighter
                    
                    # Create clickable links to fighter admin pages
                    fighter1_url = reverse('admin:fighters_fighter_change', args=[fighter1.pk])
                    fighter2_url = reverse('admin:fighters_fighter_change', args=[fighter2.pk])
                    
                    fighter1_link = f'<a href="{fighter1_url}" style="text-decoration: none; color: inherit;">{fighter1.get_full_name()}</a>'
                    fighter2_link = f'<a href="{fighter2_url}" style="text-decoration: none; color: inherit;">{fighter2.get_full_name()}</a>'
                    
                    if fight.winner:
                        if fight.winner == fighter1:
                            winner_cell = f'<strong style="color: green;">{fighter1_link}</strong>'
                            loser_cell = fighter2_link
                            def_cell = 'def.'
                        else:
                            winner_cell = f'<strong style="color: green;">{fighter2_link}</strong>'
                            loser_cell = fighter1_link
                            def_cell = 'def.'
                    else:
                        winner_cell = fighter1_link
                        def_cell = 'vs'
                        loser_cell = fighter2_link
                else:
                    winner_cell = 'TBA'
                    def_cell = 'vs'
                    loser_cell = 'TBA'
                
                # Method and Method Description (separate)
                method = fight.method or '—'
                method_description = (fight.method_details or '—').capitalize() if fight.method_details else '—'
                
                # Round and Time
                round_num = fight.ending_round or '—'
                time = fight.ending_time or '—'
                
                # View fight button
                fight_url = reverse('admin:events_fight_change', args=[fight.pk])
                view_button = f'<a href="{fight_url}" style="background: #0066cc; color: white; padding: 4px 8px; border-radius: 3px; text-decoration: none; font-size: 12px;">View Fight</a>'
                
                html += f'''
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">{weight_class}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{winner_cell}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: center; font-weight: bold;">{def_cell}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{loser_cell}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{method}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{method_description}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{round_num}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{time}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{view_button}</td>
                </tr>
                '''
            
            html += '</tbody></table>'
            return html
        
        # Build complete HTML with all sections
        html = '<div style="margin: 10px 0;">'
        
        if main_card:
            html += generate_fight_table(main_card, "Main Card")
        
        if prelims:
            html += generate_fight_table(prelims, "Preliminary Card")
        
        if early_prelims:
            html += generate_fight_table(early_prelims, "Early Preliminary Card")
        
        html += '</div>'
        
        return format_html(html)
    
    get_fight_card_overview.short_description = 'Fight Card Results'
    
    def get_fight_count(self, obj):
        """Display number of fights on card"""
        count = obj.get_fight_count()
        return format_html(
            '<strong>{}</strong> fights',
            count
        )
    get_fight_count.short_description = 'Fights'
    
    def get_name_variations_info(self, obj=None):
        """Display information about event name variations"""
        if not obj or not obj.pk:
            return "Save event first to add name variations"
        
        variations = obj.name_variations.all()
        
        if not variations:
            return format_html(
                '<div style="padding: 15px; background: #fff3e0; border: 1px solid #ff9800; border-radius: 5px;">'
                '<h4 style="margin: 0 0 10px 0; color: #f57c00;">No Name Variations Yet</h4>'
                '<p style="margin: 0 0 10px 0; color: #666;">Add name variations below to help with event matching during scraping.</p>'
                '<p style="margin: 0; color: #666;"><strong>Examples for "UFC 300":</strong></p>'
                '<ul style="margin: 5px 0 0 20px; color: #666;">'
                '<li>UFC 300</li>'
                '<li>UFC 300: Pereira vs. Hill</li>'
                '<li>UFC 300 - Pereira vs. Hill</li>'
                '</ul>'
                '</div>'
            )
        
        variations_html = '<div style="padding: 15px; background: #e8f5e8; border: 1px solid #4caf50; border-radius: 5px;">'
        variations_html += '<h4 style="margin: 0 0 10px 0; color: #2e7d32;">✅ Event Name Variations</h4>'
        variations_html += '<p style="margin: 0 0 10px 0; color: #666;">These variations will be used when scraping and matching events from different sources:</p>'
        variations_html += '<ul style="margin: 0 0 0 20px;">'
        
        for variation in variations:
            variations_html += f'<li style="margin: 5px 0;"><strong>{variation.name_variation}</strong> <em style="color: #666;">({variation.variation_type})'
            if variation.source:
                variations_html += f' - Source: {variation.source}'
            variations_html += '</em></li>'
        
        variations_html += '</ul>'
        variations_html += '<p style="margin: 10px 0 0 0; color: #666; font-size: 12px;"><em>Add more variations below as needed</em></p>'
        variations_html += '</div>'
        
        return format_html(variations_html)
    get_name_variations_info.short_description = 'Name Variations Overview'


@admin.register(Fight)
class FightAdmin(admin.ModelAdmin):
    """Admin for individual fights - Clean separation like UFCstats.com/MMADecisions.com"""
    
    list_display = [
        'get_fight_display', 'event', 'weight_class', 'status', 
        'is_main_event', 'is_title_fight', 'method', 'get_action_links'
    ]
    
    list_filter = [
        'status', 'is_main_event', 'is_title_fight', 'method',
        ('event__date', admin.DateFieldListFilter),
        'event__organization',
    ]
    
    search_fields = [
        'event__name', 'participants__fighter__first_name', 
        'participants__fighter__last_name', 'method', 'referee'
    ]
    
    fieldsets = (
        ('Fight Setup', {
            'fields': (
                ('event', 'fight_order'),
                ('weight_class', 'scheduled_rounds'),
                ('is_main_event', 'is_title_fight', 'is_interim_title'),
            )
        }),
        ('Fight Outcome', {
            'fields': (
                ('status', 'winner'),
                ('method', 'method_details'),
                ('ending_round', 'ending_time'),
                'referee',
            )
        }),
        ('Fight Storyline (Editorial Content)', {
            'fields': (
                'get_storyline_section',
            ),
            'classes': ('wide',),
        }),
        ('Navigate to Detailed Pages', {
            'fields': (
                'get_navigation_links',
            ),
            'classes': ('wide',),
        }),
        ('Bonuses & Notes', {
            'fields': (
                'performance_bonuses',
                'notes',
            ),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['get_navigation_links', 'get_storyline_section']
    inlines = [FightParticipantInline]
    autocomplete_fields = ['event', 'weight_class', 'winner']
    
    def get_fight_display(self, obj):
        """Display fight matchup"""
        return str(obj)
    get_fight_display.short_description = 'Fight'
    
    def get_action_links(self, obj):
        """Action links for statistics and decisions"""
        if not obj.pk:
            return "-"
            
        links = []
        
        # Statistics link
        if hasattr(obj, 'statistics') and obj.statistics:
            stats_url = reverse('admin:events_fightstatistics_change', args=[obj.statistics.pk])
            links.append(f'<a href="{stats_url}" target="_blank" style="color: #0066cc;">📊 Statistics</a>')
        else:
            stats_url = reverse('admin:events_fightstatistics_add') + f'?fight={obj.pk}'
            links.append(f'<a href="{stats_url}" target="_blank" style="color: #666;">➕ Add Stats</a>')
        
        # Decisions link - Single consolidated link
        scorecards_count = obj.scorecards.count()
        if scorecards_count > 0:
            # Use the first scorecard as the link (it will show all judges)
            first_scorecard = obj.scorecards.first()
            decisions_url = reverse('admin:events_scorecard_change', args=[first_scorecard.pk])
            links.append(f'<a href="{decisions_url}" target="_blank" style="color: #cc6600;">⚖️ Decisions ({scorecards_count} judges)</a>')
        else:
            decisions_url = reverse('admin:events_scorecard_add') + f'?fight={obj.pk}'
            links.append(f'<a href="{decisions_url}" target="_blank" style="color: #666;">➕ Add Decision</a>')
        
        return format_html(' | '.join(links))
    get_action_links.short_description = 'Pages'
    
    def get_storyline_section(self, obj):
        """Display storyline section for all fights"""
        if not obj.pk:
            return "Save fight first to access storyline features"
        
        # Check if storyline exists
        if hasattr(obj, 'storyline') and obj.storyline:
            storyline = obj.storyline
            storyline_url = reverse('admin:events_fightstoryline_change', args=[storyline.pk])
            
            # Count content fields
            content_fields = [
                storyline.summary, storyline.fighter1_background, storyline.fighter1_stakes, 
                storyline.fighter1_keys_to_victory, storyline.fighter2_background,
                storyline.fighter2_stakes, storyline.fighter2_keys_to_victory,
                storyline.rivalry_history, storyline.title_implications, storyline.historical_significance
            ]
            filled_fields = sum(1 for field in content_fields if field and field.strip())
            total_fields = len(content_fields)
            completion_pct = round((filled_fields / total_fields) * 100)
            
            word_count = storyline.get_word_count()
            
            return format_html(
                '<div style="padding: 20px; border: 2px solid #4caf50; border-radius: 8px; background: #e8f5e8;">'
                '<h3 style="margin: 0 0 15px 0; color: #2e7d32;">📖 Fight Storyline Available</h3>'
                '<div style="background: white; padding: 15px; border-radius: 5px; margin-bottom: 15px;">'
                '<h4 style="margin: 0 0 10px 0; color: #333;">{}</h4>'
                '<p style="margin: 0 0 10px 0; color: #555;">{}</p>'
                '<div style="margin-bottom: 10px;">'
                '<span style="background: #2e7d32; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-right: 10px;">{}% Complete</span>'
                '<span style="color: #666; font-size: 12px;">{} words • {} of {} sections filled</span>'
                '</div>'
                '<p style="margin: 0; color: #666; font-size: 12px;"><strong>Author:</strong> {}</p>'
                '</div>'
                '<a href="{}" target="_blank" style="background: #2e7d32; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">📝 Edit Storyline</a>'
                '</div>',
                storyline.headline or "Untitled Storyline",
                storyline.summary[:200] + "..." if storyline.summary and len(storyline.summary) > 200 else (storyline.summary or "No summary available"),
                completion_pct,
                word_count,
                filled_fields,
                total_fields,
                storyline.author or "Unknown",
                storyline_url
            )
        else:
            # No storyline exists, show creation link
            create_url = reverse('admin:events_fightstoryline_add') + f'?fight={obj.pk}'
            
            # Determine fight type for display
            if obj.is_main_event:
                fight_type = "main event"
                fight_description = "This main event fight"
            elif obj.fight_order == 2:
                fight_type = "co-main event" 
                fight_description = "This co-main event fight"
            else:
                fight_type = f"fight (order #{obj.fight_order})"
                fight_description = "This fight"
            
            return format_html(
                '<div style="padding: 20px; border: 2px solid #ff9800; border-radius: 8px; background: #fff3e0;">'
                '<h3 style="margin: 0 0 15px 0; color: #f57c00;">📖 Create Fight Storyline</h3>'
                '<p style="margin: 0 0 15px 0; color: #f57c00;">{} can have a detailed storyline featuring:</p>'
                '<ul style="margin: 0 0 15px 0; color: #f57c00;">'
                '<li>Fighter backgrounds and career journeys</li>'
                '<li>What\'s at stake for each fighter</li>'
                '<li>Rivalry history and beef between fighters</li>'
                '<li>Keys to victory for both sides</li>'
                '<li>Historical significance and title implications</li>'
                '<li>Expert predictions and key facts</li>'
                '</ul>'
                '<div style="margin-bottom: 15px; padding: 10px; background: rgba(255,255,255,0.7); border-radius: 5px;">'
                '<small style="color: #e65100;"><strong>Fight Type:</strong> {} | <strong>Event:</strong> {} | <strong>Date:</strong> {}</small>'
                '</div>'
                '<a href="{}" target="_blank" style="background: #f57c00; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">✨ Create Storyline</a>'
                '</div>',
                fight_description,
                fight_type,
                obj.event.name,
                obj.event.date,
                create_url
            )
    get_storyline_section.short_description = 'Editorial Storyline'
    
    def get_navigation_links(self, obj):
        """Navigation links within the fight detail page"""
        if not obj.pk:
            return "Save fight first to access statistics and decisions"
        
        links = []
        
        # Statistics section
        if hasattr(obj, 'statistics') and obj.statistics:
            stats_url = reverse('admin:events_fightstatistics_change', args=[obj.statistics.pk])
            round_count = obj.statistics.round_stats.count()
            links.append(format_html(
                '<div style="margin: 10px 0; padding: 15px; border: 2px solid #0066cc; border-radius: 5px; background: #f0f8ff;">'
                '<h3 style="margin: 0 0 10px 0; color: #0066cc;">📊 CONSOLIDATED Statistics (UFCstats.com style)</h3>'
                '<p style="margin: 0 0 10px 0;"><strong>ALL statistics in one place:</strong> Fight totals + round-by-round breakdown</p>'
                '<p style="margin: 0 0 15px 0; color: #666;"><strong>Available:</strong> {} rounds of detailed statistics</p>'
                '<a href="{}" target="_blank" style="background: #0066cc; color: white; padding: 8px 16px; text-decoration: none; border-radius: 3px;">Manage All Statistics</a>'
                '</div>', round_count, stats_url
            ))
        else:
            stats_url = reverse('admin:events_fightstatistics_add') + f'?fight={obj.pk}'
            links.append(format_html(
                '<div style="margin: 10px 0; padding: 15px; border: 2px solid #ccc; border-radius: 5px; background: #f9f9f9;">'
                '<h3 style="margin: 0 0 10px 0; color: #666;">📊 CONSOLIDATED Statistics</h3>'
                '<p style="margin: 0 0 15px 0;">No statistics available yet - add fight totals + round breakdown</p>'
                '<a href="{}" target="_blank" style="background: #666; color: white; padding: 8px 16px; text-decoration: none; border-radius: 3px;">Create All Statistics</a>'
                '</div>', stats_url
            ))
        
        # Decisions section
        scorecards_count = obj.scorecards.count()
        if scorecards_count > 0:
            # Single consolidated link to all judges' scorecards
            first_scorecard = obj.scorecards.first()
            decisions_url = reverse('admin:events_scorecard_change', args=[first_scorecard.pk])
            judge_names = ', '.join([sc.judge_name for sc in obj.scorecards.all()])
            
            links.append(format_html(
                '<div style="margin: 10px 0; padding: 15px; border: 2px solid #cc6600; border-radius: 5px; background: #fff8f0;">'
                '<h3 style="margin: 0 0 10px 0; color: #cc6600;">⚖️ CONSOLIDATED Judge Scorecards (MMADecisions.com style)</h3>'
                '<p style="margin: 0 0 10px 0;"><strong>ALL scorecards in one place:</strong> All judges + round-by-round breakdown</p>'
                '<p style="margin: 0 0 15px 0; color: #666;"><strong>Available:</strong> {} judges: {}</p>'
                '<a href="{}" target="_blank" style="background: #cc6600; color: white; padding: 8px 16px; text-decoration: none; border-radius: 3px;">Manage All Scorecards</a>'
                '</div>', 
                scorecards_count, judge_names, decisions_url
            ))
        else:
            decisions_url = reverse('admin:events_scorecard_add') + f'?fight={obj.pk}'
            links.append(format_html(
                '<div style="margin: 10px 0; padding: 15px; border: 2px solid #ccc; border-radius: 5px; background: #f9f9f9;">'
                '<h3 style="margin: 0 0 10px 0; color: #666;">⚖️ CONSOLIDATED Scorecards</h3>'
                '<p style="margin: 0 0 15px 0;">No scorecards available yet - add all judges + round scores</p>'
                '<a href="{}" target="_blank" style="background: #666; color: white; padding: 8px 16px; text-decoration: none; border-radius: 3px;">Create All Scorecards</a>'
                '</div>', decisions_url
            ))
        
        return format_html(''.join(links))
    get_navigation_links.short_description = 'Navigate to Detailed Pages'
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related(
            'event', 'weight_class', 'winner'
        ).prefetch_related('participants__fighter')


# FightParticipant is now managed exclusively through FightAdmin inlines


class RoundStatisticsInline(admin.StackedInline):
    """Enhanced inline for comprehensive round-by-round statistics"""
    model = RoundStatistics
    extra = 0
    classes = ['collapse']
    
    fieldsets = (
        ('Round Overview', {
            'fields': (
                ('round_number', 'round_duration'),
                'round_notes',
            )
        }),
        ('Fighter 1 - Striking Statistics', {
            'fields': (
                ('fighter1_head_strikes_landed', 'fighter1_head_strikes_attempted'),
                ('fighter1_body_strikes_landed', 'fighter1_body_strikes_attempted'),
                ('fighter1_leg_strikes_landed', 'fighter1_leg_strikes_attempted'),
                ('fighter1_total_strikes_landed', 'fighter1_total_strikes_attempted'),
            ),
            'classes': ['collapse'],
        }),
        ('Fighter 1 - Position & Grappling', {
            'fields': (
                ('fighter1_distance_strikes_landed', 'fighter1_distance_strikes_attempted'),
                ('fighter1_clinch_strikes_landed', 'fighter1_clinch_strikes_attempted'),
                ('fighter1_ground_strikes_landed', 'fighter1_ground_strikes_attempted'),
                ('fighter1_takedowns_landed', 'fighter1_takedown_attempts'),
                ('fighter1_submission_attempts', 'fighter1_reversals'),
                ('fighter1_control_time', 'fighter1_knockdowns'),
            ),
            'classes': ['collapse'],
        }),
        ('Fighter 2 - Striking Statistics', {
            'fields': (
                ('fighter2_head_strikes_landed', 'fighter2_head_strikes_attempted'),
                ('fighter2_body_strikes_landed', 'fighter2_body_strikes_attempted'),
                ('fighter2_leg_strikes_landed', 'fighter2_leg_strikes_attempted'),
                ('fighter2_total_strikes_landed', 'fighter2_total_strikes_attempted'),
            ),
            'classes': ['collapse'],
        }),
        ('Fighter 2 - Position & Grappling', {
            'fields': (
                ('fighter2_distance_strikes_landed', 'fighter2_distance_strikes_attempted'),
                ('fighter2_clinch_strikes_landed', 'fighter2_clinch_strikes_attempted'),
                ('fighter2_ground_strikes_landed', 'fighter2_ground_strikes_attempted'),
                ('fighter2_takedowns_landed', 'fighter2_takedown_attempts'),
                ('fighter2_submission_attempts', 'fighter2_reversals'),
                ('fighter2_control_time', 'fighter2_knockdowns'),
            ),
            'classes': ['collapse'],
        }),
    )


@admin.register(FightStatistics)
class FightStatisticsAdmin(admin.ModelAdmin):
    """CONSOLIDATED Statistics Page - ALL fight & round statistics in one place (UFCstats.com style)"""
    
    list_display = [
        'fight', 'get_fighter_names', 'get_striking_summary',
        'get_grappling_summary', 'get_round_stats_count'
    ]
    
    search_fields = [
        'fight__event__name', 'fighter1__first_name', 'fighter1__last_name',
        'fighter2__first_name', 'fighter2__last_name'
    ]
    
    fieldsets = (
        ('Fight Information', {
            'fields': (
                'get_fight_header',
                ('fight', 'fighter1', 'fighter2'),
            )
        }),
        ('JSON Import', {
            'fields': (
                'json_data',
                'get_json_import_section',
            ),
            'classes': ('collapse',),
        }),
        ('Round-by-Round Statistics Table (UFCstats.com style)', {
            'fields': (
                'get_round_statistics_table',
            ),
            'classes': ('wide',),
        }),
        ('Overall Fight Totals', {
            'fields': (
                ('fighter1_strikes_landed', 'fighter1_strikes_attempted'),
                ('fighter2_strikes_landed', 'fighter2_strikes_attempted'),
                ('fighter1_takedowns', 'fighter1_takedown_attempts'),
                ('fighter2_takedowns', 'fighter2_takedown_attempts'),
                ('fighter1_control_time', 'fighter2_control_time'),
            )
        }),
        ('Additional Statistics', {
            'fields': (
                'detailed_stats',
            ),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['get_fight_header', 'get_round_statistics_table', 'get_json_import_section']
    inlines = [RoundStatisticsInline]
    autocomplete_fields = ['fight', 'fighter1', 'fighter2']
    
    def get_fight_header(self, obj):
        """Display fight header like UFCstats.com"""
        if not obj.pk:
            return "Save to view fight header"
            
        fight = obj.fight
        return format_html(
            '<div style="background: #0066cc; color: white; padding: 20px; border-radius: 5px; margin: 10px 0;">'
            '<h2 style="margin: 0 0 10px 0;">{} vs {}</h2>'
            '<p style="margin: 0; font-size: 16px;">{} • {} • {}</p>'
            '<p style="margin: 5px 0 0 0;">Method: {} ({})</p>'
            '</div>',
            obj.fighter1.get_full_name(),
            obj.fighter2.get_full_name(), 
            fight.event.name,
            fight.event.date,
            fight.get_status_display(),
            fight.method,
            fight.method_details
        )
    get_fight_header.short_description = 'Fight Header'
    
    def get_round_statistics_table(self, obj):
        """Display round-by-round statistics in UFCstats.com table format"""
        if not obj.pk:
            return "Save to view round statistics"
            
        rounds = obj.round_stats.all()
        if not rounds:
            return format_html(
                '<div style="text-align: center; padding: 40px; background: #f9f9f9; border-radius: 5px;">'
                '<h3>No Round Statistics Available</h3>'
                '<p>Add round statistics using the inline editor below</p>'
                '</div>'
            )
        
        # Build UFCstats.com style table
        table_html = f'''
        <div style="margin: 20px 0;">
            <h3 style="color: #0066cc; margin-bottom: 15px;">📊 Round-by-Round Statistics (UFCstats.com style)</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <thead>
                    <tr style="background: #0066cc; color: white;">
                        <th style="padding: 10px; border: 1px solid #ddd;">Round</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">{obj.fighter1.get_full_name()}</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">{obj.fighter2.get_full_name()}</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">Striking Accuracy</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">Control Time</th>
                    </tr>
                </thead>
                <tbody>
        '''
        
        for round_stat in rounds:
            f1_acc = round_stat.get_fighter1_striking_accuracy()
            f2_acc = round_stat.get_fighter2_striking_accuracy()
            f1_control = f"{round_stat.fighter1_control_time // 60}:{round_stat.fighter1_control_time % 60:02d}"
            f2_control = f"{round_stat.fighter2_control_time // 60}:{round_stat.fighter2_control_time % 60:02d}"
            
            table_html += f'''
                <tr style="background: {'#f8f9fa' if round_stat.round_number % 2 == 0 else 'white'};">
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center; font-weight: bold;">
                        Round {round_stat.round_number}
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        <strong>Total:</strong> {round_stat.fighter1_total_strikes_landed}/{round_stat.fighter1_total_strikes_attempted}<br>
                        <span style="color: #666;">Head:</span> {round_stat.fighter1_head_strikes_landed}/{round_stat.fighter1_head_strikes_attempted} |
                        <span style="color: #666;">Body:</span> {round_stat.fighter1_body_strikes_landed}/{round_stat.fighter1_body_strikes_attempted} |
                        <span style="color: #666;">Leg:</span> {round_stat.fighter1_leg_strikes_landed}/{round_stat.fighter1_leg_strikes_attempted}<br>
                        <span style="color: #cc6600;">TD:</span> {round_stat.fighter1_takedowns_landed}/{round_stat.fighter1_takedown_attempts} |
                        <span style="color: #cc6600;">Sub:</span> {round_stat.fighter1_submission_attempts}
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        <strong>Total:</strong> {round_stat.fighter2_total_strikes_landed}/{round_stat.fighter2_total_strikes_attempted}<br>
                        <span style="color: #666;">Head:</span> {round_stat.fighter2_head_strikes_landed}/{round_stat.fighter2_head_strikes_attempted} |
                        <span style="color: #666;">Body:</span> {round_stat.fighter2_body_strikes_landed}/{round_stat.fighter2_body_strikes_attempted} |
                        <span style="color: #666;">Leg:</span> {round_stat.fighter2_leg_strikes_landed}/{round_stat.fighter2_leg_strikes_attempted}<br>
                        <span style="color: #cc6600;">TD:</span> {round_stat.fighter2_takedowns_landed}/{round_stat.fighter2_takedown_attempts} |
                        <span style="color: #cc6600;">Sub:</span> {round_stat.fighter2_submission_attempts}
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">
                        <span style="color: #0066cc; font-weight: bold;">{f1_acc}%</span> vs <span style="color: #cc6600; font-weight: bold;">{f2_acc}%</span>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">
                        <span style="color: #0066cc;">{f1_control}</span> vs <span style="color: #cc6600;">{f2_control}</span>
                    </td>
                </tr>
            '''
        
        table_html += '''
                </tbody>
            </table>
            <p style="margin-top: 10px; color: #666; font-size: 12px;">
                <strong>Legend:</strong> TD = Takedowns, Sub = Submission Attempts, Numbers show Landed/Attempted
            </p>
        </div>
        '''
        
        return format_html(table_html)
    get_round_statistics_table.short_description = 'Round Statistics Table'
    
    def get_fighter_names(self, obj):
        """Display fighter names"""
        return f"{obj.fighter1.get_full_name()} vs {obj.fighter2.get_full_name()}"
    get_fighter_names.short_description = 'Fighters'
    
    def get_striking_summary(self, obj):
        """Display striking summary"""
        f1_acc = round((obj.fighter1_strikes_landed / max(obj.fighter1_strikes_attempted, 1)) * 100, 1)
        f2_acc = round((obj.fighter2_strikes_landed / max(obj.fighter2_strikes_attempted, 1)) * 100, 1)
        return f"F1: {obj.fighter1_strikes_landed}/{obj.fighter1_strikes_attempted} ({f1_acc}%) | F2: {obj.fighter2_strikes_landed}/{obj.fighter2_strikes_attempted} ({f2_acc}%)"
    get_striking_summary.short_description = 'Striking Summary'
    
    def get_grappling_summary(self, obj):
        """Display grappling summary"""
        return f"TD - F1: {obj.fighter1_takedowns}/{obj.fighter1_takedown_attempts} | F2: {obj.fighter2_takedowns}/{obj.fighter2_takedown_attempts}"
    get_grappling_summary.short_description = 'Grappling Summary'
    
    def get_round_stats_count(self, obj):
        """Display round stats count"""
        count = obj.round_stats.count()
        return f"{count} rounds"
    get_round_stats_count.short_description = 'Round Stats'
    
    def get_json_import_section(self, obj):
        """JSON import functionality for fight statistics"""
        return format_html(
            '<div style="padding: 20px; background: #ffffff; border: 2px solid #0066cc; border-radius: 8px; margin: 10px 0;">'
            '<h3 style="margin: 0 0 15px 0; color: #0066cc; border-bottom: 2px solid #0066cc; padding-bottom: 10px;">📊 JSON Import Instructions</h3>'
            '<div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 15px;">'
            '<h4 style="margin: 0 0 10px 0; color: #333;">Step 1: Paste fight statistics JSON in the field above</h4>'
            '<p style="margin: 0 0 10px 0; color: #555;">Use this format for complete fight statistics with round-by-round breakdown:</p>'
            '</div>'
            '<pre style="background: #2d3748; color: #e2e8f0; padding: 15px; border-radius: 5px; font-size: 12px; line-height: 1.4; overflow-x: auto; margin: 0 0 15px 0;">'
            '{{\n'
            '  "fight_totals": {{\n'
            '    "fighter1_strikes_landed": 85,\n'
            '    "fighter1_strikes_attempted": 120,\n'
            '    "fighter2_strikes_landed": 92,\n'
            '    "fighter2_strikes_attempted": 115,\n'
            '    "fighter1_takedowns": 2,\n'
            '    "fighter1_takedown_attempts": 4,\n'
            '    "fighter2_takedowns": 0,\n'
            '    "fighter2_takedown_attempts": 1,\n'
            '    "fighter1_control_time": 180,\n'
            '    "fighter2_control_time": 45\n'
            '  }},\n'
            '  "rounds": [\n'
            '    {{\n'
            '      "round_number": 1,\n'
            '      "fighter1_total_strikes_landed": 28,\n'
            '      "fighter1_total_strikes_attempted": 40,\n'
            '      "fighter1_head_strikes_landed": 15,\n'
            '      "fighter1_head_strikes_attempted": 22,\n'
            '      "fighter1_body_strikes_landed": 8,\n'
            '      "fighter1_body_strikes_attempted": 12,\n'
            '      "fighter1_leg_strikes_landed": 5,\n'
            '      "fighter1_leg_strikes_attempted": 6,\n'
            '      "fighter1_takedowns_landed": 1,\n'
            '      "fighter1_takedown_attempts": 2,\n'
            '      "fighter1_control_time": 90,\n'
            '      "fighter2_total_strikes_landed": 32,\n'
            '      "fighter2_total_strikes_attempted": 38,\n'
            '      "fighter2_head_strikes_landed": 18,\n'
            '      "fighter2_head_strikes_attempted": 25,\n'
            '      "fighter2_body_strikes_landed": 10,\n'
            '      "fighter2_body_strikes_attempted": 10,\n'
            '      "fighter2_leg_strikes_landed": 4,\n'
            '      "fighter2_leg_strikes_attempted": 3,\n'
            '      "fighter2_takedowns_landed": 0,\n'
            '      "fighter2_takedown_attempts": 0,\n'
            '      "fighter2_control_time": 15\n'
            '    }},\n'
            '    {{\n'
            '      "round_number": 2,\n'
            '      // ... similar structure for each round\n'
            '    }}\n'
            '  ]\n'
            '}}'
            '</pre>'
            '<div style="background: #e8f5e8; border: 1px solid #4caf50; padding: 12px; border-radius: 5px; margin-bottom: 10px;">'
            '<h4 style="margin: 0 0 8px 0; color: #2e7d32;">✅ Step 2: Save the statistics</h4>'
            '<p style="margin: 0; color: #2e7d32;">After pasting JSON data, click "Save and continue editing" to process the import.</p>'
            '</div>'
            '<div style="background: #fff3cd; border: 1px solid #ffc107; padding: 12px; border-radius: 5px; margin-bottom: 10px;">'
            '<h4 style="margin: 0 0 8px 0; color: #856404;">⚠️ Note</h4>'
            '<p style="margin: 0; color: #856404;">JSON import will overwrite existing statistics and round data. Backup important data before importing.</p>'
            '</div>'
            '<div style="background: #f0f8ff; border: 1px solid #0066cc; padding: 12px; border-radius: 5px;">'
            '<h4 style="margin: 0 0 8px 0; color: #0066cc;">💡 UFCstats.com Style</h4>'
            '<p style="margin: 0; color: #0066cc;">This will automatically create the complete round-by-round breakdown table like UFCstats.com with all striking positions, grappling stats, and control time.</p>'
            '</div>'
            '</div>'
        )
    get_json_import_section.short_description = 'Import Instructions'
    
    def save_model(self, request, obj, form, change):
        """Auto-process JSON import when saving"""
        # Process JSON import if provided
        if obj.json_data and obj.json_data.strip():
            self._process_stats_json_import(obj, request)
        
        super().save_model(request, obj, form, change)
    
    def _process_stats_json_import(self, obj, request):
        """Process JSON import data and create fight statistics with round breakdown"""
        import json
        from .models import RoundStatistics
        
        try:
            data = json.loads(obj.json_data)
            
            # Set fight totals if provided
            if 'fight_totals' in data:
                totals = data['fight_totals']
                obj.fighter1_strikes_landed = totals.get('fighter1_strikes_landed', 0)
                obj.fighter1_strikes_attempted = totals.get('fighter1_strikes_attempted', 0)
                obj.fighter2_strikes_landed = totals.get('fighter2_strikes_landed', 0)
                obj.fighter2_strikes_attempted = totals.get('fighter2_strikes_attempted', 0)
                obj.fighter1_takedowns = totals.get('fighter1_takedowns', 0)
                obj.fighter1_takedown_attempts = totals.get('fighter1_takedown_attempts', 0)
                obj.fighter2_takedowns = totals.get('fighter2_takedowns', 0)
                obj.fighter2_takedown_attempts = totals.get('fighter2_takedown_attempts', 0)
                obj.fighter1_control_time = totals.get('fighter1_control_time', 0)
                obj.fighter2_control_time = totals.get('fighter2_control_time', 0)
            
            # Clear existing round statistics
            obj.round_stats.all().delete()
            
            # Create new round statistics
            if 'rounds' in data:
                for round_data in data['rounds']:
                    RoundStatistics.objects.create(
                        fight_statistics=obj,
                        round_number=round_data['round_number'],
                        # Fighter 1 striking
                        fighter1_total_strikes_landed=round_data.get('fighter1_total_strikes_landed', 0),
                        fighter1_total_strikes_attempted=round_data.get('fighter1_total_strikes_attempted', 0),
                        fighter1_head_strikes_landed=round_data.get('fighter1_head_strikes_landed', 0),
                        fighter1_head_strikes_attempted=round_data.get('fighter1_head_strikes_attempted', 0),
                        fighter1_body_strikes_landed=round_data.get('fighter1_body_strikes_landed', 0),
                        fighter1_body_strikes_attempted=round_data.get('fighter1_body_strikes_attempted', 0),
                        fighter1_leg_strikes_landed=round_data.get('fighter1_leg_strikes_landed', 0),
                        fighter1_leg_strikes_attempted=round_data.get('fighter1_leg_strikes_attempted', 0),
                        fighter1_distance_strikes_landed=round_data.get('fighter1_distance_strikes_landed', 0),
                        fighter1_distance_strikes_attempted=round_data.get('fighter1_distance_strikes_attempted', 0),
                        fighter1_clinch_strikes_landed=round_data.get('fighter1_clinch_strikes_landed', 0),
                        fighter1_clinch_strikes_attempted=round_data.get('fighter1_clinch_strikes_attempted', 0),
                        fighter1_ground_strikes_landed=round_data.get('fighter1_ground_strikes_landed', 0),
                        fighter1_ground_strikes_attempted=round_data.get('fighter1_ground_strikes_attempted', 0),
                        # Fighter 1 grappling
                        fighter1_takedowns_landed=round_data.get('fighter1_takedowns_landed', 0),
                        fighter1_takedown_attempts=round_data.get('fighter1_takedown_attempts', 0),
                        fighter1_submission_attempts=round_data.get('fighter1_submission_attempts', 0),
                        fighter1_reversals=round_data.get('fighter1_reversals', 0),
                        fighter1_control_time=round_data.get('fighter1_control_time', 0),
                        fighter1_knockdowns=round_data.get('fighter1_knockdowns', 0),
                        # Fighter 2 striking
                        fighter2_total_strikes_landed=round_data.get('fighter2_total_strikes_landed', 0),
                        fighter2_total_strikes_attempted=round_data.get('fighter2_total_strikes_attempted', 0),
                        fighter2_head_strikes_landed=round_data.get('fighter2_head_strikes_landed', 0),
                        fighter2_head_strikes_attempted=round_data.get('fighter2_head_strikes_attempted', 0),
                        fighter2_body_strikes_landed=round_data.get('fighter2_body_strikes_landed', 0),
                        fighter2_body_strikes_attempted=round_data.get('fighter2_body_strikes_attempted', 0),
                        fighter2_leg_strikes_landed=round_data.get('fighter2_leg_strikes_landed', 0),
                        fighter2_leg_strikes_attempted=round_data.get('fighter2_leg_strikes_attempted', 0),
                        fighter2_distance_strikes_landed=round_data.get('fighter2_distance_strikes_landed', 0),
                        fighter2_distance_strikes_attempted=round_data.get('fighter2_distance_strikes_attempted', 0),
                        fighter2_clinch_strikes_landed=round_data.get('fighter2_clinch_strikes_landed', 0),
                        fighter2_clinch_strikes_attempted=round_data.get('fighter2_clinch_strikes_attempted', 0),
                        fighter2_ground_strikes_landed=round_data.get('fighter2_ground_strikes_landed', 0),
                        fighter2_ground_strikes_attempted=round_data.get('fighter2_ground_strikes_attempted', 0),
                        # Fighter 2 grappling
                        fighter2_takedowns_landed=round_data.get('fighter2_takedowns_landed', 0),
                        fighter2_takedown_attempts=round_data.get('fighter2_takedown_attempts', 0),
                        fighter2_submission_attempts=round_data.get('fighter2_submission_attempts', 0),
                        fighter2_reversals=round_data.get('fighter2_reversals', 0),
                        fighter2_control_time=round_data.get('fighter2_control_time', 0),
                        fighter2_knockdowns=round_data.get('fighter2_knockdowns', 0),
                        # Round metadata
                        round_duration=round_data.get('round_duration', 300),
                        round_notes=round_data.get('round_notes', '')
                    )
                
                # Clear JSON data after successful import
                obj.json_data = ''
                
                # Add success message
                from django.contrib import messages
                messages.success(request, f'Successfully imported fight totals and {len(data["rounds"])} rounds of detailed statistics')
            
        except json.JSONDecodeError as e:
            from django.contrib import messages
            messages.error(request, f'Invalid JSON format: {str(e)}')
        except KeyError as e:
            from django.contrib import messages
            messages.error(request, f'Missing required field: {str(e)}')
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f'Error importing JSON: {str(e)}')


class RoundScoreInline(admin.StackedInline):
    """Enhanced inline for comprehensive round-by-round judge scoring"""
    model = RoundScore
    extra = 0
    classes = ['collapse']
    
    fieldsets = (
        ('Round Score', {
            'fields': (
                ('round_number', 'get_round_winner_display'),
                ('fighter1_round_score', 'fighter2_round_score'),
                'round_notes',
            )
        }),
        ('Detailed Scoring Criteria (Optional)', {
            'fields': (
                ('fighter1_effective_striking', 'fighter2_effective_striking'),
                ('fighter1_effective_grappling', 'fighter2_effective_grappling'),
                ('fighter1_control', 'fighter2_control'),
                ('fighter1_aggression', 'fighter2_aggression'),
            ),
            'classes': ['collapse'],
        }),
        ('Key Moments', {
            'fields': (
                'key_moments',
            ),
            'classes': ['collapse'],
        }),
    )
    
    readonly_fields = ('get_round_winner_display',)
    
    def get_round_winner_display(self, obj):
        """Display round winner with color coding"""
        if not obj.pk:
            return "-"
        winner = obj.get_round_winner()
        if winner == 'fighter1':
            return format_html('<span style="color: green; font-weight: bold;">Fighter 1 Wins</span>')
        elif winner == 'fighter2':
            return format_html('<span style="color: blue; font-weight: bold;">Fighter 2 Wins</span>')
        elif winner == 'draw':
            return format_html('<span style="color: orange; font-weight: bold;">Draw Round</span>')
        else:
            return format_html('<span style="color: gray; font-weight: bold;">Unknown</span>')
    get_round_winner_display.short_description = 'Round Winner'


@admin.register(Scorecard)
class ScorecardAdmin(admin.ModelAdmin):
    """Individual Judge Scorecard with Round-by-Round Scoring"""
    
    list_display = [
        'get_fight_display', 'judge_name', 'get_total_score', 'get_decision'
    ]
    
    list_filter = [
        'fight__event__organization',
        'fight__event__date',
    ]
    
    search_fields = [
        'fight__participants__fighter__first_name',
        'fight__participants__fighter__last_name',
        'judge_name'
    ]
    
    fieldsets = (
        ('Fight Information', {
            'fields': (
                'fight',
                'get_fighter_names',
            )
        }),
        ('Judge Details', {
            'fields': (
                'judge_name',
                'get_scorecard_preview',
            )
        }),
        ('JSON Import', {
            'fields': (
                'json_data',
                'get_json_import_section',
            ),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['get_fighter_names', 'get_scorecard_preview', 'get_json_import_section']
    autocomplete_fields = ['fight']
    inlines = [RoundScoreInline]
    
    def get_fighter_names(self, obj):
        """Display fighter names for context"""
        if not obj or not obj.fight:
            return "Select a fight first"
        
        participants = obj.fight.participants.all()
        if len(participants) >= 2:
            fighter1 = participants[0].fighter.get_full_name()
            fighter2 = participants[1].fighter.get_full_name()
            return format_html(
                '<div style="padding: 10px; background: #f0f8ff; border-radius: 5px;">'
                '<strong>📊 Scoring:</strong> {fighter1} vs {fighter2}<br>'
                '<small>{event} • {date}</small>'
                '</div>',
                fighter1=fighter1,
                fighter2=fighter2,
                event=obj.fight.event.name,
                date=obj.fight.event.date
            )
        return "Fighters not set"
    get_fighter_names.short_description = 'Fight Details'
    
    def get_scorecard_preview(self, obj):
        """Display live scorecard preview as user enters round scores"""
        if not obj.pk:
            return "Save judge information first, then add round scores below"
        
        participants = obj.fight.participants.all() if obj.fight else []
        if len(participants) < 2:
            return "Fight must have two participants"
        
        fighter1_name = participants[0].fighter.get_full_name()
        fighter2_name = participants[1].fighter.get_full_name()
        
        # Get round scores
        round_scores = obj.round_details.all().order_by('round_number')
        
        if not round_scores:
            return format_html(
                '<div style="text-align: center; padding: 20px; background: #f9f9f9; border-radius: 5px;">'
                '<p>No round scores entered yet.</p>'
                '<p><strong>Add round scores using the "Round scores" section below.</strong></p>'
                '</div>'
            )
        
        # Build scorecard table
        table_html = f'''
        <div style="margin: 10px 0;">
            <h4 style="color: #cc6600; text-align: center;">{obj.judge_name}</h4>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px; text-align: center;">
                <thead>
                    <tr style="background: #cc6600; color: white;">
                        <th style="border: 1px solid #ddd; padding: 8px;">ROUND</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">{fighter1_name}</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">{fighter2_name}</th>
                    </tr>
                </thead>
                <tbody>
        '''
        
        total_f1 = 0
        total_f2 = 0
        
        for round_score in round_scores:
            total_f1 += round_score.fighter1_round_score
            total_f2 += round_score.fighter2_round_score
            
            table_html += f'''
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">{round_score.round_number}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{round_score.fighter1_round_score}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{round_score.fighter2_round_score}</td>
                </tr>
            '''
        
        # Add total row
        winner_color_f1 = 'green' if total_f1 > total_f2 else '#666'
        winner_color_f2 = 'green' if total_f2 > total_f1 else '#666'
        
        table_html += f'''
                <tr style="background: #f0f0f0; font-weight: bold;">
                    <td style="border: 1px solid #ddd; padding: 8px;">TOTAL</td>
                    <td style="border: 1px solid #ddd; padding: 8px; color: {winner_color_f1};">{total_f1}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; color: {winner_color_f2};">{total_f2}</td>
                </tr>
            </tbody>
        </table>
        </div>
        '''
        
        return format_html(table_html)
    get_scorecard_preview.short_description = 'Scorecard Preview'
    
    def get_json_import_section(self, obj):
        """JSON import functionality for scorecards"""
        return format_html(
            '<div style="padding: 20px; background: #ffffff; border: 2px solid #0066cc; border-radius: 8px; margin: 10px 0;">'
            '<h3 style="margin: 0 0 15px 0; color: #0066cc; border-bottom: 2px solid #0066cc; padding-bottom: 10px;">📥 JSON Import Instructions</h3>'
            '<div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 15px;">'
            '<h4 style="margin: 0 0 10px 0; color: #333;">Step 1: Paste JSON data in the field above</h4>'
            '<p style="margin: 0 0 10px 0; color: #555;">Use this exact format:</p>'
            '</div>'
            '<pre style="background: #2d3748; color: #e2e8f0; padding: 15px; border-radius: 5px; font-size: 13px; line-height: 1.5; overflow-x: auto; margin: 0 0 15px 0;">'
            '{{\n'
            '  "judge_name": "Michael Bell",\n'
            '  "rounds": [\n'
            '    {{"round": 1, "fighter1_score": 9, "fighter2_score": 10}},\n'
            '    {{"round": 2, "fighter1_score": 10, "fighter2_score": 9}},\n'
            '    {{"round": 3, "fighter1_score": 10, "fighter2_score": 9}}\n'
            '  ]\n'
            '}}'
            '</pre>'
            '<div style="background: #e8f5e8; border: 1px solid #4caf50; padding: 12px; border-radius: 5px; margin-bottom: 10px;">'
            '<h4 style="margin: 0 0 8px 0; color: #2e7d32;">✅ Step 2: Save the scorecard</h4>'
            '<p style="margin: 0; color: #2e7d32;">After pasting JSON data, click "Save and continue editing" to process the import.</p>'
            '</div>'
            '<div style="background: #fff3cd; border: 1px solid #ffc107; padding: 12px; border-radius: 5px;">'
            '<h4 style="margin: 0 0 8px 0; color: #856404;">⚠️ Note</h4>'
            '<p style="margin: 0; color: #856404;">JSON import will overwrite existing round scores. Make sure your JSON data is correct before saving.</p>'
            '</div>'
            '</div>'
        )
    get_json_import_section.short_description = 'Import Instructions'
    
    def get_total_score(self, obj):
        """Display total score"""
        round_scores = obj.round_details.all()
        if not round_scores:
            return "No rounds scored"
        
        total_f1 = sum(rs.fighter1_round_score for rs in round_scores)
        total_f2 = sum(rs.fighter2_round_score for rs in round_scores)
        return f"{total_f1}-{total_f2}"
    get_total_score.short_description = 'Total Score'
    
    def get_decision(self, obj):
        """Display decision"""
        round_scores = obj.round_details.all()
        if not round_scores:
            return "Incomplete"
        
        total_f1 = sum(rs.fighter1_round_score for rs in round_scores)
        total_f2 = sum(rs.fighter2_round_score for rs in round_scores)
        
        if total_f1 > total_f2:
            return format_html('<span style="color: green; font-weight: bold;">Fighter 1</span>')
        elif total_f2 > total_f1:
            return format_html('<span style="color: blue; font-weight: bold;">Fighter 2</span>')
        else:
            return format_html('<span style="color: orange; font-weight: bold;">Draw</span>')
    get_decision.short_description = 'Decision'
    
    def get_fight_display(self, obj):
        """Display fight"""
        return str(obj.fight)
    get_fight_display.short_description = 'Fight'
    
    def save_model(self, request, obj, form, change):
        """Auto-calculate totals and process JSON import when saving"""
        # Process JSON import if provided
        if obj.json_data and obj.json_data.strip():
            self._process_json_import(obj, request)
        
        super().save_model(request, obj, form, change)
        
        # Calculate totals from round details
        round_scores = obj.round_details.all()
        if round_scores:
            obj.fighter1_score = sum(rs.fighter1_round_score for rs in round_scores)
            obj.fighter2_score = sum(rs.fighter2_round_score for rs in round_scores)
            obj.save(update_fields=['fighter1_score', 'fighter2_score'])
    
    def _process_json_import(self, obj, request):
        """Process JSON import data and create round scores"""
        import json
        from .models import RoundScore
        
        try:
            data = json.loads(obj.json_data)
            
            # Set judge name if provided
            if 'judge_name' in data:
                obj.judge_name = data['judge_name']
            
            # Clear existing round scores
            obj.round_details.all().delete()
            
            # Create new round scores
            if 'rounds' in data:
                for round_data in data['rounds']:
                    RoundScore.objects.create(
                        scorecard=obj,
                        round_number=round_data['round'],
                        fighter1_round_score=round_data['fighter1_score'],
                        fighter2_round_score=round_data['fighter2_score']
                    )
                
                # Clear JSON data after successful import
                obj.json_data = ''
                
                # Add success message
                from django.contrib import messages
                messages.success(request, f'Successfully imported {len(data["rounds"])} rounds for judge {obj.judge_name}')
            
        except json.JSONDecodeError as e:
            from django.contrib import messages
            messages.error(request, f'Invalid JSON format: {str(e)}')
        except KeyError as e:
            from django.contrib import messages
            messages.error(request, f'Missing required field: {str(e)}')
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f'Error importing JSON: {str(e)}')


# RoundStatistics and RoundScore are now managed exclusively through their parent admin inlines
# This eliminates the need for separate admin pages and keeps related data together


@admin.register(FightStoryline)
class FightStorylineAdmin(admin.ModelAdmin):
    """Admin interface for fight storylines - Editorial content for all fights"""
    
    list_display = [
        'get_fight_display', 'headline', 'author', 'get_completion_status', 
        'get_word_count_display', 'publication_date'
    ]
    
    list_filter = [
        'publication_date',
        'author',
        'fight__event__organization',
        'fight__event__date',
    ]
    
    search_fields = [
        'headline', 'summary', 'author',
        'fight__participants__fighter__first_name',
        'fight__participants__fighter__last_name',
        'fight__event__name'
    ]
    
    fieldsets = (
        ('Fight Information', {
            'fields': (
                'fight',
                'get_fight_context',
            )
        }),
        ('Storyline Header', {
            'fields': (
                'headline',
                'summary',
                ('author', 'publication_date'),
                'featured_image_url',
            )
        }),
        ('JSON Import', {
            'fields': (
                'json_data',
                'get_json_import_section',
            ),
            'classes': ('collapse',),
        }),
        ('Fighter 1 Profile', {
            'fields': (
                'get_fighter1_header',
                'fighter1_background',
                'fighter1_stakes',
                'fighter1_keys_to_victory',
            ),
            'classes': ('wide',),
        }),
        ('Fighter 2 Profile', {
            'fields': (
                'get_fighter2_header',
                'fighter2_background',
                'fighter2_stakes',
                'fighter2_keys_to_victory',
            ),
            'classes': ('wide',),
        }),
        ('Fight Context & Analysis', {
            'fields': (
                'rivalry_history',
                'title_implications',
                'historical_significance',
            ),
            'classes': ('wide',),
        }),
        ('Facts & Predictions', {
            'fields': (
                'key_facts',
                'expert_predictions',
            ),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = [
        'get_fight_context', 'get_fighter1_header', 'get_fighter2_header', 
        'get_json_import_section'
    ]
    autocomplete_fields = ['fight']
    
    def get_fight_display(self, obj):
        """Display fight information"""
        return str(obj.fight)
    get_fight_display.short_description = 'Fight'
    
    def get_completion_status(self, obj):
        """Display completion percentage"""
        content_fields = [
            obj.summary, obj.fighter1_background, obj.fighter1_stakes, 
            obj.fighter1_keys_to_victory, obj.fighter2_background,
            obj.fighter2_stakes, obj.fighter2_keys_to_victory,
            obj.rivalry_history, obj.title_implications, obj.historical_significance
        ]
        filled_fields = sum(1 for field in content_fields if field and field.strip())
        total_fields = len(content_fields)
        completion_pct = round((filled_fields / total_fields) * 100)
        
        if completion_pct >= 80:
            color = 'green'
        elif completion_pct >= 50:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}% Complete</span>',
            color, completion_pct
        )
    get_completion_status.short_description = 'Completion'
    
    def get_word_count_display(self, obj):
        """Display word count"""
        word_count = obj.get_word_count()
        return f"{word_count} words"
    get_word_count_display.short_description = 'Word Count'
    
    def get_fight_context(self, obj):
        """Display fight context"""
        if not obj.fight:
            return "Select a fight first"
        
        fighters = obj.fight.get_fighters()
        if len(fighters) < 2:
            return "Fight must have two participants"
        
        fighter1, fighter2 = fighters[0], fighters[1]
        
        return format_html(
            '<div style="padding: 15px; background: #f0f8ff; border-radius: 5px; border: 1px solid #0066cc;">'
            '<h3 style="margin: 0 0 10px 0; color: #0066cc;">📖 Storyline Context</h3>'
            '<div style="display: grid; grid-template-columns: 1fr auto 1fr; gap: 15px; align-items: center;">'
            '<div style="text-align: center;">'
            '<h4 style="margin: 0 0 5px 0; color: #333;">{}</h4>'
            '<p style="margin: 0; color: #666; font-size: 12px;">{}</p>'
            '</div>'
            '<div style="text-align: center; font-size: 20px; font-weight: bold; color: #0066cc;">VS</div>'
            '<div style="text-align: center;">'
            '<h4 style="margin: 0 0 5px 0; color: #333;">{}</h4>'
            '<p style="margin: 0; color: #666; font-size: 12px;">{}</p>'
            '</div>'
            '</div>'
            '<div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd; text-align: center; color: #666;">'
            '<strong>{}</strong><br>'
            '{} • {} • Fight Order: {}'
            '</div>'
            '</div>',
            fighter1.get_full_name(),
            fighter1.nationality or "Unknown nationality",
            fighter2.get_full_name(),
            fighter2.nationality or "Unknown nationality",
            obj.fight.event.name,
            obj.fight.event.date,
            obj.fight.weight_class.name if obj.fight.weight_class else "No weight class",
            obj.fight.fight_order
        )
    get_fight_context.short_description = 'Fight Context'
    
    def get_fighter1_header(self, obj):
        """Display Fighter 1 header"""
        if not obj.fight:
            return "Select a fight first"
        
        fighters = obj.fight.get_fighters()
        if len(fighters) < 1:
            return "Fight needs participants"
        
        fighter = fighters[0]
        return format_html(
            '<div style="padding: 10px; background: #e8f5e8; border-radius: 5px; border-left: 4px solid #4caf50;">'
            '<h4 style="margin: 0; color: #2e7d32;">🥊 {} Profile</h4>'
            '</div>',
            fighter.get_full_name()
        )
    get_fighter1_header.short_description = 'Fighter 1'
    
    def get_fighter2_header(self, obj):
        """Display Fighter 2 header"""
        if not obj.fight:
            return "Select a fight first"
        
        fighters = obj.fight.get_fighters()
        if len(fighters) < 2:
            return "Fight needs both participants"
        
        fighter = fighters[1]
        return format_html(
            '<div style="padding: 10px; background: #e3f2fd; border-radius: 5px; border-left: 4px solid #2196f3;">'
            '<h4 style="margin: 0; color: #1976d2;">🥊 {} Profile</h4>'
            '</div>',
            fighter.get_full_name()
        )
    get_fighter2_header.short_description = 'Fighter 2'
    
    def get_json_import_section(self, obj):
        """JSON import functionality for storylines"""
        return format_html(
            '<div style="padding: 20px; background: #ffffff; border: 2px solid #0066cc; border-radius: 8px; margin: 10px 0;">'
            '<h3 style="margin: 0 0 15px 0; color: #0066cc; border-bottom: 2px solid #0066cc; padding-bottom: 10px;">📖 Storyline JSON Import</h3>'
            '<div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 15px;">'
            '<h4 style="margin: 0 0 10px 0; color: #333;">Import complete storyline content with this JSON structure:</h4>'
            '</div>'
            '<pre style="background: #2d3748; color: #e2e8f0; padding: 15px; border-radius: 5px; font-size: 12px; line-height: 1.4; overflow-x: auto; margin: 0 0 15px 0;">'
            '{{\n'
            '  "headline": "Jones vs Miocic: Legacy Defining Heavyweight Showdown",\n'
            '  "summary": "Two legends collide in a fight that will define heavyweight history...",\n'
            '  "author": "MMA Editorial Team",\n'
            '  "featured_image_url": "https://example.com/fight-poster.jpg",\n'
            '  "fighter1": {{\n'
            '    "background": "Jon Jones, widely considered the greatest light heavyweight...",\n'
            '    "stakes": "A chance to cement his legacy as the greatest of all time...",\n'
            '    "keys_to_victory": "Utilize his reach advantage and elite wrestling..."\n'
            '  }},\n'
            '  "fighter2": {{\n'
            '    "background": "Stipe Miocic, the most successful heavyweight champion...",\n'
            '    "stakes": "Prove he is still the king of the heavyweight division...",\n'
            '    "keys_to_victory": "Pressure Jones early and use his boxing skills..."\n'
            '  }},\n'
            '  "rivalry_history": "While they never fought before, both have been...",\n'
            '  "title_implications": "The winner will be undisputed heavyweight champion...",\n'
            '  "historical_significance": "This fight represents a passing of the torch...",\n'
            '  "key_facts": [\n'
            '    "Jones has never lost a legitimate fight in his career",\n'
            '    "Miocic holds the record for most heavyweight title defenses",\n'
            '    "Both fighters are in their late 30s"\n'
            '  ],\n'
            '  "expert_predictions": [\n'
            '    "Daniel Cormier predicts Jones by decision",\n'
            '    "Joe Rogan thinks Miocic by knockout",\n'
            '    "Most experts favor Jones 60-40"\n'
            '  ],\n'
            '  "publication_date": "2024-11-15T10:00:00Z"\n'
            '}}'
            '</pre>'
            '<div style="background: #e8f5e8; border: 1px solid #4caf50; padding: 12px; border-radius: 5px; margin-bottom: 10px;">'
            '<h4 style="margin: 0 0 8px 0; color: #2e7d32;">✅ After Import</h4>'
            '<p style="margin: 0; color: #2e7d32;">Click "Save and continue editing" to process the JSON data and populate all storyline fields.</p>'
            '</div>'
            '<div style="background: #fff3cd; border: 1px solid #ffc107; padding: 12px; border-radius: 5px;">'
            '<h4 style="margin: 0 0 8px 0; color: #856404;">💡 Pro Tip</h4>'
            '<p style="margin: 0; color: #856404;">JSON import will overwrite existing content. Use this for bulk importing complete storylines from external sources.</p>'
            '</div>'
            '</div>'
        )
    get_json_import_section.short_description = 'JSON Import'
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related(
            'fight__event', 'fight__weight_class'
        ).prefetch_related('fight__participants__fighter')


