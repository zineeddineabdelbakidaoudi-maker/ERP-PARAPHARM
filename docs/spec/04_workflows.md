# ParaFarm ERP — Workflow Specifications

---

# 6. POS / SALES WORKFLOW

## 6.1 Session Opening

1. Cashier logs in → system checks for open register
2. If no open session → "Ouvrir la Caisse" dialog → enter physical cash count
3. Confirm → `cash_register` created (status=OPEN)
4. POS screen activated, barcode input auto-focused

## 6.2 Product Scan / Search

- **Barcode scan**: exact match on `products.barcode` or `barcodes.barcode_value`
- **Text search** (≥2 chars): LIKE on name, code, barcode. Max 20 results. 300ms debounce.
- **Found**: add to cart (qty=1, increment if already present)
- **Not found**: toast "Produit introuvable"

## 6.3 Cart Management

**Add to cart**: snapshot unit_price, cost_price, tax_rate from product at sale time.

**Quantity**: spinner (min=1), +/- keys. qty=0 → remove with confirm.

**Stock check**: if stock < qty → warning dialog. Allow override (logs warning).

**Line discount**: right-click → "Appliquer Remise" → % or fixed. Cashier ≤ 10%, Supervisor ≤ 50%, Admin unlimited. Exceeding limit → supervisor PIN dialog.

**Global discount**: F5 → dialog. Same permission rules.

## 6.4 Tax Calculation

```python
for item in cart:
    item.line_subtotal = item.unit_price * item.quantity
    item.discount_amount = calc_discount(item.line_subtotal, item.discount_type, item.discount_value)
    item.taxable = item.line_subtotal - item.discount_amount
    item.tax_amount = item.taxable * (item.tax_rate / 100)
    item.line_total = item.taxable + item.tax_amount

sale.subtotal = sum(item.line_subtotal)
sale.discount_amount = global_discount
sale.tax_total = sum(item.tax_amount)
sale.total_amount = sale.subtotal - sale.discount_amount + sale.tax_total
```

TVA rates: 0% (exempt pharma), 9% (reduced), 19% (standard parapharma/cosmetics).

## 6.5 Payment

- **Espèces**: enter received ≥ total → calculate change → trigger cash drawer
- **Carte**: full amount card
- **Mixte**: enter cash portion, remainder = card
- **Crédit**: full amount → debt. Requires client_id. Check credit_limit.

**Partial payment → debt**: if paid < total, creates `debts` record (entity_type=CLIENT, remaining=total-paid).

## 6.6 Sale Confirmation

1. Save `sales` + `sale_items` to DB
2. Decrement `stock.quantity` per item
3. Create `stock_movements` (type=SALE_OUT) per item
4. Update `cash_register` totals
5. If credit → create `debts` record
6. Print receipt (thermal) — non-blocking (QThreadPool)
7. Clear cart → return to scan mode

Sale number: `VNT-YYYYMMDD-XXXX` (auto-sequential).

## 6.7 Receipt Printing

**Thermal (80mm)**:
```
================================
       PARAFARM PHARMACY
    123 Rue Example, Alger
      Tél: 021 XX XX XX
================================
Date: 14/05/2026    Heure: 14:32
Ticket: VNT-20260514-0042
Caissier: Ahmed
Client: Comptoir
--------------------------------
Doliprane 1000mg    2 × 150.00
                         300.00
Vitamine C          1 × 450.00
  Remise 10%             -45.00
                         405.00
--------------------------------
Sous-total:              705.00
TVA (9%):                 63.45
                    ============
TOTAL:                   768.45
Espèces:               1,000.00
Monnaie:                 231.55
================================
    Merci de votre visite!
   Échange sous 48h avec ticket
================================
         [BARCODE: VNT-...]
```

**Print failure does NOT block sale**. Data saved regardless. Failed print queued for retry.

## 6.8 Void / Cancel

- Same day only. Supervisor PIN required. Enter reason.
- `sale.status = 'VOIDED'`. Stock restored. Cash register reversed. Debt cancelled if exists.
- Audit log created.

## 6.9 Return / Refund

- Search original sale by receipt number
- Select items + quantities to return
- Creates negative sale (type=RETURN)
- Stock incremented. Payment reversed. Debt reduced if credit.

## 6.10 Hold / Recall

- **F8**: serialize cart to memory (max 10 held, auto-clear after 24h)
- **F9**: list held sales → select → restore to cart
- Held sales NOT in database until completed.

## 6.11 Daily Closure

- F12 → Closure dialog → display expected balance
- Enter physical count by denomination
- Calculate variance (counted - expected)
- If variance > threshold → supervisor notification
- Confirm → `cash_register.status='CLOSED'`. Print closure report. Logout.

**Expected = opening + cash_sales - expenses - withdrawals + deposits** (card sales excluded).

## 6.12 Duplicate Prevention

- Sequential sale_number. Double-click protection (2s disable). Debounce barcode scanner 200ms.

---

# 7. PURCHASE WORKFLOW

## 7.1 Purchase Order Creation

1. Select supplier → load info + terms
2. Add products (search/barcode) → pre-fill last purchase price
3. Set quantities + negotiated prices
4. Save as DRAFT (editable) or CONFIRMED (locked)
5. Print PO for supplier (A4)

## 7.2 Goods Receiving

1. Open confirmed PO → "Réceptionner"
2. Per line: enter received_qty, batch_number, expiry_date
3. Confirm receiving:
   - Increment `stock.quantity` per product
   - Create `stock_movements` (type=PURCHASE_IN)
   - Recalculate cost price (weighted average):
     ```python
     new_cost = ((current_stock * current_cost) + (received_qty * purchase_cost)) / (current_stock + received_qty)
     ```
   - Create supplier debt
4. Partial receiving: PO stays CONFIRMED until all items fully received → CLOSED
5. Over-receive: warning, supervisor approval

## 7.3 Supplier Payment

- Select supplier debt → enter amount (full/partial) → select method → reference → confirm
- `payments` record. `debts.paid_amount += amount`. If remaining=0 → PAID.

## 7.4 Purchase Return

- Open completed purchase → "Retour Fournisseur" → select items/qty → reason
- Stock decremented. Supplier credit note. Debt reduced.

---

# 8. DELIVERY WORKFLOW

## 8.1 Creation

- Create from sale or standalone → select client → add items → assign operator → set date → set address/zone → Save (PENDING) → Print delivery note (A4)

## 8.2 Status Flow

```
PENDING → IN_TRANSIT → DELIVERED
                    → FAILED → PENDING (reschedule)
PENDING → CANCELLED
```

- FAILED requires failure_reason (Absent/Adresse incorrecte/Refusé/Autre)
- All transitions logged in `audit_logs`

## 8.3 Delivery Note (A4)

Header: company info + BON DE LIVRAISON N° + Date + Client + Livreur. Items table: # | Produit | Qté | Observation. Footer: Signature Client ___ | Signature Livreur ___

---

# 9. DEBT MANAGEMENT

## 9.1 Client Debts

- Auto-created on credit sale. remaining = total - paid.
- Payment recording: dialog → amount → method → confirm → update debt.
- Aging buckets: 🟢 0-30d, 🟡 31-60d, 🟠 61-90d, 🔴 91-120d, ⚫ 120+d
- Credit limit check: `total_outstanding + new_sale > credit_limit → warning`
- Write-off: admin only → audit log → status=WRITTEN_OFF

## 9.2 Supplier Debts

- Auto-created on purchase invoice. Same aging/payment structure.
- Due date = purchase_date + supplier.credit_period_days.

## 9.3 Account Statements (Relevé de Compte)

- Header: entity info
- Opening balance (carried forward from before date range)
- Transactions: date, reference, description, debit, credit, running balance
- Closing balance
- Export: PDF (A4) / Excel

---

# 10. INVENTORY & STOCK

## 10.1 Movement Types

| Type | Dir | Trigger |
|---|---|---|
| PURCHASE_IN | + | Purchase receiving |
| SALE_OUT | - | Sale confirmation |
| RETURN_IN | + | Customer return |
| RETURN_OUT | - | Supplier return |
| ADJUSTMENT | ± | Manual (reason required) |
| DAMAGE | - | Damaged goods |
| EXPIRED | - | Expired disposal |

## 10.2 Stock Alerts

```python
if stock.quantity <= 0: notification(type='LOW_STOCK', priority='CRITICAL')
elif stock.quantity <= product.min_stock_level: notification(type='LOW_STOCK', priority='HIGH')
```

## 10.3 Expiration

- Run on app startup + hourly timer
- expired (≤ today) → cannot sell (hard block on POS)
- ≤ 30 days → POS warning on scan
- Disposal workflow → EXPIRED movement → audit log

## 10.4 Reconciliation

1. Print count sheet (product list with blank qty column)
2. Enter physical counts
3. System compares physical vs system
4. Differences → ADJUSTMENT movements
5. Logged in audit trail
