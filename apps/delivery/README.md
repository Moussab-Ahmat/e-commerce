# Delivery App

Delivery zone and fee management system.

## Features

- **DeliveryZone**: Geographic delivery zones (Admin-only management)
- **DeliveryFeeRule**: Flexible fee calculation (Fixed, Percentage, Tiered)
- Admin CRUD for all models
- Read-only API endpoints for zones
- Fee calculation service function
- GPS coordinates-based delivery addresses

## Models

### DeliveryZone
- Geographic delivery zones
- Code and name for identification
- Active/inactive status
- Managed exclusively via Django Admin

### DeliveryFeeRule
- Three rule types:
  - **FIXED**: Fixed fee regardless of cart total
  - **PERCENTAGE**: Percentage of cart total (with min/max constraints)
  - **TIERED**: Different fees based on cart total ranges
- Priority system (lower number = higher priority)
- Active/inactive status

## API Endpoints

### Zones (Read-Only)
```
GET /api/v1/delivery/zones/
GET /api/v1/delivery/zones/{id}/
POST /api/v1/delivery/zones/{id}/calculate_fee/
```

**Calculate Fee Request:**
```json
{
  "zone_id": 1,
  "cart_total_xaf": 50000
}
```

**Response:**
```json
{
  "zone_id": 1,
  "cart_total_xaf": 50000,
  "delivery_fee_xaf": 2000
}
```

## Fee Calculation

The `calculate_delivery_fee(zone_id, cart_total_xaf)` function:
1. Finds the zone
2. Gets active fee rules ordered by priority
3. Uses the first (highest priority) rule
4. Calculates fee based on rule type

### Rule Types

**FIXED:**
- Returns `fixed_fee` regardless of cart total

**PERCENTAGE:**
- Calculates: `(cart_total * percentage) / 100`
- Applies min_fee and max_fee constraints

**TIERED:**
- Finds matching tier based on cart total
- Returns fee for that tier
- Format: `[{"min": 0, "max": 10000, "fee": 2000}, ...]`

## Admin

Access admin at `/admin/` to manage:
- **Delivery Zones**: Create zones with inline fee rules
- **Delivery Fee Rules**: Configure fee calculation rules

**Note**: Delivery zones are admin-only. Customers can only view available zones via the API.

## Setup

1. Create migrations:
```bash
python manage.py makemigrations delivery
python manage.py migrate
```

2. Run tests:
```bash
pytest tests/test_delivery.py -v
```

## Examples

### Fixed Fee Rule
```python
rule = DeliveryFeeRule.objects.create(
    zone=zone,
    rule_type=DeliveryFeeRule.RuleType.FIXED,
    fixed_fee=2000
)
# Always returns 2000 XAF
```

### Percentage Fee Rule
```python
rule = DeliveryFeeRule.objects.create(
    zone=zone,
    rule_type=DeliveryFeeRule.RuleType.PERCENTAGE,
    percentage=Decimal('5.00'),  # 5%
    min_fee=1000,
    max_fee=5000
)
# 5% of cart total, min 1000, max 5000
```

### Tiered Fee Rule
```python
tier_rules = [
    {'min': 0, 'max': 10000, 'fee': 2000},
    {'min': 10000, 'max': 50000, 'fee': 1500},
    {'min': 50000, 'max': float('inf'), 'fee': 1000},
]
rule = DeliveryFeeRule.objects.create(
    zone=zone,
    rule_type=DeliveryFeeRule.RuleType.TIERED,
    tier_rules=tier_rules
)
# Different fees based on cart total ranges
```

