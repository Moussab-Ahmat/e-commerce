# E-Commerce MVP for Chad

Django 5 + DRF + PostgreSQL + Redis + Celery backend for Flutter Android client.

## Project Structure

```
ecommerce/
├── config/                 # Django project settings
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/          # User management & authentication
│   ├── products/          # Products, categories, inventory
│   ├── orders/            # Orders, order items
│   ├── deliveries/        # Delivery management
│   ├── payments/          # COD transactions
│   ├── notifications/     # SMS/Email notifications
│   └── audit/             # Audit logging
├── core/                  # Shared utilities
│   ├── __init__.py
│   ├── exceptions.py
│   ├── permissions.py
│   ├── pagination.py
│   └── validators.py
├── manage.py
├── requirements.txt
└── README.md
```

## Key Features

- **Low Bandwidth Optimized**: Pagination, field selection, compression
- **COD Only**: Cash on Delivery payment method
- **Stock Integrity**: Pessimistic locking, atomic operations
- **Status Machines**: Order and Delivery state management
- **Security**: JWT, OTP, throttling, audit logging

## Money Handling

All money fields stored as **integer XAF** (Central African CFA Franc).
- 1 XAF = 1 integer unit
- Example: 5000 XAF stored as 5000

## Status Machines

### Order Status
- `PENDING` → `CONFIRMED` → `PROCESSING` → `READY_FOR_DELIVERY` → `OUT_FOR_DELIVERY` → `DELIVERED` → `COMPLETED`
- Can transition to: `CANCELLED`, `REFUNDED`

### Delivery Status
- `PENDING` → `ASSIGNED` → `IN_TRANSIT` → `DELIVERED` → `COMPLETED`
- Can transition to: `FAILED`, `RETURNED`

## Security Checklist

- [x] JWT authentication (access + refresh tokens)
- [x] OTP verification for phone numbers
- [x] Rate limiting/throttling
- [x] Audit logging for sensitive operations
- [x] CORS configuration
- [x] Input validation & sanitization
- [x] SQL injection prevention (ORM)
- [x] XSS prevention
- [x] CSRF protection
- [x] Password hashing (bcrypt/argon2)
- [x] Secure headers (HSTS, CSP)
- [x] Environment variables for secrets

## Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. Setup PostgreSQL database
3. Setup Redis for caching and Celery
4. Run migrations: `python manage.py migrate`
5. Create superuser: `python manage.py createsuperuser`
6. Run server: `python manage.py runserver`

