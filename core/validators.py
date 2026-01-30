"""
Custom validators for the e-commerce application.
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_phone_number(value):
    """Validate phone number format for Chad (+235)."""
    # Chad phone number format: +235XXXXXXXXX or 235XXXXXXXXX
    pattern = r'^(\+?235)?[0-9]{8,9}$'
    if not re.match(pattern, value):
        raise ValidationError(
            _('Invalid phone number format. Use format: +235XXXXXXXXX')
        )


def validate_xaf_amount(value):
    """Validate XAF amount is positive integer."""
    if not isinstance(value, int):
        raise ValidationError(_('Amount must be an integer.'))
    if value < 0:
        raise ValidationError(_('Amount must be positive.'))

