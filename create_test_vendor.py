"""
Script pour créer un vendeur de test avec sa boutique.
Usage: python manage.py shell < create_test_vendor.py
"""

from apps.accounts.models import User
from apps.vendors.models import Shop
from apps.catalog.models import Product, Category

print("\n" + "="*60)
print("CREATION D'UN VENDEUR DE TEST")
print("="*60 + "\n")

# 1. Créer un utilisateur vendeur
print("1. Creation de l'utilisateur vendeur...")
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
    print(f"   [CREE] Vendeur: {vendor.email}")
else:
    print(f"   [EXISTE] Vendeur: {vendor.email}")

# 2. Créer une boutique
print("\n2. Creation de la boutique...")
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
        'status': 'ACTIVE',  # Activee directement pour les tests
        'is_verified': True,
    }
)
if created:
    print(f"   [CREE] Boutique: {shop.name}")
else:
    print(f"   [EXISTE] Boutique: {shop.name}")

# 3. Créer quelques produits
print("\n3. Creation de produits...")

# Obtenir ou créer une catégorie
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
        print(f"   [CREE] Produit: {product.name} - {product.price} XAF")
        created_count += 1
    else:
        print(f"   [EXISTE] Produit: {product.name}")

print("\n" + "="*60)
print("RESUME")
print("="*60)
print(f"Vendeur: {vendor.email}")
print(f"Mot de passe: vendor123")
print(f"Boutique: {shop.name}")
print(f"Produits dans la boutique: {shop.products.count()}")
print(f"Statut de la boutique: {shop.status}")
print("\n" + "="*60)
print("PROCHAINES ETAPES")
print("="*60)
print("1. Connectez-vous au Django Admin:")
print("   http://localhost:8000/admin")
print("\n2. Allez dans VENDORS > Shops pour voir la boutique")
print("\n3. Testez l'API vendeur:")
print("   - Login: POST http://localhost:8000/api/auth/login/")
print("   - Stats: GET http://localhost:8000/api/v1/vendors/dashboard/stats/")
print("="*60 + "\n")
