"""
Tests for procurement app.
"""
import pytest
from django.db import transaction
from django.utils import timezone
from datetime import date
from apps.procurement.models import (
    Supplier, PurchaseOrder, PurchaseOrderItem,
    GoodsReceipt, ReceiptItem
)
from apps.procurement.services import ProcurementService
from apps.catalog.models import Product, Category
from apps.inventory.models import InventoryItem, StockMovement
from apps.accounts.models import User


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
        stock_quantity=0,
        sku='TEST-001'
    )


@pytest.fixture
def supplier():
    """Create a test supplier."""
    return Supplier.objects.create(
        name='Test Supplier',
        code='SUP-001',
        email='supplier@test.com'
    )


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        phone_number='+23512345678',
        password='testpass'
    )


@pytest.fixture
def purchase_order(supplier, product, user):
    """Create a test purchase order."""
    po = PurchaseOrder.objects.create(
        po_number='PO-001',
        supplier=supplier,
        order_date=date.today(),
        created_by=user
    )
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        product=product,
        quantity_ordered=100,
        unit_price=5000
    )
    return po


@pytest.mark.django_db
class TestReceiptValidation:
    """Test goods receipt validation."""
    
    def test_validate_receipt_full_acceptance(self, purchase_order, product, user):
        """Test validating receipt with full acceptance."""
        # Create receipt
        receipt = GoodsReceipt.objects.create(
            receipt_number='GR-001',
            purchase_order=purchase_order,
            receipt_date=date.today(),
            created_by=user
        )
        
        po_item = purchase_order.items.first()
        ReceiptItem.objects.create(
            goods_receipt=receipt,
            purchase_order_item=po_item,
            quantity_accepted=100,
            quantity_rejected=0
        )
        
        # Validate receipt
        result = ProcurementService.validate_receipt(receipt.id, validated_by=user)
        
        assert result['success'] is True
        assert result['movements_created'] == 1
        assert result['items_processed'] == 1
        
        # Check receipt status
        receipt.refresh_from_db()
        assert receipt.status == GoodsReceipt.Status.VALIDATED
        assert receipt.validated_at is not None
        assert receipt.validated_by == user
        
        # Check inventory updated
        inventory_item = InventoryItem.objects.get(product=product)
        assert inventory_item.on_hand == 100
        
        # Check stock movement created
        movement = StockMovement.objects.filter(
            inventory_item=inventory_item,
            reference='GR-001'
        ).first()
        assert movement is not None
        assert movement.movement_type == StockMovement.MovementType.INBOUND
        assert movement.quantity == 100
        
        # Check PO item updated
        po_item.refresh_from_db()
        assert po_item.quantity_received == 100
        
        # Check PO status
        purchase_order.refresh_from_db()
        assert purchase_order.status == PurchaseOrder.Status.RECEIVED
    
    def test_validate_receipt_partial_acceptance(self, purchase_order, product, user):
        """Test validating receipt with partial acceptance."""
        # Create receipt
        receipt = GoodsReceipt.objects.create(
            receipt_number='GR-002',
            purchase_order=purchase_order,
            receipt_date=date.today(),
            created_by=user
        )
        
        po_item = purchase_order.items.first()
        ReceiptItem.objects.create(
            goods_receipt=receipt,
            purchase_order_item=po_item,
            quantity_accepted=60,
            quantity_rejected=40,
            rejection_reason='Damaged goods'
        )
        
        # Validate receipt
        result = ProcurementService.validate_receipt(receipt.id, validated_by=user)
        
        assert result['success'] is True
        assert result['movements_created'] == 1
        
        # Check inventory updated (only accepted quantity)
        inventory_item = InventoryItem.objects.get(product=product)
        assert inventory_item.on_hand == 60
        
        # Check stock movement
        movement = StockMovement.objects.filter(
            inventory_item=inventory_item,
            reference='GR-002'
        ).first()
        assert movement.quantity == 60
        
        # Check PO item updated
        po_item.refresh_from_db()
        assert po_item.quantity_received == 60
        
        # Check PO status (partially received)
        purchase_order.refresh_from_db()
        assert purchase_order.status == PurchaseOrder.Status.PARTIALLY_RECEIVED
    
    def test_validate_receipt_rejected_quantities(self, purchase_order, product, user):
        """Test validating receipt with rejected quantities."""
        # Create receipt
        receipt = GoodsReceipt.objects.create(
            receipt_number='GR-003',
            purchase_order=purchase_order,
            receipt_date=date.today(),
            created_by=user
        )
        
        po_item = purchase_order.items.first()
        ReceiptItem.objects.create(
            goods_receipt=receipt,
            purchase_order_item=po_item,
            quantity_accepted=0,
            quantity_rejected=100,
            rejection_reason='All items damaged'
        )
        
        # Validate receipt
        result = ProcurementService.validate_receipt(receipt.id, validated_by=user)
        
        assert result['success'] is True
        assert result['movements_created'] == 0  # No accepted items
        
        # Check inventory not updated
        inventory_item, created = InventoryItem.objects.get_or_create(
            product=product,
            defaults={'on_hand': 0, 'reserved': 0}
        )
        assert inventory_item.on_hand == 0
        
        # Check no stock movement created
        movement = StockMovement.objects.filter(
            inventory_item=inventory_item,
            reference='GR-003'
        ).first()
        assert movement is None
        
        # Check PO item not updated
        po_item.refresh_from_db()
        assert po_item.quantity_received == 0
    
    def test_validate_receipt_idempotency(self, purchase_order, product, user):
        """Test that validating the same receipt twice does not double stock."""
        # Create receipt
        receipt = GoodsReceipt.objects.create(
            receipt_number='GR-004',
            purchase_order=purchase_order,
            receipt_date=date.today(),
            created_by=user
        )
        
        po_item = purchase_order.items.first()
        ReceiptItem.objects.create(
            goods_receipt=receipt,
            purchase_order_item=po_item,
            quantity_accepted=50,
            quantity_rejected=0
        )
        
        # Validate receipt first time
        result1 = ProcurementService.validate_receipt(receipt.id, validated_by=user)
        assert result1['success'] is True
        
        # Check inventory
        inventory_item = InventoryItem.objects.get(product=product)
        on_hand_after_first = inventory_item.on_hand
        assert on_hand_after_first == 50
        
        # Count movements
        movements_count_after_first = StockMovement.objects.filter(
            inventory_item=inventory_item,
            reference='GR-004'
        ).count()
        assert movements_count_after_first == 1
        
        # Validate receipt second time (idempotency test)
        result2 = ProcurementService.validate_receipt(receipt.id, validated_by=user)
        assert result2['success'] is True
        assert 'already validated' in result2['errors'][0].lower()
        
        # Check inventory not doubled
        inventory_item.refresh_from_db()
        assert inventory_item.on_hand == on_hand_after_first  # Still 50, not 100
        
        # Check no new movement created
        movements_count_after_second = StockMovement.objects.filter(
            inventory_item=inventory_item,
            reference='GR-004'
        ).count()
        assert movements_count_after_second == movements_count_after_first  # Still 1
    
    def test_validate_receipt_multiple_items(self, supplier, category, user):
        """Test validating receipt with multiple items."""
        # Create products
        product1 = Product.objects.create(
            name='Product 1',
            slug='product-1',
            category=category,
            price=10000,
            sku='PROD-1'
        )
        product2 = Product.objects.create(
            name='Product 2',
            slug='product-2',
            category=category,
            price=20000,
            sku='PROD-2'
        )
        
        # Create PO
        po = PurchaseOrder.objects.create(
            po_number='PO-002',
            supplier=supplier,
            order_date=date.today(),
            created_by=user
        )
        po_item1 = PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product1,
            quantity_ordered=50,
            unit_price=5000
        )
        po_item2 = PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product2,
            quantity_ordered=30,
            unit_price=10000
        )
        
        # Create receipt
        receipt = GoodsReceipt.objects.create(
            receipt_number='GR-005',
            purchase_order=po,
            receipt_date=date.today(),
            created_by=user
        )
        ReceiptItem.objects.create(
            goods_receipt=receipt,
            purchase_order_item=po_item1,
            quantity_accepted=50,
            quantity_rejected=0
        )
        ReceiptItem.objects.create(
            goods_receipt=receipt,
            purchase_order_item=po_item2,
            quantity_accepted=25,
            quantity_rejected=5
        )
        
        # Validate receipt
        result = ProcurementService.validate_receipt(receipt.id, validated_by=user)
        
        assert result['success'] is True
        assert result['movements_created'] == 2
        assert result['items_processed'] == 2
        
        # Check inventory for both products
        inventory_item1 = InventoryItem.objects.get(product=product1)
        assert inventory_item1.on_hand == 50
        
        inventory_item2 = InventoryItem.objects.get(product=product2)
        assert inventory_item2.on_hand == 25
        
        # Check PO items updated
        po_item1.refresh_from_db()
        assert po_item1.quantity_received == 50
        
        po_item2.refresh_from_db()
        assert po_item2.quantity_received == 25


@pytest.mark.django_db
class TestCreateReceipt:
    """Test creating goods receipts."""
    
    def test_create_receipt(self, purchase_order, user):
        """Test creating a goods receipt."""
        po_item = purchase_order.items.first()
        
        result = ProcurementService.create_receipt(
            purchase_order_id=purchase_order.id,
            receipt_number='GR-006',
            receipt_date=date.today(),
            items=[
                {
                    'purchase_order_item_id': po_item.id,
                    'quantity_accepted': 80,
                    'quantity_rejected': 20,
                    'rejection_reason': 'Some items damaged'
                }
            ],
            created_by=user
        )
        
        assert result['success'] is True
        assert result['receipt_id'] is not None
        
        receipt = GoodsReceipt.objects.get(pk=result['receipt_id'])
        assert receipt.receipt_number == 'GR-006'
        assert receipt.status == GoodsReceipt.Status.DRAFT
        
        receipt_item = receipt.items.first()
        assert receipt_item.quantity_accepted == 80
        assert receipt_item.quantity_rejected == 20
    
    def test_create_receipt_duplicate_number(self, purchase_order, user):
        """Test creating receipt with duplicate number."""
        GoodsReceipt.objects.create(
            receipt_number='GR-007',
            purchase_order=purchase_order,
            receipt_date=date.today()
        )
        
        po_item = purchase_order.items.first()
        result = ProcurementService.create_receipt(
            purchase_order_id=purchase_order.id,
            receipt_number='GR-007',
            receipt_date=date.today(),
            items=[
                {
                    'purchase_order_item_id': po_item.id,
                    'quantity_accepted': 50,
                    'quantity_rejected': 0
                }
            ],
            created_by=user
        )
        
        assert result['success'] is False
        assert 'already exists' in result['errors'][0].lower()
