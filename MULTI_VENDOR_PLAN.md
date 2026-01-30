# 🏪 Multi-Vendor Marketplace Transformation Plan

## 📊 Current State Analysis

### ✅ What You Have
- **User Model** with roles: `CUSTOMER`, `ADMIN`, `WAREHOUSE`, `COURIER`
- **Product Model** with categories, pricing, stock
- **Order/OrderItem** system with status machine
- **CollaborationRequest** model (perfect for vendor onboarding!)
- **Flutter App** with home, products, cart, checkout, orders

### 🎯 What We'll Build
A complete multi-vendor marketplace where:
- Vendors manage their own shop, products, and orders
- Customers shop from multiple vendors in a single order
- Admin controls all vendors and approves registrations
- Orders are automatically split by vendor

---

## 🗄️ Phase 1: Database Architecture

### 1.1 Add VENDOR Role to User Model

**File**: `apps/accounts/models.py`

```python
class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        VENDOR = 'VENDOR', 'Vendor'  # ← ADD THIS
        ADMIN = 'ADMIN', 'Admin'
        WAREHOUSE = 'WAREHOUSE', 'Warehouse'
        COURIER = 'COURIER', 'Courier'

    # ... rest of model
```

**Migration**:
```bash
python manage.py makemigrations accounts
python manage.py migrate accounts
```

---

### 1.2 Create Shop Model

**NEW FILE**: `apps/vendors/__init__.py`
**NEW FILE**: `apps/vendors/models.py`

```python
"""
Vendor and Shop models for multi-vendor marketplace.
"""
from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator


class Shop(models.Model):
    """
    Vendor's shop/store.
    Each vendor has ONE shop.
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Approval'
        ACTIVE = 'ACTIVE', 'Active'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        INACTIVE = 'INACTIVE', 'Inactive'

    # Ownership
    vendor = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='shop',
        limit_choices_to={'role': 'VENDOR'},
        help_text='Vendor who owns this shop'
    )

    # Shop Details
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='shops/logos/', null=True, blank=True)
    banner = models.ImageField(upload_to='shops/banners/', null=True, blank=True)

    # Contact
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    # Business Info
    business_license = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)

    # Address
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)

    # Status & Performance
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    is_verified = models.BooleanField(default=False, db_index=True)
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    total_sales = models.BigIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_shops',
        limit_choices_to={'role': 'ADMIN'}
    )

    class Meta:
        db_table = 'shops'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug', 'status']),
            models.Index(fields=['status', 'is_verified']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate slug if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def activate(self, admin_user):
        """Activate shop (called by admin)."""
        from django.utils import timezone
        self.status = self.Status.ACTIVE
        self.is_verified = True
        self.approved_at = timezone.now()
        self.approved_by = admin_user
        self.save(update_fields=['status', 'is_verified', 'approved_at', 'approved_by'])

    def suspend(self):
        """Suspend shop for policy violations."""
        self.status = self.Status.SUSPENDED
        self.save(update_fields=['status'])
```

**Add to Django settings**:
```python
# config/settings/base.py
INSTALLED_APPS = [
    # ... existing apps
    'apps.vendors',  # ← ADD THIS
]
```

**Create migrations**:
```bash
python manage.py makemigrations vendors
python manage.py migrate vendors
```

---

### 1.3 Update Product Model

**File**: `apps/catalog/models.py`

```python
class Product(models.Model):
    """Product model - now linked to Shop."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products'
    )

    # ← ADD THIS: Link to Shop
    shop = models.ForeignKey(
        'vendors.Shop',
        on_delete=models.CASCADE,
        related_name='products',
        help_text='Shop selling this product'
    )

    # ... rest of fields (price, stock, etc.)
```

**Migration**:
```bash
python manage.py makemigrations catalog
# This will ask what to do with existing products
# Choose option to set a default shop (create one first!)
python manage.py migrate catalog
```

---

### 1.4 Update OrderItem Model

**File**: `apps/orders/models.py`

```python
class OrderItem(models.Model):
    """Order item model - now tracks vendor."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='order_items'
    )

    # ← ADD THIS: Track which shop this item is from
    shop = models.ForeignKey(
        'vendors.Shop',
        on_delete=models.PROTECT,
        related_name='order_items',
        help_text='Shop that fulfills this item'
    )

    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.BigIntegerField(
        validators=[MinValueValidator(0), validate_xaf_amount],
        help_text='Price per unit at time of order (XAF)'
    )
    total_price = models.BigIntegerField(
        validators=[MinValueValidator(0), validate_xaf_amount],
        help_text='Total price for this item (XAF)'
    )

    # ← ADD THIS: Item-level status for vendor tracking
    item_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('CONFIRMED', 'Confirmed'),
            ('PREPARING', 'Preparing'),
            ('READY', 'Ready'),
            ('DELIVERED', 'Delivered'),
        ],
        default='PENDING',
        db_index=True
    )

    class Meta:
        db_table = 'order_items'
        unique_together = [['order', 'product']]
        indexes = [
            models.Index(fields=['shop', 'item_status']),  # ← ADD THIS
        ]

    def save(self, *args, **kwargs):
        """Calculate total price and set shop from product."""
        self.total_price = self.unit_price * self.quantity

        # Auto-set shop from product
        if not self.shop_id and self.product:
            self.shop = self.product.shop

        super().save(*args, **kwargs)
```

**Migration**:
```bash
python manage.py makemigrations orders
python manage.py migrate orders
```

---

## 🔐 Phase 2: Permissions & API

### 2.1 Create Custom Permissions

**NEW FILE**: `apps/vendors/permissions.py`

```python
from rest_framework import permissions


class IsVendor(permissions.BasePermission):
    """Allow only users with VENDOR role."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'VENDOR'
        )


class IsVendorOwner(permissions.BasePermission):
    """Allow only the vendor who owns the shop."""

    def has_object_permission(self, request, view, obj):
        # obj is a Shop, Product, or OrderItem
        if hasattr(obj, 'shop'):
            # Product or OrderItem
            return obj.shop.vendor == request.user
        elif hasattr(obj, 'vendor'):
            # Shop itself
            return obj.vendor == request.user
        return False


class IsAdminOrReadOnly(permissions.BasePermission):
    """Allow read-only for all, write only for admin."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff
```

---

### 2.2 Create Vendor Serializers

**NEW FILE**: `apps/vendors/serializers.py`

```python
from rest_framework import serializers
from .models import Shop
from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem


class ShopSerializer(serializers.ModelSerializer):
    """Shop serializer for vendor dashboard."""

    vendor_name = serializers.CharField(source='vendor.get_full_name', read_only=True)
    total_products = serializers.SerializerMethodField()
    pending_orders = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = [
            'id', 'name', 'slug', 'description', 'logo', 'banner',
            'email', 'phone', 'status', 'is_verified',
            'average_rating', 'total_sales',
            'vendor_name', 'total_products', 'pending_orders',
            'created_at',
        ]
        read_only_fields = ['slug', 'status', 'is_verified', 'total_sales']

    def get_total_products(self, obj):
        return obj.products.filter(is_active=True).count()

    def get_pending_orders(self, obj):
        return obj.order_items.filter(item_status='PENDING').count()


class VendorProductSerializer(serializers.ModelSerializer):
    """Product serializer for vendors (includes shop auto-assignment)."""

    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'category', 'category_name',
            'price', 'stock_quantity', 'sku', 'is_active', 'is_featured',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['slug', 'shop']  # shop is auto-set

    def create(self, validated_data):
        """Auto-assign shop from request user."""
        request = self.context.get('request')
        if request and hasattr(request.user, 'shop'):
            validated_data['shop'] = request.user.shop
        return super().create(validated_data)


class VendorOrderItemSerializer(serializers.ModelSerializer):
    """OrderItem serializer for vendors (their items only)."""

    product_name = serializers.CharField(source='product.name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    customer_name = serializers.CharField(source='order.user.get_full_name', read_only=True)
    delivery_address = serializers.CharField(source='order.delivery_address_line1', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'order', 'order_number', 'product', 'product_name',
            'quantity', 'unit_price', 'total_price', 'item_status',
            'customer_name', 'delivery_address',
        ]
        read_only_fields = ['order', 'product', 'quantity', 'unit_price', 'total_price']
```

---

### 2.3 Create Vendor ViewSets

**NEW FILE**: `apps/vendors/views.py`

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Shop
from .serializers import (
    ShopSerializer,
    VendorProductSerializer,
    VendorOrderItemSerializer,
)
from .permissions import IsVendor, IsVendorOwner
from apps.catalog.models import Product
from apps.orders.models import OrderItem


class VendorDashboardViewSet(viewsets.ReadOnlyModelViewSet):
    """Vendor dashboard - shop info and stats."""

    serializer_class = ShopSerializer
    permission_classes = [IsAuthenticated, IsVendor]

    def get_queryset(self):
        """Return only the current vendor's shop."""
        return Shop.objects.filter(vendor=self.request.user)

    @action(detail=False, methods=['GET'])
    def stats(self, request):
        """Get vendor statistics."""
        try:
            shop = request.user.shop
        except Shop.DoesNotExist:
            return Response(
                {'error': 'No shop found for this vendor'},
                status=status.HTTP_404_NOT_FOUND
            )

        total_products = shop.products.filter(is_active=True).count()
        pending_orders = shop.order_items.filter(item_status='PENDING').count()
        preparing_orders = shop.order_items.filter(item_status='PREPARING').count()

        return Response({
            'total_products': total_products,
            'pending_orders': pending_orders,
            'preparing_orders': preparing_orders,
            'total_sales': shop.total_sales,
            'average_rating': float(shop.average_rating),
        })


class VendorProductViewSet(viewsets.ModelViewSet):
    """Vendor product management."""

    serializer_class = VendorProductSerializer
    permission_classes = [IsAuthenticated, IsVendor, IsVendorOwner]

    def get_queryset(self):
        """Return only products from vendor's shop."""
        try:
            return Product.objects.filter(shop=self.request.user.shop)
        except Shop.DoesNotExist:
            return Product.objects.none()


class VendorOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Vendor order management (view and update status)."""

    serializer_class = VendorOrderItemSerializer
    permission_classes = [IsAuthenticated, IsVendor]

    def get_queryset(self):
        """Return only order items for vendor's shop."""
        try:
            return OrderItem.objects.filter(
                shop=self.request.user.shop
            ).select_related('order', 'product', 'order__user')
        except Shop.DoesNotExist:
            return OrderItem.objects.none()

    @action(detail=True, methods=['POST'])
    def update_status(self, request, pk=None):
        """Update order item status."""
        item = self.get_object()
        new_status = request.data.get('status')

        if new_status not in ['CONFIRMED', 'PREPARING', 'READY', 'DELIVERED']:
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        item.item_status = new_status
        item.save(update_fields=['item_status'])

        serializer = self.get_serializer(item)
        return Response(serializer.data)
```

---

### 2.4 Create Vendor URLs

**NEW FILE**: `apps/vendors/urls.py`

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'dashboard', views.VendorDashboardViewSet, basename='vendor-dashboard')
router.register(r'products', views.VendorProductViewSet, basename='vendor-products')
router.register(r'orders', views.VendorOrderViewSet, basename='vendor-orders')

urlpatterns = [
    path('', include(router.urls)),
]
```

**Update main URLs**:
```python
# config/urls.py
urlpatterns = [
    # ... existing URLs
    path('api/v1/vendor/', include('apps.vendors.urls')),  # ← ADD THIS
]
```

---

## 📱 Phase 3: Flutter - Navigation & Menu

### 3.1 Update App Router

**File**: `lib/core/router/app_router.dart`

```dart
// Add vendor routes
GoRoute(
  path: '/vendor',
  redirect: (context, state) {
    final authProvider = context.read<AuthProvider>();
    if (!authProvider.isAuthenticated) {
      return '/login?redirect=/vendor';
    }
    if (authProvider.user?.role != 'VENDOR') {
      return '/'; // Only vendors can access
    }
    return null;
  },
  routes: [
    GoRoute(
      path: 'dashboard',
      name: 'vendor-dashboard',
      builder: (context, state) => const VendorDashboardScreen(),
    ),
    GoRoute(
      path: 'products',
      name: 'vendor-products',
      builder: (context, state) => const VendorProductsScreen(),
    ),
    GoRoute(
      path: 'products/new',
      name: 'vendor-product-create',
      builder: (context, state) => const VendorProductFormScreen(),
    ),
    GoRoute(
      path: 'products/:id/edit',
      name: 'vendor-product-edit',
      builder: (context, state) => VendorProductFormScreen(
        productId: int.parse(state.pathParameters['id']!),
      ),
    ),
    GoRoute(
      path: 'orders',
      name: 'vendor-orders',
      builder: (context, state) => const VendorOrdersScreen(),
    ),
  ],
),
```

---

### 3.2 Create Main Navigation Menu

**NEW FILE**: `lib/presentation/widgets/main_drawer.dart`

```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../providers/auth_provider.dart';
import '../providers/category_provider.dart';
import '../theme/app_colors.dart';

class MainDrawer extends StatelessWidget {
  const MainDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    final authProvider = context.watch<AuthProvider>();
    final categoryProvider = context.watch<CategoryProvider>();
    final isVendor = authProvider.user?.role == 'VENDOR';
    final isAuthenticated = authProvider.isAuthenticated;

    return Drawer(
      child: SafeArea(
        child: Column(
          children: [
            // Header
            _buildHeader(context, authProvider),

            const Divider(height: 1),

            // Menu Items
            Expanded(
              child: ListView(
                padding: EdgeInsets.zero,
                children: [
                  _buildMenuItem(
                    context,
                    icon: Icons.home_outlined,
                    label: 'Home',
                    onTap: () {
                      context.go('/');
                      Scaffold.of(context).closeDrawer();
                    },
                  ),

                  // Categories
                  _buildCategoriesExpansionTile(context, categoryProvider),

                  // Vendor Space (only for vendors)
                  if (isAuthenticated && isVendor) ...[
                    const Divider(),
                    _buildSectionHeader('Vendor Space'),
                    _buildMenuItem(
                      context,
                      icon: Icons.dashboard_outlined,
                      label: 'Dashboard',
                      onTap: () {
                        context.go('/vendor/dashboard');
                        Scaffold.of(context).closeDrawer();
                      },
                    ),
                    _buildMenuItem(
                      context,
                      icon: Icons.inventory_2_outlined,
                      label: 'My Products',
                      onTap: () {
                        context.go('/vendor/products');
                        Scaffold.of(context).closeDrawer();
                      },
                    ),
                    _buildMenuItem(
                      context,
                      icon: Icons.shopping_bag_outlined,
                      label: 'My Orders',
                      onTap: () {
                        context.go('/vendor/orders');
                        Scaffold.of(context).closeDrawer();
                      },
                    ),
                  ],

                  const Divider(),

                  // Customer menu
                  if (isAuthenticated && !isVendor) ...[
                    _buildMenuItem(
                      context,
                      icon: Icons.receipt_long_outlined,
                      label: 'My Orders',
                      onTap: () {
                        context.go('/orders');
                        Scaffold.of(context).closeDrawer();
                      },
                    ),
                  ],

                  // Become a Vendor (for customers)
                  if (isAuthenticated && !isVendor) ...[
                    _buildMenuItem(
                      context,
                      icon: Icons.store_outlined,
                      label: 'Become a Vendor',
                      onTap: () {
                        _showVendorRequestDialog(context);
                      },
                    ),
                  ],
                ],
              ),
            ),

            const Divider(height: 1),

            // Footer
            _buildFooter(context, authProvider),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context, AuthProvider authProvider) {
    return Container(
      padding: const EdgeInsets.all(20),
      color: AppColors.primary.withOpacity(0.1),
      child: Row(
        children: [
          CircleAvatar(
            radius: 30,
            backgroundColor: AppColors.primary,
            child: Icon(
              authProvider.isAuthenticated
                  ? Icons.person
                  : Icons.person_outline,
              size: 30,
              color: Colors.white,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  authProvider.isAuthenticated
                      ? authProvider.user?.fullName ?? 'User'
                      : 'Guest',
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                if (authProvider.isAuthenticated) ...[
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: _getRoleColor(authProvider.user?.role),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      authProvider.user?.role ?? '',
                      style: const TextStyle(
                        fontSize: 11,
                        color: Colors.white,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMenuItem(
    BuildContext context, {
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return ListTile(
      leading: Icon(icon, color: AppColors.foreground),
      title: Text(label),
      onTap: onTap,
    );
  }

  Widget _buildCategoriesExpansionTile(
    BuildContext context,
    CategoryProvider categoryProvider,
  ) {
    return ExpansionTile(
      leading: const Icon(Icons.category_outlined),
      title: const Text('Categories'),
      children: categoryProvider.categories.map((category) {
        return ListTile(
          contentPadding: const EdgeInsets.only(left: 72, right: 16),
          title: Text(category.name),
          onTap: () {
            // Navigate to category
            context.go('/?category=${category.id}');
            Scaffold.of(context).closeDrawer();
          },
        );
      }).toList(),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Text(
        title,
        style: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: AppColors.mutedForeground,
        ),
      ),
    );
  }

  Widget _buildFooter(BuildContext context, AuthProvider authProvider) {
    if (!authProvider.isAuthenticated) {
      return Padding(
        padding: const EdgeInsets.all(16),
        child: ElevatedButton(
          onPressed: () {
            context.push('/login');
          },
          child: const Text('Sign In'),
        ),
      );
    }

    return ListTile(
      leading: const Icon(Icons.logout, color: AppColors.destructive),
      title: const Text(
        'Logout',
        style: TextStyle(color: AppColors.destructive),
      ),
      onTap: () async {
        await authProvider.logout();
        if (context.mounted) {
          context.go('/');
        }
      },
    );
  }

  Color _getRoleColor(String? role) {
    switch (role) {
      case 'VENDOR':
        return Colors.purple;
      case 'ADMIN':
        return Colors.red;
      case 'COURIER':
        return Colors.blue;
      default:
        return AppColors.primary;
    }
  }

  void _showVendorRequestDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Become a Vendor'),
        content: const Text(
          'Would you like to apply to become a vendor on our platform? '
          'You\'ll be able to sell your own products.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              context.push('/vendor/apply');
            },
            child: const Text('Apply Now'),
          ),
        ],
      ),
    );
  }
}
```

---

### 3.3 Update Home Screen with Drawer

**File**: `lib/presentation/screens/home_screen.dart`

```dart
@override
Widget build(BuildContext context) {
  // ... existing code

  return Scaffold(
    backgroundColor: AppColors.background,
    drawer: const MainDrawer(),  // ← ADD THIS
    body: Column(
      children: [
        // Navigation bar
        AppNavigationBar(
          // Add menu button
          leading: IconButton(
            icon: const Icon(Icons.menu),
            onPressed: () {
              Scaffold.of(context).openDrawer();
            },
          ),
          // ... rest of AppNavigationBar
        ),
        // ... rest of body
      ],
    ),
  );
}
```

---

## 🎨 Phase 4: Vendor Space UI

### 4.1 Vendor Dashboard Screen

**NEW FILE**: `lib/presentation/screens/vendor/vendor_dashboard_screen.dart`

```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../providers/vendor_provider.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_theme.dart';

class VendorDashboardScreen extends StatefulWidget {
  const VendorDashboardScreen({super.key});

  @override
  State<VendorDashboardScreen> createState() => _VendorDashboardScreenState();
}

class _VendorDashboardScreenState extends State<VendorDashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<VendorProvider>().loadDashboardStats();
    });
  }

  @override
  Widget build(BuildContext context) {
    final vendorProvider = context.watch<VendorProvider>();

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Vendor Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined),
            onPressed: () {
              // TODO: Navigate to notifications
            },
          ),
        ],
      ),
      body: vendorProvider.isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: () => vendorProvider.loadDashboardStats(),
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Shop Info Card
                    _buildShopInfoCard(vendorProvider),

                    const SizedBox(height: 24),

                    // Stats Grid
                    _buildStatsGrid(vendorProvider),

                    const SizedBox(height: 24),

                    // Quick Actions
                    _buildQuickActions(context),

                    const SizedBox(height: 24),

                    // Recent Orders
                    _buildRecentOrders(context, vendorProvider),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildShopInfoCard(VendorProvider provider) {
    final shop = provider.shop;
    if (shop == null) return const SizedBox.shrink();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            // Shop Logo
            Container(
              width: 60,
              height: 60,
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: shop.logo != null
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Image.network(
                        shop.logo!,
                        fit: BoxFit.cover,
                      ),
                    )
                  : const Icon(
                      Icons.store,
                      size: 32,
                      color: AppColors.primary,
                    ),
            ),

            const SizedBox(width: 16),

            // Shop Details
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    shop.name,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      _buildStatusBadge(shop.status),
                      const SizedBox(width: 8),
                      if (shop.isVerified)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.green.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: const [
                              Icon(
                                Icons.verified,
                                size: 12,
                                color: Colors.green,
                              ),
                              SizedBox(width: 4),
                              Text(
                                'Verified',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Colors.green,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
                ],
              ),
            ),

            IconButton(
              icon: const Icon(Icons.edit_outlined),
              onPressed: () {
                // TODO: Navigate to shop settings
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusBadge(String status) {
    Color color;
    switch (status) {
      case 'ACTIVE':
        color = Colors.green;
        break;
      case 'PENDING':
        color = Colors.orange;
        break;
      case 'SUSPENDED':
        color = Colors.red;
        break;
      default:
        color = Colors.grey;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        status,
        style: TextStyle(
          fontSize: 11,
          color: color,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  Widget _buildStatsGrid(VendorProvider provider) {
    final stats = provider.stats;

    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      childAspectRatio: 1.5,
      children: [
        _buildStatCard(
          icon: Icons.inventory_2_outlined,
          label: 'Products',
          value: stats?['total_products']?.toString() ?? '0',
          color: Colors.blue,
        ),
        _buildStatCard(
          icon: Icons.shopping_bag_outlined,
          label: 'Pending Orders',
          value: stats?['pending_orders']?.toString() ?? '0',
          color: Colors.orange,
        ),
        _buildStatCard(
          icon: Icons.local_shipping_outlined,
          label: 'Preparing',
          value: stats?['preparing_orders']?.toString() ?? '0',
          color: Colors.purple,
        ),
        _buildStatCard(
          icon: Icons.attach_money,
          label: 'Total Sales',
          value: '${stats?['total_sales'] ?? 0} XAF',
          color: Colors.green,
        ),
      ],
    );
  }

  Widget _buildStatCard({
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Icon(icon, size: 32, color: color),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value,
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  label,
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.mutedForeground,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickActions(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Quick Actions',
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _buildActionButton(
                icon: Icons.add_circle_outline,
                label: 'Add Product',
                onTap: () => context.push('/vendor/products/new'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildActionButton(
                icon: Icons.list_alt,
                label: 'View Orders',
                onTap: () => context.push('/vendor/orders'),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildActionButton({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return ElevatedButton(
      onPressed: onTap,
      style: ElevatedButton.styleFrom(
        padding: const EdgeInsets.all(20),
      ),
      child: Column(
        children: [
          Icon(icon, size: 32),
          const SizedBox(height: 8),
          Text(label),
        ],
      ),
    );
  }

  Widget _buildRecentOrders(BuildContext context, VendorProvider provider) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Recent Orders',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            TextButton(
              onPressed: () => context.push('/vendor/orders'),
              child: const Text('View All'),
            ),
          ],
        ),
        const SizedBox(height: 12),
        const Card(
          child: Padding(
            padding: EdgeInsets.all(32),
            child: Center(
              child: Text(
                'Recent orders will appear here',
                style: TextStyle(color: AppColors.mutedForeground),
              ),
            ),
          ),
        ),
      ],
    );
  }
}
```

This is a comprehensive multi-vendor transformation plan. Would you like me to:

1. **Continue with Vendor Products Screen** implementation?
2. **Create the VendorProvider** for state management?
3. **Implement the order splitting logic** in the backend?
4. **Create migration scripts** to convert existing data?

Let me know which part you'd like me to focus on next!
