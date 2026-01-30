# API Contracts

## Base URL
```
/api/v1/
```

## Authentication

All endpoints (except registration, login, and OTP) require JWT authentication:
```
Authorization: Bearer <access_token>
```

---

## Accounts API

### Register User
```
POST /api/v1/auth/register/
```
**Request Body:**
```json
{
  "phone_number": "+235123456789",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "password": "securepassword",
  "password_confirm": "securepassword",
  "address_line1": "123 Main St",
  "city": "N'Djamena",
  "region": "Chari-Baguirmi"
}
```

**Response:** `201 Created`
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "phone_number": "+235123456789",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_verified": false
  }
}
```

### Login
```
POST /api/v1/auth/login/
```
**Request Body:**
```json
{
  "phone_number": "+235123456789",
  "password": "securepassword"
}
```

**Response:** `200 OK`
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": { ... }
}
```

### Request OTP
```
POST /api/v1/auth/otp/request/
```
**Request Body:**
```json
{
  "phone_number": "+235123456789"
}
```

**Response:** `200 OK`
```json
{
  "message": "OTP sent successfully",
  "expires_in": 600
}
```

### Verify OTP
```
POST /api/v1/auth/otp/verify/
```
**Request Body:**
```json
{
  "phone_number": "+235123456789",
  "otp_code": "123456"
}
```

### Get Current User
```
GET /api/v1/auth/users/me/
```

### Update Current User
```
PUT /api/v1/auth/users/me/
PATCH /api/v1/auth/users/me/
```

---

## Products API

### List Products
```
GET /api/v1/products/products/?page=1&page_size=20&category=1&is_featured=true
```
**Query Parameters:**
- `page`: Page number
- `page_size`: Items per page (max 100)
- `category`: Filter by category ID
- `is_featured`: Filter featured products
- `search`: Search in name, description, SKU

**Response:** `200 OK`
```json
{
  "count": 100,
  "next": "http://api.example.com/api/v1/products/products/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Product Name",
      "slug": "product-name",
      "category_name": "Electronics",
      "price": 50000,
      "available_quantity": 10,
      "image1": "http://...",
      "is_featured": true
    }
  ]
}
```

### Get Product Detail
```
GET /api/v1/products/products/{id}/
```

### Check Product Availability
```
GET /api/v1/products/products/{id}/availability/
```

---

## Orders API

### Create Order
```
POST /api/v1/orders/orders/
```
**Request Body:**
```json
{
  "delivery_address_line1": "123 Main St",
  "delivery_city": "N'Djamena",
  "delivery_region": "Chari-Baguirmi",
  "delivery_phone": "+235123456789",
  "delivery_fee": 2000,
  "customer_notes": "Please deliver in the morning",
  "items": [
    {
      "product_id": 1,
      "quantity": 2
    },
    {
      "product_id": 3,
      "quantity": 1
    }
  ]
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "order_number": "ORD-20240101-000001",
  "status": "PENDING",
  "subtotal": 100000,
  "delivery_fee": 2000,
  "total": 102000,
  "items": [ ... ],
  "created_at": "2024-01-01T10:00:00Z"
}
```

### List Orders
```
GET /api/v1/orders/orders/
```

### Get Order Detail
```
GET /api/v1/orders/orders/{id}/
```

### Cancel Order
```
POST /api/v1/orders/orders/{id}/cancel/
```

### Confirm Order (Admin)
```
POST /api/v1/orders/orders/{id}/confirm/
```

---

## Deliveries API

### List Deliveries
```
GET /api/v1/deliveries/deliveries/
```

### Get Delivery Detail
```
GET /api/v1/deliveries/deliveries/{id}/
```

### Assign Delivery (Admin)
```
POST /api/v1/deliveries/deliveries/{id}/assign/
```
**Request Body:**
```json
{
  "agent_id": 1
}
```

### Update Delivery Status
```
POST /api/v1/deliveries/deliveries/{id}/update_status/
```
**Request Body:**
```json
{
  "status": "IN_TRANSIT"
}
```

**Valid Statuses:**
- `PENDING`
- `ASSIGNED`
- `IN_TRANSIT`
- `DELIVERED`
- `COMPLETED`
- `FAILED`
- `RETURNED`

---

## Payments API

### List Payments
```
GET /api/v1/payments/payments/
```

### Get Payment Detail
```
GET /api/v1/payments/payments/{id}/
```

### Collect Payment (Agent/Admin)
```
POST /api/v1/payments/payments/{id}/collect/
```
**Request Body:**
```json
{
  "notes": "Payment collected successfully"
}
```

---

## Notifications API

### List Notifications
```
GET /api/v1/notifications/notifications/
```

### Get Notification Detail
```
GET /api/v1/notifications/notifications/{id}/
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Error message",
  "field_name": ["Field-specific error"]
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "error": "Permission denied"
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error"
}
```

---

## Status Codes

### Order Status Flow
```
PENDING → CONFIRMED → PROCESSING → READY_FOR_DELIVERY → 
OUT_FOR_DELIVERY → DELIVERED → COMPLETED
```
Can also transition to: `CANCELLED`, `REFUNDED`

### Delivery Status Flow
```
PENDING → ASSIGNED → IN_TRANSIT → DELIVERED → COMPLETED
```
Can also transition to: `FAILED`, `RETURNED`

---

## Low Bandwidth Optimizations

1. **Pagination**: All list endpoints are paginated (default 20 items)
2. **Field Selection**: Use query parameters to select specific fields
3. **Lightweight Serializers**: List endpoints use minimal data
4. **Image Optimization**: Limit product images to 3 main images
5. **Compression**: Enable gzip compression in production

---

## Rate Limiting

- **Anonymous**: 100 requests/hour
- **Authenticated**: 1000 requests/hour
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

