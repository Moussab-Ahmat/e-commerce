# Guide de Gestion des Catégories

## 📋 Vue d'ensemble

Les catégories de produits sont maintenant **dynamiques** et s'affichent automatiquement sur la homepage de l'application Flutter. Toutes les catégories créées dans Django admin apparaissent instantanément dans l'app.

---

## ✅ Changements Effectués

### Backend (Django)
- **API Endpoint**: `GET /api/v1/catalog/categories/`
- **Modèle**: `apps.catalog.models.Category`
- **Format de réponse**: Paginé avec `{"count": 12, "results": [...]}`

### Frontend (Flutter)
- **Nouveau modèle**: `lib/data/models/category_model.dart`
- **Nouveau repository**: `lib/data/repositories/category_repository.dart`
- **Nouveau provider**: `lib/presentation/providers/category_provider.dart`
- **Écran mis à jour**: `lib/presentation/screens/home_screen.dart`

### Catégories Créées
Les catégories suivantes ont été créées automatiquement:
1. **Electronics** - Electronic devices and gadgets
2. **Computers & Laptops** - Desktop computers, laptops, and accessories
3. **Smartphones** - Mobile phones and smartphones
4. **Audio & Headphones** - Headphones, speakers, and audio equipment
5. **Cameras & Photography** - Digital cameras, lenses, and photography gear
6. **Gaming** - Gaming consoles, accessories, and peripherals
7. **Wearables** - Smartwatches and fitness trackers
8. **Home Appliances** - Kitchen and home appliances

---

## 🎯 Comment Ajouter des Catégories

### Méthode 1: Django Admin (Interface graphique)

1. **Accédez à l'admin Django**:
   ```
   http://localhost:8000/admin/catalog/category/
   ```

2. **Cliquez sur "Add Category"**

3. **Remplissez les champs**:
   - **Name**: Nom de la catégorie (ex: "Tablets")
   - **Slug**: URL-friendly (ex: "tablets") - Auto-généré à partir du nom
   - **Description**: Description de la catégorie (facultatif)
   - **Parent**: Catégorie parente (facultatif, pour sous-catégories)
   - **Is active**: ✅ Coché (pour afficher sur l'app)

4. **Sauvegardez**

5. **Rafraîchissez l'app Flutter** - La catégorie apparaît automatiquement!

### Méthode 2: Django Shell (Ligne de commande)

```bash
cd C:\Users\legion\Documents\my_projet\e-commerce\ecommerce\cursor
.venv\Scripts\python.exe manage.py shell
```

```python
from apps.catalog.models import Category

# Créer une nouvelle catégorie
category = Category.objects.create(
    name='Tablets',
    slug='tablets',
    description='iPad, Samsung Galaxy Tab, and other tablets',
    is_active=True
)

print(f'✅ Created: {category.name}')
```

### Méthode 3: Script Python (Création en masse)

Éditez `create_categories.py` pour ajouter vos catégories, puis:

```bash
cd C:\Users\legion\Documents\my_projet\e-commerce\ecommerce\cursor
.venv\Scripts\python.exe manage.py shell < create_categories.py
```

---

## 📱 Comment les Catégories s'Affichent dans Flutter

### Flux de Données
```
Django API → CategoryRepository → CategoryProvider → HomeScreen → UI
```

### Chargement Automatique
Au démarrage de la homepage:
1. `CategoryProvider.loadCategories()` est appelé
2. L'API `/api/v1/catalog/categories/` est interrogée
3. Les catégories actives sont filtrées
4. L'interface affiche: **"All"** + catégories de l'API

### Exemple de Rendu
```
All | Electronics | Computers & Laptops | Smartphones | ...
```

---

## 🔧 Gestion des Catégories

### Désactiver une Catégorie
Dans Django admin:
1. Trouvez la catégorie
2. Décochez **"Is active"**
3. Sauvegardez
4. Elle disparaît de l'app Flutter

### Modifier une Catégorie
1. Accédez à Django admin
2. Cliquez sur la catégorie
3. Modifiez les champs
4. Sauvegardez
5. Rafraîchissez Flutter pour voir les changements

### Supprimer une Catégorie
⚠️ **Attention**: La suppression d'une catégorie peut affecter les produits associés.

Dans Django admin:
1. Sélectionnez la catégorie
2. Cliquez "Delete"
3. Confirmez

Ou via shell:
```python
from apps.catalog.models import Category
Category.objects.filter(slug='old-category').delete()
```

---

## 🌳 Catégories Hiérarchiques (Parent/Enfant)

Vous pouvez créer des sous-catégories:

### Exemple
```python
# Catégorie parente
electronics = Category.objects.create(
    name='Electronics',
    slug='electronics',
    is_active=True
)

# Sous-catégorie
smartphones = Category.objects.create(
    name='Smartphones',
    slug='smartphones',
    parent=electronics,  # 👈 Lien parent-enfant
    is_active=True
)
```

**Note**: Actuellement, l'app Flutter affiche toutes les catégories au même niveau. Pour afficher une hiérarchie, il faudrait modifier l'interface.

---

## 📊 Vérifier les Catégories

### Via API
```bash
curl http://localhost:8000/api/v1/catalog/categories/
```

### Via Django Shell
```python
from apps.catalog.models import Category

# Compter les catégories actives
active_count = Category.objects.filter(is_active=True).count()
print(f'{active_count} catégories actives')

# Lister toutes les catégories
for cat in Category.objects.filter(is_active=True):
    print(f'- {cat.name} ({cat.slug})')
```

### Via Django Admin
```
http://localhost:8000/admin/catalog/category/
```

---

## 🎨 Personnalisation de l'Interface Flutter

### Modifier l'Ordre d'Affichage
Éditez `home_screen.dart` pour trier les catégories:

```dart
final categoryNames = [
  'All',
  ...categoryProvider.categories
      .map((c) => c.name)
      .toList()
      ..sort(), // 👈 Tri alphabétique
];
```

### Limiter le Nombre de Catégories Affichées
```dart
final categoryNames = [
  'All',
  ...categoryProvider.categories
      .take(8) // 👈 Afficher seulement les 8 premières
      .map((c) => c.name),
];
```

---

## 🐛 Dépannage

### Les catégories n'apparaissent pas dans Flutter
1. Vérifiez que l'API fonctionne:
   ```bash
   curl http://localhost:8000/api/v1/catalog/categories/
   ```
2. Vérifiez les logs Flutter:
   ```
   flutter run
   ```
   Cherchez: `✅ Loaded X categories from API`

3. Vérifiez que les catégories sont actives dans Django admin

### Erreur "No categories found"
- Assurez-vous d'avoir créé des catégories dans Django
- Vérifiez que `is_active=True` sur les catégories
- Redémarrez le serveur Django

### La homepage affiche toujours les anciennes catégories
- Actualisez l'app Flutter (pull to refresh sur la liste de produits)
- Ou redémarrez l'app:
  ```bash
  flutter run
  ```

---

## 📝 Notes Importantes

1. **Synchronisation Automatique**: Les catégories sont chargées automatiquement au démarrage de la homepage
2. **Cache**: Les catégories sont mises en cache côté Flutter pour de meilleures performances
3. **Rafraîchissement**: Tirez vers le bas (pull to refresh) pour recharger les catégories
4. **Performance**: L'API est paginée mais retourne toutes les catégories actives d'un coup

---

## ✨ Prochaines Améliorations Possibles

- [ ] Filtrage de produits par catégorie (recherche par ID de catégorie)
- [ ] Affichage hiérarchique des sous-catégories
- [ ] Icônes personnalisées par catégorie
- [ ] Compteur de produits par catégorie
- [ ] Tri des catégories par popularité

---

## 🚀 Résumé

Vous pouvez maintenant:
✅ Créer des catégories depuis Django admin
✅ Les voir automatiquement dans l'app Flutter
✅ Les modifier/désactiver/supprimer facilement
✅ Créer des sous-catégories avec parent/enfant
✅ Gérer tout depuis l'interface web Django

**Les catégories sont maintenant 100% dynamiques - plus besoin de modifier le code Flutter!**
