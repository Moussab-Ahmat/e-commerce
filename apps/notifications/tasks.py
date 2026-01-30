"""
Celery tasks for notifications.
"""
from celery import shared_task
from celery.exceptions import Retry
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging
from .models import NotificationLog, NotificationStatus
from .services import NotificationService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=None,  # Use notification's max_retries
    default_retry_delay=60,  # Initial retry delay in seconds
)
def send_notification_task(self, notification_id: int):
    """
    Celery task to send notification with retry/backoff.
    
    Args:
        notification_id: Notification log ID
    
    Returns:
        dict: Task result
    """
    try:
        notification = NotificationLog.objects.get(pk=notification_id)
    except NotificationLog.DoesNotExist:
        logger.error(f'Notification {notification_id} not found')
        return {'success': False, 'error': 'Notification not found'}
    
    # Check if already sent
    if notification.status == NotificationStatus.SENT:
        logger.info(f'Notification {notification_id} already sent')
        return {'success': True, 'status': 'already_sent'}
    
    # Mark as retrying if this is a retry
    if notification.status in [NotificationStatus.FAILED, NotificationStatus.RETRYING]:
        notification.mark_retrying()
    
    # Send notification
    result = NotificationService.send_notification(notification_id)
    
    if result['success']:
        logger.info(f'Notification {notification_id} sent successfully')
        return {'success': True, 'status': 'sent'}
    
    # If failed and can retry, schedule retry with exponential backoff
    notification = result['notification']
    if notification and notification.can_retry():
        # Calculate exponential backoff: 60s * 2^(retry_count - 1)
        retry_delay = 60 * (2 ** (notification.retry_count - 1))
        # Cap at 1 hour
        retry_delay = min(retry_delay, 3600)
        
        logger.warning(
            f'Notification {notification_id} failed, retrying in {retry_delay}s '
            f'(attempt {notification.retry_count + 1}/{notification.max_retries})'
        )
        
        # Raise Retry exception to trigger Celery retry
        raise self.retry(
            exc=Exception(result['errors'][0] if result['errors'] else 'Send failed'),
            countdown=retry_delay
        )
    
    # Max retries exceeded
    logger.error(
        f'Notification {notification_id} failed after {notification.retry_count} attempts'
    )
    return {'success': False, 'status': 'failed', 'error': result['errors'][0] if result['errors'] else 'Unknown error'}


@shared_task
def send_pending_notifications():
    """
    Celery beat task to send pending notifications.
    Runs periodically to process pending notifications.
    """
    # Get pending notifications older than 1 minute (to avoid race conditions)
    cutoff_time = timezone.now() - timedelta(minutes=1)
    
    pending_notifications = NotificationLog.objects.filter(
        status=NotificationStatus.PENDING,
        created_at__lt=cutoff_time
    )[:100]  # Process in batches
    
    sent_count = 0
    for notification in pending_notifications:
        send_notification_task.delay(notification.id)
        sent_count += 1
    
    return {
        'processed': sent_count,
        'timestamp': timezone.now().isoformat()
    }
