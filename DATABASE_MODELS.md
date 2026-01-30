# Database Models Outline

## Accounts App

### User
- **Primary Key**: `id`
- **Username Field**: `phone_number` (unique)
- **Fields**:
  - `phone_number` (CharField, unique, validated)
  - `email` (EmailField, optional)
  - `first_name`, `last_name` (CharField)
  - `is_active`, `is_staff`, `is_verified` (BooleanField)
  - Address fields: `address_line1`, `address_line2`, `city`, `region`, `postal_code`
  - `date_joined`, `last_login` (DateTimeField)
- **Indexes**: `phone_number`, `(is_active, is_verified)`

### OTPVerification
- **Fields**:
  - `phone_number` (CharField)
  - `otp_code` (CharField, 6 digits)
  - `is_verified` (BooleanField)
  - `created_at`, `expires_at` (DateTimeField)
- **Indexes**: `(phone_number, is_verified)`

---

## Products App

### Category
- **Fields**:
  - `name` (CharField, unique)
  - `slug` (SlugField, unique)
  - `description` (TextField)
  - `parent` (ForeignKey to self, nullable, for hierarchy)
  - `image` (ImageField)
  - `is_active` (BooleanField)
  - `created_at`, `updated_at` (DateTimeField)
- **Indexes**: `(slug, is_active)`

### Product
- **Fields**:
  - `name`, `slug` (CharField/SlugField)
  - `description` (TextField)
  - `category` (ForeignKey to Category)
  - **Pricing**: `price` (BigIntegerField, XAF integer)
  - **Stock Management**:
    - `stock_quantity` (IntegerField)
    - `reserved_quantity` (IntegerField)
    - `available_quantity` (property: stock - reserved)
  - `sku` (CharField, unique)
  - `barcode` (CharField, nullable)
  - `weight` (DecimalField, kg)
  - `dimensions` (CharField, LxWxH format)
  - **Images**: `image1`, `image2`, `image3` (ImageField, max 3 for low bandwidth)
  - `is_active`, `is_featured` (BooleanField)
  - `created_at`, `updated_at` (DateTimeField)
- **Methods**:
  - `reserve_stock(quantity)` - Reserve stock with locking
  - `release_stock(quantity)` - Release reserved stock
  - `commit_stock(quantity)` - Commit reserved stock (order confirmed)
- **Indexes**: `(slug, is_active)`, `(category, is_active)`, `sku`, `(is_featured, is_active)`

### ProductImage
- **Fields**:
  - `product` (ForeignKey to Product)
  - `image` (ImageField)
  - `alt_text` (CharField)
  - `order` (IntegerField)

---

## Orders App

### Order
- **Fields**:
  - `order_number` (CharField, unique, format: ORD-YYYYMMDD-XXXXXX)
  - `user` (ForeignKey to User)
  - **Status Machine**: `status` (CharField, choices: OrderStatus)
  - **Pricing** (all BigIntegerField, XAF integer):
    - `subtotal`
    - `delivery_fee`
    - `total`
  - **Delivery Address**:
    - `delivery_address_line1`, `delivery_address_line2`
    - `delivery_city`, `delivery_region`, `delivery_postal_code`
    - `delivery_phone`
  - **Payment**:
    - `payment_method` (CharField, default: 'COD')
    - `payment_status` (CharField, choices: PENDING, PAID, FAILED)
  - `customer_notes`, `admin_notes` (TextField)
  - **Timestamps**:
    - `created_at`, `updated_at`
    - `confirmed_at`, `delivered_at`, `cancelled_at` (nullable)
- **Methods**:
  - `can_transition_to(new_status)` - Validate status transition
  - `transition_status(new_status, user)` - Change status with validation
  - `calculate_total()` - Recalculate order total
- **Indexes**: `order_number`, `(user, status)`, `(status, created_at)`

### OrderItem
- **Fields**:
  - `order` (ForeignKey to Order)
  - `product` (ForeignKey to Product)
  - `quantity` (IntegerField)
  - `unit_price` (BigIntegerField, XAF integer, snapshot at order time)
  - `total_price` (BigIntegerField, XAF integer, calculated)
- **Unique Together**: `(order, product)`

### OrderStatusHistory
- **Fields**:
  - `order` (ForeignKey to Order)
  - `old_status`, `new_status` (CharField)
  - `changed_by` (ForeignKey to User, nullable)
  - `notes` (TextField)
  - `created_at` (DateTimeField)

---

## Deliveries App

### DeliveryAgent
- **Fields**:
  - `user` (OneToOneField to User)
  - `agent_id` (CharField, unique)
  - `vehicle_type` (CharField, choices: MOTORCYCLE, CAR, TRUCK, BICYCLE)
  - `vehicle_number` (CharField)
  - `phone_number` (CharField)
  - `is_active` (BooleanField)
  - `current_latitude`, `current_longitude` (DecimalField, for GPS)
  - `created_at`, `updated_at` (DateTimeField)

### Delivery
- **Fields**:
  - `order` (OneToOneField to Order)
  - `delivery_number` (CharField, unique)
  - **Status Machine**: `status` (CharField, choices: DeliveryStatus)
  - `agent` (ForeignKey to DeliveryAgent, nullable)
  - `estimated_delivery_date`, `actual_delivery_date` (DateTimeField)
  - **Delivery Address** (denormalized from order):
    - `delivery_address_line1`, `delivery_address_line2`
    - `delivery_city`, `delivery_region`, `delivery_postal_code`
    - `delivery_phone`
  - `delivery_notes`, `failure_reason` (TextField)
  - **Timestamps**:
    - `created_at`, `updated_at`
    - `assigned_at`, `completed_at` (nullable)
- **Methods**:
  - `can_transition_to(new_status)` - Validate status transition
  - `transition_status(new_status, user)` - Change status with validation
- **Indexes**: `delivery_number`, `(status, created_at)`, `(agent, status)`

### DeliveryStatusHistory
- **Fields**:
  - `delivery` (ForeignKey to Delivery)
  - `old_status`, `new_status` (CharField)
  - `changed_by` (ForeignKey to User, nullable)
  - `notes` (TextField)
  - `created_at` (DateTimeField)

---

## Payments App

### Payment
- **Fields**:
  - `order` (OneToOneField to Order)
  - `payment_number` (CharField, unique)
  - `amount` (BigIntegerField, XAF integer)
  - `payment_method` (CharField, choices: COD)
  - `status` (CharField, choices: PENDING, COLLECTED, FAILED, REFUNDED)
  - `collected_by` (ForeignKey to DeliveryAgent, nullable)
  - `collected_at` (DateTimeField, nullable)
  - `notes` (TextField)
  - `created_at`, `updated_at` (DateTimeField)
- **Indexes**: `payment_number`, `(status, created_at)`, `order`

### PaymentHistory
- **Fields**:
  - `payment` (ForeignKey to Payment)
  - `old_status`, `new_status` (CharField)
  - `changed_by` (ForeignKey to User, nullable)
  - `notes` (TextField)
  - `created_at` (DateTimeField)

---

## Notifications App

### Notification
- **Fields**:
  - `user` (ForeignKey to User)
  - `notification_type` (CharField, choices: SMS, EMAIL, PUSH)
  - `recipient` (CharField, phone or email)
  - `subject` (CharField)
  - `message` (TextField)
  - `status` (CharField, choices: PENDING, SENT, FAILED, DELIVERED)
  - **Generic Foreign Key**:
    - `content_type` (ForeignKey to ContentType)
    - `object_id` (PositiveIntegerField)
    - `related_object` (GenericForeignKey)
  - `sent_at`, `delivered_at` (DateTimeField, nullable)
  - `error_message` (TextField)
  - `retry_count`, `max_retries` (IntegerField)
  - `created_at`, `updated_at` (DateTimeField)
- **Indexes**: `(user, status)`, `(notification_type, status)`, `created_at`

---

## Audit App

### AuditLog
- **Fields**:
  - `user` (ForeignKey to User, nullable)
  - `action` (CharField, e.g., 'CREATE_ORDER', 'UPDATE_STOCK')
  - `resource_type` (CharField, e.g., 'Order', 'Product')
  - **Generic Foreign Key**:
    - `content_type` (ForeignKey to ContentType, nullable)
    - `object_id` (PositiveIntegerField, nullable)
    - `related_object` (GenericForeignKey)
  - `old_values`, `new_values` (JSONField)
  - `ip_address` (GenericIPAddressField)
  - `user_agent` (CharField)
  - `request_path` (CharField)
  - `request_method` (CharField)
  - `notes` (TextField)
  - `created_at` (DateTimeField)
- **Indexes**: `(user, created_at)`, `(action, created_at)`, `(resource_type, created_at)`

---

## Key Design Decisions

1. **Money Storage**: All money fields stored as `BigIntegerField` (integer XAF)
2. **Stock Integrity**: Pessimistic locking with `select_for_update()` and atomic transactions
3. **Status Machines**: Enforced at model level with validation methods
4. **Low Bandwidth**: Limited product images (3 max), lightweight list serializers
5. **Audit Trail**: Comprehensive logging of all sensitive operations
6. **Denormalization**: Delivery address stored in both Order and Delivery for performance
7. **Generic Foreign Keys**: Used in Notification and AuditLog for flexibility

