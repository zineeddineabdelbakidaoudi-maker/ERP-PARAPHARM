# ParaFarm ERP — Printing & Reporting Architecture

---

# 12. PRINTING SYSTEM

## Architecture

```
PrintManager (orchestrator)
├── ThermalEngine (ESC/POS abstraction)
│   └── ESCPOSBuilder (command builder)
├── A4Engine (Win32 spooler + ReportLab PDF)
└── LabelEngine (ReportLab PDF + spooler)

All printing runs on QThreadPool worker threads.
Print failure never blocks data saving.
```

> **Design Note**: Printer implementation is **abstract**. ESC/POS commands target the standard command set, not XP-80 specific SDKs. Any ESC/POS-compatible thermal printer will work. Printer profiles in DB configure paper width, encoding, connection.

## ESC/POS Abstraction Layer

```python
class ESCPOSBuilder:
    # Initialize
    INIT = b'\x1b\x40'
    CUT = b'\x1d\x56\x00'
    PARTIAL_CUT = b'\x1d\x56\x01'
    
    # Alignment
    ALIGN_LEFT = b'\x1b\x61\x00'
    ALIGN_CENTER = b'\x1b\x61\x01'
    ALIGN_RIGHT = b'\x1b\x61\x02'
    
    # Text
    BOLD_ON = b'\x1b\x45\x01'
    BOLD_OFF = b'\x1b\x45\x00'
    DOUBLE_HEIGHT = b'\x1b\x21\x10'
    DOUBLE_WIDTH = b'\x1b\x21\x20'
    DOUBLE_HW = b'\x1b\x21\x30'
    NORMAL_SIZE = b'\x1b\x21\x00'
    
    # Cash drawer
    DRAWER_KICK = b'\x1b\x70\x00\x19\xfa'
    
    # Barcode
    BARCODE_TEXT_BELOW = b'\x1d\x48\x02'
    BARCODE_HEIGHT = b'\x1d\x68'      # + height byte
    BARCODE_WIDTH = b'\x1d\x77'       # + width byte
    BARCODE_CODE128 = b'\x1d\x6b\x49' # + length + data
    
    def __init__(self, paper_width=80, encoding='cp437'):
        self.paper_width = paper_width
        self.encoding = encoding
        self.char_width = 48 if paper_width == 80 else 32
        self.buffer = bytearray(self.INIT)
    
    def text(self, content):
        self.buffer.extend(content.encode(self.encoding, errors='replace'))
        return self
    
    def newline(self, count=1):
        self.buffer.extend(b'\n' * count)
        return self
    
    def separator(self, char='-'):
        return self.text(char * self.char_width).newline()
    
    def two_columns(self, left, right):
        space = max(1, self.char_width - len(left) - len(right))
        return self.text(left + ' ' * space + right).newline()
    
    def barcode(self, data):
        self.buffer.extend(self.BARCODE_TEXT_BELOW)
        self.buffer.extend(self.BARCODE_HEIGHT + bytes([60]))
        self.buffer.extend(self.BARCODE_WIDTH + bytes([2]))
        self.buffer.extend(self.BARCODE_CODE128 + bytes([len(data)]))
        self.buffer.extend(data.encode('ascii'))
        return self
    
    def open_drawer(self):
        self.buffer.extend(self.DRAWER_KICK)
        return self
    
    def cut(self):
        self.newline(3)
        self.buffer.extend(self.PARTIAL_CUT)
        return self
    
    def build(self):
        return bytes(self.buffer)
```

## Sending to Printer (Win32 Raw)

```python
import win32print

def send_raw_to_printer(printer_name: str, data: bytes):
    """Send raw ESC/POS bytes to printer via Windows spooler."""
    handle = win32print.OpenPrinter(printer_name)
    try:
        win32print.StartDocPrinter(handle, 1, ("Receipt", None, "RAW"))
        win32print.StartPagePrinter(handle)
        win32print.WritePrinter(handle, data)
        win32print.EndPagePrinter(handle)
        win32print.EndDocPrinter(handle)
    finally:
        win32print.ClosePrinter(handle)
```

## Print Queue (Threaded)

```python
class PrintJob(QRunnable):
    def __init__(self, job_id, printer_config, data):
        super().__init__()
        self.job_id = job_id
        self.config = printer_config
        self.data = data
        self.signals = PrintSignals()  # finished(str), error(str,str)
    
    def run(self):
        try:
            if self.config.printer_type == 'THERMAL':
                send_raw_to_printer(self.config.connection_string, self.data)
            elif self.config.printer_type == 'A4':
                # Save PDF to temp → print via ShellExecute
                pass
            self.signals.finished.emit(self.job_id)
        except Exception as e:
            self.signals.error.emit(self.job_id, str(e))

class PrintManager:
    def __init__(self):
        self.pool = QThreadPool()
        self.pool.setMaxThreadCount(2)
    
    def print_receipt(self, sale):
        printer = get_default_receipt_printer()
        data = ReceiptFormatter().format(sale, get_company_info(), printer)
        job = PrintJob(f"RCP-{sale.sale_number}", printer, data)
        job.signals.error.connect(self._on_error)
        self.pool.start(job)
```

**Error handling**: Notification on failure. Retry button. Max 3 retries. Sale never blocked.

## Printer Discovery

```python
def discover_printers():
    return [
        {'name': p[2], 'description': p[1]}
        for p in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        )
    ]
```

## A4 Document Templates (ReportLab)

| Document | Key Sections |
|---|---|
| Facture de Vente | Company header + Client + Items table + Totals + Payment |
| Facture d'Achat | Supplier + Items + Totals |
| Bon de Commande | Supplier + Ordered items + Terms |
| Bon de Livraison | Client + Delivery items + Signatures |
| Relevé de Compte | Entity + Transactions + Balance |
| Rapport de Caisse | Opening + Sales + Expenses + Closure |
| Rapports | Title + Filters + Data table + Charts |

## Label Templates (ReportLab)

| Template | Size | Contents |
|---|---|---|
| Small Barcode | 30×20mm | Barcode + Price |
| Medium | 40×30mm | Name + Barcode + Price |
| Large | 50×25mm | Name + Barcode + Price + Code |
| A4 Sheet | 210×297mm | Grid of labels (e.g., 3×8) |

---

# 11. REPORTING SYSTEM

## Sales Reports

**Ventes Journalières** — Filters: date, cashier, payment. Columns: Heure, Ticket, Client, Articles, Sous-total, Remise, TVA, Total, Paiement. Agg: total sales/discount/tax/grand total/count. Chart: hourly distribution.

**Ventes Hebdomadaires** — Weekly grouping. Daily trend line chart.

**Ventes Mensuelles** — Monthly with comparison %. Category pie chart.

**Ventes par Produit** — Date range, category. Qty sold, CA, marge brute, % CA. Top 20 bar chart.

**Ventes par Catégorie** — Category distribution pie.

**Ventes par Caissier** — Nb ventes, totals, avg per sale.

**Ventes Annulées** — Date, ticket, montant, raison, annulé par.

## Inventory Reports

**Stock Actuel** — Category filter. Code, produit, catégorie, stock, min, statut, valeur (qty×cost). Total stock value.

**Stock Faible** — Below minimum. Red=out, Orange=low.

**Produits Expirés** — Status filter. Lot, date, qty, valeur, jours restants.

**Historique Mouvements** — Product, type, date range. All movements.

## Financial Reports

**Chiffre d'Affaires** — Date grouping. CA Brut, Remises, CA Net, TVA, Coût, Marge, Marge%. Trend chart.

**Dépenses** — Category, date. Total by category. Pie chart.

**Résultat** — Revenue - COGS = Gross Profit - Expenses = Net Profit.

**Créances Clients** — Client, status, aging. Total outstanding. Aging stacked bar.

**Dettes Fournisseurs** — Same structure for suppliers.

**Historique Paiements** — Entity, date, method. All payments.

## Purchase Reports

**Achats Fournisseur** — Supplier, date, status. Total purchases/paid/outstanding.

**Historique Achats par Produit** — Date, supplier, qty, cost, total, lot, expiry.

## Delivery Reports

**Performance Livraisons** — Date, operator, status. Success rate, avg time.

**Livraisons Échouées** — Date, client, raison, replanifié oui/non.

## Cash Register Reports

**Sessions de Caisse** — Date, cashier. Opening, cash sales, card sales, expenses, expected, counted, variance. Red for variance > threshold.

## Report Engine

```python
class ReportGenerator:
    def generate(self, report_type, filters) -> pd.DataFrame:
        query = self._build_query(report_type, filters)
        return pd.read_sql(query, self.engine)
    
    def to_pdf(self, df, config, output_path):
        """ReportLab PDF with company branding, table, totals."""
        pass
    
    def to_excel(self, df, config, output_path):
        """OpenPyXL with styled header, auto-fit columns."""
        wb = Workbook()
        ws = wb.active
        ws.title = config.title
        # Header with green fill, white bold font
        # Data rows
        # Auto-fit columns
        wb.save(output_path)
    
    def to_chart(self, df, config):
        """matplotlib figure for embedding in QPixmap or PDF."""
        pass
```

## Performance

- All date columns indexed
- Pagination: 50 rows default (25/50/100/200 options)
- Reports > 1000 rows → QThreadPool worker
- Daily sales summary cached on first generation; invalidated on new sale
- Charts rendered only when visible (lazy)
