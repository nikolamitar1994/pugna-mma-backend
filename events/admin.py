from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Event, Fight, FightParticipant, FightStatistics, 
    RoundStatistics, Scorecard, RoundScore
)


class FightParticipantInline(admin.TabularInline):
    """Inline editing for fight participants"""
    model = FightParticipant
    extra = 2
    max_num = 2
    fields = ('fighter', 'corner', 'result', 'weigh_in_weight', 'purse')
    autocomplete_fields = ['fighter']


class FightInline(admin.StackedInline):
    """Inline editing for fights within events"""
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
        ('Location', {
            'fields': (
                'location',
                ('venue', 'city'),
                ('state', 'country'),
            )
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
    
    inlines = [FightInline]
    date_hierarchy = 'date'
    
    def get_fight_count(self, obj):
        """Display number of fights on card"""
        count = obj.get_fight_count()
        return format_html(
            '<strong>{}</strong> fights',
            count
        )
    get_fight_count.short_description = 'Fights'


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
    
    readonly_fields = ['get_navigation_links']
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
    
    readonly_fields = ['get_fight_header', 'get_round_statistics_table']
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
    """CONSOLIDATED Judge Scorecards - ALL judges & round scores in one place (MMADecisions.com style)"""
    
    list_display = [
        'get_fight_display', 'get_all_judges_display', 'get_decision_summary',
        'get_all_judges_count'
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
    
    def get_queryset(self, request):
        """Show only one scorecard per fight (the first one) to avoid duplicates"""
        qs = super().get_queryset(request)
        # Get distinct fights by getting the first scorecard for each fight
        fight_ids = qs.values('fight').distinct()
        first_scorecard_ids = []
        
        for fight_data in fight_ids:
            fight_id = fight_data['fight']
            first_scorecard = qs.filter(fight_id=fight_id).first()
            if first_scorecard:
                first_scorecard_ids.append(first_scorecard.id)
        
        return qs.filter(id__in=first_scorecard_ids).select_related('fight')
    
    def get_all_judges_display(self, obj):
        """Display all judges for this fight"""
        all_scorecards = obj.fight.scorecards.all()
        judge_names = [sc.judge_name for sc in all_scorecards]
        return ', '.join(judge_names)
    get_all_judges_display.short_description = 'All Judges'
    
    def get_decision_summary(self, obj):
        """Display overall decision summary"""
        all_scorecards = obj.fight.scorecards.all()
        if not all_scorecards:
            return '-'
            
        # Count wins for each fighter
        f1_wins = sum(1 for sc in all_scorecards if sc.fighter1_score > sc.fighter2_score)
        f2_wins = sum(1 for sc in all_scorecards if sc.fighter2_score > sc.fighter1_score)
        
        if f1_wins > f2_wins:
            return format_html('<span style="color: green; font-weight: bold;">Fighter 1 Wins ({}-{})</span>', f1_wins, f2_wins)
        elif f2_wins > f1_wins:
            return format_html('<span style="color: blue; font-weight: bold;">Fighter 2 Wins ({}-{})</span>', f2_wins, f1_wins)
        else:
            return format_html('<span style="color: orange; font-weight: bold;">Split Decision ({}-{})</span>', f1_wins, f2_wins)
    get_decision_summary.short_description = 'Overall Decision'
    
    def get_all_judges_count(self, obj):
        """Display total number of judges"""
        count = obj.fight.scorecards.count()
        return f"{count} judges"
    get_all_judges_count.short_description = 'Judge Count'
    
    fieldsets = (
        ('Fight Information', {
            'fields': (
                'get_fight_header',
                'fight',
            )
        }),
        ('ALL Judges\' Scorecards - Consolidated View (MMADecisions.com style)', {
            'fields': (
                'get_judge_scorecard_table',
            ),
            'classes': ('wide',),
        }),
        ('Manage Individual Judge Scores', {
            'fields': (
                'get_judge_management_info',
            ),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['get_fight_header', 'get_judge_scorecard_table', 'get_judge_management_info']
    autocomplete_fields = ['fight']
    
    def get_judge_management_info(self, obj):
        """Information about managing individual judge scores"""
        if not obj.pk:
            return "Save to manage judge scores"
            
        all_scorecards = obj.fight.scorecards.all()
        
        info_html = f'''
        <div style="padding: 15px; background: #f0f8ff; border-radius: 5px; border: 1px solid #0066cc;">
            <h4 style="margin: 0 0 15px 0; color: #0066cc;">Individual Judge Score Management</h4>
            <p style="margin: 0 0 10px 0;">This interface shows <strong>ALL judges consolidated</strong>, but you can still manage individual judges:</p>
            <ul style="margin: 0;">
        '''
        
        for scorecard in all_scorecards:
            edit_url = f'/admin/events/scorecard/{scorecard.pk}/change/'
            info_html += f'''
                <li style="margin: 5px 0;">
                    <strong>{scorecard.judge_name}:</strong> {scorecard.fighter1_score}-{scorecard.fighter2_score} 
                    [<a href="{edit_url}">Edit Individual Judge</a>]
                </li>
            '''
        
        info_html += '''
            </ul>
            <p style="margin: 10px 0 0 0; color: #666; font-size: 12px;">
                <strong>Note:</strong> Use the consolidated table above to view all judges together, 
                or click individual judge links to edit specific scorecards.
            </p>
        </div>
        '''
        
        return format_html(info_html)
    get_judge_management_info.short_description = 'Individual Judge Management'
    
    def get_fight_header(self, obj):
        """Display fight header like MMADecisions.com"""
        if not obj.pk:
            return "Save to view fight header"
            
        fight = obj.fight
        participants = fight.participants.all()
        if len(participants) >= 2:
            fighter1_name = participants[0].fighter.get_full_name()
            fighter2_name = participants[1].fighter.get_full_name()
        else:
            fighter1_name = "Fighter 1"
            fighter2_name = "Fighter 2"
            
        return format_html(
            '<div style="background: #cc6600; color: white; padding: 20px; border-radius: 5px; margin: 10px 0;">'\
            '<h2 style="margin: 0 0 10px 0;">⚖️ Official Judge Scorecards - All Judges</h2>'\
            '<h3 style="margin: 0 0 10px 0;">{} vs {}</h3>'\
            '<p style="margin: 0; font-size: 16px;">{} • {} • {}</p>'\
            '<p style="margin: 5px 0 0 0;">Method: {} ({})</p>'\
            '<p style="margin: 5px 0 0 0; font-size: 14px;">Currently viewing: Judge {}</p>'\
            '</div>',
            fighter1_name,
            fighter2_name,
            fight.event.name,
            fight.event.date,
            fight.get_status_display(),
            fight.method,
            fight.method_details,
            obj.judge_name
        )
    get_fight_header.short_description = 'Fight Header'
    
    def get_judge_scorecard_table(self, obj):
        """Display ALL judges' scorecards for this fight in MMADecisions.com table format"""
        if not obj.pk:
            return "Save to view scorecards"
            
        fight = obj.fight
        participants = fight.participants.all()
        all_scorecards = fight.scorecards.all().order_by('judge_name')
        
        if len(participants) >= 2:
            fighter1_name = participants[0].fighter.get_full_name()
            fighter2_name = participants[1].fighter.get_full_name()
        else:
            fighter1_name = "Fighter 1"
            fighter2_name = "Fighter 2"
        
        if not all_scorecards:
            return format_html(
                '<div style="text-align: center; padding: 40px; background: #f9f9f9; border-radius: 5px;">'\
                '<h3>No Official Scorecards Available</h3>'\
                '<p>Add judge scorecards for this fight</p>'\
                '</div>'
            )
        
        # Determine number of rounds (could be 3 or 5)
        max_rounds = 0
        for scorecard in all_scorecards:
            round_details = scorecard.round_details.all()
            if round_details:
                max_rounds = max(max_rounds, max(rd.round_number for rd in round_details))
        
        if max_rounds == 0:
            max_rounds = 3  # Default to 3 rounds if no round details
        
        # Build consolidated MMADecisions.com style table
        table_html = f'''
        <div style="margin: 20px 0;">
            <h3 style="color: #cc6600; margin-bottom: 15px;">⚖️ Official Judge Scorecards - All Judges (MMADecisions.com style)</h3>
            
            <!-- Official Decision Summary -->
            <div style="margin-bottom: 20px; padding: 15px; background: #fff8f0; border-radius: 5px; border: 2px solid #cc6600;">
                <h4 style="margin: 0 0 10px 0; color: #cc6600;">🏆 Official Decision</h4>
                <div style="display: flex; gap: 20px; flex-wrap: wrap;">
        '''
        
        # Display each judge's final score
        for scorecard in all_scorecards:
            score_color = 'green' if scorecard.fighter1_score > scorecard.fighter2_score else 'blue' if scorecard.fighter2_score > scorecard.fighter1_score else 'orange'
            table_html += f'''
                <div style="text-align: center;">
                    <div style="font-weight: bold; margin-bottom: 5px;">{scorecard.judge_name}</div>
                    <div style="font-size: 18px; color: {score_color}; font-weight: bold;">
                        {scorecard.fighter1_score}-{scorecard.fighter2_score}
                    </div>
                </div>
            '''
        
        # Determine overall winner
        f1_wins = sum(1 for sc in all_scorecards if sc.fighter1_score > sc.fighter2_score)
        f2_wins = sum(1 for sc in all_scorecards if sc.fighter2_score > sc.fighter1_score)
        if f1_wins > f2_wins:
            decision = f"{fighter1_name} wins ({f1_wins}-{f2_wins})"
            decision_color = "green"
        elif f2_wins > f1_wins:
            decision = f"{fighter2_name} wins ({f2_wins}-{f1_wins})"
            decision_color = "blue"
        else:
            decision = f"Split decision ({f1_wins}-{f2_wins})"
            decision_color = "orange"
        
        table_html += f'''
                </div>
                <div style="margin-top: 15px; text-align: center;">
                    <strong style="font-size: 20px; color: {decision_color};">Official Result: {decision}</strong>
                </div>
            </div>
            
            <!-- Round-by-Round Comparison Table -->
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead>
                    <tr style="background: #cc6600; color: white;">
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: center;">Round</th>
                        <th style="padding: 12px; border: 1px solid #ddd;">{fighter1_name}</th>
                        <th style="padding: 12px; border: 1px solid #ddd;">{fighter2_name}</th>
        '''
        
        # Add column for each judge
        for scorecard in all_scorecards:
            table_html += f'<th style="padding: 12px; border: 1px solid #ddd; text-align: center;">{scorecard.judge_name}</th>'
        
        table_html += '''
                    </tr>
                </thead>
                <tbody>
        '''
        
        # Create rows for each round
        for round_num in range(1, max_rounds + 1):
            table_html += f'''
                <tr style="background: {'#f8f9fa' if round_num % 2 == 0 else 'white'};">
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-weight: bold;">
                        Round {round_num}
                    </td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-weight: bold; color: #0066cc;">
                        {fighter1_name}
                    </td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-weight: bold; color: #cc6600;">
                        {fighter2_name}
                    </td>
            '''
            
            # Add each judge's score for this round
            for scorecard in all_scorecards:
                round_detail = scorecard.round_details.filter(round_number=round_num).first()
                if round_detail:
                    winner = round_detail.get_round_winner()
                    if winner == 'fighter1':
                        score_color = '#0066cc'
                        score_text = f'<strong>{round_detail.fighter1_round_score}-{round_detail.fighter2_round_score}</strong>'
                    elif winner == 'fighter2':
                        score_color = '#cc6600'
                        score_text = f'<strong>{round_detail.fighter1_round_score}-{round_detail.fighter2_round_score}</strong>'
                    elif winner == 'draw':
                        score_color = '#ff8800'
                        score_text = f'<strong>{round_detail.fighter1_round_score}-{round_detail.fighter2_round_score}</strong>'
                    else:
                        score_color = '#666'
                        score_text = 'Unknown'
                    
                    table_html += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: center; color: {score_color};">{score_text}</td>'
                else:
                    table_html += '<td style="padding: 10px; border: 1px solid #ddd; text-align: center; color: #999;">-</td>'
            
            table_html += '</tr>'
        
        # Add totals row
        table_html += f'''
                <tr style="background: #e9ecef; font-weight: bold;">
                    <td style="padding: 12px; border: 1px solid #ddd; text-align: center;">
                        <strong>TOTAL</strong>
                    </td>
                    <td style="padding: 12px; border: 1px solid #ddd; text-align: center; color: #0066cc;">
                        <strong>{fighter1_name}</strong>
                    </td>
                    <td style="padding: 12px; border: 1px solid #ddd; text-align: center; color: #cc6600;">
                        <strong>{fighter2_name}</strong>
                    </td>
        '''
        
        for scorecard in all_scorecards:
            total_color = 'green' if scorecard.fighter1_score > scorecard.fighter2_score else 'blue' if scorecard.fighter2_score > scorecard.fighter1_score else 'orange'
            table_html += f'''
                <td style="padding: 12px; border: 1px solid #ddd; text-align: center; color: {total_color};">
                    <strong>{scorecard.fighter1_score}-{scorecard.fighter2_score}</strong>
                </td>
            '''
        
        table_html += '''
                </tr>
                </tbody>
            </table>
            
            <div style="margin-top: 15px; padding: 10px; background: #f0f8ff; border-radius: 3px;">
                <p style="margin: 0; color: #666; font-size: 12px;">
                    <strong>Scoring Criteria:</strong> 10-9 rounds are close, 10-8 rounds show clear dominance, 10-7 rounds show extreme dominance<br>
                    <strong>Official MMA Judging:</strong> Based on Effective Striking, Effective Grappling, Control, and Aggression
                </p>
            </div>
        </div>
        '''
        
        return format_html(table_html)
    get_judge_scorecard_table.short_description = 'All Judges Scorecards Table'
    
    def get_fight_display(self, obj):
        """Display fight"""
        return str(obj.fight)
    get_fight_display.short_description = 'Fight'


# RoundStatistics and RoundScore are now managed exclusively through their parent admin inlines
# This eliminates the need for separate admin pages and keeps related data together


