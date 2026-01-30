"""
Management command to create a test vendor with shop and products.
Usage: python manage.py create_test_vendor
"""

from django.core.management.base import BaseCommand
from apps.accounts.models import User
from apps.vendors.models import Shop
from apps.catalog.models import Product, Category


class Command(BaseCommand):
    help = 'Create a test vendor with shop and products'

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("CREATION D'UN VENDEUR DE TEST"))
        self.stdout.write("="*60 + "\n")

        # 1. Create vendor user
        self.stdout.write("1. Creation de l'utilisateur vendeur...")
        vendor, created = User.objects.get_or_create(
            email='vendor@test.com',
            defaults={
                'first_name': 'John',
                'last_name': 'Vendor',
                'role': 'VENDOR',
                'is_active': True,
                'is_verified': True,
            }
        )
        if created:
            vendor.set_password('vendor123')
            vendor.save()
            self.stdout.write(self.style.SUCCESS(f"   [CREE] Vendeur: {vendor.email}"))
        else:
            self.stdout.write(self.style.WARNING(f"   [EXISTE] Vendeur: {vendor.email}"))

        # 2. Create shop
        self.stdout.write("\n2. Creation de la boutique...")
        shop, created = Shop.objects.get_or_create(
            vendor=vendor,
            defaults={
                'name': 'Electronics Paradise',
                'description': 'Les meilleurs produits electroniques en ville',
                'email': 'shop@electronics-paradise.com',
                'phone': '+237123456789',
                'address_line1': '123 Rue du Commerce',
                'city': 'Douala',
                'region': 'Littoral',
                'postal_code': '00237',
                'status': 'ACTIVE',
                'is_verified': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"   [CREE] Boutique: {shop.name}"))
        else:
            self.stdout.write(self.style.WARNING(f"   [EXISTE] Boutique: {shop.name}"))

        # 3. Create products
        self.stdout.write("\n3. Creation de produits...")

        # Get or create category
        category, _ = Category.objects.get_or_create(
            name='Electronics',
            defaults={'slug': 'electronics', 'is_active': True}
        )

        products_data = [
            {
                'name': 'Souris Sans Fil',
                'sku': 'MOUSE-WL-001',
                'price': 15000,
                'stock_quantity': 50,
                'description': 'Souris ergonomique sans fil avec batterie longue duree',
            },
            {
                'name': 'Clavier USB',
                'sku': 'KB-USB-001',
                'price': 25000,
                'stock_quantity': 30,
                'description': 'Clavier USB professionnel avec retroeclairage',
            },
            {
                'name': 'Cable HDMI 2m',
                'sku': 'HDMI-CABLE-001',
                'price': 5000,
                'stock_quantity': 100,
                'description': 'Cable HDMI haute vitesse 2 metres',
            },
        ]

        created_count = 0
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                sku=product_data['sku'],
                defaults={
                    **product_data,
                    'shop': shop,
                    'category': category,
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f"   [CREE] Produit: {product.name} - {product.price} XAF"
                ))
                created_count += 1
            else:
                self.stdout.write(self.style.WARNING(
                    f"   [EXISTE] Produit: {product.name}"
                ))

        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("RESUME"))
        self.stdout.write("="*60)
        self.stdout.write(f"Vendeur: {vendor.email}")
        self.stdout.write(f"Mot de passe: vendor123")
        self.stdout.write(f"Boutique: {shop.name}")
        self.stdout.write(f"Produits dans la boutique: {shop.products.count()}")
        self.stdout.write(f"Statut de la boutique: {shop.status}")

        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("PROCHAINES ETAPES"))
        self.stdout.write("="*60)
        self.stdout.write("1. Connectez-vous au Django Admin:")
        self.stdout.write("   http://localhost:8000/admin")
        self.stdout.write("\n2. Allez dans VENDORS > Shops pour voir la boutique")
        self.stdout.write("\n3. Testez l'API vendeur:")
        self.stdout.write("   - Login: POST http://localhost:8000/api/auth/login/")
        self.stdout.write("   - Stats: GET http://localhost:8000/api/v1/vendors/dashboard/stats/")
        self.stdout.write("="*60 + "\n")

        self.stdout.write(self.style.SUCCESS("\n✅ Vendeur de test créé avec succès!\n"))
