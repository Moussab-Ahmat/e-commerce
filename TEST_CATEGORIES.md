# 🧪 Guide de Test - Catégories Dynamiques

## Test Rapide en 3 Étapes

### ✅ Étape 1: Vérifier que l'API Django Fonctionne

Ouvrez un terminal et testez l'API:

```bash
curl http://127.0.0.1:8000/api/v1/catalog/categories/
```

**Résultat attendu**: Vous devriez voir 12 catégories en JSON:
```json
{
  "count": 12,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 5,
      "name": "Electronics",
      "slug": "electronics",
      "description": "Electronic devices and gadgets",
      "parent": null,
      "is_active": true
    },
    ...
  ]
}
```

✅ **Si l'API retourne les catégories, passez à l'étape 2**

---

### ✅ Étape 2: Lancer l'Application Flutter

#### Sur Navigateur Web (Chrome)
```bash
cd C:\Users\legion\Documents\my_projet\e-commerce\ecommerce\cursor\flutter_app
flutter run -d chrome
```

#### Sur Appareil Android Physique (Recommandé)
1. Activez le débogage USB sur votre téléphone Android
2. Connectez le téléphone via USB
3. Vérifiez la connexion:
   ```bash
   flutter devices
   ```
4. Lancez l'app:
   ```bash
   flutter run
   ```

**Note**: Assurez-vous que `physicalDeviceHost` dans `app_config.dart` est configuré avec votre IP locale.

---

### ✅ Étape 3: Vérifier l'Affichage des Catégories

Une fois l'app lancée:

1. **Regardez la console Flutter** pour voir les logs:
   ```
   ╔══════════════════════════════════════════════════════════════
   ║ APP CONFIG
   ╠══════════════════════════════════════════════════════════════
   ║ Environment: DEVELOPMENT
   ║ Platform: android
   ║ Physical Device Mode: true
   ║ Host: 192.168.65.1
   ║ Base URL: http://192.168.65.1:8000
   ╚══════════════════════════════════════════════════════════════

   🔍 API Response: 12 zones
   ✅ Loaded 12 categories from API
   📦 CategoryProvider: Loaded 12 categories
   ```

2. **Sur la homepage**, vous devriez voir une rangée de catégories horizontale:
   ```
   All | Electronics | Computers & Laptops | Smartphones | ...
   ```

3. **Cliquez sur une catégorie** pour filtrer les produits

---

## 🧪 Test Complet: Ajouter une Nouvelle Catégorie

### 1. Ajoutez une Catégorie dans Django Admin

1. Ouvrez http://localhost:8000/admin
2. Connectez-vous avec votre compte admin
3. Allez dans **Catalog** → **Categories**
4. Cliquez sur **"Add Category"** en haut à droite
5. Remplissez le formulaire:
   - **Name**: `Tablets`
   - **Slug**: `tablets` (ou laissez auto-générer)
   - **Description**: `iPads, Samsung Galaxy Tab, and other tablets`
   - **Parent**: Laissez vide
   - **Is active**: ✅ Coché
6. Cliquez sur **"Save"**

### 2. Vérifiez dans l'API

```bash
curl http://127.0.0.1:8000/api/v1/catalog/categories/ | grep -i "Tablets"
```

Vous devriez voir:
```json
{
  "id": 13,
  "name": "Tablets",
  "slug": "tablets",
  ...
}
```

### 3. Rafraîchissez l'App Flutter

**Option 1: Pull-to-refresh** (si implémenté)
- Tirez vers le bas sur la liste de produits

**Option 2: Redémarrer l'app**
- Appuyez sur `r` dans le terminal Flutter pour hot reload
- Ou appuyez sur `R` pour hot restart complet

**Option 3: Recharger manuellement**
- Fermez et relancez l'app

### 4. Vérifiez l'Affichage

La nouvelle catégorie "Tablets" devrait maintenant apparaître dans la rangée de catégories!

```
All | Electronics | Computers & Laptops | Smartphones | Tablets | ...
```

---

## 🔍 Tests de Validation

### Test 1: Désactiver une Catégorie

1. Dans Django admin, trouvez une catégorie
2. Décochez **"Is active"**
3. Sauvegardez
4. Rafraîchissez l'app Flutter
5. ✅ La catégorie ne devrait plus apparaître

### Test 2: Modifier le Nom d'une Catégorie

1. Dans Django admin, changez le nom d'une catégorie
   - Ex: "Smartphones" → "Mobile Phones"
2. Sauvegardez
3. Rafraîchissez l'app Flutter
4. ✅ Le nouveau nom devrait s'afficher

### Test 3: Supprimer une Catégorie

1. Dans Django admin, supprimez une catégorie de test
2. Confirmez la suppression
3. Rafraîchissez l'app Flutter
4. ✅ La catégorie ne devrait plus apparaître

### Test 4: Créer une Sous-Catégorie

1. Créez une catégorie avec un parent:
   - **Name**: `Gaming Consoles`
   - **Parent**: Gaming
   - **Is active**: ✅
2. Sauvegardez
3. Rafraîchissez l'app Flutter
4. ✅ Elle devrait apparaître comme catégorie normale (hiérarchie pas encore implémentée dans UI)

---

## 🐛 Résolution de Problèmes

### ❌ Les catégories n'apparaissent pas

**Vérifications**:

1. **Backend Django est-il lancé?**
   ```bash
   cd C:\Users\legion\Documents\my_projet\e-commerce\ecommerce\cursor
   .venv\Scripts\python.exe manage.py runserver
   ```

2. **L'API retourne-t-elle des données?**
   ```bash
   curl http://127.0.0.1:8000/api/v1/catalog/categories/
   ```

3. **Les catégories sont-elles actives?**
   - Vérifiez dans Django admin que `is_active=True`

4. **Y a-t-il des erreurs dans les logs Flutter?**
   - Cherchez des messages d'erreur dans la console

5. **Configuration réseau correcte?**
   - Vérifiez `app_config.dart`:
     - Web: `_webHost = '127.0.0.1'`
     - Physical device: `physicalDeviceHost = 'VOTRE_IP'`

### ❌ Erreur "Failed to load categories"

**Causes possibles**:
- Backend Django non lancé
- Mauvaise configuration de l'IP
- CORS mal configuré

**Solution**:
1. Vérifiez que Django tourne sur port 8000
2. Vérifiez `development.py`: `CORS_ALLOW_ALL_ORIGINS = True`
3. Testez l'API avec curl

### ❌ "Connection refused" ou "Server failure"

**Testez sur un navigateur web d'abord**:
```bash
flutter run -d chrome
```

Si ça fonctionne sur web mais pas sur appareil physique:
- Vérifiez que votre téléphone et PC sont sur le même réseau Wi-Fi
- Trouvez votre IP locale:
  ```bash
  ipconfig  # Windows
  ```
  Cherchez "IPv4 Address" (ex: 192.168.1.100)
- Mettez à jour `app_config.dart`:
  ```dart
  static const String physicalDeviceHost = '192.168.1.100';  // VOTRE IP
  ```

---

## ✅ Checklist de Validation

Cochez chaque item au fur et à mesure:

- [ ] L'API Django retourne 12 catégories via curl
- [ ] L'app Flutter se lance sans erreur
- [ ] Les logs montrent `✅ Loaded 12 categories from API`
- [ ] Les catégories s'affichent sur la homepage
- [ ] Cliquer sur une catégorie change l'affichage
- [ ] Ajouter une nouvelle catégorie dans Django admin fonctionne
- [ ] La nouvelle catégorie apparaît dans l'app après refresh
- [ ] Désactiver une catégorie la fait disparaître de l'app
- [ ] Modifier le nom d'une catégorie met à jour l'app

---

## 📊 Logs Attendus

### Console Flutter (Succès)
```
[ImageURL] /media/products/sample.jpg → http://192.168.65.1:8000/media/products/sample.jpg
🔍 API Response: 12 zones
✅ Loaded 12 zones delivery zones
✅ Loaded 12 categories from API
📦 CategoryProvider: Loaded 12 categories
```

### Console Django (Requête API)
```
DEBUG GET /api/v1/catalog/categories/
DEBUG SELECT "categories"."id", "categories"."name", "categories"."slug" ...
DEBUG 200 OK
```

---

## 🎯 Résumé

Si tous les tests passent:
✅ **Les catégories sont 100% dynamiques et fonctionnelles!**

Vous pouvez maintenant gérer toutes vos catégories depuis Django admin sans jamais toucher au code Flutter.

**Prochaine étape recommandée**: Ajoutez le filtrage de produits par catégorie pour que cliquer sur une catégorie affiche uniquement les produits de cette catégorie.
