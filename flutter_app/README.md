# Flutter E-commerce Client

Client Flutter (Android, iOS, Web) connecte au backend REST existant.

## Fonctionnalites

- Catalogue avec recherche + filtres (categories)
- Detail produit avec carousel, transitions Hero
- Panier local (offline)
- Checkout COD en etapes + capture GPS
- Liste commandes + suivi + contact support (WhatsApp)

## Architecture

```
lib/
  core/
    config/         # Endpoints API
    errors/         # Failures
    network/        # Dio + retry
    services/       # Location
    storage/        # Cache Hive
    utils/          # Formatters
  data/
    data_sources/   # Remote + cache
    models/         # DTOs
    repositories/   # Repos
  presentation/
    providers/      # Provider
    screens/        # UI
    theme/          # Theme
    widgets/        # Reusable UI
```

## Setup

1) Installer les dependances :
```bash
flutter pub get
```

2) Configurer la base URL et les query params :
- `lib/core/config/api_endpoints.dart`

3) Lancer :
```bash
flutter run
```

## API requise

Les endpoints sont centralises dans `lib/core/config/api_endpoints.dart`.

- `GET /api/v1/catalog/products/` (pagination)
- `GET /api/v1/catalog/products/{id}/`
- `GET /api/v1/catalog/categories/`
- `GET /api/v1/delivery/zones/`
- `GET /api/v1/delivery/slots/?zone_id=`
- `GET /api/v1/orders/orders/`
- `GET /api/v1/orders/orders/{id}/`
- `POST /api/v1/orders/orders/`

### Parametres de recherche (si ton backend differe)

Dans `lib/core/config/api_endpoints.dart` :
- `searchParam` (ex: `q` ou `search`)
- `categoryParam` (ex: `category_id`)

### Payload creation commande (COD + GPS)

Le client envoie :
```
{
  "items": [{"product_id":"...", "variant_id":null, "qty":2}],
  "zone_id":"...",
  "address_text":"...",
  "landmark":"...",
  "slot_id":"...",
  "payment_mode":"COD",
  "contact_phone":"...",
  "customer_location": {
    "lat": 0.0,
    "lng": 0.0,
    "accuracy_m": 12.5,
    "captured_at": "ISO-8601"
  }
}
```

Si ton backend utilise d autres champs, ajuste la methode `_normalizeOrderPayload` dans `lib/data/repositories/order_repository.dart`.

## Notes

- Cache catalogue: Hive (offline-lite)
- Images: cached_network_image
- Panier: local uniquement
- Localisation: Geolocator (web + mobile)
