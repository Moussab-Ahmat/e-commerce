"""
Product, category, and inventory models with strong stock integrity.
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.db import transaction
from core.validators import validate_xaf_amount


class Category(models.Model):
    """Product category model."""
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'categories'
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug', 'is_active']),
        ]
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Product model with stock management."""
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products'
    )
    
    # Pricing (stored as integer XAF)
    price = models.BigIntegerField(
        validators=[MinValueValidator(0), validate_xaf_amount],
        help_text='Price in XAF (integer)'
    )
    
    # Stock management
    stock_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Available stock quantity'
    )
    reserved_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Quantity reserved in pending orders'
    )
    
    # Product details
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    barcode = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # kg
    dimensions = models.CharField(max_length=100, blank=True)  # LxWxH format
    
    # Images (optimized for low bandwidth - limit to 3)
    image1 = models.ImageField(upload_to='products/', blank=True, null=True)
    image2 = models.ImageField(upload_to='products/', blank=True, null=True)
    image3 = models.ImageField(upload_to='products/', blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug', 'is_active']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['sku']),
            models.Index(fields=['is_featured', 'is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def available_quantity(self):
        """Calculate available quantity (stock - reserved)."""
        return max(0, self.stock_quantity - self.reserved_quantity)
    
    def reserve_stock(self, quantity):
        """Reserve stock for an order (with locking)."""
        with transaction.atomic():
            # Use select_for_update to lock the row
            product = Product.objects.select_for_update().get(pk=self.pk)
            
            if product.available_quantity < quantity:
                raise ValueError(f'Insufficient stock. Available: {product.available_quantity}, Requested: {quantity}')
            
            product.reserved_quantity += quantity
            product.save(update_fields=['reserved_quantity'])
            return product
    
    def release_stock(self, quantity):
        """Release reserved stock."""
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=self.pk)
            product.reserved_quantity = max(0, product.reserved_quantity - quantity)
            product.save(update_fields=['reserved_quantity'])
            return product
    
    def commit_stock(self, quantity):
        """Commit reserved stock (when order is confirmed)."""
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=self.pk)
            
            if product.reserved_quantity < quantity:
                raise ValueError('Cannot commit more stock than reserved')
            
            product.reserved_quantity -= quantity
            product.stock_quantity -= quantity
            product.save(update_fields=['reserved_quantity', 'stock_quantity'])
            return product


class ProductImage(models.Model):
    """Additional product images (if needed beyond the 3 main ones)."""
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='additional_images'
    )
    image = models.ImageField(upload_to='products/additional/')
    alt_text = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'product_images'
        ordering = ['order', 'id']

