"""
Catalog models: Category, Product, ProductImage.
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from django.utils import timezone
from PIL import Image
import os


class Category(models.Model):
    """Product category model."""
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    image = models.ImageField(
        upload_to='categories/',
        null=True,
        blank=True,
        help_text='Category image'
    )
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
    
    def save(self, *args, **kwargs):
        """Auto-generate slug if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    """Product model."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products'
    )

    # Multi-vendor: Link to Shop
    shop = models.ForeignKey(
        'vendors.Shop',
        on_delete=models.CASCADE,
        related_name='products',
        null=True,
        blank=True,
        help_text='Shop selling this product (required for multi-vendor)'
    )

    # Pricing (stored as integer XAF)
    price = models.BigIntegerField(
        validators=[MinValueValidator(0)],
        help_text='Price in XAF (integer)'
    )
    
    # Stock
    stock_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)

    # Promotion fields
    is_on_sale = models.BooleanField(default=False, db_index=True)
    sale_price = models.BigIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text='Promotional price in XAF. Must be less than regular price.'
    )
    sale_start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the sale starts'
    )
    sale_end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the sale ends'
    )

    # Publishing
    is_published = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug', 'is_active']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['shop', 'is_active']),
            models.Index(fields=['sku']),
            models.Index(fields=['is_featured', 'is_active']),
            models.Index(fields=['is_on_sale', 'is_active']),
            models.Index(fields=['is_published', 'is_active']),
        ]

    def __str__(self):
        return self.name

    def is_sale_active(self):
        """Check if sale is currently active."""
        if not self.is_on_sale or not self.sale_price:
            return False
        now = timezone.now()
        if self.sale_start_date and now < self.sale_start_date:
            return False
        if self.sale_end_date and now > self.sale_end_date:
            return False
        return True

    def get_effective_price(self):
        """Return sale_price if sale is active, else regular price."""
        if self.is_sale_active():
            return self.sale_price
        return self.price

    def get_discount_percentage(self):
        """Calculate percentage reduction."""
        if self.is_sale_active() and self.sale_price and self.price > 0:
            return round((1 - self.sale_price / self.price) * 100)
        return 0

    def get_savings(self):
        """Calculate savings in XAF."""
        if self.is_sale_active() and self.sale_price:
            return self.price - self.sale_price
        return 0

    def save(self, *args, **kwargs):
        """Auto-generate slug and invalidate cache."""
        if not self.slug:
            self.slug = slugify(self.name)

        # Invalidate all products list cache keys
        from django.core.cache import cache
        try:
            for page in range(1, 11):
                for size in [20, 50, 100]:
                    cache.delete(f'products_list_page_{page}_size_{size}')
        except:
            pass

        super().save(*args, **kwargs)


class ProductImage(models.Model):
    """Product image with original and thumbnail."""
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    original = models.ImageField(upload_to='products/original/')
    thumbnail = models.ImageField(upload_to='products/thumbnails/', blank=True)
    alt_text = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_images'
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['product', 'is_primary']),
        ]
    
    def __str__(self):
        return f'{self.product.name} - Image {self.id}'
    
    def save(self, *args, **kwargs):
        """Generate thumbnail on save."""
        super().save(*args, **kwargs)
        
        if self.original and not self.thumbnail:
            self.generate_thumbnail()
    
    def generate_thumbnail(self):
        """Generate thumbnail from original image."""
        from django.core.files.base import ContentFile
        from io import BytesIO
        
        if not self.original:
            return
        
        # Open original image
        img = Image.open(self.original)
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Create thumbnail (300x300 max)
        img.thumbnail((300, 300), Image.Resampling.LANCZOS)
        
        # Save to BytesIO
        thumb_io = BytesIO()
        img.save(thumb_io, format='JPEG', quality=85)
        thumb_io.seek(0)
        
        # Generate filename
        original_name = os.path.basename(self.original.name)
        name, ext = os.path.splitext(original_name)
        thumb_filename = f'{name}_thumb{ext}'
        
        # Save thumbnail
        self.thumbnail.save(
            thumb_filename,
            ContentFile(thumb_io.read()),
            save=False
        )
        self.save(update_fields=['thumbnail'])

