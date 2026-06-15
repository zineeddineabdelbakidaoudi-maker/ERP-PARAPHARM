# ParaFarm ERP — Complete Module Specification

---

## Module 1: DASHBOARD (Tableau de Bord)

**Purpose**: Central KPI display with alerts and quick-access actions.

**Features**: Revenue summary (today/week/month), top-selling products chart, low-stock alerts badge, expiring products alerts, pending debts total, recent sales ticker, cash register balance, delivery status, quick-action buttons.

**User Actions**: View KPIs → click card to navigate to detail → toggle date range on chart → acknowledge alerts → click stock alert → navigate filtered.

**DB Entities**: `sales`, `sale_items`, `products`, `stock`, `debts`, `cash_register`, `deliveries`, `notifications`

**Business Rules**:
- Revenue = SUM(sale.total_amount) for period, excluding VOIDED sales
- Low stock = product.stock.quantity ≤ product.min_stock_level
- Expiration alert = batch expiry_date ≤ TODAY + configured_days
- Debts = remaining_amount > 0

**UI**: 6 StatCards, 2 ChartWidgets, AlertList, RecentSalesTable, QuickActionBar

**Permissions**: Admin/Supervisor see all; Cashier sees sales only; Inventory Manager sees stock; Accountant sees financial.

---

## Module 2: POS / SALES (Point de Vente)

**Purpose**: High-speed barcode-driven sales terminal.

**Features**: Barcode scan auto-add, product search by name/code, cart with qty ±, line discount (% or fixed), global discount, TVA calculation (0%/9%/19%), payment methods (Espèces/Carte/Mixte/Crédit), partial payment → debt, client association, receipt preview, thermal printing, A4 invoice, void/cancel with supervisor PIN, return/refund, hold/recall sale, daily closure with cash count, cash drawer trigger.

**User Actions**: Scan → add to cart → adjust qty → apply discount → select client (optional) → Pay → enter amount → confirm → receipt prints → stock decrements → clear cart.

**DB Entities**: `sales`, `sale_items`, `products`, `stock`, `stock_movements`, `cash_register`, `debts`, `payments`

**Business Rules**:
- Price snapshot at time of sale (not live reference)
- Cashier discount ≤ 10%; Supervisor ≤ 50%; Admin unlimited
- line_total = (unit_price × qty) - discount; tax = line_total × tax_rate
- total = SUM(line_totals + taxes) - global_discount
- received_amount ≥ total for cash; partial → creates debt record
- Void: same day only, supervisor PIN, stock restored
- Refund: negative sale_items, stock incremented
- Sale number: `VNT-YYYYMMDD-XXXX`
- Stock check: warn if qty > available, allow override

**Validations**: qty > 0, price > 0, discount ≤ line_total, client required for credit, cash ≥ total for cash method.

**Keyboard Shortcuts**: F2=search name, F3=search barcode, F4=select client, F5=global discount, F8=hold, F9=recall, F10=pay, F12=close register, Del=remove item, +/-=qty.

**Printing**: Thermal receipt (58/80mm), A4 invoice (optional), reprint by sale_id.

---

## Module 3: PURCHASES (Achats)

**Purpose**: Complete procurement — PO creation, receiving, cost tracking, supplier debt.

**Features**: PO creation (Bon de Commande), supplier selection with history, product selection with last purchase price, qty/price entry, PO printing, goods receiving with batch/expiry entry, partial receiving, purchase invoice recording, supplier payment tracking, purchase return, cost price recalculation (weighted average), auto stock increment.

**DB Entities**: `purchases`, `purchase_items`, `suppliers`, `stock`, `stock_movements`, `debts`, `payments`

**Business Rules**:
- Cost recalc: new_cost = ((old_stock × old_cost) + (received × purchase_cost)) / (old_stock + received)
- Partial receiving: PO stays CONFIRMED until all received → CLOSED
- Over-receive warning; supervisor approval required
- Purchase number: `ACH-YYYYMMDD-XXXX`
- Supplier debt auto-created on invoice confirmation

**Permissions**: Inventory Manager=create PO + receive; Accountant=invoice + payment; Admin=all.

---

## Module 4: SUPPLIERS (Fournisseurs)

**Purpose**: Supplier master data, transaction history, debt tracking.

**Features**: CRUD, contact details (name/phone/email/address/tax_id), payment terms (credit days/limit), supplier balance, transaction history, account statement (Relevé de Compte), categorization (Pharmaceutique/Parapharmacie/Cosmétique/Général), search/filter.

**Business Rules**: Cannot delete supplier with outstanding debt. Credit limit warning on new purchase. Balance = SUM(purchases) - SUM(payments).

---

## Module 5: CLIENTS

**Purpose**: Customer management, purchase history, credit tracking.

**Features**: CRUD, client types (Particulier/Entreprise), credit limits, transaction history, account statement, search by name/phone/code, quick-add from POS.

**Business Rules**: Walk-in = client_id=NULL. Credit sales require client. Warning when exceeding credit_limit. Cannot delete with outstanding debt. Code: `CLT-XXXXX`.

---

## Module 6: INVENTORY (Stock)

**Purpose**: Product catalog with pricing, barcodes, stock levels, expiration.

**Features**: Product CRUD, category hierarchy, barcode assignment (manual or auto EAN-13), pricing (cost/selling/wholesale), TVA assignment, min stock level, product image, batch tracking, expiration dates, import/export Excel, label printing, product duplication.

**DB Entities**: `products`, `categories`, `stock`, `stock_movements`, `barcodes`

**Business Rules**: Code auto-gen `PRD-XXXXX`. Barcode unique. selling_price ≥ cost_price (warning). Cost updated via weighted avg on purchase. Stock qty ≤ min_stock → notification.

---

## Module 7: STOCK MOVEMENT (Mouvements de Stock)

**Purpose**: Audit trail for every stock change.

**Features**: Movement log with filtering, types: PURCHASE_IN, SALE_OUT, RETURN_IN, RETURN_OUT, ADJUSTMENT, DAMAGE, EXPIRED, manual adjustment with reason, stock reconciliation (physical vs system).

**DB Entities**: `stock_movements` — product_id, movement_type, quantity (+/-), reference_type/id, batch_number, expiry_date, user_id, notes

**Business Rules**: Every stock change MUST create a movement record. Manual adjustments require reason. Reconciliation = physical - system → creates adjustment.

---

## Module 8: DELIVERY / LIVRAISON

**Purpose**: Outbound delivery management with status tracking.

**Features**: Create from sale or standalone, delivery note (Bon de Livraison), operator assignment, status flow (PENDING→IN_TRANSIT→DELIVERED→FAILED), note printing (A4/thermal), delivery history per client, failed delivery handling with reason, rescheduling.

**DB Entities**: `deliveries`, `delivery_items`

**Business Rules**: Number: `LVR-YYYYMMDD-XXXX`. Cannot deliver > sale qty. Failed requires reason code. Status changes logged in audit.

---

## Module 9: DEBT MANAGEMENT (Gestion des Dettes)

**Purpose**: Unified client/supplier debt tracking with aging.

**Features**: Client debt ledger, supplier debt ledger, partial payment recording, payment history, debt aging (30/60/90/120+), credit limit enforcement, account statements, statement printing, overdue alerts, debt write-off with admin approval.

**DB Entities**: `debts`, `payments`

**Business Rules**: remaining = total - SUM(payments). Status: PENDING→PARTIAL→PAID→WRITTEN_OFF. Aging from created_at. Write-off requires admin + audit log.

---

## Module 10: TREASURY / CASH REGISTER (Caisse)

**Purpose**: Daily cash operations and session management.

**Features**: Session open/close, opening balance entry, auto sales tracking, expense recording, withdrawal/deposit, daily closure with physical count, variance calculation, session history, cash flow summary.

**DB Entities**: `cash_register`, `expenses`, `cash_movements`

**Business Rules**: One open register at a time. expected = opening + cash_sales - expenses - withdrawals + deposits. variance = counted - expected. Cannot close without count. Significant variance → notification.

---

## Module 11: REPORTS & ANALYTICS (Rapports)

**Purpose**: 20+ pre-built reports with PDF/Excel export.

**Features**: Report templates, date range filtering, multi-criteria filters, grouping (daily/weekly/monthly), chart visualization, PDF export with branding, Excel export, direct printing.

*Full report catalog in [05_printing_reports.md](file:///c:/Users/pc%20gamer/Documents/desktop-illyes/docs/spec/05_printing_reports.md)*

---

## Module 12: PRODUCT LABELING (Étiquettes)

**Purpose**: Barcode/price label generation and printing.

**Features**: Single/batch label printing, templates (barcode+price, barcode+name+price, shelf), size config (30×20, 40×30, 50×25, custom mm), quantity per product, preview, printer selection, A4 sheet grid layout.

---

## Module 13: USER MANAGEMENT (Utilisateurs)

**Purpose**: Local user accounts with role-based access.

**Features**: User CRUD, role assignment, password management, PIN for overrides, login history, session tracking.

**DB Entities**: `users`, `roles`, `permissions`, `login_history`

---

## Module 14: SETTINGS (Paramètres)

**Purpose**: Application configuration.

**Features**: Company info (name/address/phone/tax_id/logo), tax rates, currency (DA), default printers, stock thresholds, expiration alert window, receipt header/footer, backup schedule, theme.

**DB Entities**: `settings` (key/value store)

---

## Module 15: PRINTER MANAGEMENT (Imprimantes)

**Purpose**: Printer profile configuration.

**Features**: Windows printer discovery, profile creation (name/type/connection), types: THERMAL/A4/LABEL, test print, default assignments, paper width config (58/80mm), encoding config.

**DB Entities**: `printers`

**Design Note**: Printer implementation kept abstract. ESC/POS abstraction layer, not hardcoded to XP-80 SDK. Configurable profiles allow any ESC/POS-compatible thermal printer.

---

## Module 16: BACKUP & RESTORE (Sauvegarde)

**Purpose**: Local database backup and disaster recovery.

**Features**: One-click manual backup, auto-backup on app close, backup dir config (local/USB), backup encryption (AES-256), restore from file, backup history, integrity verification (SHA-256 checksum), retention (keep last N).

---

## Module 17: LOGS & AUDIT (Journal)

**Purpose**: Activity logging for security and compliance.

**Features**: User action logging, financial transaction logging, system event logging, log viewer with filters, log export, retention policy.

**DB Entities**: `audit_logs` — user_id, action, module, entity_type/id, old_values (JSON), new_values (JSON)

---

## Module 18: NOTIFICATIONS

**Purpose**: In-app alerts for stock, expiration, debts, cash variance.

**Features**: Low stock alerts, expiration alerts, debt overdue alerts, cash variance alerts, notification bell with unread count, mark read/dismiss, preferences per user.

**DB Entities**: `notifications`

---

## Module 19: BARCODE MANAGEMENT

**Purpose**: Generate and manage product barcodes.

**Features**: Auto-generate EAN-13, manual entry, formats: EAN-13/Code128/QR, uniqueness validation, barcode lookup, bulk generation.

**DB Entities**: `barcodes`

---

## Module 20: EXPIRATION TRACKING (Péremption)

**Purpose**: Batch expiration monitoring and disposal.

**Features**: Batch-level tracking, multi-tier alerts (90/60/30/expired days), dashboard widget, expiration report, disposal workflow (creates EXPIRED movement), return to supplier for near-expiry.

**Business Rules**: expiry_date ≤ TODAY → cannot sell (hard block). expiry ≤ TODAY+30 → POS warning. Disposal requires inventory manager approval.

---

## Module 21: MULTI-DOCUMENT CENTER (Centre de Documents)

**Purpose**: Centralized document generation hub.

**Features**: Document types: Facture de Vente, Bon de Commande, Bon de Livraison, Relevé de Compte, Rapport. Document history with search, reprinting, PDF preview, batch generation, sequential numbering, company branding.

**Business Rules**: Documents immutable once confirmed. Each type has own numbering sequence.
