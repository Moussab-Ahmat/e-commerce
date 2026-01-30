# 📱 Menu de Navigation - Guide d'Utilisation

## ✅ Ce Qui a Été Créé

### 1. **MainDrawer** - Menu Latéral Complet
📁 `lib/presentation/widgets/main_drawer.dart`

Un menu latéral (drawer) professionnel avec:
- **Header personnalisé** avec avatar et rôle de l'utilisateur
- **Section Home**
- **Section Catégories** (chargées dynamiquement depuis Django)
- **Section Espace Vendeur** (adapté selon le rôle)
- **Footer** avec bouton connexion/déconnexion

---

## 🎨 Structure du Menu

### Pour les Invités (Non connectés)
```
┌─────────────────────────┐
│  👤 Invité              │
├─────────────────────────┤
│  🏠 Home                │
├─────────────────────────┤
│  CATEGORIES             │
│  📦 Electronics         │
│  📦 Smartphones         │
│  📦 Audio & Headphones  │
│  📦 ... (dynamique)     │
├─────────────────────────┤
│  ESPACE VENDEUR         │
│  Connectez-vous pour... │
├─────────────────────────┤
│  [Se Connecter]         │
└─────────────────────────┘
```

### Pour les Clients (CUSTOMER)
```
┌─────────────────────────┐
│  👤 John Doe            │
│  🏷️ Client              │
├─────────────────────────┤
│  🏠 Home                │
├─────────────────────────┤
│  CATEGORIES             │
│  📦 Electronics         │
│  📦 Smartphones         │
│  ...                    │
├─────────────────────────┤
│  ESPACE VENDEUR         │
│  🏪 Devenir Vendeur     │
├─────────────────────────┤
│  🚪 Déconnexion         │
└─────────────────────────┘
```

### Pour les Vendeurs (VENDOR)
```
┌─────────────────────────┐
│  👤 Jane Smith          │
│  🏷️ Vendeur             │
├─────────────────────────┤
│  🏠 Home                │
├─────────────────────────┤
│  CATEGORIES             │
│  📦 Electronics         │
│  📦 Smartphones         │
│  ...                    │
├─────────────────────────┤
│  ESPACE VENDEUR         │
│  📊 Tableau de Bord     │
│  📦 Mes Produits        │
│  🛍️ Mes Commandes       │
├─────────────────────────┤
│  🚪 Déconnexion         │
└─────────────────────────┘
```

---

## 🎯 Fonctionnalités

### 1. **Header Dynamique**
- Affiche le nom de l'utilisateur ou "Invité"
- Badge de rôle avec couleur (Client, Vendeur, Admin, etc.)
- Design moderne avec dégradé de couleur

### 2. **Navigation Home**
- Retour à la page d'accueil
- Ferme automatiquement le drawer

### 3. **Catégories Dynamiques**
- ✅ Chargées depuis l'API Django (`/api/v1/catalog/categories/`)
- ✅ S'affichent automatiquement dans le menu
- ✅ Cliquez pour filtrer les produits par catégorie
- ✅ Skeleton loader pendant le chargement
- ✅ Message si aucune catégorie disponible

### 4. **Espace Vendeur**

#### Pour les Invités:
- Message invitant à se connecter

#### Pour les Clients:
- **Bouton "Devenir Vendeur"**
- Dialog informatif expliquant les avantages
- Prêt pour le formulaire de demande (à implémenter)

#### Pour les Vendeurs:
- **Tableau de Bord** → `/vendor/dashboard` (à créer)
- **Mes Produits** → `/vendor/products` (à créer)
- **Mes Commandes** → `/vendor/orders` (à créer)

### 5. **Footer Intelligent**
- **Non connecté**: Bouton "Se Connecter"
- **Connecté**: Bouton "Déconnexion" avec confirmation

---

## 🔧 Intégration avec HomeScreen

### Modifications Apportées

**Fichier**: `lib/presentation/screens/home_screen.dart`

1. **Import du drawer**:
```dart
import '../widgets/main_drawer.dart';
```

2. **Ajout au Scaffold**:
```dart
return Scaffold(
  drawer: const MainDrawer(),  // ← NOUVEAU
  body: Builder(
    builder: (context) => Column(
      // ...
    ),
  ),
);
```

3. **Bouton menu dans AppNavigationBar**:
```dart
AppNavigationBar(
  onMenuTap: () => Scaffold.of(context).openDrawer(),  // ← NOUVEAU
  // ...
)
```

---

## 🧪 Comment Tester

### 1. Lancer l'Application

```bash
cd C:\Users\legion\Documents\my_projet\e-commerce\ecommerce\cursor\flutter_app
flutter run
```

### 2. Ouvrir le Menu

**Méthode 1**: Cliquez sur le **bouton menu** (☰) en haut à gauche

**Méthode 2**: Glissez depuis le bord gauche de l'écran (swipe gesture)

### 3. Tester les Fonctionnalités

#### Test 1: Navigation Home
- Ouvrez le menu
- Cliquez sur "Home"
- ✅ Le menu se ferme
- ✅ Vous restez sur la homepage

#### Test 2: Catégories Dynamiques
- Ouvrez le menu
- Regardez la section "CATEGORIES"
- ✅ Vous devriez voir les catégories de votre base de données
- Cliquez sur une catégorie
- ✅ Les produits sont filtrés
- ✅ Le menu se ferme

#### Test 3: Devenir Vendeur (Client)
- Connectez-vous en tant que CLIENT
- Ouvrez le menu
- Cliquez sur "Devenir Vendeur"
- ✅ Dialog informatif s'affiche
- ✅ Bouton "Postuler" affiche un SnackBar (TODO)

#### Test 4: Espace Vendeur (Vendor)
- Connectez-vous en tant que VENDOR
- Ouvrez le menu
- ✅ Vous devriez voir:
  - Tableau de Bord
  - Mes Produits
  - Mes Commandes
- Cliquez sur un élément
- ⚠️ Routes à créer (TODO)

#### Test 5: Déconnexion
- Connectez-vous
- Ouvrez le menu
- Cliquez sur "Déconnexion"
- ✅ Dialog de confirmation
- ✅ Déconnexion réussie
- ✅ Retour à la homepage

---

## 🎨 Personnalisation

### Changer les Couleurs

**Fichier**: `lib/presentation/widgets/main_drawer.dart`

```dart
// Header gradient
decoration: BoxDecoration(
  gradient: LinearGradient(
    colors: [
      AppColors.primary,  // ← Changez ici
      AppColors.primary.withValues(alpha: 0.8),
    ],
  ),
)
```

### Ajouter des Éléments au Menu

```dart
// Dans la section ListView > children
_buildMenuItem(
  context,
  icon: Icons.info_outline,
  label: 'À Propos',
  onTap: () {
    context.push('/about');
    Navigator.pop(context);
  },
),
```

---

## 🔒 Gestion des Rôles

Le menu s'adapte automatiquement selon le rôle:

| Rôle | Badge Couleur | Accès Espace Vendeur |
|------|---------------|---------------------|
| Invité | - | Message "Connectez-vous" |
| CUSTOMER | 🔵 Bleu | Bouton "Devenir Vendeur" |
| VENDOR | 🟣 Violet | Menu complet vendeur |
| ADMIN | 🔴 Rouge | Menu complet vendeur |
| COURIER | 🟢 Vert | Message "Connectez-vous" |

---

## 📝 Code Labels

Tous les textes sont en **français**:
- "Se Connecter" / "Déconnexion"
- "Devenir Vendeur"
- "Tableau de Bord"
- "Mes Produits"
- "Mes Commandes"

---

## 🚀 Prochaines Étapes

### Routes à Créer

1. **`/vendor/dashboard`** - Tableau de bord vendeur
2. **`/vendor/products`** - Gestion des produits
3. **`/vendor/orders`** - Gestion des commandes
4. **`/vendor/apply`** - Formulaire de demande vendeur

### Fonctionnalités à Implémenter

- [ ] Formulaire de demande vendeur
- [ ] Écrans vendeur (dashboard, products, orders)
- [ ] Notifications dans le drawer
- [ ] Avatar utilisateur avec photo
- [ ] Compteurs (produits, commandes en attente)

---

## 🐛 Résolution de Problèmes

### Le menu ne s'ouvre pas
- Vérifiez que le `Builder` entoure bien le `Column`
- Vérifiez que `onMenuTap` est passé à `AppNavigationBar`

### Les catégories ne s'affichent pas
- Vérifiez que le backend Django est lancé
- Vérifiez que `CategoryProvider` charge les catégories
- Vérifiez les logs: `✅ Loaded X categories from API`

### Erreur de navigation
- Assurez-vous que les routes existent dans `app_router.dart`
- Les routes vendeur ne sont pas encore créées (TODO)

---

## ✅ Checklist de Vérification

- [x] MainDrawer créé
- [x] AppNavigationBar mis à jour avec bouton menu
- [x] HomeScreen intégré avec le drawer
- [x] Header avec avatar et rôle
- [x] Navigation Home fonctionnelle
- [x] Catégories chargées dynamiquement
- [x] Section Espace Vendeur selon le rôle
- [x] Dialog "Devenir Vendeur" pour clients
- [x] Bouton connexion/déconnexion
- [x] Gestion des états (loading, empty)
- [ ] Routes vendeur (TODO)
- [ ] Formulaire demande vendeur (TODO)

---

**🎉 Le menu de navigation est prêt et fonctionnel !**

Vous pouvez maintenant ouvrir le menu, naviguer vers Home, filtrer par catégories, et accéder à l'espace vendeur (une fois les écrans créés).
