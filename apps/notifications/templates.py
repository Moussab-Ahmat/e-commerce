"""
Notification message templates.
"""
from typing import Dict, Any, Optional
from apps.orders.models import Order
from apps.deliveries.models import Delivery


class NotificationTemplates:
    """Notification message templates."""
    
    @staticmethod
    def get_order_confirmation_message(order: Order) -> str:
        """Get order confirmation message."""
        return (
            f"Votre commande {order.order_number} a été confirmée. "
            f"Montant total: {order.total / 100:.0f} XAF. "
            f"Merci pour votre achat!"
        )
    
    @staticmethod
    def get_order_reminder_message(order: Order) -> str:
        """Get order reminder message."""
        return (
            f"Rappel: Votre commande {order.order_number} est en cours de préparation. "
            f"Montant: {order.total / 100:.0f} XAF. "
            f"Paiement à la livraison."
        )
    
    @staticmethod
    def get_order_delivered_message(order: Order) -> str:
        """Get order delivered message."""
        return (
            f"Votre commande {order.order_number} a été livrée avec succès! "
            f"Merci d'avoir fait vos achats avec nous."
        )
    
    @staticmethod
    def get_order_failed_message(order: Order, reason: Optional[str] = None) -> str:
        """Get order failed message."""
        base_message = (
            f"Votre commande {order.order_number} n'a pas pu être livrée."
        )
        if reason:
            return f"{base_message} Raison: {reason}"
        return base_message
    
    @staticmethod
    def get_delivery_assigned_message(delivery: Delivery) -> str:
        """Get delivery assigned message."""
        return (
            f"Votre commande {delivery.order.order_number} a été assignée à un livreur. "
            f"Vous serez contacté bientôt."
        )
    
    @staticmethod
    def get_delivery_in_transit_message(delivery: Delivery) -> str:
        """Get delivery in transit message."""
        return (
            f"Votre commande {delivery.order.order_number} est en route. "
            f"Le livreur arrivera bientôt."
        )
    
    @staticmethod
    def get_message(
        notification_type: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Get message for notification type.
        
        Args:
            notification_type: Notification type
            context: Context dict with 'order' and/or 'delivery'
        
        Returns:
            str: Formatted message
        """
        order = context.get('order')
        delivery = context.get('delivery')
        reason = context.get('reason')
        
        if notification_type == 'ORDER_CONFIRMATION' and order:
            return NotificationTemplates.get_order_confirmation_message(order)
        elif notification_type == 'ORDER_REMINDER' and order:
            return NotificationTemplates.get_order_reminder_message(order)
        elif notification_type == 'ORDER_DELIVERED' and order:
            return NotificationTemplates.get_order_delivered_message(order)
        elif notification_type == 'ORDER_FAILED' and order:
            return NotificationTemplates.get_order_failed_message(order, reason)
        elif notification_type == 'DELIVERY_ASSIGNED' and delivery:
            return NotificationTemplates.get_delivery_assigned_message(delivery)
        elif notification_type == 'DELIVERY_IN_TRANSIT' and delivery:
            return NotificationTemplates.get_delivery_in_transit_message(delivery)
        else:
            return f"Notification: {notification_type}"
