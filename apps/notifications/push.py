"""
Firebase Cloud Messaging push notification utilities.

Firebase is used ONLY for sending push notifications.
All notification history is stored in PostgreSQL via PushNotification model.
"""
import logging
from typing import Optional
import firebase_admin
from firebase_admin import messaging
from apps.accounts.models import User
from .models import PushNotification

logger = logging.getLogger(__name__)


def send_push_notification(
    user_id: int,
    title: str,
    body: str,
    notification_type: str,
    data: Optional[dict] = None,
) -> bool:
    """
    Send a push notification to a user via FCM and save to database.

    Args:
        user_id: ID of the recipient user
        title: Notification title
        body: Notification body text
        notification_type: Type from PushNotificationType choices
        data: Optional extra data payload (order_id, product_id, etc.)

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f'Push notification failed: user {user_id} not found')
        return False

    # Save notification to database regardless of FCM send result
    notification = PushNotification.objects.create(
        user=user,
        title=title,
        body=body,
        notification_type=notification_type,
        data=data,
        is_sent=False,
    )

    # Check if user has an FCM token
    if not user.fcm_token:
        logger.warning(f'User {user_id} has no FCM token, notification saved but not pushed')
        return False

    # Check if Firebase is initialized
    if not firebase_admin._apps:
        logger.warning('Firebase not initialized, notification saved but not pushed')
        return False

    # Build and send FCM message
    try:
        # Ensure all data values are strings (FCM requirement)
        fcm_data = {}
        if data:
            fcm_data = {k: str(v) for k, v in data.items()}
        fcm_data['notification_type'] = notification_type
        fcm_data['notification_id'] = str(notification.id)

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=fcm_data,
            token=user.fcm_token,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound='default',
                    channel_id='default_channel',
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=PushNotification.objects.filter(
                            user=user, is_read=False
                        ).count(),
                    ),
                ),
            ),
        )

        response = messaging.send(message)
        notification.is_sent = True
        notification.save(update_fields=['is_sent'])
        logger.info(f'Push notification sent to user {user_id}: {response}')
        return True

    except messaging.UnregisteredError:
        # Token is invalid/expired - clear it
        logger.warning(f'FCM token invalid for user {user_id}, clearing token')
        user.fcm_token = None
        user.save(update_fields=['fcm_token'])
        return False

    except messaging.SenderIdMismatchError:
        logger.error(f'FCM sender ID mismatch for user {user_id}')
        user.fcm_token = None
        user.save(update_fields=['fcm_token'])
        return False

    except Exception as e:
        logger.error(f'FCM send failed for user {user_id}: {e}')
        return False


def send_push_to_multiple_users(
    user_ids: list,
    title: str,
    body: str,
    notification_type: str,
    data: Optional[dict] = None,
    batch_size: int = 500,
) -> dict:
    """
    Send push notifications to multiple users in batches.

    Args:
        user_ids: List of user IDs
        title: Notification title
        body: Notification body text
        notification_type: Type from PushNotificationType choices
        data: Optional extra data payload
        batch_size: Max tokens per FCM batch (max 500)

    Returns:
        dict with sent_count, failed_count, total
    """
    result = {'sent_count': 0, 'failed_count': 0, 'total': len(user_ids)}

    users = User.objects.filter(
        pk__in=user_ids,
        fcm_token__isnull=False,
    ).exclude(fcm_token='')

    # Save notifications for ALL users (even those without tokens)
    notifications = []
    for uid in user_ids:
        notifications.append(PushNotification(
            user_id=uid,
            title=title,
            body=body,
            notification_type=notification_type,
            data=data,
            is_sent=False,
        ))
    PushNotification.objects.bulk_create(notifications)

    if not firebase_admin._apps:
        logger.warning('Firebase not initialized, notifications saved but not pushed')
        return result

    # Collect tokens and send in batches
    tokens = list(users.values_list('fcm_token', flat=True))
    if not tokens:
        return result

    fcm_data = {}
    if data:
        fcm_data = {k: str(v) for k, v in data.items()}
    fcm_data['notification_type'] = notification_type

    for i in range(0, len(tokens), batch_size):
        batch_tokens = tokens[i:i + batch_size]
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=fcm_data,
            tokens=batch_tokens,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound='default',
                    channel_id='default_channel',
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound='default'),
                ),
            ),
        )

        try:
            response = messaging.send_each_for_multicast(message)
            result['sent_count'] += response.success_count
            result['failed_count'] += response.failure_count

            # Clear invalid tokens
            for idx, send_response in enumerate(response.responses):
                if send_response.exception and isinstance(
                    send_response.exception,
                    (messaging.UnregisteredError, messaging.SenderIdMismatchError)
                ):
                    User.objects.filter(
                        fcm_token=batch_tokens[idx]
                    ).update(fcm_token=None)

        except Exception as e:
            logger.error(f'FCM batch send failed: {e}')
            result['failed_count'] += len(batch_tokens)

    # Mark sent notifications
    PushNotification.objects.filter(
        user__fcm_token__isnull=False,
        user_id__in=user_ids,
        is_sent=False,
        notification_type=notification_type,
    ).update(is_sent=True)

    logger.info(
        f'Batch push: {result["sent_count"]} sent, '
        f'{result["failed_count"]} failed out of {result["total"]}'
    )
    return result
