import json
from django.core.management.base import BaseCommand
from django.test import RequestFactory
from apps.catalog.models import Product, ProductImage
from apps.catalog.serializers import ProductListSerializer


class Command(BaseCommand):
    help = 'Test product images API response'

    def handle(self, *args, **options):
        self.stdout.write("=== Testing Product API Response ===\n")

        # Create a fake request for building absolute URLs
        factory = RequestFactory()
        request = factory.get('/api/v1/products/')
        request.META['HTTP_HOST'] = 'localhost:8000'

        # Get products with images
        products_with_images = Product.objects.filter(images__isnull=False).distinct()

        if products_with_images.exists():
            product = products_with_images.first()
            self.stdout.write(f"Product: {product.name} (ID: {product.id})")
            self.stdout.write(f"Images count: {product.images.count()}\n")

            # Show raw database data
            self.stdout.write("Raw ProductImage data:")
            for img in product.images.all():
                self.stdout.write(f"  - ID: {img.id}")
                self.stdout.write(f"    Original: {img.original}")
                self.stdout.write(f"    Original name: {img.original.name}")
                if img.original:
                    self.stdout.write(f"    Original URL: {img.original.url}")
                self.stdout.write(f"    Thumbnail: {img.thumbnail}")
                self.stdout.write(f"    Thumbnail name: {img.thumbnail.name}")
                if img.thumbnail:
                    self.stdout.write(f"    Thumbnail URL: {img.thumbnail.url}")
                self.stdout.write(f"    Is Primary: {img.is_primary}\n")

            # Serialize the product
            serializer = ProductListSerializer(product, context={'request': request})
            data = serializer.data

            self.stdout.write("Serialized API Response:")
            self.stdout.write(json.dumps(dict(data), indent=2))

            self.stdout.write("\n=== KEY CHECK ===")
            if 'primary_image' in data:
                self.stdout.write(self.style.SUCCESS(f"✓ primary_image exists: {data['primary_image']}"))
            else:
                self.stdout.write(self.style.ERROR("✗ primary_image field is MISSING!"))

        else:
            self.stdout.write(self.style.WARNING("No products with images found!"))
            self.stdout.write("\nAll products:")
            for p in Product.objects.all():
                self.stdout.write(f"  - {p.name}: {p.images.count()} images")
