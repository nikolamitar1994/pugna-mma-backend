import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class Fighter(models.Model):
    """Fighter model with structured names matching PostgreSQL schema"""
    
    # Stance choices
    STANCE_CHOICES = [
        ('orthodox', 'Orthodox'),
        ('southpaw', 'Southpaw'),
        ('switch', 'Switch'),
    ]
    
    # Data source choices
    DATA_SOURCE_CHOICES = [
        ('manual', 'Manual Entry'),
        ('wikipedia', 'Wikipedia'),
        ('ufc_stats', 'UFC Stats'),
        ('ai_completion', 'AI Completion'),
    ]
    
    # Primary identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Structured name fields (matching schema)
    first_name = models.CharField(max_length=100, help_text="Fighter's first name")
    last_name = models.CharField(max_length=100, blank=True, default='', 
                                help_text="Fighter's last name (empty for single-name fighters like 'Shogun')")
    display_name = models.CharField(max_length=255, blank=True, 
                                   help_text="Preferred display name (auto-generated if empty)")
    birth_first_name = models.CharField(max_length=100, blank=True, 
                                       help_text="Legal first name at birth")
    birth_last_name = models.CharField(max_length=100, blank=True, 
                                      help_text="Legal last name at birth")
    nickname = models.CharField(max_length=255, blank=True, 
                               help_text="Fighter nickname (e.g., 'Bones')")
    
    # Personal information
    date_of_birth = models.DateField(null=True, blank=True)
    birth_place = models.CharField(max_length=255, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    
    # Physical attributes
    height_cm = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(120), MaxValueValidator(250)],
        help_text="Height in centimeters"
    )
    weight_kg = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(40), MaxValueValidator(200)],
        help_text="Weight in kilograms"
    )
    reach_cm = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(120), MaxValueValidator(250)],
        help_text="Reach in centimeters"
    )
    stance = models.CharField(max_length=20, choices=STANCE_CHOICES, blank=True)
    
    # Career information
    fighting_out_of = models.CharField(max_length=255, blank=True)
    team = models.CharField(max_length=255, blank=True)
    years_active = models.CharField(max_length=100, blank=True, 
                                   help_text="e.g., '2010-present' or '2005-2018'")
    is_active = models.BooleanField(default=True)
    
    # Media and links
    profile_image_url = models.URLField(blank=True)
    wikipedia_url = models.URLField(blank=True)
    social_media = models.JSONField(default=dict, blank=True)
    
    # Career statistics (calculated fields)
    total_fights = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    draws = models.PositiveIntegerField(default=0)
    no_contests = models.PositiveIntegerField(default=0)
    
    # Win breakdown
    wins_by_ko = models.PositiveIntegerField(default=0, help_text="Wins by KO")
    wins_by_tko = models.PositiveIntegerField(default=0, help_text="Wins by TKO")
    wins_by_submission = models.PositiveIntegerField(default=0)
    wins_by_decision = models.PositiveIntegerField(default=0)
    
    # Data quality and source tracking
    data_source = models.CharField(max_length=50, choices=DATA_SOURCE_CHOICES, default='manual')
    data_quality_score = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Data completeness/quality score (0.0-1.0)"
    )
    last_data_update = models.DateTimeField(null=True, blank=True)
    
    # Search vector for full-text search
    search_vector = SearchVectorField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'fighters'
        verbose_name = 'Fighter'
        verbose_name_plural = 'Fighters'
        ordering = ['last_name', 'first_name']
        indexes = [
            # Search indexes matching schema
            models.Index(fields=['first_name', 'last_name'], name='idx_fighters_first_last'),
            models.Index(fields=['last_name'], name='idx_fighters_last_name'),
            models.Index(fields=['nationality'], name='idx_fighters_nationality'),
            models.Index(fields=['is_active'], name='idx_fighters_active'),
            # Full-text search index
            GinIndex(fields=['search_vector'], name='idx_fighters_search_vector'),
        ]
    
    def __str__(self):
        return self.get_full_name()
    
    def get_full_name(self):
        """Get full name - computed property matching PostgreSQL schema"""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name
    
    def get_display_name(self):
        """Get display name or fall back to full name"""
        return self.display_name or self.get_full_name()
    
    def get_record_string(self):
        """Get record string like '23-1-0 (1 NC)'"""
        record = f"{self.wins}-{self.losses}-{self.draws}"
        if self.no_contests > 0:
            record += f" ({self.no_contests} NC)"
        return record
    
    def get_finish_rate(self):
        """Calculate finish rate percentage"""
        if self.wins == 0:
            return 0.0
        finishes = self.wins_by_ko + self.wins_by_tko + self.wins_by_submission
        return round((finishes / self.wins) * 100, 1)
    
    def update_search_vector(self):
        """Update search vector for full-text search"""
        # For creation, we'll set this to None and update it later
        # SearchVector can only be used for updates, not inserts
        if self.pk:
            # Update existing record with proper SearchVector
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE fighters SET search_vector = to_tsvector('english', %s) WHERE id = %s",
                    [f"{self.first_name} {self.last_name} {self.nickname or ''}".strip(), str(self.id)]
                )
        else:
            # For new records, just set to None - we'll update after save
            self.search_vector = None
    
    def save(self, *args, **kwargs):
        """Override save to auto-generate display_name and update search vector"""
        # Auto-generate display_name if not provided
        if not self.display_name:
            self.display_name = self.get_full_name()
        
        # Update search vector before save
        self.update_search_vector()
        
        # Save the record
        super().save(*args, **kwargs)
        
        # Update search vector after save if this was a new record
        if not self.search_vector:
            self.update_search_vector()


class FighterNameVariation(models.Model):
    """Fighter name variations for search and matching"""
    
    VARIATION_TYPE_CHOICES = [
        ('alternative', 'Alternative Spelling'),
        ('translation', 'Translation'),
        ('nickname', 'Nickname Variation'),
        ('alias', 'Alias'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fighter = models.ForeignKey(Fighter, on_delete=models.CASCADE, related_name='name_variations')
    
    # Structured name variation fields
    first_name_variation = models.CharField(max_length=100, blank=True)
    last_name_variation = models.CharField(max_length=100, blank=True)
    full_name_variation = models.CharField(max_length=255)
    
    variation_type = models.CharField(max_length=50, choices=VARIATION_TYPE_CHOICES, default='alternative')
    source = models.CharField(max_length=100, blank=True, help_text="Where this variation was found")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'fighter_name_variations'
        verbose_name = 'Fighter Name Variation'
        verbose_name_plural = 'Fighter Name Variations'
        unique_together = ['fighter', 'full_name_variation']
        indexes = [
            models.Index(fields=['first_name_variation'], name='idx_name_var_first'),
            models.Index(fields=['last_name_variation'], name='idx_name_var_last'),
            models.Index(fields=['full_name_variation'], name='idx_name_var_full'),
        ]
    
    def __str__(self):
        return f"{self.fighter.get_full_name()} → {self.full_name_variation}"
    
    def save(self, *args, **kwargs):
        """Auto-generate full_name_variation if not provided"""
        if not self.full_name_variation:
            if self.last_name_variation:
                self.full_name_variation = f"{self.first_name_variation} {self.last_name_variation}"
            else:
                self.full_name_variation = self.first_name_variation
        super().save(*args, **kwargs)


class FightHistory(models.Model):
    """
    Structured fight history matching Wikipedia MMA record format.
    This model captures complete career history for each fighter with interconnected network support.
    """
    
    RESULT_CHOICES = [
        ('win', 'Win'),
        ('loss', 'Loss'),
        ('draw', 'Draw'),
        ('no_contest', 'No Contest'),
    ]
    
    METHOD_CHOICES = [
        # Simplified core methods
        ('decision', 'Decision'),
        ('ko', 'KO'),
        ('tko', 'TKO'),
        ('submission', 'Submission'),
        
        # Special cases (kept separate for clarity)
        ('disqualification', 'Disqualification'),
        ('forfeit', 'Forfeit'),
        ('no_contest', 'No Contest'),
        ('other', 'Other'),
    ]
    
    DATA_SOURCE_CHOICES = [
        ('wikipedia', 'Wikipedia'),
        ('manual', 'Manual Entry'),
        ('ufc_stats', 'UFC Stats'),
        ('sherdog', 'Sherdog'),
        ('tapology', 'Tapology'),
        ('ai_completion', 'AI Completion'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core relationship - which fighter this history belongs to
    fighter = models.ForeignKey(Fighter, on_delete=models.CASCADE, related_name='fight_history')
    
    # NEW: Link to authoritative Fight record (for interconnected network)
    fight = models.ForeignKey(
        'events.Fight', on_delete=models.CASCADE, null=True, blank=True,
        related_name='fighter_perspectives',
        help_text="Link to the authoritative Fight record (None for legacy data)"
    )
    
    # Fight result and record tracking
    result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    fighter_record_at_time = models.CharField(
        max_length=50, blank=True,
        help_text="Fighter's record at the time of this fight (e.g., '34-11 (1)')"
    )
    
    # Opponent information (structured like Fighter names)
    opponent_first_name = models.CharField(max_length=100, help_text="Opponent's first name")
    opponent_last_name = models.CharField(max_length=100, blank=True, help_text="Opponent's last name")
    opponent_full_name = models.CharField(max_length=255, help_text="Full opponent name as it appeared")
    opponent_fighter = models.ForeignKey(
        Fighter, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='opponent_history', help_text="Link to opponent's Fighter record if exists"
    )
    
    # Fight method and details (simplified)
    method = models.CharField(max_length=50, choices=METHOD_CHOICES, blank=True)
    method_description = models.CharField(
        max_length=255, blank=True,
        help_text="Method description (e.g., 'rear naked choke', 'unanimous', 'head kick and punches')"
    )
    # Legacy field - kept for backward compatibility during transition
    method_details = models.CharField(
        max_length=255, blank=True,
        help_text="Legacy method details field (deprecated - use method_description)"
    )
    
    # Event information
    event_name = models.CharField(max_length=255, help_text="Event name as it appeared")
    event_date = models.DateField(help_text="Date of the fight")
    event = models.ForeignKey(
        'events.Event', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='historical_fights', help_text="Link to Event record if exists"
    )
    
    # Fight timing
    ending_round = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Round the fight ended (1-12)"
    )
    ending_time = models.CharField(
        max_length=10, blank=True,
        help_text="Time in round when fight ended (MM:SS format)"
    )
    scheduled_rounds = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Number of scheduled rounds"
    )
    
    # Location information
    location = models.CharField(max_length=255, blank=True, help_text="Fight location")
    venue = models.CharField(max_length=255, blank=True, help_text="Venue name")
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Weight class and title information
    weight_class_name = models.CharField(max_length=100, blank=True, help_text="Weight class as it appeared")
    weight_class = models.ForeignKey(
        'organizations.WeightClass', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Link to WeightClass if exists"
    )
    is_title_fight = models.BooleanField(default=False)
    is_interim_title = models.BooleanField(default=False)
    title_belt = models.CharField(max_length=255, blank=True, help_text="Specific title belt name")
    
    # Additional context
    notes = models.TextField(blank=True, help_text="Additional notes or context from Wikipedia")
    performance_bonuses = models.JSONField(
        default=list, blank=True,
        help_text="Any performance bonuses awarded (Fight/Performance of the Night, etc.)"
    )
    
    # Organizational context
    organization_name = models.CharField(max_length=100, blank=True, help_text="Organization as it appeared")
    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Link to Organization if exists"
    )
    
    # Data source and quality
    data_source = models.CharField(max_length=50, choices=DATA_SOURCE_CHOICES, default='wikipedia')
    source_url = models.URLField(blank=True, help_text="URL where this data was found")
    parsed_data = models.JSONField(
        default=dict, blank=True,
        help_text="Raw parsed data from source for debugging"
    )
    data_quality_score = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Data completeness score (0.0-1.0)"
    )
    
    # Order and chronology
    fight_order = models.PositiveIntegerField(
        help_text="Chronological order of this fight in fighter's career (1 = first fight)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'fight_history'
        verbose_name = 'Fight History Record'
        verbose_name_plural = 'Fight History Records'
        ordering = ['fighter', '-fight_order']  # Most recent fights first for each fighter
        indexes = [
            # Fighter-specific indexes
            models.Index(fields=['fighter', '-fight_order'], name='idx_fh_fighter_order'),
            models.Index(fields=['fighter', 'result'], name='idx_fh_fighter_result'),
            models.Index(fields=['fighter', 'event_date'], name='idx_fh_fighter_date'),
            
            # Opponent searches
            models.Index(fields=['opponent_first_name'], name='idx_fh_opp_first'),
            models.Index(fields=['opponent_last_name'], name='idx_fh_opp_last'),
            models.Index(fields=['opponent_full_name'], name='idx_fh_opp_full'),
            models.Index(fields=['opponent_fighter'], name='idx_fh_opp_fighter'),
            
            # Event and date searches
            models.Index(fields=['event_date'], name='idx_fh_date'),
            models.Index(fields=['event_name'], name='idx_fh_event'),
            models.Index(fields=['organization'], name='idx_fh_org'),
            
            # Method and result analytics
            models.Index(fields=['method'], name='idx_fh_method'),
            models.Index(fields=['result', 'method'], name='idx_fh_result_method'),
            
            # Title fight searches
            models.Index(fields=['is_title_fight'], name='idx_fh_title'),
            
            # Data quality
            models.Index(fields=['data_source'], name='idx_fh_source'),
            models.Index(fields=['data_quality_score'], name='idx_fh_quality'),
        ]
        unique_together = ['fighter', 'fight_order']  # Ensure unique ordering per fighter
    
    def __str__(self):
        """String representation showing key fight info"""
        date_str = self.event_date.strftime('%Y-%m-%d') if self.event_date else 'Unknown Date'
        result_str = self.result.upper()
        method_str = f" by {self.method}" if self.method else ""
        return f"{self.fighter.get_full_name()} {result_str} vs {self.opponent_full_name}{method_str} ({date_str})"
    
    def get_opponent_display_name(self):
        """Get formatted opponent name (uses linked fighter if available)"""
        # Use linked opponent fighter if available (interconnected network)
        if self.opponent_fighter:
            return self.opponent_fighter.get_full_name()
        
        # Fallback to stored string data (legacy data)
        if self.opponent_last_name:
            return f"{self.opponent_first_name} {self.opponent_last_name}"
        return self.opponent_first_name
    
    @property
    def opponent(self):
        """Get the opponent Fighter object (interconnected network)"""
        if self.opponent_fighter:
            return self.opponent_fighter
        
        # If linked to Fight record, get opponent from there
        if self.fight:
            if self.fight.fighter_a == self.fighter:
                return self.fight.fighter_b
            return self.fight.fighter_a
        
        # No interconnected data available
        return None
    
    @property
    def linked_event(self):
        """Get the Event object through interconnected network"""
        if self.fight and self.fight.event:
            return self.fight.event
        
        # Try to find event by name and date (fallback)
        if self.event_name and self.event_date:
            from events.models import Event
            return Event.objects.filter(
                name__icontains=self.event_name,
                date=self.event_date
            ).first()
        
        return None
    
    @property
    def linked_organization(self):
        """Get the Organization through interconnected network"""
        event = self.linked_event
        if event and event.organization:
            return event.organization
        
        # Try to find organization by name (fallback)
        if self.organization_name:
            from organizations.models import Organization
            return Organization.objects.filter(
                name__icontains=self.organization_name
            ).first()
        
        return None
    
    def get_method_display(self):
        """Get human-readable method with description"""
        if not self.method:
            return "Unknown"
        
        method_display = dict(self.METHOD_CHOICES).get(self.method, self.method)
        
        # Use new method_description field first, fall back to legacy method_details
        description = self.method_description or self.method_details
        
        if description:
            return f"{method_display} ({description})"
        return method_display
    
    def get_location_display(self):
        """Get formatted location string"""
        if self.location:
            return self.location
        
        # Build location from components
        parts = []
        if self.venue:
            parts.append(self.venue)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.country:
            parts.append(self.country)
        
        return ", ".join(parts) if parts else "Unknown Location"
    
    def get_finish_details(self):
        """Get finish details for finishes"""
        if not self.ending_round or not self.ending_time:
            return None
        
        round_str = f"R{self.ending_round}"
        return f"{round_str} {self.ending_time}"
    
    def is_finish(self):
        """Check if this was a finish (not decision)"""
        return self.method and 'decision' not in self.method.lower()
    
    def calculate_data_quality(self):
        """Calculate data quality score based on filled fields"""
        total_fields = 20  # Core fields to check
        filled_fields = 0
        
        # Core required fields
        if self.result: filled_fields += 1
        if self.opponent_full_name: filled_fields += 1
        if self.event_name: filled_fields += 1
        if self.event_date: filled_fields += 1
        
        # Method information
        if self.method: filled_fields += 1
        if self.ending_round: filled_fields += 1
        if self.ending_time: filled_fields += 1
        
        # Location information
        if self.location or (self.city and self.country): filled_fields += 1
        if self.venue: filled_fields += 1
        
        # Opponent details
        if self.opponent_first_name and self.opponent_last_name: filled_fields += 1
        if self.opponent_fighter: filled_fields += 2  # Bonus for linked fighter
        
        # Event details
        if self.event: filled_fields += 2  # Bonus for linked event
        if self.organization: filled_fields += 1
        
        # Weight class
        if self.weight_class or self.weight_class_name: filled_fields += 1
        
        # Record tracking
        if self.fighter_record_at_time: filled_fields += 1
        
        # Additional context
        if self.notes: filled_fields += 1
        if self.scheduled_rounds: filled_fields += 1
        
        return round(filled_fields / total_fields, 2)
    
    def save(self, *args, **kwargs):
        """Override save to auto-calculate fields"""
        # Auto-generate opponent_full_name if not provided
        if not self.opponent_full_name:
            self.opponent_full_name = self.get_opponent_display_name()
        
        # Calculate data quality score
        self.data_quality_score = self.calculate_data_quality()
        
        super().save(*args, **kwargs)
    
    @classmethod
    def get_fighter_record_at_fight(cls, fighter, fight_order):
        """Calculate fighter's record up to a specific fight"""
        previous_fights = cls.objects.filter(
            fighter=fighter,
            fight_order__lt=fight_order
        ).order_by('fight_order')
        
        wins = previous_fights.filter(result='win').count()
        losses = previous_fights.filter(result='loss').count()
        draws = previous_fights.filter(result='draw').count()
        no_contests = previous_fights.filter(result='no_contest').count()
        
        if no_contests > 0:
            return f"{wins}-{losses}-{draws} ({no_contests} NC)"
        return f"{wins}-{losses}-{draws}"


class FighterRanking(models.Model):
    """
    Fighter rankings across different weight classes and organizations.
    Supports divisional rankings and pound-for-pound rankings.
    """
    
    RANKING_TYPE_CHOICES = [
        ('divisional', 'Divisional Ranking'),
        ('p4p', 'Pound-for-Pound'),
        ('organization', 'Organization-Specific'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fighter = models.ForeignKey(Fighter, on_delete=models.CASCADE, related_name='rankings')
    
    # Ranking context
    ranking_type = models.CharField(max_length=20, choices=RANKING_TYPE_CHOICES, default='divisional')
    weight_class = models.ForeignKey(
        'organizations.WeightClass', on_delete=models.CASCADE, null=True, blank=True,
        help_text="Weight class for divisional rankings (null for P4P)"
    )
    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Specific organization (null for global rankings)"
    )
    
    # Ranking data
    current_rank = models.PositiveIntegerField()
    previous_rank = models.PositiveIntegerField(null=True, blank=True)
    ranking_score = models.DecimalField(
        max_digits=10, decimal_places=4, default=0.0,
        help_text="Computed ranking score (higher = better)"
    )
    
    # Ranking components (for transparency)
    record_score = models.DecimalField(max_digits=8, decimal_places=4, default=0.0)
    opponent_quality_score = models.DecimalField(max_digits=8, decimal_places=4, default=0.0)
    activity_score = models.DecimalField(max_digits=8, decimal_places=4, default=0.0)
    performance_score = models.DecimalField(max_digits=8, decimal_places=4, default=0.0)
    
    # Metadata
    calculation_date = models.DateTimeField(auto_now=True)
    manual_adjustment = models.IntegerField(
        default=0, 
        help_text="Manual ranking adjustment (+/- positions)"
    )
    is_champion = models.BooleanField(default=False)
    is_interim_champion = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'fighter_rankings'
        verbose_name = 'Fighter Ranking'
        verbose_name_plural = 'Fighter Rankings'
        ordering = ['weight_class', 'organization', 'current_rank']
        indexes = [
            models.Index(fields=['weight_class', 'current_rank'], name='idx_rankings_division'),
            models.Index(fields=['organization', 'current_rank'], name='idx_rankings_org'),
            models.Index(fields=['ranking_type', 'current_rank'], name='idx_rankings_type'),
            models.Index(fields=['fighter'], name='idx_rankings_fighter'),
            models.Index(fields=['is_champion'], name='idx_rankings_champion'),
        ]
        unique_together = [
            ['weight_class', 'organization', 'current_rank', 'ranking_type'],
            ['fighter', 'weight_class', 'organization', 'ranking_type']
        ]
    
    def __str__(self):
        if self.ranking_type == 'p4p':
            return f"P4P #{self.current_rank}: {self.fighter.get_full_name()}"
        
        weight_class_str = f"{self.weight_class.name}" if self.weight_class else "Unknown"
        org_str = f" ({self.organization.abbreviation})" if self.organization else ""
        
        return f"{weight_class_str}{org_str} #{self.current_rank}: {self.fighter.get_full_name()}"
    
    def get_rank_change(self):
        """Get ranking change from previous ranking"""
        if not self.previous_rank:
            return 0
        return self.previous_rank - self.current_rank  # Positive = moved up
    
    def get_rank_change_display(self):
        """Get human-readable rank change"""
        change = self.get_rank_change()
        if change == 0:
            return "No change"
        elif change > 0:
            return f"↑ {change}"
        else:
            return f"↓ {abs(change)}"


class FighterStatistics(models.Model):
    """
    Comprehensive fighter statistics calculated from fight history.
    Updated automatically when fight data changes.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fighter = models.OneToOneField(Fighter, on_delete=models.CASCADE, related_name='statistics')
    
    # Basic career statistics (mirrors Fighter model but calculated)
    total_fights = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    draws = models.PositiveIntegerField(default=0)
    no_contests = models.PositiveIntegerField(default=0)
    
    # Win method breakdown
    wins_ko = models.PositiveIntegerField(default=0)
    wins_tko = models.PositiveIntegerField(default=0)
    wins_submission = models.PositiveIntegerField(default=0)
    wins_decision = models.PositiveIntegerField(default=0)
    wins_other = models.PositiveIntegerField(default=0)
    
    # Loss method breakdown
    losses_ko = models.PositiveIntegerField(default=0)
    losses_tko = models.PositiveIntegerField(default=0)
    losses_submission = models.PositiveIntegerField(default=0)
    losses_decision = models.PositiveIntegerField(default=0)
    losses_other = models.PositiveIntegerField(default=0)
    
    # Performance metrics
    finish_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.0,
        help_text="Percentage of wins by finish"
    )
    finish_resistance = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.0,
        help_text="Percentage of losses that went to decision"
    )
    average_fight_time = models.DecimalField(
        max_digits=6, decimal_places=2, default=0.0,
        help_text="Average fight duration in minutes"
    )
    
    # Streaks and momentum
    current_streak = models.IntegerField(default=0, help_text="Current win/loss streak (positive = wins)")
    longest_win_streak = models.PositiveIntegerField(default=0)
    longest_losing_streak = models.PositiveIntegerField(default=0)
    
    # Activity metrics
    fights_last_12_months = models.PositiveIntegerField(default=0)
    fights_last_24_months = models.PositiveIntegerField(default=0)
    fights_last_36_months = models.PositiveIntegerField(default=0)
    last_fight_date = models.DateField(null=True, blank=True)
    days_since_last_fight = models.PositiveIntegerField(null=True, blank=True)
    
    # Competition level
    title_fights = models.PositiveIntegerField(default=0)
    title_wins = models.PositiveIntegerField(default=0)
    main_events = models.PositiveIntegerField(default=0)
    top_5_wins = models.PositiveIntegerField(default=0, help_text="Wins against top 5 ranked opponents")
    top_10_wins = models.PositiveIntegerField(default=0, help_text="Wins against top 10 ranked opponents")
    
    # Performance bonuses
    performance_bonuses = models.PositiveIntegerField(default=0)
    fight_bonuses = models.PositiveIntegerField(default=0)
    total_bonuses = models.PositiveIntegerField(default=0)
    
    # Weight class activity
    primary_weight_class = models.ForeignKey(
        'organizations.WeightClass', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Weight class with most fights"
    )
    weight_classes_fought = models.PositiveIntegerField(default=1)
    
    # Age and career metrics
    debut_date = models.DateField(null=True, blank=True)
    career_length_days = models.PositiveIntegerField(null=True, blank=True)
    age_at_debut = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    current_age = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    
    # Quality metrics for ranking
    strength_of_schedule = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.0,
        help_text="Average ranking of opponents at fight time"
    )
    signature_wins = models.PositiveIntegerField(default=0, help_text="Wins against former champions/contenders")
    quality_losses = models.PositiveIntegerField(default=0, help_text="Competitive losses to elite opponents")
    
    # Last calculation metadata
    last_calculated = models.DateTimeField(auto_now=True)
    needs_recalculation = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'fighter_statistics'
        verbose_name = 'Fighter Statistics'
        verbose_name_plural = 'Fighter Statistics'
        indexes = [
            models.Index(fields=['fighter'], name='idx_stats_fighter'),
            models.Index(fields=['finish_rate'], name='idx_stats_finish_rate'),
            models.Index(fields=['current_streak'], name='idx_stats_streak'),
            models.Index(fields=['last_fight_date'], name='idx_stats_last_fight'),
            models.Index(fields=['needs_recalculation'], name='idx_stats_needs_calc'),
        ]
    
    def __str__(self):
        return f"Stats: {self.fighter.get_full_name()} ({self.wins}-{self.losses}-{self.draws})"
    
    def get_record_display(self):
        """Get formatted record string"""
        if self.no_contests > 0:
            return f"{self.wins}-{self.losses}-{self.draws} ({self.no_contests} NC)"
        return f"{self.wins}-{self.losses}-{self.draws}"
    
    def get_win_percentage(self):
        """Calculate win percentage"""
        if self.total_fights == 0:
            return 0.0
        return round((self.wins / self.total_fights) * 100, 1)
    
    def calculate_all_statistics(self):
        """Recalculate all statistics from fight history"""
        from django.db.models import Count, Avg, Q, Max, Min
        from django.utils import timezone
        from datetime import timedelta
        
        # Get all fight history for this fighter
        fights = self.fighter.fight_history.all().order_by('fight_order')
        
        if not fights.exists():
            return
        
        # Basic record calculation
        wins = fights.filter(result='win').count()
        losses = fights.filter(result='loss').count()
        draws = fights.filter(result='draw').count()
        no_contests = fights.filter(result='no_contest').count()
        total = fights.count()
        
        # Win method breakdown
        win_fights = fights.filter(result='win')
        wins_ko = win_fights.filter(method='ko').count()
        wins_tko = win_fights.filter(method='tko').count()
        wins_submission = win_fights.filter(method='submission').count()
        wins_decision = win_fights.filter(method='decision').count()
        wins_other = win_fights.exclude(method__in=['ko', 'tko', 'submission', 'decision']).count()
        
        # Loss method breakdown
        loss_fights = fights.filter(result='loss')
        losses_ko = loss_fights.filter(method='ko').count()
        losses_tko = loss_fights.filter(method='tko').count()
        losses_submission = loss_fights.filter(method='submission').count()
        losses_decision = loss_fights.filter(method='decision').count()
        losses_other = loss_fights.exclude(method__in=['ko', 'tko', 'submission', 'decision']).count()
        
        # Performance metrics
        finishes = wins_ko + wins_tko + wins_submission
        finish_rate = (finishes / wins * 100) if wins > 0 else 0.0
        decision_losses = losses_decision
        finish_resistance = (decision_losses / losses * 100) if losses > 0 else 100.0
        
        # Current streak calculation
        current_streak = 0
        for fight in fights.order_by('-fight_order'):
            if fight.result == 'win':
                current_streak += 1
            elif fight.result == 'loss':
                current_streak -= 1
                break
            else:  # draw or no contest
                break
        
        # Activity metrics
        today = timezone.now().date()
        last_12_months = today - timedelta(days=365)
        last_24_months = today - timedelta(days=730)
        last_36_months = today - timedelta(days=1095)
        
        fights_last_12 = fights.filter(event_date__gte=last_12_months).count()
        fights_last_24 = fights.filter(event_date__gte=last_24_months).count()
        fights_last_36 = fights.filter(event_date__gte=last_36_months).count()
        
        # Last fight info
        last_fight = fights.order_by('-event_date').first()
        last_fight_date = last_fight.event_date if last_fight else None
        days_since_last = (today - last_fight_date).days if last_fight_date else None
        
        # Competition level
        title_fights_count = fights.filter(is_title_fight=True).count()
        title_wins_count = fights.filter(is_title_fight=True, result='win').count()
        
        # Career span
        first_fight = fights.order_by('fight_order').first()
        debut_date = first_fight.event_date if first_fight else None
        career_days = (today - debut_date).days if debut_date else None
        
        # Update all fields
        self.total_fights = total
        self.wins = wins
        self.losses = losses  
        self.draws = draws
        self.no_contests = no_contests
        
        self.wins_ko = wins_ko
        self.wins_tko = wins_tko
        self.wins_submission = wins_submission
        self.wins_decision = wins_decision
        self.wins_other = wins_other
        
        self.losses_ko = losses_ko
        self.losses_tko = losses_tko
        self.losses_submission = losses_submission
        self.losses_decision = losses_decision
        self.losses_other = losses_other
        
        self.finish_rate = round(finish_rate, 2)
        self.finish_resistance = round(finish_resistance, 2)
        
        self.current_streak = current_streak
        self.fights_last_12_months = fights_last_12
        self.fights_last_24_months = fights_last_24
        self.fights_last_36_months = fights_last_36
        self.last_fight_date = last_fight_date
        self.days_since_last_fight = days_since_last
        
        self.title_fights = title_fights_count
        self.title_wins = title_wins_count
        
        self.debut_date = debut_date
        self.career_length_days = career_days
        
        self.needs_recalculation = False
        self.save()


class RankingHistory(models.Model):
    """
    Historical tracking of ranking changes over time.
    Enables trend analysis and ranking movement visualization.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fighter_ranking = models.ForeignKey(FighterRanking, on_delete=models.CASCADE, related_name='history')
    
    # Historical ranking data
    rank_on_date = models.PositiveIntegerField()
    ranking_score = models.DecimalField(max_digits=10, decimal_places=4)
    calculation_date = models.DateField()
    
    # Change context
    rank_change = models.IntegerField(default=0, help_text="Change from previous ranking")
    trigger_event = models.CharField(
        max_length=255, blank=True,
        help_text="Event that triggered ranking change (fight result, etc.)"
    )
    trigger_fight = models.ForeignKey(
        'events.Fight', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Fight that caused ranking change"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ranking_history'
        verbose_name = 'Ranking History'
        verbose_name_plural = 'Ranking History'
        ordering = ['-calculation_date', 'rank_on_date']
        indexes = [
            models.Index(fields=['fighter_ranking', '-calculation_date'], name='idx_rank_history_fighter_date'),
            models.Index(fields=['calculation_date'], name='idx_rank_history_date'),
            models.Index(fields=['rank_on_date'], name='idx_rank_history_rank'),
        ]
    
    def __str__(self):
        change_str = f" ({self.get_change_display()})" if self.rank_change != 0 else ""
        return f"{self.fighter_ranking.fighter.get_full_name()} #{self.rank_on_date} on {self.calculation_date}{change_str}"
    
    def get_change_display(self):
        """Get human-readable change display"""
        if self.rank_change == 0:
            return "No change"
        elif self.rank_change > 0:
            return f"↑{self.rank_change}"
        else:
            return f"↓{abs(self.rank_change)}"