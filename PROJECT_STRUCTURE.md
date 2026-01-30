# Project Structure

## Directory Layout

```
ecommerce/
├── config/                          # Django project configuration
│   ├── __init__.py                 # Celery app initialization
│   ├── celery.py                   # Celery configuration
│   ├── settings/                   # Environment-specific settings
│   │   ├── __init__.py
│   │   ├── base.py                 # Base settings
│   │   ├── development.py          # Development settings
│   │   └── production.py           # Production settings
│   ├── urls.py                     # Main URL configuration
│   └── wsgi.py                     # WSGI configuration
│
├── apps/                            # Django applications
│   ├── accounts/                   # User management & authentication
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py               # User, OTPVerification
│   │   ├── serializers.py          # User, Login, Registration serializers
│   │   ├── views.py                # Registration, Login, OTP views
│   │   ├── urls.py                 # Account URLs
│   │   └── admin.py                # Admin configuration
│   │
│   ├── products/                   # Products, categories, inventory
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py               # Category, Product, ProductImage
│   │   ├── serializers.py          # Product, Category serializers
│   │   ├── views.py                # Product, Category viewsets
│   │   ├── urls.py                 # Product URLs
│   │   └── admin.py                # Admin configuration
│   │
│   ├── orders/                     # Orders and order items
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py               # Order, OrderItem, OrderStatusHistory
│   │   ├── serializers.py          # Order serializers
│   │   ├── views.py                # Order viewset with status transitions
│   │   ├── urls.py                 # Order URLs
│   │   └── admin.py                # Admin configuration
│   │
│   ├── deliveries/                 # Delivery management
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py               # DeliveryAgent, Delivery, DeliveryStatusHistory
│   │   ├── serializers.py          # Delivery serializers
│   │   ├── views.py                # Delivery viewset with status transitions
│   │   ├── urls.py                 # Delivery URLs
│   │   └── admin.py                # Admin configuration
│   │
│   ├── payments/                   # COD payment handling
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py               # Payment, PaymentHistory
│   │   ├── serializers.py          # Payment serializers
│   │   ├── views.py                # Payment viewset
│   │   ├── urls.py                 # Payment URLs
│   │   └── admin.py                # Admin configuration
│   │
│   ├── notifications/              # SMS/Email notifications
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py               # Notification
│   │   ├── serializers.py          # Notification serializer
│   │   ├── views.py                # Notification viewset
│   │   ├── urls.py                 # Notification URLs
│   │   ├── tasks.py                # Celery tasks for sending notifications
│   │   └── admin.py                # Admin configuration
│   │
│   └── audit/                      # Audit logging
│       ├── __init__.py
│       ├── apps.py
│       ├── models.py               # AuditLog
│       ├── middleware.py           # Audit logging middleware
│       ├── utils.py                # Audit logging utilities
│       └── admin.py                # Admin configuration
│
├── core/                           # Shared utilities
│   ├── __init__.py
│   ├── exceptions.py               # Custom exceptions
│   ├── pagination.py               # Custom pagination classes
│   ├── permissions.py              # Custom permissions
│   └── validators.py               # Custom validators
│
├── manage.py                        # Django management script
├── requirements.txt                 # Python dependencies
├── .env.example                    # Environment variables template
├── .gitignore                      # Git ignore rules
│
├── README.md                        # Project overview
├── SECURITY.md                     # Security checklist
├── API_CONTRACTS.md                # API documentation
├── DATABASE_MODELS.md              # Database models outline
└── PROJECT_STRUCTURE.md            # This file
```

## Naming Conventions

### Files
- **Models**: `models.py`
- **Serializers**: `serializers.py`
- **Views**: `views.py` or `viewsets.py`
- **URLs**: `urls.py`
- **Admin**: `admin.py`
- **Tasks**: `tasks.py` (Celery tasks)
- **Utils**: `utils.py` or `helpers.py`

### Models
- **Singular nouns**: `User`, `Product`, `Order`, `Category`
- **CamelCase**: `OrderItem`, `DeliveryAgent`
- **Table names**: Plural, lowercase with underscores: `orders`, `order_items`

### API Endpoints
- **RESTful**: `/api/v1/products/`, `/api/v1/orders/`
- **Actions**: `/api/v1/orders/{id}/cancel/`, `/api/v1/deliveries/{id}/assign/`
- **Nested resources**: Use query parameters or separate endpoints

### Variables
- **Python**: `snake_case` for variables and functions
- **Constants**: `UPPER_SNAKE_CASE`
- **Models**: `PascalCase`

## App Responsibilities

### accounts
- User registration and authentication
- Phone number verification (OTP)
- User profile management
- JWT token management

### products
- Product catalog management
- Category hierarchy
- Stock management with integrity
- Product search and filtering

### orders
- Order creation and management
- Order status machine
- Order items management
- Stock reservation on order creation

### deliveries
- Delivery agent management
- Delivery assignment
- Delivery status machine
- Delivery tracking

### payments
- COD payment processing
- Payment status tracking
- Payment collection by agents
- Payment history

### notifications
- SMS notifications
- Email notifications
- Notification status tracking
- Retry logic for failed notifications

### audit
- Audit logging middleware
- Sensitive operation tracking
- User action history
- Request/response logging

## Key Design Patterns

1. **Status Machines**: Implemented at model level with validation
2. **Stock Integrity**: Pessimistic locking with `select_for_update()`
3. **Audit Trail**: Comprehensive logging via middleware and utilities
4. **Generic Foreign Keys**: Used for flexible relationships (notifications, audit)
5. **Denormalization**: Delivery address stored in both Order and Delivery
6. **API Versioning**: `/api/v1/` prefix for future compatibility

## Environment Configuration

### Development
- `DEBUG = True`
- Console logging
- CORS allows all origins
- Debug toolbar enabled

### Production
- `DEBUG = False`
- File and console logging
- CORS restricted to whitelist
- SSL/TLS enforced
- Security headers enabled

## Database Strategy

- **PostgreSQL**: Primary database
- **Redis**: Caching and Celery broker
- **Migrations**: Version controlled
- **Indexes**: Optimized for common queries
- **Transactions**: Used for critical operations (stock, orders)

## API Design Principles

1. **RESTful**: Follow REST conventions
2. **Versioned**: `/api/v1/` prefix
3. **Paginated**: All list endpoints
4. **Filtered**: Query parameters for filtering
5. **Low Bandwidth**: Lightweight serializers for lists
6. **Consistent**: Uniform error responses
7. **Documented**: Swagger/OpenAPI documentation

