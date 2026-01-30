"""
Delivery models: DeliveryZone, DeliverySlot, DeliveryFeeRule.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from core.validators import validate_xaf_amount


class DeliveryZone(models.Model):
    """Delivery zone model."""
    
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, db_index=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'delivery_zones'
        ordering = ['name']
        indexes = [
            models.Index(fields=['code', 'is_active']),
        ]
    
    def __str__(self):
        return f'{self.name} ({self.code})'


class DeliveryFeeRule(models.Model):
    """Delivery fee calculation rule."""
    
    class RuleType(models.TextChoices):
        FIXED = 'FIXED', 'Fixed Fee'
        PERCENTAGE = 'PERCENTAGE', 'Percentage of Cart Total'
        TIERED = 'TIERED', 'Tiered by Cart Total'
    
    zone = models.ForeignKey(
        DeliveryZone,
        on_delete=models.CASCADE,
        related_name='fee_rules'
    )
    rule_type = models.CharField(
        max_length=20,
        choices=RuleType.choices,
        default=RuleType.FIXED,
        db_index=True
    )
    
    # For FIXED type
    fixed_fee = models.BigIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), validate_xaf_amount],
        help_text='Fixed delivery fee in XAF (for FIXED type)'
    )
    
    # For PERCENTAGE type
    percentage = models.DecimalField(
        null=True,
        blank=True,
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Percentage of cart total (for PERCENTAGE type)'
    )
    min_fee = models.BigIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), validate_xaf_amount],
        help_text='Minimum fee in XAF (for PERCENTAGE type)'
    )
    max_fee = models.BigIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), validate_xaf_amount],
        help_text='Maximum fee in XAF (for PERCENTAGE type)'
    )
    
    # For TIERED type - stored as JSON
    tier_rules = models.JSONField(
        null=True,
        blank=True,
        help_text='Tiered rules: [{"min": 0, "max": 10000, "fee": 2000}, ...]'
    )
    
    # Priority (lower number = higher priority)
    priority = models.IntegerField(
        default=0,
        db_index=True,
        help_text='Rule priority (lower = higher priority)'
    )
    
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'delivery_fee_rules'
        ordering = ['priority', '-created_at']
        indexes = [
            models.Index(fields=['zone', 'is_active', 'priority']),
        ]
    
    def __str__(self):
        return f'{self.zone.name} - {self.get_rule_type_display()} (Priority: {self.priority})'
    
    def calculate_fee(self, cart_total_xaf):
        """Calculate delivery fee based on cart total."""
        if not self.is_active:
            return 0
        
        if self.rule_type == self.RuleType.FIXED:
            return self.fixed_fee or 0
        
        elif self.rule_type == self.RuleType.PERCENTAGE:
            if not self.percentage:
                return 0
            
            fee = int((cart_total_xaf * self.percentage) / 100)
            
            # Apply min/max constraints
            if self.min_fee:
                fee = max(fee, self.min_fee)
            if self.max_fee:
                fee = min(fee, self.max_fee)
            
            return fee
        
        elif self.rule_type == self.RuleType.TIERED:
            if not self.tier_rules:
                return 0
            
            # Find matching tier
            for tier in sorted(self.tier_rules, key=lambda x: x.get('min', 0)):
                min_total = tier.get('min', 0)
                max_total = tier.get('max', float('inf'))
                fee = tier.get('fee', 0)
                
                if min_total <= cart_total_xaf < max_total:
                    return fee
            
            # If no tier matches, return 0 or last tier fee
            if self.tier_rules:
                return self.tier_rules[-1].get('fee', 0)
            return 0
        
        return 0

