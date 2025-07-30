import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.utils import timezone


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
    birth_first_name = models.CharField(max_length=100, blank=True, null=True,
                                       help_text="Legal first name at birth")
    birth_last_name = models.CharField(max_length=100, blank=True, null=True,
                                      help_text="Legal last name at birth")
    nickname = models.CharField(max_length=255, blank=True, null=True,
                               help_text="Fighter nickname (e.g., 'Bones')")
    
    # Personal information
    date_of_birth = models.DateField(null=True, blank=True)
    birth_place = models.CharField(max_length=255, blank=True, null=True)
    nationality = models.CharField(max_length=100, null=True, blank=True)
    
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
    stance = models.CharField(max_length=20, choices=STANCE_CHOICES, blank=True, null=True)
    
    # Career information
    fighting_out_of = models.CharField(max_length=255, blank=True, null=True)
    team = models.CharField(max_length=255, blank=True, null=True)
    years_active = models.CharField(max_length=100, blank=True, null=True,
                                   help_text="e.g., '2010-present' or '2005-2018'")
    is_active = models.BooleanField(default=True)
    
    # Media and links
    profile_image_url = models.URLField(blank=True, null=True)
    wikipedia_url = models.URLField(blank=True, null=True)
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
    data_source = models.CharField(max_length=200, choices=DATA_SOURCE_CHOICES, default='manual')
    data_quality_score = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Data completeness/quality score (0.0-1.0)"
    )
    last_data_update = models.DateTimeField(null=True, blank=True)
    
    # Search vector for full-text search
    search_vector = SearchVectorField(null=True, blank=True)
    
    # JSON import field for direct data population
    json_import_data = models.TextField(
        blank=True,
        help_text="Paste complete fighter JSON here to automatically populate all fields and fight history. Data will be processed on save and this field will be cleared."
    )
    
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
    
    def process_json_import(self):
        """
        Process JSON import data and populate fighter fields.
        Returns (success: bool, message: str, fight_history_created: int)
        """
        if not self.json_import_data.strip():
            return True, "No JSON data to process", 0
        
        try:
            import json
            from .templates import JSONImportProcessor
            
            # Parse JSON
            json_data = json.loads(self.json_import_data)
            
            # Validate it's a fighter template
            if json_data.get('entity_type') != 'fighter':
                return False, "JSON must have entity_type: 'fighter'", 0
            
            # Validate the template
            validation = JSONImportProcessor.validate_fighter_template(json_data)
            if not validation['is_valid']:
                return False, f"Invalid JSON: {'; '.join(validation['errors'])}", 0
            
            # Process fighter data
            fighter_data = JSONImportProcessor.process_fighter_template(json_data)
            
            # Update fighter fields (excluding the ones we don't want to overwrite)
            exclude_fields = {'id', 'created_at', 'updated_at', 'json_import_data', 'search_vector'}
            
            for field, value in fighter_data.items():
                if field not in exclude_fields and hasattr(self, field):
                    # Only update if the new value is not empty/None
                    if value is not None and value != '':
                        setattr(self, field, value)
            
            # Process fight history if provided
            fight_history_data = json_data.get('fight_history', [])
            fight_history_created = 0
            
            if fight_history_data:
                fight_history_created = self._create_fight_history_from_json(fight_history_data)
            
            # Update data quality score
            self.data_quality_score = self.calculate_data_quality()
            self.last_data_update = timezone.now()
            
            # Clear the JSON field after successful processing
            self.json_import_data = ''
            
            return True, f"Successfully imported fighter data. Created {fight_history_created} fight history records.", fight_history_created
            
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {e}", 0
        except Exception as e:
            return False, f"Error processing JSON: {e}", 0
    
    def _create_fight_history_from_json(self, fight_history_data):
        """Create FightHistory records from JSON data"""
        # FightHistory is defined in this same file, no import needed
        from events.models import Event
        from organizations.models import Organization, WeightClass
        
        created_count = 0
        
        for fight_data in fight_history_data:
            try:
                # Extract fight information
                fight_order = fight_data.get('fight_order')
                result = fight_data.get('result')
                
                if not fight_order or not result:
                    continue
                
                # Check if this fight record already exists
                existing_fight = FightHistory.objects.filter(
                    fighter=self,
                    fight_order=fight_order
                ).first()
                
                if existing_fight:
                    continue  # Skip if already exists
                
                # Extract opponent info
                opponent_info = fight_data.get('opponent_info', {})
                fight_details = fight_data.get('fight_details', {})
                event_info = fight_data.get('event_info', {})
                additional_info = fight_data.get('additional_info', {})
                
                # Try to find existing event
                event = None
                if event_info.get('event_name') and event_info.get('event_date'):
                    event = Event.objects.filter(
                        name__iexact=event_info['event_name'],
                        date=event_info['event_date']
                    ).first()
                
                # Try to find existing organization
                organization = None
                if event_info.get('organization_name'):
                    organization = Organization.objects.filter(
                        name__iexact=event_info['organization_name']
                    ).first()
                
                # Try to find weight class
                weight_class = None
                if event_info.get('weight_class_name') and organization:
                    weight_class = WeightClass.objects.filter(
                        name__iexact=event_info['weight_class_name'],
                        organization=organization
                    ).first()
                
                # Create fight history record
                fight_history = FightHistory.objects.create(
                    fighter=self,
                    fight_order=fight_order,
                    result=result,
                    fighter_record_at_time=fight_data.get('fighter_record_at_time', ''),
                    
                    # Opponent information
                    opponent_first_name=opponent_info.get('opponent_first_name', ''),
                    opponent_last_name=opponent_info.get('opponent_last_name', ''),
                    opponent_full_name=opponent_info.get('opponent_full_name', ''),
                    
                    # Fight details (convert method to lowercase for model)
                    method=fight_details.get('method', '').lower(),
                    method_description=fight_details.get('method_description', ''),
                    ending_round=fight_details.get('ending_round'),
                    ending_time=fight_details.get('ending_time', ''),
                    scheduled_rounds=fight_details.get('scheduled_rounds'),
                    is_title_fight=fight_details.get('is_title_fight', False),
                    is_interim_title=fight_details.get('is_interim_title', False),
                    title_belt=fight_details.get('title_belt', ''),
                    
                    # Event information
                    event=event,
                    event_name=event_info.get('event_name', ''),
                    event_date=event_info.get('event_date'),
                    organization=organization,
                    organization_name=event_info.get('organization_name', ''),
                    weight_class=weight_class,
                    weight_class_name=event_info.get('weight_class_name', ''),
                    location=event_info.get('location', ''),
                    venue=event_info.get('venue', ''),
                    city=event_info.get('city', ''),
                    state=event_info.get('state', ''),
                    country=event_info.get('country', ''),
                    
                    # Additional information
                    notes=additional_info.get('notes', ''),
                    performance_bonuses=additional_info.get('performance_bonuses', []),
                    data_source=additional_info.get('data_source', 'json_import'),
                    source_url=additional_info.get('source_url', '')
                )
                
                # Calculate data quality
                fight_history.data_quality_score = fight_history.calculate_data_quality()
                fight_history.save()
                
                created_count += 1
                
            except Exception as e:
                # Log error but continue with other fights
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error creating fight history for {self.get_full_name()}: {e}")
                continue
        
        return created_count
    
    def calculate_data_quality(self):
        """Calculate data quality score based on filled fields"""
        filled_fields = 0
        total_important_fields = 15
        
        # Check important fields
        if self.date_of_birth:
            filled_fields += 1
        if self.birth_place:
            filled_fields += 1
        if self.nationality:
            filled_fields += 1
        if self.height_cm:
            filled_fields += 1
        if self.weight_kg:
            filled_fields += 1
        if self.reach_cm:
            filled_fields += 1
        if self.stance:
            filled_fields += 1
        if self.fighting_out_of:
            filled_fields += 1
        if self.team:
            filled_fields += 1
        if self.wikipedia_url:
            filled_fields += 1
        if self.profile_image_url:
            filled_fields += 1
        if self.nickname:
            filled_fields += 1
        if self.wins or self.losses:
            filled_fields += 1
        if self.years_active:
            filled_fields += 1
        if self.social_media:
            filled_fields += 1
        
        return round(filled_fields / total_important_fields, 2)
    
    def save(self, *args, **kwargs):
        """Override save to process JSON import data and update computed fields"""
        # Process JSON import data if provided
        json_success = True
        json_message = ""
        fight_history_created = 0
        
        if self.json_import_data.strip():
            json_success, json_message, fight_history_created = self.process_json_import()
            
            # Store the message for display in admin
            if hasattr(self, '_json_import_message'):
                self._json_import_message = json_message
            
            if not json_success:
                # If JSON processing failed, we might want to still save the fighter
                # but keep the JSON data for correction
                pass
        
        # Generate display name if not set
        if not self.display_name:
            self.display_name = self.get_full_name()
        
        # Update data quality score
        if not hasattr(self, '_skip_data_quality_update'):
            self.data_quality_score = self.calculate_data_quality()
        
        # Update last data update timestamp
        self.last_data_update = timezone.now()
        
        super().save(*args, **kwargs)
        
        # Update search vector after save
        self.update_search_vector()
    
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
        max_length=15, blank=True,
        help_text="Time in round when fight ended (MM:SS format, supports long durations)"
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
    data_source = models.CharField(max_length=200, choices=DATA_SOURCE_CHOICES, default='wikipedia')
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


class PendingFighter(models.Model):
    """
    Pending fighters discovered during scraping that don't exist in the database.
    Used for manual review and approval workflow before creating Fighter records.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved - Create Fighter'),
        ('rejected', 'Rejected'),
        ('duplicate', 'Duplicate - Matched to Existing'),
        ('created', 'Fighter Created'),
    ]
    
    SOURCE_CHOICES = [
        ('scraper', 'Event Scraper'),
        ('manual', 'Manual Entry'),
        ('api_import', 'API Import'),
    ]
    
    CONFIDENCE_CHOICES = [
        ('low', 'Low - Manual Review Required'),
        ('medium', 'Medium - Likely New Fighter'),
        ('high', 'High - Definitely New Fighter'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic fighter information discovered during scraping
    first_name = models.CharField(max_length=100, help_text="Fighter's first name as found in source")
    last_name = models.CharField(max_length=100, blank=True, help_text="Fighter's last name as found in source")
    full_name_raw = models.CharField(max_length=255, help_text="Full name as originally scraped")
    nickname = models.CharField(max_length=255, blank=True, help_text="Nickname if discovered")
    
    # Source context information
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='scraper')
    source_event = models.ForeignKey(
        'events.Event', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Event where this fighter was discovered"
    )
    source_url = models.URLField(blank=True, help_text="URL where fighter was discovered")
    source_data = models.JSONField(
        default=dict, blank=True,
        help_text="Raw data scraped about the fighter"
    )
    
    # Review workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    confidence_level = models.CharField(
        max_length=10, choices=CONFIDENCE_CHOICES, default='medium',
        help_text="Confidence that this is a new fighter"
    )
    
    # Potential matching to existing fighters
    potential_matches = models.JSONField(
        default=list, blank=True,
        help_text="List of potential existing fighters this might match"
    )
    matched_fighter = models.ForeignKey(
        Fighter, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pending_duplicates',
        help_text="Existing fighter this was matched to (if duplicate)"
    )
    
    # Additional discovered information
    nationality = models.CharField(max_length=100, null=True, blank=True)
    weight_class_name = models.CharField(max_length=100, blank=True)
    record_text = models.CharField(max_length=50, blank=True, help_text="Fight record as text")
    
    # AI-assisted data completion
    ai_suggested_data = models.JSONField(
        default=dict, blank=True,
        help_text="AI-generated suggestions for complete fighter profile"
    )
    json_template_url = models.URLField(
        blank=True, 
        help_text="URL to JSON template for manual completion"
    )
    
    # Review information
    reviewed_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Admin user who reviewed this pending fighter"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, help_text="Notes from reviewer")
    
    # Created fighter reference
    created_fighter = models.OneToOneField(
        Fighter, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pending_source',
        help_text="Fighter record created from this pending fighter"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pending_fighters'
        verbose_name = 'Pending Fighter'
        verbose_name_plural = 'Pending Fighters'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status'], name='idx_pend_fighters_status'),
            models.Index(fields=['source'], name='idx_pend_fighters_source'),
            models.Index(fields=['confidence_level'], name='idx_pend_fighters_conf'),
            models.Index(fields=['first_name', 'last_name'], name='idx_pend_fighters_name'),
            models.Index(fields=['-created_at'], name='idx_pend_fighters_created'),
        ]
    
    def __str__(self):
        return f"Pending: {self.full_name_raw} ({self.status})"
    
    def get_display_name(self):
        """Get display name for the pending fighter"""
        if self.nickname:
            return f"{self.full_name_raw} '{self.nickname}'"
        return self.full_name_raw
    
    def get_potential_match_names(self):
        """Get list of potential match names for display"""
        if not self.potential_matches:
            return []
        return [match.get('name', 'Unknown') for match in self.potential_matches]
    
    def create_fighter_from_pending(self, user=None):
        """
        Create a Fighter record from this pending fighter.
        Returns the created Fighter instance.
        """
        if self.status == 'created':
            return self.created_fighter
        
        if self.status != 'approved':
            raise ValueError("Cannot create fighter from non-approved pending fighter")
        
        # Create fighter with basic information
        fighter_data = {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'nickname': self.nickname,
            'nationality': self.nationality,
            'data_source': 'ai_completion' if self.ai_suggested_data else 'manual',
        }
        
        # Add AI-suggested data if available
        if self.ai_suggested_data:
            ai_data = self.ai_suggested_data
            
            # Map AI suggestions to fighter fields
            if 'date_of_birth' in ai_data:
                fighter_data['date_of_birth'] = ai_data['date_of_birth']
            if 'birth_place' in ai_data:
                fighter_data['birth_place'] = ai_data['birth_place']
            if 'height_cm' in ai_data:
                fighter_data['height_cm'] = ai_data['height_cm']
            if 'weight_kg' in ai_data:
                fighter_data['weight_kg'] = ai_data['weight_kg']
            if 'reach_cm' in ai_data:
                fighter_data['reach_cm'] = ai_data['reach_cm']
            if 'stance' in ai_data:
                fighter_data['stance'] = ai_data['stance']
            if 'fighting_out_of' in ai_data:
                fighter_data['fighting_out_of'] = ai_data['fighting_out_of']
            if 'team' in ai_data:
                fighter_data['team'] = ai_data['team']
        
        # Create the fighter
        fighter = Fighter.objects.create(**fighter_data)
        
        # Update this pending fighter
        self.status = 'created'
        self.created_fighter = fighter
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.save()
        
        return fighter
    
    def mark_as_duplicate(self, existing_fighter, user=None):
        """Mark this pending fighter as a duplicate of an existing fighter"""
        self.status = 'duplicate'
        self.matched_fighter = existing_fighter
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.save()
    
    def generate_json_template(self):
        """Generate JSON template for manual completion"""
        template = {
            'fighter_data': {
                'first_name': self.first_name,
                'last_name': self.last_name,
                'nickname': self.nickname,
                'nationality': self.nationality,
                'date_of_birth': None,
                'birth_place': '',
                'height_cm': None,
                'weight_kg': None,
                'reach_cm': None,
                'stance': '',
                'fighting_out_of': '',
                'team': '',
                'years_active': '',
                'profile_image_url': '',
                'wikipedia_url': '',
                'social_media': {}
            },
            'source_info': {
                'discovered_in_event': self.source_event.name if self.source_event else '',
                'source_url': self.source_url,
                'raw_name': self.full_name_raw,
                'weight_class': self.weight_class_name,
                'record_text': self.record_text
            },
            'ai_suggestions': self.ai_suggested_data,
            'completion_instructions': {
                'required_fields': ['first_name', 'last_name'],
                'recommended_fields': ['nationality', 'date_of_birth', 'height_cm', 'weight_kg'],
                'optional_fields': ['nickname', 'birth_place', 'reach_cm', 'stance', 'fighting_out_of', 'team'],
                'data_sources': ['Official websites', 'Wikipedia', 'MMA databases', 'Social media'],
                'validation_notes': 'Verify all information from multiple sources before submission'
            }
        }
        
        return template
    
    @classmethod
    def create_from_scraping(cls, fighter_name, event=None, source_url='', additional_data=None):
        """
        Create a pending fighter from scraping data.
        Returns the created PendingFighter instance.
        """
        # Parse name components
        name_parts = fighter_name.strip().split()
        first_name = name_parts[0] if name_parts else ''
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        
        # Check for existing pending fighter with same name
        existing_pending = cls.objects.filter(
            full_name_raw__iexact=fighter_name,
            status__in=['pending', 'approved']
        ).first()
        
        if existing_pending:
            return existing_pending
        
        # Create new pending fighter
        pending_fighter = cls.objects.create(
            first_name=first_name,
            last_name=last_name,
            full_name_raw=fighter_name,
            source='scraper',
            source_event=event,
            source_url=source_url,
            source_data=additional_data or {},
            confidence_level='medium'  # Will be refined by matching logic
        )
        
        # Run fuzzy matching to find potential duplicates
        pending_fighter.run_fuzzy_matching()
        
        return pending_fighter
    
    def run_fuzzy_matching(self):
        """Run fuzzy matching against existing fighters to find potential duplicates"""
        from .services.matching import FighterMatcher
        
        # Find potential matches
        fighter, confidence = FighterMatcher.find_fighter_by_name(
            self.first_name, 
            self.last_name,
            context_data={'nationality': self.nationality} if self.nationality else None
        )
        
        potential_matches = []
        
        if fighter and confidence > 0.6:
            potential_matches.append({
                'fighter_id': str(fighter.id),
                'name': fighter.get_full_name(),
                'confidence': confidence,
                'nationality': fighter.nationality,
                'record': fighter.get_record_string()
            })
            
            # If high confidence match, mark as duplicate candidate
            if confidence > 0.85:
                self.confidence_level = 'low'  # Needs manual review
                self.potential_matches = potential_matches
                if confidence > 0.95:
                    self.matched_fighter = fighter
                    self.status = 'duplicate'
        
        # Update potential matches and confidence
        if potential_matches:
            self.potential_matches = potential_matches
        else:
            self.confidence_level = 'high'  # Likely new fighter
        
        self.save()