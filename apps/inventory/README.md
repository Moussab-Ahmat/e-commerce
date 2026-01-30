# Inventory App

Inventory management with atomic stock operations and concurrency protection.

## Features

- **InventoryItem**: Tracks on-hand and reserved quantities per product
- **StockMovement**: Records all stock movements (INBOUND, OUTBOUND, ADJUST, RETURN_IN, DAMAGED)
- **InventoryService**: Atomic operations with `select_for_update` and transactions
- Concurrency protection to prevent overselling
- Admin integration for inventory management

## Models

### InventoryItem
- One-to-one relationship with Product
- Tracks `on_hand` (available stock)
- Tracks `reserved` (reserved for orders)
- `available` property: `on_hand - reserved`
- `reorder_point` for inventory alerts
- `needs_reorder` property

### StockMovement
- Tracks all stock movements
- Movement types: INBOUND, OUTBOUND, ADJUST, RETURN_IN, DAMAGED
- Links to inventory item and user
- Reference field for order numbers, PO numbers, etc.

## InventoryService Methods

All methods use `@transaction.atomic` and `select_for_update()` for concurrency safety.

### check_available(items)
Check if items are available in requested quantities.

**Input:**
```python
items = [
    {'product_id': 1, 'quantity': 50},
    {'product_id': 2, 'quantity': 30}
]
```

**Output:**
```python
{
    'available': True/False,
    'items': [
        {
            'product_id': 1,
            'requested': 50,
            'available': 100,
            'sufficient': True
        }
    ]
}
```

### reserve(order_items, reference='')
Reserve stock for order items. Uses pessimistic locking.

**Input:**
```python
order_items = [
    {'product_id': 1, 'quantity': 50}
]
reference = 'ORDER-001'
```

**Output:**
```python
{
    'success': True,
    'reserved_items': [...],
    'errors': []
}
```

### release(order_items, reference='')
Release reserved stock (e.g., order cancelled).

### commit_outbound(order_items, reference='')
Commit outbound stock (confirm order fulfillment). Reduces both reserved and on_hand.

### adjust_inventory(product_id, quantity, reason='', created_by=None)
Manual inventory adjustment.

### record_inbound(product_id, quantity, reference='', notes='', created_by=None)
Record inbound stock (receiving goods).

## Concurrency Protection

- All operations use `@transaction.atomic`
- `select_for_update()` ensures row-level locking
- Prevents race conditions and overselling
- Test included: `test_concurrent_reservations_last_stock`

## API Endpoints

All endpoints require authentication.

### Inventory Items
```
GET /api/v1/inventory/items/
POST /api/v1/inventory/items/check_available/
POST /api/v1/inventory/items/reserve/
POST /api/v1/inventory/items/release/
POST /api/v1/inventory/items/commit_outbound/
```

### Stock Movements
```
GET /api/v1/inventory/movements/
GET /api/v1/inventory/movements/?inventory_item_id=1
```

## Admin

Access admin at `/admin/` to manage:
- **Inventory Items**: View stock levels, reorder points, movements
- **Stock Movements**: View all stock movement history

## Setup

1. Create migrations:
```bash
python manage.py makemigrations inventory
python manage.py migrate
```

2. Run tests:
```bash
pytest tests/test_inventory.py -v
pytest tests/test_inventory.py::TestConcurrency -v
```

## Usage Example

```python
from apps.inventory.services import InventoryService

# Check availability
items = [{'product_id': 1, 'quantity': 50}]
availability = InventoryService.check_available(items)

if availability['available']:
    # Reserve stock
    result = InventoryService.reserve(
        items,
        reference='ORDER-001'
    )
    
    if result['success']:
        # Process order...
        
        # Commit outbound when order fulfilled
        InventoryService.commit_outbound(
            items,
            reference='ORDER-001'
        )
    else:
        # Release if order fails
        InventoryService.release(
            items,
            reference='ORDER-001'
        )
```
