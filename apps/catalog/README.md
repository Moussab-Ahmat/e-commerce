# Catalog App

Product catalog with categories, products, and images.

## Features

- Category model with parent-child relationships
- Product model with pricing (XAF integer)
- ProductImage model with automatic thumbnail generation
- Admin CRUD for all models
- DRF endpoints with pagination
- Redis caching for products list (15 min TTL)
- Cache invalidation on product save
- Optimized queries (no N+1)

## API Endpoints

### Categories
```
GET /api/v1/catalog/categories/
GET /api/v1/catalog/categories/{id}/
```

### Products List (Paginated, Lightweight)
```
GET /api/v1/catalog/products/
GET /api/v1/catalog/products/?page=1&page_size=20
```

**Response fields:**
- id, name, slug, category_name, price, stock_quantity, sku, is_featured, primary_image

### Product Detail (Full Fields)
```
GET /api/v1/catalog/products/{id}/
```

**Response fields:**
- All fields including description, category object, images array

## Caching

- Products list endpoint is cached in Redis
- TTL: 15 minutes (900 seconds)
- Cache key format: `products_list_page_{page}_size_{page_size}`
- Cache is invalidated when a product is saved

## Image Handling

- ProductImage model automatically generates thumbnails (300x300)
- Thumbnails are generated from original images
- Original and thumbnail URLs are available in API responses

## Setup

1. Create migrations:
```bash
python manage.py makemigrations catalog
python manage.py migrate
```

2. Create media directory:
```bash
mkdir -p media/products/original media/products/thumbnails
```

3. Run tests:
```bash
pytest tests/test_catalog.py -v
```

## Admin

Access admin at `/admin/` to manage:
- Categories (with parent selection)
- Products (with inline image management)
- Product Images (with automatic thumbnail generation)

## Performance

- List endpoint uses `select_related('category')` for category data
- List endpoint uses `prefetch_related('images')` to avoid N+1 queries
- Detail endpoint prefetches all images
- Redis caching reduces database load

