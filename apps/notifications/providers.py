"""
Notification provider interface and implementations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class NotificationProvider(ABC):
    """Abstract base class for notification providers."""
    
    @abstractmethod
    def send(self, recipient_phone: str, message: str, **kwargs) -> Dict[str, Any]:
        """
        Send notification to recipient.
        
        Args:
            recipient_phone: Recipient phone number
            message: Notification message
            **kwargs: Additional provider-specific parameters
        
        Returns:
            dict: {
                'success': bool,
                'message_id': str or None,
                'error': str or None
            }
        """
        pass


class LoggingNotificationProvider(NotificationProvider):
    """Logging provider (for development/testing)."""
    
    def send(self, recipient_phone: str, message: str, **kwargs) -> Dict[str, Any]:
        """
        Log notification instead of sending (for development).
        
        Args:
            recipient_phone: Recipient phone number
            message: Notification message
            **kwargs: Additional parameters (ignored)
        
        Returns:
            dict: Success result
        """
        logger.info(
            f'[NOTIFICATION] To: {recipient_phone}, Message: {message}',
            extra={
                'recipient_phone': recipient_phone,
                'message': message,
                'provider': 'logging'
            }
        )
        
        return {
            'success': True,
            'message_id': f'log-{recipient_phone}',
            'error': None
        }


class MockNotificationProvider(NotificationProvider):
    """Mock provider that can simulate failures for testing."""
    
    def __init__(self, fail_on_attempts=None):
        """
        Initialize mock provider.
        
        Args:
            fail_on_attempts: List of attempt numbers (1-indexed) that should fail
                             e.g., [1, 2] means first and second attempts fail
        """
        self.fail_on_attempts = fail_on_attempts or []
        self.attempt_count = 0
    
    def send(self, recipient_phone: str, message: str, **kwargs) -> Dict[str, Any]:
        """
        Mock send with configurable failures.
        
        Args:
            recipient_phone: Recipient phone number
            message: Notification message
            **kwargs: Additional parameters
        
        Returns:
            dict: Success or failure result
        """
        self.attempt_count += 1
        
        if self.attempt_count in self.fail_on_attempts:
            logger.warning(
                f'[MOCK NOTIFICATION FAILURE] Attempt {self.attempt_count} failed for {recipient_phone}'
            )
            return {
                'success': False,
                'message_id': None,
                'error': f'Simulated failure on attempt {self.attempt_count}'
            }
        
        logger.info(
            f'[MOCK NOTIFICATION] To: {recipient_phone}, Message: {message}',
            extra={
                'recipient_phone': recipient_phone,
                'message': message,
                'provider': 'mock',
                'attempt': self.attempt_count
            }
        )
        
        return {
            'success': True,
            'message_id': f'mock-{recipient_phone}-{self.attempt_count}',
            'error': None
        }
