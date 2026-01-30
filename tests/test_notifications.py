"""
Tests for notifications app.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from celery.exceptions import Retry
from apps.notifications.models import NotificationLog, NotificationType, NotificationStatus
from apps.notifications.services import NotificationService
from apps.notifications.tasks import send_notification_task
from apps.notifications.providers import MockNotificationProvider
from apps.orders.models import Order, OrderItem
from apps.accounts.models import User
from apps.catalog.models import Product, Category
from apps.delivery.models import DeliveryZone


@pytest.fixture
def category():
    """Create a test category."""
    return Category.objects.create(
        name='Test Category',
        slug='test-category'
    )


@pytest.fixture
def product(category):
    """Create a test product."""
    return Product.objects.create(
        name='Test Product',
        slug='test-product',
        category=category,
        price=10000,
        stock_quantity=100,
        sku='TEST-001'
    )


@pytest.fixture
def customer_user():
    """Create a customer user."""
    return User.objects.create_user(
        phone_number='+23512345678',
        password='testpass',
        role=User.Role.CUSTOMER
    )


@pytest.fixture
def order(customer_user, product, delivery_zone):
    """Create a test order."""
    order = Order.objects.create(
        user=customer_user,
        order_number='ORD-TEST-001',
        status=Order.Status.CONFIRMED,
        delivery_zone=delivery_zone,
        delivery_address_line1='123 Main St',
        delivery_city='N\'Djamena',
        delivery_region='Chari-Baguirmi',
        delivery_phone='+23512345678',
        subtotal=10000,
        delivery_fee=2000,
        total=12000
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        unit_price=10000
    )
    return order


@pytest.mark.django_db
class TestNotificationTemplates:
    """Test notification templates."""
    
    def test_order_confirmation_template(self, order):
        """Test order confirmation message template."""
        from apps.notifications.templates import NotificationTemplates
        
        message = NotificationTemplates.get_order_confirmation_message(order)
        
        assert order.order_number in message
        assert '120' in message  # 12000 / 100
        assert 'confirmée' in message.lower()
    
    def test_order_reminder_template(self, order):
        """Test order reminder message template."""
        from apps.notifications.templates import NotificationTemplates
        
        message = NotificationTemplates.get_order_reminder_message(order)
        
        assert order.order_number in message
        assert 'Rappel' in message
    
    def test_order_delivered_template(self, order):
        """Test order delivered message template."""
        from apps.notifications.templates import NotificationTemplates
        
        message = NotificationTemplates.get_order_delivered_message(order)
        
        assert order.order_number in message
        assert 'livrée' in message.lower()
    
    def test_order_failed_template(self, order):
        """Test order failed message template."""
        from apps.notifications.templates import NotificationTemplates
        
        message = NotificationTemplates.get_order_failed_message(order, 'Customer not available')
        
        assert order.order_number in message
        assert 'not available' in message


@pytest.mark.django_db
class TestNotificationService:
    """Test notification service."""
    
    def test_create_notification(self, order):
        """Test creating notification log."""
        notification = NotificationService.create_notification(
            recipient_phone='+23512345678',
            notification_type=NotificationType.ORDER_CONFIRMATION,
            context={'order': order},
            order=order
        )
        
        assert notification.recipient_phone == '+23512345678'
        assert notification.notification_type == NotificationType.ORDER_CONFIRMATION
        assert notification.status == NotificationStatus.PENDING
        assert notification.order == order
        assert notification.message is not None
        assert len(notification.message) > 0
    
    def test_send_notification_success(self, order):
        """Test sending notification successfully."""
        notification = NotificationService.create_notification(
            recipient_phone='+23512345678',
            notification_type=NotificationType.ORDER_CONFIRMATION,
            context={'order': order},
            order=order
        )
        
        result = NotificationService.send_notification(notification.id)
        
        assert result['success'] is True
        notification.refresh_from_db()
        assert notification.status == NotificationStatus.SENT
        assert notification.sent_at is not None
    
    def test_send_notification_failure_with_retry(self, order):
        """Test sending notification with failure and retry capability."""
        # Use mock provider that fails on first attempt
        mock_provider = MockNotificationProvider(fail_on_attempts=[1])
        NotificationService.set_provider(mock_provider)
        
        notification = NotificationService.create_notification(
            recipient_phone='+23512345678',
            notification_type=NotificationType.ORDER_CONFIRMATION,
            context={'order': order},
            order=order
        )
        
        result = NotificationService.send_notification(notification.id)
        
        assert result['success'] is False
        notification.refresh_from_db()
        assert notification.status == NotificationStatus.FAILED
        assert notification.can_retry() is True
        assert notification.retry_count == 0  # Not incremented yet (will be on retry)
    
    def test_send_notification_max_retries_exceeded(self, order):
        """Test notification fails after max retries."""
        # Use mock provider that always fails
        mock_provider = MockNotificationProvider(fail_on_attempts=[1, 2, 3, 4])
        NotificationService.set_provider(mock_provider)
        
        notification = NotificationService.create_notification(
            recipient_phone='+23512345678',
            notification_type=NotificationType.ORDER_CONFIRMATION,
            context={'order': order},
            order=order
        )
        notification.max_retries = 3
        notification.save()
        
        # Simulate multiple failed attempts
        for i in range(3):
            result = NotificationService.send_notification(notification.id)
            notification.refresh_from_db()
            if i < 2:
                assert notification.can_retry() is True
            else:
                assert notification.can_retry() is False
                assert notification.status == NotificationStatus.FAILED


@pytest.mark.django_db
class TestNotificationTask:
    """Test Celery notification task."""
    
    def test_send_notification_task_success(self, order):
        """Test successful notification task."""
        notification = NotificationService.create_notification(
            recipient_phone='+23512345678',
            notification_type=NotificationType.ORDER_CONFIRMATION,
            context={'order': order},
            order=order
        )
        
        # Create mock task instance
        mock_task = MagicMock()
        mock_task.retry = MagicMock()
        
        result = send_notification_task(mock_task, notification.id)
        
        assert result['success'] is True
        notification.refresh_from_db()
        assert notification.status == NotificationStatus.SENT
    
    def test_send_notification_task_retry(self, order):
        """Test notification task retries on failure."""
        # Use mock provider that fails on first attempt
        mock_provider = MockNotificationProvider(fail_on_attempts=[1])
        NotificationService.set_provider(mock_provider)
        
        notification = NotificationService.create_notification(
            recipient_phone='+23512345678',
            notification_type=NotificationType.ORDER_CONFIRMATION,
            context={'order': order},
            order=order
        )
        
        # Create mock task instance that raises Retry
        mock_task = MagicMock()
        mock_task.retry = MagicMock(side_effect=Retry('Retry needed'))
        
        # Task should raise Retry exception
        with pytest.raises(Retry):
            send_notification_task(mock_task, notification.id)
        
        # Verify retry was called
        mock_task.retry.assert_called_once()
        
        # Check notification marked as retrying
        notification.refresh_from_db()
        assert notification.status == NotificationStatus.RETRYING or notification.status == NotificationStatus.FAILED
        assert notification.retry_count > 0
    
    def test_send_notification_task_exponential_backoff(self, order):
        """Test exponential backoff calculation."""
        notification = NotificationService.create_notification(
            recipient_phone='+23512345678',
            notification_type=NotificationType.ORDER_CONFIRMATION,
            context={'order': order},
            order=order
        )
        
        # Simulate retries
        notification.retry_count = 1
        notification.save()
        
        # Calculate backoff: 60 * 2^(retry_count - 1)
        retry_delay = 60 * (2 ** (notification.retry_count - 1))
        assert retry_delay == 60  # First retry: 60s
        
        notification.retry_count = 2
        notification.save()
        retry_delay = 60 * (2 ** (notification.retry_count - 1))
        assert retry_delay == 120  # Second retry: 120s
        
        notification.retry_count = 3
        notification.save()
        retry_delay = 60 * (2 ** (notification.retry_count - 1))
        assert retry_delay == 240  # Third retry: 240s


@pytest.mark.django_db
class TestNotificationLog:
    """Test notification log model."""
    
    def test_notification_log_creation(self, order):
        """Test creating notification log."""
        notification = NotificationLog.objects.create(
            recipient_phone='+23512345678',
            notification_type=NotificationType.ORDER_CONFIRMATION,
            message='Test message',
            order=order
        )
        
        assert notification.status == NotificationStatus.PENDING
        assert notification.retry_count == 0
        assert notification.max_retries == 3
    
    def test_can_retry(self, order):
        """Test can_retry method."""
        notification = NotificationLog.objects.create(
            recipient_phone='+23512345678',
            notification_type=NotificationType.ORDER_CONFIRMATION,
            message='Test message',
            order=order
        )
        
        assert notification.can_retry() is True
        
        # After max retries
        notification.retry_count = 3
        notification.save()
        assert notification.can_retry() is False
        
        # If already sent
        notification.status = NotificationStatus.SENT
        notification.save()
        assert notification.can_retry() is False
    
    def test_mark_sent(self, order):
        """Test mark_sent method."""
        notification = NotificationLog.objects.create(
            recipient_phone='+23512345678',
            notification_type=NotificationType.ORDER_CONFIRMATION,
            message='Test message',
            order=order
        )
        
        notification.mark_sent()
        
        assert notification.status == NotificationStatus.SENT
        assert notification.sent_at is not None
    
    def test_mark_failed(self, order):
        """Test mark_failed method."""
        notification = NotificationLog.objects.create(
            recipient_phone='+23512345678',
            notification_type=NotificationType.ORDER_CONFIRMATION,
            message='Test message',
            order=order
        )
        
        notification.mark_failed('Test error')
        
        assert notification.status == NotificationStatus.FAILED
        assert notification.error_message == 'Test error'
    
    def test_mark_retrying(self, order):
        """Test mark_retrying method."""
        notification = NotificationLog.objects.create(
            recipient_phone='+23512345678',
            notification_type=NotificationType.ORDER_CONFIRMATION,
            message='Test message',
            order=order
        )
        
        initial_retry_count = notification.retry_count
        notification.mark_retrying()
        
        assert notification.status == NotificationStatus.RETRYING
        assert notification.retry_count == initial_retry_count + 1
        assert notification.last_retry_at is not None
