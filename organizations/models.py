import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Organization(models.Model):
    """MMA Organizations (UFC, KSW, Oktagon, PFL, etc.)"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    abbreviation = models.CharField(max_length=10, unique=True)
    founded_date = models.DateField(null=True, blank=True)
    headquarters = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'organizations'
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.abbreviation})"


class WeightClass(models.Model):
    """Weight classes for different organizations"""
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='weight_classes')
    name = models.CharField(max_length=100)
    weight_limit_lbs = models.PositiveIntegerField(null=True, blank=True)
    weight_limit_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='male')
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'weight_classes'
        verbose_name = 'Weight Class'
        verbose_name_plural = 'Weight Classes'
        ordering = ['organization', 'weight_limit_kg']
        unique_together = ['organization', 'name', 'gender']
    
    def __str__(self):
        gender_str = f" ({self.gender})" if self.gender == 'female' else ""
        return f"{self.organization.abbreviation} {self.name}{gender_str} ({self.weight_limit_lbs}lbs)"