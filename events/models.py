import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from organizations.models import Organization, WeightClass
from fighters.models import Fighter


class Event(models.Model):
    """MMA Events"""
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='events')
    
    # Event details
    name = models.CharField(max_length=255)
    event_number = models.PositiveIntegerField(null=True, blank=True)
    date = models.DateField()
    location = models.CharField(max_length=255)
    venue = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Event metrics
    attendance = models.PositiveIntegerField(null=True, blank=True)
    gate_revenue = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ppv_buys = models.PositiveIntegerField(null=True, blank=True, help_text="Pay-per-view purchases")
    broadcast_info = models.JSONField(default=dict, blank=True)
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    poster_url = models.URLField(blank=True)
    wikipedia_url = models.URLField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'events'
        verbose_name = 'Event'
        verbose_name_plural = 'Events'
        ordering = ['-date', 'name']
        indexes = [
            models.Index(fields=['-date'], name='idx_events_date'),
            models.Index(fields=['organization'], name='idx_events_organization'),
            models.Index(fields=['status'], name='idx_events_status'),
        ]
    
    def __str__(self):
        return f"{self.organization.abbreviation}: {self.name}"
    
    def get_main_event(self):
        """Get the main event fight"""
        return self.fights.filter(is_main_event=True).first()
    
    def get_fight_count(self):
        """Get total number of fights on card"""
        return self.fights.count()


class Fight(models.Model):
    """Individual fights within events"""
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_contest', 'No Contest'),
    ]
    
    RESULT_CHOICES = [
        ('win', 'Win'),
        ('loss', 'Loss'),
        ('draw', 'Draw'),
        ('no_contest', 'No Contest'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='fights')
    weight_class = models.ForeignKey(WeightClass, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Fight details
    fight_order = models.PositiveIntegerField(help_text="Order on the card (1 = main event)")
    is_main_event = models.BooleanField(default=False)
    is_title_fight = models.BooleanField(default=False)
    is_interim_title = models.BooleanField(default=False)
    scheduled_rounds = models.PositiveIntegerField(default=3)
    
    # Fight outcome
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    winner = models.ForeignKey(Fighter, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_fights')
    method = models.CharField(max_length=50, blank=True, help_text="KO, TKO, Submission, Decision, etc.")
    method_details = models.CharField(max_length=255, blank=True, help_text="Specific submission type, etc.")
    ending_round = models.PositiveIntegerField(null=True, blank=True)
    ending_time = models.CharField(max_length=10, blank=True, help_text="Time format: MM:SS")
    referee = models.CharField(max_length=100, blank=True)
    
    # Performance bonuses
    performance_bonuses = models.JSONField(default=list, blank=True, 
                                         help_text="List of bonus types awarded")
    
    # Metadata
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'fights'
        verbose_name = 'Fight'
        verbose_name_plural = 'Fights'
        ordering = ['event', 'fight_order']
        indexes = [
            models.Index(fields=['event'], name='idx_fights_event'),
            models.Index(fields=['status'], name='idx_fights_status'),
            models.Index(fields=['event', 'fight_order'], name='idx_fights_date'),
        ]
        unique_together = ['event', 'fight_order']
    
    def __str__(self):
        fighters = self.participants.all()[:2]
        if len(fighters) == 2:
            return f"{fighters[0].fighter.get_full_name()} vs {fighters[1].fighter.get_full_name()}"
        return f"Fight {self.fight_order} - {self.event.name}"
    
    def get_fighters(self):
        """Get both fighters in the fight"""
        return [p.fighter for p in self.participants.all()[:2]]
    
    def is_decision(self):
        """Check if fight went to decision"""
        return 'decision' in self.method.lower() if self.method else False
    
    # Interconnected Fight History Methods
    
    def create_history_perspectives(self):
        """
        Create FightHistory records for both fighters' perspectives.
        This makes Fight the authoritative source with bidirectional history views.
        """
        from fighters.models import FightHistory
        
        participants = list(self.participants.all()[:2])
        if len(participants) != 2:
            return []
        
        created_histories = []
        
        for i, participant in enumerate(participants):
            opponent = participants[1-i]  # Get the other fighter
            
            # Check if history already exists for this perspective
            history, created = FightHistory.objects.get_or_create(
                authoritative_fight=self,
                perspective_fighter=participant.fighter,
                defaults={
                    'fighter': participant.fighter,  # Legacy field
                    'result': participant.result or 'win' if participant == self.winner else 'loss',
                    'opponent_full_name': opponent.fighter.get_full_name(),
                    'opponent_first_name': opponent.fighter.first_name,
                    'opponent_last_name': opponent.fighter.last_name,
                    'opponent_fighter': opponent.fighter,
                    'event_name': self.event.name,
                    'event_date': self.event.date,
                    'event': self.event,
                    'method': self.method,
                    'method_details': self.method_details,
                    'ending_round': self.ending_round,
                    'ending_time': self.ending_time,
                    'scheduled_rounds': self.scheduled_rounds,
                    'is_title_fight': self.is_title_fight,
                    'is_interim_title': self.is_interim_title,
                    'weight_class': self.weight_class,
                    'weight_class_name': self.weight_class.name if self.weight_class else '',
                    'organization': self.event.organization,
                    'organization_name': self.event.organization.name,
                    'location': self.event.location,
                    'venue': self.event.venue,
                    'city': self.event.city,
                    'state': self.event.state,
                    'country': self.event.country,
                    'fight_order': self.get_fighter_career_order(participant.fighter),
                    'data_source': 'authoritative_fight',
                    'is_authoritative_derived': True,
                    'reconciled_at': timezone.now(),
                }
            )
            
            # Update existing record if not created
            if not created:
                self._update_history_from_fight(history, participant, opponent)
            
            created_histories.append(history)
        
        return created_histories
    
    def _update_history_from_fight(self, history, participant, opponent):
        """Update existing FightHistory record with current Fight data."""
        changed = False
        
        # Update core result
        expected_result = participant.result or ('win' if self.winner == participant.fighter else 'loss')
        if history.result != expected_result:
            history.result = expected_result
            changed = True
        
        # Update opponent information
        if history.opponent_full_name != opponent.fighter.get_full_name():
            history.opponent_full_name = opponent.fighter.get_full_name()
            history.opponent_first_name = opponent.fighter.first_name
            history.opponent_last_name = opponent.fighter.last_name
            history.opponent_fighter = opponent.fighter
            changed = True
        
        # Update event information
        if history.event_name != self.event.name:
            history.event_name = self.event.name
            changed = True
        if history.event_date != self.event.date:
            history.event_date = self.event.date
            changed = True
        if history.event != self.event:
            history.event = self.event
            changed = True
        
        # Update fight details
        if history.method != self.method:
            history.method = self.method
            changed = True
        if history.method_details != self.method_details:
            history.method_details = self.method_details
            changed = True
        if history.ending_round != self.ending_round:
            history.ending_round = self.ending_round
            changed = True
        if history.ending_time != self.ending_time:
            history.ending_time = self.ending_time
            changed = True
        if history.is_title_fight != self.is_title_fight:
            history.is_title_fight = self.is_title_fight
            changed = True
        if history.is_interim_title != self.is_interim_title:
            history.is_interim_title = self.is_interim_title
            changed = True
        
        if changed:
            # Add sync metadata
            if not history.parsed_data:
                history.parsed_data = {}
            history.parsed_data['last_fight_sync'] = timezone.now().isoformat()
            history.save()
    
    def get_fighter_career_order(self, fighter):
        """Calculate this fight's order in the fighter's career."""
        from fighters.models import FightHistory
        
        # Count fights before this date for the fighter
        earlier_fights = FightHistory.objects.filter(
            perspective_fighter=fighter,
            event_date__lt=self.event.date
        ).count()
        
        # Also check Fight records for more accuracy
        earlier_authoritative_fights = Fight.objects.filter(
            participants__fighter=fighter,
            event__date__lt=self.event.date
        ).distinct().count()
        
        # Use the higher count for accuracy
        return max(earlier_fights, earlier_authoritative_fights) + 1
    
    def sync_history_perspectives(self):
        """
        Sync all associated FightHistory records with current Fight data.
        Call this when Fight data changes to keep history views up to date.
        """
        from fighters.models import FightHistory
        
        histories = FightHistory.objects.filter(authoritative_fight=self)
        synced_count = 0
        
        for history in histories:
            if history.sync_from_authoritative_fight():
                synced_count += 1
        
        return synced_count
    
    def get_history_perspectives(self):
        """Get all FightHistory records that represent perspectives of this fight."""
        from fighters.models import FightHistory
        
        return FightHistory.objects.filter(
            authoritative_fight=self
        ).select_related('perspective_fighter', 'opponent_fighter')
    
    def has_complete_history_perspectives(self):
        """Check if this fight has history perspectives for both fighters."""
        perspectives = self.get_history_perspectives()
        participant_fighters = set(p.fighter for p in self.participants.all())
        perspective_fighters = set(h.perspective_fighter for h in perspectives)
        
        return participant_fighters == perspective_fighters
    
    def save(self, *args, **kwargs):
        """Override save to maintain FightHistory perspectives."""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Create/update history perspectives after save (but not for new records to avoid issues)
        if not is_new and self.participants.exists():
            self.create_history_perspectives()


class FightParticipant(models.Model):
    """Many-to-many relationship between fights and fighters"""
    
    CORNER_CHOICES = [
        ('red', 'Red Corner'),
        ('blue', 'Blue Corner'),
    ]
    
    RESULT_CHOICES = [
        ('win', 'Win'),
        ('loss', 'Loss'),
        ('draw', 'Draw'),
        ('no_contest', 'No Contest'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fight = models.ForeignKey(Fight, on_delete=models.CASCADE, related_name='participants')
    fighter = models.ForeignKey(Fighter, on_delete=models.CASCADE, related_name='fight_participations')
    
    corner = models.CharField(max_length=10, choices=CORNER_CHOICES)
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, blank=True)
    weigh_in_weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    purse = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'fight_participants'
        verbose_name = 'Fight Participant'
        verbose_name_plural = 'Fight Participants'
        unique_together = [['fight', 'fighter'], ['fight', 'corner']]
        indexes = [
            models.Index(fields=['fighter'], name='idx_participants_fighter'),
            models.Index(fields=['fight'], name='idx_participants_fight'),
        ]
    
    def __str__(self):
        return f"{self.fighter.get_full_name()} ({self.corner} corner) - {self.fight}"


class FightStatistics(models.Model):
    """Detailed fight statistics"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fight = models.OneToOneField(Fight, on_delete=models.CASCADE, related_name='statistics')
    fighter1 = models.ForeignKey(Fighter, on_delete=models.CASCADE, related_name='fight_stats_1')
    fighter2 = models.ForeignKey(Fighter, on_delete=models.CASCADE, related_name='fight_stats_2')
    
    # Striking statistics
    fighter1_strikes_landed = models.PositiveIntegerField(default=0)
    fighter1_strikes_attempted = models.PositiveIntegerField(default=0)
    fighter2_strikes_landed = models.PositiveIntegerField(default=0)
    fighter2_strikes_attempted = models.PositiveIntegerField(default=0)
    
    # Grappling statistics
    fighter1_takedowns = models.PositiveIntegerField(default=0)
    fighter1_takedown_attempts = models.PositiveIntegerField(default=0)
    fighter2_takedowns = models.PositiveIntegerField(default=0)
    fighter2_takedown_attempts = models.PositiveIntegerField(default=0)
    
    # Control time (in seconds)
    fighter1_control_time = models.PositiveIntegerField(default=0)
    fighter2_control_time = models.PositiveIntegerField(default=0)
    
    # Additional detailed statistics
    detailed_stats = models.JSONField(default=dict, blank=True)
    json_data = models.TextField(blank=True, help_text="Paste JSON data here to import fight statistics")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'fight_statistics'
        verbose_name = 'Fight Statistics'
        verbose_name_plural = 'Fight Statistics'
    
    def __str__(self):
        return f"Stats: {self.fight}"


class Scorecard(models.Model):
    """Judge scorecards for decision fights"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fight = models.ForeignKey(Fight, on_delete=models.CASCADE, related_name='scorecards')
    judge_name = models.CharField(max_length=100)
    fighter1_score = models.PositiveIntegerField(default=0)
    fighter2_score = models.PositiveIntegerField(default=0)
    round_scores = models.JSONField(default=dict, help_text="Round-by-round scores as array")
    json_data = models.TextField(blank=True, help_text="Paste JSON data here to import scorecard")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'scorecards'
        verbose_name = 'Scorecard'
        verbose_name_plural = 'Scorecards'
        indexes = [
            models.Index(fields=['fight'], name='idx_scorecards_fight'),
        ]
    
    def __str__(self):
        return f"{self.judge_name}: {self.fighter1_score}-{self.fighter2_score} - {self.fight}"
    
    def get_total_rounds(self):
        """Get total number of rounds from round details"""
        return self.round_details.count()
    
    def get_round_summary(self):
        """Get a summary of round-by-round scoring"""
        rounds = []
        for round_detail in self.round_details.all():
            rounds.append(f"R{round_detail.round_number}: {round_detail.fighter1_round_score}-{round_detail.fighter2_round_score}")
        return " | ".join(rounds) if rounds else str(self.round_scores)


class RoundStatistics(models.Model):
    """Round-by-round fight statistics (UFCstats.com style)"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fight_statistics = models.ForeignKey(FightStatistics, on_delete=models.CASCADE, related_name='round_stats')
    round_number = models.PositiveIntegerField()
    
    # Fighter 1 Striking Statistics (by target)
    fighter1_head_strikes_landed = models.PositiveIntegerField(default=0)
    fighter1_head_strikes_attempted = models.PositiveIntegerField(default=0)
    fighter1_body_strikes_landed = models.PositiveIntegerField(default=0)
    fighter1_body_strikes_attempted = models.PositiveIntegerField(default=0)
    fighter1_leg_strikes_landed = models.PositiveIntegerField(default=0)
    fighter1_leg_strikes_attempted = models.PositiveIntegerField(default=0)
    
    # Fighter 1 Striking by Position
    fighter1_distance_strikes_landed = models.PositiveIntegerField(default=0)
    fighter1_distance_strikes_attempted = models.PositiveIntegerField(default=0)
    fighter1_clinch_strikes_landed = models.PositiveIntegerField(default=0)
    fighter1_clinch_strikes_attempted = models.PositiveIntegerField(default=0)
    fighter1_ground_strikes_landed = models.PositiveIntegerField(default=0)
    fighter1_ground_strikes_attempted = models.PositiveIntegerField(default=0)
    
    # Fighter 1 Grappling
    fighter1_takedowns_landed = models.PositiveIntegerField(default=0)
    fighter1_takedown_attempts = models.PositiveIntegerField(default=0)
    fighter1_submission_attempts = models.PositiveIntegerField(default=0)
    fighter1_reversals = models.PositiveIntegerField(default=0)
    fighter1_control_time = models.PositiveIntegerField(default=0)  # seconds
    
    # Fighter 1 Other Stats
    fighter1_knockdowns = models.PositiveIntegerField(default=0)
    fighter1_total_strikes_landed = models.PositiveIntegerField(default=0)
    fighter1_total_strikes_attempted = models.PositiveIntegerField(default=0)
    
    # Fighter 2 - Same structure
    fighter2_head_strikes_landed = models.PositiveIntegerField(default=0)
    fighter2_head_strikes_attempted = models.PositiveIntegerField(default=0)
    fighter2_body_strikes_landed = models.PositiveIntegerField(default=0)
    fighter2_body_strikes_attempted = models.PositiveIntegerField(default=0)
    fighter2_leg_strikes_landed = models.PositiveIntegerField(default=0)
    fighter2_leg_strikes_attempted = models.PositiveIntegerField(default=0)
    
    fighter2_distance_strikes_landed = models.PositiveIntegerField(default=0)
    fighter2_distance_strikes_attempted = models.PositiveIntegerField(default=0)
    fighter2_clinch_strikes_landed = models.PositiveIntegerField(default=0)
    fighter2_clinch_strikes_attempted = models.PositiveIntegerField(default=0)
    fighter2_ground_strikes_landed = models.PositiveIntegerField(default=0)
    fighter2_ground_strikes_attempted = models.PositiveIntegerField(default=0)
    
    fighter2_takedowns_landed = models.PositiveIntegerField(default=0)
    fighter2_takedown_attempts = models.PositiveIntegerField(default=0)
    fighter2_submission_attempts = models.PositiveIntegerField(default=0)
    fighter2_reversals = models.PositiveIntegerField(default=0)
    fighter2_control_time = models.PositiveIntegerField(default=0)
    
    fighter2_knockdowns = models.PositiveIntegerField(default=0)
    fighter2_total_strikes_landed = models.PositiveIntegerField(default=0)
    fighter2_total_strikes_attempted = models.PositiveIntegerField(default=0)
    
    # Round metadata
    round_duration = models.PositiveIntegerField(default=300)  # seconds, default 5 minutes
    round_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'round_statistics'
        verbose_name = 'Round Statistics'
        verbose_name_plural = 'Round Statistics'
        ordering = ['fight_statistics', 'round_number']
        unique_together = [['fight_statistics', 'round_number']]
        indexes = [
            models.Index(fields=['fight_statistics', 'round_number'], name='idx_round_stats_fight_round'),
        ]
    
    def __str__(self):
        return f"Round {self.round_number} Stats - {self.fight_statistics.fight}"
    
    def get_fighter1_striking_accuracy(self):
        """Calculate fighter 1's striking accuracy for this round"""
        if self.fighter1_total_strikes_attempted == 0:
            return 0
        return round((self.fighter1_total_strikes_landed / self.fighter1_total_strikes_attempted) * 100, 1)
    
    def get_fighter2_striking_accuracy(self):
        """Calculate fighter 2's striking accuracy for this round"""
        if self.fighter2_total_strikes_attempted == 0:
            return 0
        return round((self.fighter2_total_strikes_landed / self.fighter2_total_strikes_attempted) * 100, 1)
    
    def get_fighter1_takedown_accuracy(self):
        """Calculate fighter 1's takedown accuracy for this round"""
        if self.fighter1_takedown_attempts == 0:
            return 0
        return round((self.fighter1_takedowns_landed / self.fighter1_takedown_attempts) * 100, 1)
        
    def get_fighter2_takedown_accuracy(self):
        """Calculate fighter 2's takedown accuracy for this round"""
        if self.fighter2_takedown_attempts == 0:
            return 0
        return round((self.fighter2_takedowns_landed / self.fighter2_takedown_attempts) * 100, 1)


class RoundScore(models.Model):
    """Detailed round-by-round scoring (MMADecisions.com style)"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scorecard = models.ForeignKey(Scorecard, on_delete=models.CASCADE, related_name='round_details')
    round_number = models.PositiveIntegerField()
    fighter1_round_score = models.PositiveIntegerField()  # Usually 10 or 9
    fighter2_round_score = models.PositiveIntegerField()  # Usually 9 or 8
    
    # Detailed scoring criteria (optional)
    fighter1_effective_striking = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    fighter1_effective_grappling = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    fighter1_control = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    fighter1_aggression = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    
    fighter2_effective_striking = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    fighter2_effective_grappling = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    fighter2_control = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    fighter2_aggression = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    
    # Round notes and highlights
    round_notes = models.TextField(blank=True)
    key_moments = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'round_scores'
        verbose_name = 'Round Score'
        verbose_name_plural = 'Round Scores'
        ordering = ['scorecard', 'round_number']
        unique_together = [['scorecard', 'round_number']]
        indexes = [
            models.Index(fields=['scorecard', 'round_number'], name='idx_round_score_card_round'),
        ]
    
    def __str__(self):
        return f"Round {self.round_number}: {self.fighter1_round_score}-{self.fighter2_round_score} ({self.scorecard.judge_name})"
    
    def get_round_winner(self):
        """Determine round winner"""
        if self.fighter1_round_score is None or self.fighter2_round_score is None:
            return 'unknown'
        
        if self.fighter1_round_score > self.fighter2_round_score:
            return 'fighter1'
        elif self.fighter2_round_score > self.fighter1_round_score:
            return 'fighter2'
        else:
            return 'draw'
    
    def get_score_display(self):
        """Get formatted score display"""
        return f"{self.fighter1_round_score}-{self.fighter2_round_score}"


class MediaScorecard(models.Model):
    """Media/Fan scorecards for controversial decisions"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fight = models.ForeignKey(Fight, on_delete=models.CASCADE, related_name='media_scorecards')
    media_outlet = models.CharField(max_length=100)
    scorer_name = models.CharField(max_length=100)
    fighter1_score = models.PositiveIntegerField()
    fighter2_score = models.PositiveIntegerField()
    round_scores = models.JSONField(help_text="Round-by-round scores as array")
    scorecard_url = models.URLField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'media_scorecards'
        verbose_name = 'Media Scorecard'
        verbose_name_plural = 'Media Scorecards'
        indexes = [
            models.Index(fields=['fight'], name='idx_media_scorecard_fight'),
        ]
    
    def __str__(self):
        return f"{self.media_outlet} ({self.scorer_name}): {self.fighter1_score}-{self.fighter2_score} - {self.fight}"
    
    def get_decision_display(self):
        """Get decision type display"""
        if self.fighter1_score > self.fighter2_score:
            return f"Fighter 1 by UD {self.fighter1_score}-{self.fighter2_score}"
        elif self.fighter2_score > self.fighter1_score:
            return f"Fighter 2 by UD {self.fighter2_score}-{self.fighter1_score}"
        else:
            return f"Draw {self.fighter1_score}-{self.fighter2_score}"


class FightStoryline(models.Model):
    """Editorial storylines for all fights - rich content for fight promotion and analysis"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fight = models.OneToOneField(Fight, on_delete=models.CASCADE, related_name='storyline')
    
    # Main storyline content
    headline = models.CharField(max_length=255, help_text="Main headline for the fight storyline")
    summary = models.TextField(help_text="Brief summary of the fight's significance")
    
    # Fighter backgrounds and stakes
    fighter1_background = models.TextField(blank=True, help_text="Fighter 1's career background and journey to this fight")
    fighter1_stakes = models.TextField(blank=True, help_text="What's at stake for Fighter 1")
    fighter1_keys_to_victory = models.TextField(blank=True, help_text="Fighter 1's keys to victory")
    
    fighter2_background = models.TextField(blank=True, help_text="Fighter 2's career background and journey to this fight")
    fighter2_stakes = models.TextField(blank=True, help_text="What's at stake for Fighter 2")
    fighter2_keys_to_victory = models.TextField(blank=True, help_text="Fighter 2's keys to victory")
    
    # Fight context and rivalry
    rivalry_history = models.TextField(blank=True, help_text="History and beef between the fighters")
    title_implications = models.TextField(blank=True, help_text="Championship or ranking implications")
    historical_significance = models.TextField(blank=True, help_text="Historical context and significance")
    
    # Key facts and predictions
    key_facts = models.JSONField(default=list, blank=True, help_text="Key facts and statistics")
    expert_predictions = models.JSONField(default=list, blank=True, help_text="Expert predictions and analysis")
    
    # Editorial metadata
    author = models.CharField(max_length=100, blank=True, help_text="Author/Editor of the storyline")
    publication_date = models.DateTimeField(null=True, blank=True)
    featured_image_url = models.URLField(blank=True, help_text="Main image for the storyline")
    
    # JSON import functionality
    json_data = models.TextField(blank=True, help_text="Paste JSON data here to import storyline content")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'fight_storylines'
        verbose_name = 'Fight Storyline'
        verbose_name_plural = 'Fight Storylines'
        indexes = [
            models.Index(fields=['fight'], name='idx_storylines_fight'),
            models.Index(fields=['publication_date'], name='idx_storylines_pub_date'),
        ]
    
    def __str__(self):
        return f"Storyline: {self.headline} - {self.fight}"
    
    def get_fighters(self):
        """Get both fighters in the storyline fight"""
        return self.fight.get_fighters()
    
    def is_main_or_co_main(self):
        """Check if this is for a main or co-main event (legacy method - now available for all fights)"""
        return self.fight.fight_order <= 2
    
    def get_word_count(self):
        """Calculate total word count for all text fields"""
        text_fields = [
            self.summary, self.fighter1_background, self.fighter1_stakes, 
            self.fighter1_keys_to_victory, self.fighter2_background,
            self.fighter2_stakes, self.fighter2_keys_to_victory,
            self.rivalry_history, self.title_implications, self.historical_significance
        ]
        total_words = 0
        for field in text_fields:
            if field:
                total_words += len(field.split())
        return total_words
    
    def save(self, *args, **kwargs):
        """Override save to process JSON import data"""
        if self.json_data:
            try:
                import json
                data = json.loads(self.json_data)
                self._process_json_import(data)
                # Clear JSON data after processing
                self.json_data = ""
            except json.JSONDecodeError as e:
                # Keep the JSON data for user to fix
                pass
        
        super().save(*args, **kwargs)
    
    def _process_json_import(self, data):
        """Process imported JSON data"""
        # Basic storyline info
        if 'headline' in data:
            self.headline = data['headline']
        if 'summary' in data:
            self.summary = data['summary']
        if 'author' in data:
            self.author = data['author']
        if 'featured_image_url' in data:
            self.featured_image_url = data['featured_image_url']
        
        # Fighter 1 data
        fighter1_data = data.get('fighter1', {})
        if 'background' in fighter1_data:
            self.fighter1_background = fighter1_data['background']
        if 'stakes' in fighter1_data:
            self.fighter1_stakes = fighter1_data['stakes']
        if 'keys_to_victory' in fighter1_data:
            self.fighter1_keys_to_victory = fighter1_data['keys_to_victory']
        
        # Fighter 2 data
        fighter2_data = data.get('fighter2', {})
        if 'background' in fighter2_data:
            self.fighter2_background = fighter2_data['background']
        if 'stakes' in fighter2_data:
            self.fighter2_stakes = fighter2_data['stakes']
        if 'keys_to_victory' in fighter2_data:
            self.fighter2_keys_to_victory = fighter2_data['keys_to_victory']
        
        # Fight context
        if 'rivalry_history' in data:
            self.rivalry_history = data['rivalry_history']
        if 'title_implications' in data:
            self.title_implications = data['title_implications']
        if 'historical_significance' in data:
            self.historical_significance = data['historical_significance']
        
        # Lists
        if 'key_facts' in data and isinstance(data['key_facts'], list):
            self.key_facts = data['key_facts']
        if 'expert_predictions' in data and isinstance(data['expert_predictions'], list):
            self.expert_predictions = data['expert_predictions']
        
        # Handle publication date
        if 'publication_date' in data:
            try:
                from datetime import datetime
                self.publication_date = datetime.fromisoformat(data['publication_date'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass