"""
Notification service for creating and sending notifications.
"""
from typing import Dict, Any, Optional
from django.conf import settings
from .models import NotificationLog, NotificationType, NotificationStatus
from .templates import NotificationTemplates
from .providers import NotificationProvider, LoggingNotificationProvider


class NotificationService:
    """Service for notification operations."""
    
    _provider: Optional[NotificationProvider] = None
    
    @classmethod
    def get_provider(cls) -> NotificationProvider:
        """Get notification provider instance."""
        if cls._provider is None:
            # Use provider from settings or default to logging
            provider_class = getattr(
                settings,
                'NOTIFICATION_PROVIDER_CLASS',
                'apps.notifications.providers.LoggingNotificationProvider'
            )
            
            if isinstance(provider_class, str):
                from django.utils.module_loading import import_string
                provider_class = import_string(provider_class)
            
            cls._provider = provider_class()
        
        return cls._provider
    
    @classmethod
    def set_provider(cls, provider: NotificationProvider):
        """Set notification provider (for testing)."""
        cls._provider = provider
    
    @classmethod
    def create_notification(
        cls,
        recipient_phone: str,
        notification_type: str,
        context: Dict[str, Any],
        order=None,
        delivery=None
    ) -> NotificationLog:
        """
        Create a notification log entry.
        
        Args:
            recipient_phone: Recipient phone number
            notification_type: Notification type
            context: Context dict for template
            order: Related order (optional)
            delivery: Related delivery (optional)
        
        Returns:
            NotificationLog instance
        """
        # Get message from template
        message = NotificationTemplates.get_message(notification_type, context)
        
        # Create notification log
        notification = NotificationLog.objects.create(
            recipient_phone=recipient_phone,
            notification_type=notification_type,
            message=message,
            status=NotificationStatus.PENDING,
            order=order,
            delivery=delivery
        )
        
        return notification
    
    @classmethod
    def send_notification(cls, notification_id: int) -> Dict[str, Any]:
        """
        Send notification via provider.
        
        Args:
            notification_id: Notification log ID
        
        Returns:
            dict: {
                'success': bool,
                'notification': NotificationLog instance or None,
                'errors': list
            }
        """
        result = {
            'success': True,
            'notification': None,
            'errors': []
        }
        
        try:
            notification = NotificationLog.objects.get(pk=notification_id)
        except NotificationLog.DoesNotExist:
            result['success'] = False
            result['errors'].append(f'Notification {notification_id} not found')
            return result
        
        # Check if already sent
        if notification.status == NotificationStatus.SENT:
            result['notification'] = notification
            return result
        
        # Get provider
        provider = cls.get_provider()
        
        # Send notification
        try:
            send_result = provider.send(
                recipient_phone=notification.recipient_phone,
                message=notification.message
            )
            
            if send_result['success']:
                notification.mark_sent()
                result['notification'] = notification
            else:
                # Mark as failed if retries exhausted
                if not notification.can_retry():
                    notification.mark_failed(send_result.get('error', 'Unknown error'))
                    result['success'] = False
                    result['errors'].append(send_result.get('error', 'Failed to send'))
                else:
                    # Will be retried
                    notification.mark_failed(send_result.get('error', 'Unknown error'))
                    result['success'] = False
                    result['errors'].append('Failed to send, will retry')
                
                result['notification'] = notification
                
        except Exception as e:
            # Mark as failed if retries exhausted
            if not notification.can_retry():
                notification.mark_failed(str(e))
                result['success'] = False
                result['errors'].append(str(e))
            else:
                notification.mark_failed(str(e))
                result['success'] = False
                result['errors'].append(f'Error: {str(e)}, will retry')
            
            result['notification'] = notification
        
        return result
