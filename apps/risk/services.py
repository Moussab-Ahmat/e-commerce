"""
Risk services for blacklist and COD limit checks.
"""
from django.utils import timezone
from .models import Blacklist, CodLimitRule
from apps.orders.models import Order


class RiskService:
    """Service for risk management operations."""
    
    @staticmethod
    def check_blacklist(phone_number):
        """
        Check if phone number is blacklisted.
        
        Args:
            phone_number: Phone number to check
        
        Returns:
            dict: {
                'is_blacklisted': bool,
                'blacklist': Blacklist instance or None,
                'reason': str or None
            }
        """
        blacklist = Blacklist.objects.filter(
            phone_number=phone_number,
            is_active=True
        ).first()
        
        if blacklist:
            return {
                'is_blacklisted': True,
                'blacklist': blacklist,
                'reason': blacklist.reason
            }
        
        return {
            'is_blacklisted': False,
            'blacklist': None,
            'reason': None
        }
    
    @staticmethod
    def check_cod_limit(user, order_total_xaf):
        """
        Check if order total exceeds COD limit for the day.
        
        Args:
            user: User placing the order
            order_total_xaf: Order total in XAF
        
        Returns:
            dict: {
                'within_limit': bool,
                'current_total': int,
                'limit': int or None,
                'remaining': int or None,
                'error': str or None
            }
        """
        rule = CodLimitRule.get_active_limit()
        
        if not rule:
            # No limit rule, allow all
            return {
                'within_limit': True,
                'current_total': 0,
                'limit': None,
                'remaining': None,
                'error': None
            }
        
        # Get today's COD total for user
        today = timezone.now().date()
        current_total = CodLimitRule.get_daily_cod_total(user, today)
        
        # Check if adding this order would exceed limit
        new_total = current_total + order_total_xaf
        
        if new_total > rule.limit_amount_xaf:
            return {
                'within_limit': False,
                'current_total': current_total,
                'limit': rule.limit_amount_xaf,
                'remaining': max(0, rule.limit_amount_xaf - current_total),
                'error': f'COD limit exceeded. Daily limit: {rule.limit_amount_xaf} XAF, '
                        f'Current: {current_total} XAF, Order: {order_total_xaf} XAF'
            }
        
        return {
            'within_limit': True,
            'current_total': current_total,
            'limit': rule.limit_amount_xaf,
            'remaining': rule.limit_amount_xaf - new_total,
            'error': None
        }
    
    @staticmethod
    def validate_order_creation(user, order_total_xaf):
        """
        Validate order creation against risk rules.
        
        Args:
            user: User creating the order
            order_total_xaf: Order total in XAF
        
        Returns:
            dict: {
                'allowed': bool,
                'errors': list
            }
        """
        errors = []
        
        # Check blacklist
        blacklist_check = RiskService.check_blacklist(user.phone_number)
        if blacklist_check['is_blacklisted']:
            errors.append(f'Phone number is blacklisted: {blacklist_check["reason"]}')
        
        # Check COD limit
        cod_check = RiskService.check_cod_limit(user, order_total_xaf)
        if not cod_check['within_limit']:
            errors.append(cod_check['error'])
        
        return {
            'allowed': len(errors) == 0,
            'errors': errors
        }
