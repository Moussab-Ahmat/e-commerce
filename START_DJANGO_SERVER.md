# Démarrer le Serveur Django

## Pour Windows

```bash
cd C:\Users\legion\Documents\my_projet\e-commerce\ecommerce\cursor
.venv\Scripts\python.exe manage.py runserver
```

## Accéder au Django Admin

1. Ouvrez votre navigateur
2. Allez sur: **http://localhost:8000/admin**
3. Connectez-vous avec vos identifiants admin

## Vous devriez voir dans le menu:

```
ACCOUNTS
├── Collaboration requests
├── OTP verifications
├── SMS logs
└── Users

CATALOG
├── Categories
├── Product images
└── Products

VENDORS                    ← NOUVEAU !
└── Shops                  ← NOUVEAU !

DELIVERY
└── Delivery zones

ORDERS
├── Order items
└── Orders

... (autres apps)
```

## Si le menu "VENDORS" n'apparaît pas:

1. **Arrêtez le serveur** (Ctrl+C)
2. **Redémarrez-le**:
   ```bash
   .venv\Scripts\python.exe manage.py runserver
   ```
3. **Rafraîchissez** la page du navigateur (F5)

## Créer votre premier Shop

1. Cliquez sur **"Vendors"** → **"Shops"**
2. Cliquez sur **"Add Shop"** en haut à droite
3. Remplissez le formulaire :
   - **Vendor**: Choisissez un utilisateur avec le rôle VENDOR
   - **Name**: Nom de la boutique
   - **Email**: Email de contact
   - **Phone**: Téléphone
   - **Address**: Adresse complète
   - **Status**: PENDING (sera activé par admin)

4. Cliquez sur **"Save"**
