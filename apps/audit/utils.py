"""
Audit logging utilities.
"""
from .models import AuditLog
from django.contrib.contenttypes.models import ContentType


def log_audit_event(
    user,
    action,
    resource_type,
    related_object=None,
    old_values=None,
    new_values=None,
    request=None,
    notes=''
):
    """Create an audit log entry."""
    audit_data = {
        'user': user,
        'action': action,
        'resource_type': resource_type,
        'old_values': old_values,
        'new_values': new_values,
        'notes': notes,
    }
    
    if related_object:
        audit_data['content_type'] = ContentType.objects.get_for_model(related_object)
        audit_data['object_id'] = related_object.pk
    
    if request:
        audit_data['ip_address'] = getattr(request, '_audit_data', {}).get('ip_address')
        audit_data['user_agent'] = getattr(request, '_audit_data', {}).get('user_agent')
        audit_data['request_path'] = getattr(request, '_audit_data', {}).get('request_path')
        audit_data['request_method'] = getattr(request, '_audit_data', {}).get('request_method')
    
    return AuditLog.objects.create(**audit_data)

