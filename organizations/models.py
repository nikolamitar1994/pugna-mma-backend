import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Organization(models.Model):
    """MMA Organizations (UFC, KSW, Oktagon, PFL, etc.) - Enhanced for multi-org support"""
    
    # Organization types
    ORG_TYPE_CHOICES = [
        ('major', 'Major Organization'),
        ('regional', 'Regional Organization'),
        ('defunct', 'Defunct Organization'),
    ]
    
    # Scoring system choices
    SCORING_SYSTEM_CHOICES = [
        ('unified', 'Unified Rules of MMA'),
        ('pride', 'PRIDE Rules'),
        ('one_fc', 'ONE Championship Rules'),
        ('custom', 'Custom Rules'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    abbreviation = models.CharField(max_length=10, unique=True)
    full_name = models.CharField(max_length=255, blank=True, help_text="Full legal name of organization")
    
    # Organization details
    org_type = models.CharField(max_length=20, choices=ORG_TYPE_CHOICES, default='major')
    founded_date = models.DateField(null=True, blank=True)
    defunct_date = models.DateField(null=True, blank=True, help_text="Date organization ceased operations")
    headquarters = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Contact and media
    website = models.URLField(blank=True)
    wikipedia_url = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)
    social_media = models.JSONField(default=dict, blank=True,
                                   help_text="Social media links (twitter, instagram, etc.)")
    
    # Rules and regulations
    scoring_system = models.CharField(max_length=20, choices=SCORING_SYSTEM_CHOICES, default='unified')
    round_duration_minutes = models.PositiveIntegerField(default=5, help_text="Standard round duration")
    championship_rounds = models.PositiveIntegerField(default=5, help_text="Number of championship rounds")
    non_title_rounds = models.PositiveIntegerField(default=3, help_text="Number of non-title fight rounds")
    
    # Special rules
    allows_knees_to_grounded = models.BooleanField(default=False)
    allows_soccer_kicks = models.BooleanField(default=False)
    allows_stomps = models.BooleanField(default=False)
    weight_allowance_lbs = models.DecimalField(max_digits=3, decimal_places=1, default=1.0,
                                              help_text="Weight allowance for non-title fights")
    hydration_testing = models.BooleanField(default=False, help_text="Uses hydration testing (like ONE FC)")
    
    # Data configuration
    event_naming_pattern = models.CharField(max_length=255, blank=True,
                                           help_text="Pattern for event names (e.g., 'UFC {number}')")
    uses_event_numbers = models.BooleanField(default=True, help_text="Events use numbering system")
    
    # Scraping configuration
    wikipedia_category = models.CharField(max_length=255, blank=True,
                                         help_text="Wikipedia category for event scraping")
    stats_url_pattern = models.CharField(max_length=255, blank=True,
                                        help_text="URL pattern for statistics scraping")
    decisions_url_pattern = models.CharField(max_length=255, blank=True,
                                           help_text="URL pattern for decisions scraping")
    
    # Status
    is_active = models.BooleanField(default=True)
    priority_order = models.PositiveIntegerField(default=100,
                                                help_text="Display order (lower = higher priority)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'organizations'
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'
        ordering = ['priority_order', 'name']
        indexes = [
            models.Index(fields=['is_active'], name='idx_org_active'),
            models.Index(fields=['org_type'], name='idx_org_type'),
            models.Index(fields=['priority_order'], name='idx_org_priority'),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.abbreviation})"
    
    def get_event_count(self):
        """Get total number of events for this organization"""
        return self.events.count()
    
    def get_fighter_count(self):
        """Get approximate number of fighters who competed in this organization"""
        from events.models import FightParticipant
        return FightParticipant.objects.filter(
            fight__event__organization=self
        ).values('fighter').distinct().count()
    
    @classmethod
    def get_active_organizations(cls):
        """Get all active organizations ordered by priority"""
        return cls.objects.filter(is_active=True).order_by('priority_order')


class WeightClass(models.Model):
    """Weight classes for different organizations - Enhanced for organization-specific limits"""
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('mixed', 'Mixed/Open'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='weight_classes')
    
    # Weight class details
    name = models.CharField(max_length=100, help_text="e.g., 'Lightweight', 'Middleweight'")
    abbreviation = models.CharField(max_length=10, blank=True, help_text="e.g., 'LW', 'MW'")
    
    # Weight limits
    weight_limit_lbs = models.PositiveIntegerField(null=True, blank=True)
    weight_limit_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # ONE FC style with hydration
    hydrated_weight_limit_lbs = models.PositiveIntegerField(null=True, blank=True,
                                                           help_text="Hydrated weight limit (ONE FC)")
    
    # Weight class specifics
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='male')
    is_championship_weight = models.BooleanField(default=True,
                                                help_text="Is this a championship weight class?")
    display_order = models.PositiveIntegerField(default=100,
                                               help_text="Display order (lower = lighter weight)")
    
    # Special weight classes
    is_catchweight = models.BooleanField(default=False)
    is_openweight = models.BooleanField(default=False)
    is_tournament_weight = models.BooleanField(default=False,
                                             help_text="Special weight class for tournaments")
    
    # Status
    is_active = models.BooleanField(default=True)
    introduced_date = models.DateField(null=True, blank=True,
                                      help_text="Date this weight class was introduced")
    retired_date = models.DateField(null=True, blank=True,
                                   help_text="Date this weight class was retired")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'weight_classes'
        verbose_name = 'Weight Class'
        verbose_name_plural = 'Weight Classes'
        ordering = ['organization', 'gender', 'display_order', 'weight_limit_kg']
        unique_together = ['organization', 'name', 'gender']
        indexes = [
            models.Index(fields=['organization', 'is_active'], name='idx_weight_org_active'),
            models.Index(fields=['gender'], name='idx_weight_gender'),
            models.Index(fields=['display_order'], name='idx_weight_order'),
        ]
    
    def __str__(self):
        gender_str = f" ({self.get_gender_display()})" if self.gender != 'male' else ""
        weight_str = f" - {self.weight_limit_lbs}lbs" if self.weight_limit_lbs else ""
        return f"{self.organization.abbreviation} {self.name}{gender_str}{weight_str}"
    
    def get_weight_range_display(self):
        """Get human-readable weight range"""
        if self.is_openweight:
            return "Open Weight"
        elif self.is_catchweight:
            return "Catchweight"
        elif self.weight_limit_lbs:
            return f"Up to {self.weight_limit_lbs} lbs"
        return self.name
    
    def save(self, *args, **kwargs):
        """Auto-calculate kg from lbs or vice versa"""
        if self.weight_limit_lbs and not self.weight_limit_kg:
            self.weight_limit_kg = round(self.weight_limit_lbs * 0.453592, 2)
        elif self.weight_limit_kg and not self.weight_limit_lbs:
            self.weight_limit_lbs = round(self.weight_limit_kg * 2.20462)
        
        # Generate abbreviation if not provided
        if not self.abbreviation and self.name:
            words = self.name.split()
            if len(words) == 1:
                self.abbreviation = self.name[:2].upper()
            else:
                self.abbreviation = ''.join(word[0].upper() for word in words)
        
        super().save(*args, **kwargs)