# ParaFarm ERP — Screen Map & UI/UX Design System

---

# SCREEN HIERARCHY

```
Application
├── Login Screen (LoginWindow — frameless dialog)
└── Main Window (QMainWindow)
    ├── Sidebar (collapsible, 240px/60px)
    ├── Header Bar (user, notifications, clock)
    ├── Status Bar (DB status, printer status)
    └── Content Area (QStackedWidget)
        ├── Dashboard (Tableau de Bord)
        ├── POS / Sales (Point de Vente)
        ├── Products (Gestion des Produits)
        │   └── Categories (Catégories)
        ├── Clients
        ├── Suppliers (Fournisseurs)
        ├── Purchases (Achats)
        ├── Deliveries (Livraisons)
        ├── Stock
        ├── Debt Management (Dettes)
        ├── Cash Register (Caisse)
        ├── Reports (Rapports)
        ├── Labels (Étiquettes)
        ├── Expiration (Péremption)
        ├── Users (Utilisateurs)
        ├── Settings (Paramètres)
        ├── Printers (Imprimantes)
        ├── Backup (Sauvegarde)
        ├── Statistics (Statistiques)
        └── Logs (Journal)
```

---

## LOGIN SCREEN

| Property | Value |
|---|---|
| Title | ParaFarm ERP — Connexion |
| Type | Frameless QDialog, centered, 450×400px fixed |

**Layout**: Company logo → App name "ParaFarm ERP" → Username field (placeholder: "Nom d'utilisateur") → Password field → "Se Connecter" button (full-width) → Version number (bottom-right)

**Actions**: Enter=submit, Tab=next field, Esc=quit. Failed login → red shake animation. 5 failures → 5-minute lockout.

---

## DASHBOARD

| Property | Value |
|---|---|
| Title | ParaFarm ERP — Tableau de Bord |

**Layout**:
```
┌──────┬───────┬───────┬──────┐
│Revenu│Ventes │Stock⚠ │Dettes│  ← StatCards
├──────┴───┬───┴───────┴──────┤
│Revenue   │Top Produits      │  ← Charts
│Trend     │(Barres)          │
├──────────┼──────────────────┤
│Ventes    │Alertes           │  ← Tables
│Récentes  │(Stock/Péremption)│
└──────────┴──────────────────┘
```

**Quick Actions**: Nouvelle Vente, Nouvel Achat, Nouveau Produit

---

## POS / SALES SCREEN

| Property | Value |
|---|---|
| Title | ParaFarm ERP — Point de Vente |
| Layout | Dual-panel: Cart (60% left) + Product Panel (40% right) |

**Left — Cart**:
```
Client: [____Recherche____▼] [+ Nouveau]
┌───┬──────────┬─────┬────────┬────────┬────────┐
│ # │ Produit  │ Qté │ Prix   │ Remise │ Total  │
├───┼──────────┼─────┼────────┼────────┼────────┤
│ 1 │ Dolip... │  2  │ 150.00 │  0.00  │ 300.00 │
│ 2 │ Vitam... │  1  │ 450.00 │  10%   │ 405.00 │
└───┴──────────┴─────┴────────┴────────┴────────┘
  Sous-total:                         705.00 DA
  Remise:                               0.00 DA
  TVA:                                 63.45 DA
  ═══════════════════════════════════════════════
  TOTAL:                              768.45 DA
[🗑 Vider]  [⏸ Attente]  [💰 PAYER]
```

**Right — Product Entry**:
```
🔍 [____Scan / Recherche____]  ← auto-focus
┌─────────────────────┐
│ Suggestions live     │
│ (max 20 résultats)  │
└─────────────────────┘
[7] [8] [9] [Qté]
[4] [5] [6] [Rem%]
[1] [2] [3] [Suppr]
[0] [00] [.] [Enter]
```

**Payment Dialog (Modal)**:
```
PAIEMENT
Total à payer:     768.45 DA
Méthode: ○ Espèces ○ Carte ○ Mixte ○ Crédit
Montant reçu: [________]
Monnaie:        231.55 DA
[Annuler]     [✓ Confirmer]
```

**Context Menu (right-click cart item)**: Modifier quantité, Appliquer remise, Supprimer, Voir produit

**Shortcuts**: F2=name search, F3=barcode, F4=client, F5=discount, F8=hold, F9=recall, F10=pay, F12=close register, Del=remove, +/-=qty, Esc=cancel

---

## PRODUCT MANAGEMENT

**Top**: Search + Category filter + Status filter + [+ Nouveau Produit]

**Table**: Code | Barcode | Nom | Catégorie | Prix Achat | Prix Vente | Stock | Statut

**Bottom**: Pagination + Count + [Exporter Excel] + [Imprimer Étiquettes]

**Product Dialog**: Code (auto), Barcode (manual/[Générer]), Nom, Catégorie (dropdown), Description, Prix d'achat, Prix de vente, Prix de gros, TVA (dropdown), Stock minimum, Unité, [Annuler] [Enregistrer]

**Row Actions**: Double-click=edit, Right-click → Modifier | Supprimer | Stock | Étiquette | Dupliquer

---

## CLIENT/SUPPLIER LEDGER (Relevé de Compte)

**Header**: Entity info (name, code, phone, address)

**Summary Cards**: Total Achats | Total Payé | Solde Restant

**Filter**: Date range (Du / Au)

**Table**: Date | Référence | Type | Montant | Solde

**Actions**: [Imprimer Relevé] [Exporter PDF] [Enregistrer Paiement]

---

## CASH REGISTER

**Active Session Layout**: Session info (date, opened by, opening balance) → Summary cards (Espèces, Carte, Total, Dépenses, Solde Attendu) → Today's sales table → Today's expenses table → [+ Dépense] [Clôturer Caisse]

**Closure Dialog**:
```
CLÔTURE DE CAISSE
Solde attendu:           12,450.00 DA
Billets 2000 DA × [__] = _____
Billets 1000 DA × [__] = _____
Billets  500 DA × [__] = _____
Billets  200 DA × [__] = _____
Pièces   100 DA × [__] = _____
Pièces    50 DA × [__] = _____
Autres:           [_______]
Total compté:            12,350.00 DA
Écart:                     -100.00 DA
Notes: [________________________]
[Annuler]        [✓ Confirmer]
```

---

## REPORT GENERATOR

**Left**: Report category tree (Ventes | Stock | Finance | Achats | Livraisons)

**Center**: Filters (dates, product, client, supplier, cashier) → Preview table/chart

**Bottom**: [Actualiser] [PDF] [Excel] [Imprimer]

---

## LABEL PRINTING

**Left**: Product selector (search + multi-select table with qty)

**Center**: Label preview (live render)

**Right**: Template, size, printer selection

**Bottom**: [Imprimer] [Annuler]

---

## STOCK ALERTS

**Tabs**: Rupture | Stock Faible | Expirés | Bientôt Expirés

**Table**: Produit | Barcode | Stock | Min | Statut | Dernier Mouvement

**Actions**: [Commander] [Ajuster] [Exporter]

---

# UI/UX DESIGN SYSTEM

## Color Palette

| Token | Hex | Usage |
|---|---|---|
| --primary | #1B5E20 | Primary buttons, active sidebar (pharmacy green) |
| --primary-light | #4CAF50 | Hover states |
| --primary-dark | #0D3B14 | Pressed states |
| --secondary | #1565C0 | Links, info badges |
| --accent | #FF6F00 | Warnings, attention |
| --danger | #C62828 | Delete, errors, overdue |
| --success | #2E7D32 | Completed, in-stock |
| --warning | #F9A825 | Low stock, expiring |
| --bg-primary | #F5F5F5 | Main background |
| --bg-card | #FFFFFF | Card/panel |
| --bg-sidebar | #1B2631 | Sidebar dark |
| --text-primary | #212121 | Main text |
| --text-secondary | #757575 | Muted text |
| --text-on-dark | #ECEFF1 | Text on dark bg |
| --border | #E0E0E0 | Borders |
| --hover | #E8F5E9 | Row/item hover |
| --selected | #C8E6C9 | Selected row |

## Typography

| Element | Font | Size | Weight |
|---|---|---|---|
| App Title | Inter | 20px | 700 |
| Page Title | Inter | 18px | 600 |
| Section Header | Inter | 15px | 600 |
| Table Header | Inter | 13px | 600 |
| Body / Table Cell | Inter | 12-13px | 400 |
| Button | Inter | 13px | 500 |
| Stat Card Value | Inter | 28px | 700 |
| Caption | Inter | 11px | 400 |

## Spacing

| Token | Value |
|---|---|
| --spacing-xs | 4px |
| --spacing-sm | 8px |
| --spacing-md | 16px |
| --spacing-lg | 24px |
| --spacing-xl | 32px |

## Components

**Sidebar**: 240px expanded / 60px collapsed. Dark bg. Items: icon + label, 44px height. Active: 4px left accent border.

**Data Table**: Alternating rows (white/#FAFAFA). Hover highlight. Dark header. 8px cell padding. Sort arrows. Column resize.

**Forms**: Labels above inputs. 36px input height. Red asterisk required. Error: red border + text below.

**Modals**: Semi-transparent overlay. White card, 8px corners. Max 600px forms / 900px complex. Right-aligned action buttons.

**Toasts**: Top-right corner. 5s auto-dismiss (info). Persistent (errors). Success=green, Error=red, Warning=orange, Info=blue.

**Confirmations**: Centered, icon, clear message in French, [Annuler] + [Confirmer]. Red confirm for destructive.

## Global Shortcuts

| Key | Action |
|---|---|
| Ctrl+K | Global search |
| Ctrl+N | New (context-dependent) |
| Ctrl+P | Print current view |
| Ctrl+E | Export current view |
| Ctrl+S | Save form |
| Ctrl+1-9 | Sidebar navigation |
| F11 | Toggle fullscreen |
| Esc | Close dialog / cancel |

## Status Bar

Left: 🟢 DB connected. Center: User + Role. Right: Printer status + Clock.

## Minimum Size: 1024×768px. Sidebar collapses at < 1280px.
