"""
Script to create initial product categories for the e-commerce platform.
Run with: python manage.py shell < create_categories.py
"""

from apps.catalog.models import Category

# Categories to create
categories_data = [
    {
        'name': 'Electronics',
        'slug': 'electronics',
        'description': 'Electronic devices and gadgets',
    },
    {
        'name': 'Computers & Laptops',
        'slug': 'computers-laptops',
        'description': 'Desktop computers, laptops, and accessories',
    },
    {
        'name': 'Smartphones',
        'slug': 'smartphones',
        'description': 'Mobile phones and smartphones',
    },
    {
        'name': 'Audio & Headphones',
        'slug': 'audio-headphones',
        'description': 'Headphones, speakers, and audio equipment',
    },
    {
        'name': 'Cameras & Photography',
        'slug': 'cameras-photography',
        'description': 'Digital cameras, lenses, and photography gear',
    },
    {
        'name': 'Gaming',
        'slug': 'gaming',
        'description': 'Gaming consoles, accessories, and peripherals',
    },
    {
        'name': 'Wearables',
        'slug': 'wearables',
        'description': 'Smartwatches and fitness trackers',
    },
    {
        'name': 'Home Appliances',
        'slug': 'home-appliances',
        'description': 'Kitchen and home appliances',
    },
]

print('Creating categories...')
created_count = 0
updated_count = 0

for cat_data in categories_data:
    category, created = Category.objects.update_or_create(
        slug=cat_data['slug'],
        defaults={
            'name': cat_data['name'],
            'description': cat_data['description'],
            'is_active': True,
        }
    )

    if created:
        created_count += 1
        print(f'✅ Created: {category.name}')
    else:
        updated_count += 1
        print(f'🔄 Updated: {category.name}')

print(f'\n📊 Summary:')
print(f'   - Created: {created_count} categories')
print(f'   - Updated: {updated_count} categories')
print(f'   - Total: {Category.objects.filter(is_active=True).count()} active categories')
