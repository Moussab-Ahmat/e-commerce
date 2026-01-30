"""
Custom exceptions for the e-commerce application.
"""
from rest_framework.exceptions import APIException
from rest_framework import status


class InsufficientStockError(APIException):
    """Raised when product stock is insufficient."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Insufficient stock available.'
    default_code = 'insufficient_stock'


class InvalidOrderStatusError(APIException):
    """Raised when order status transition is invalid."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid order status transition.'
    default_code = 'invalid_order_status'


class InvalidDeliveryStatusError(APIException):
    """Raised when delivery status transition is invalid."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid delivery status transition.'
    default_code = 'invalid_delivery_status'


class OrderAlreadyProcessedError(APIException):
    """Raised when trying to modify an already processed order."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Order has already been processed and cannot be modified.'
    default_code = 'order_already_processed'

