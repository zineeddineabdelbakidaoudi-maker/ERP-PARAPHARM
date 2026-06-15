# ParaFarm ERP — Master Implementation Plan

> **Project**: ParaFarm Desktop ERP — Pharmacy & Parapharmacy Management System  
> **Type**: Commercial-grade Desktop ERP  
> **Language**: French (UI), Python (codebase)  
> **Date**: 2026-05-14  

> [!IMPORTANT]
> This is the **master plan**. Detailed specifications are split across companion documents:
> - [01_modules.md](file:///C:/Users/pc%20gamer/Documents/desktop-illyes/docs/spec/01_modules.md) — Complete Module Breakdown
> - [02_database.md](file:///C:/Users/pc%20gamer/Documents/desktop-illyes/docs/spec/02_database.md) — Database Design
> - [03_screens_ui.md](file:///C:/Users/pc%20gamer/Documents/desktop-illyes/docs/spec/03_screens_ui.md) — Screen Map & UI/UX Design System
> - [04_workflows.md](file:///C:/Users/pc%20gamer/Documents/desktop-illyes/docs/spec/04_workflows.md) — POS, Purchase, Delivery, Debt Workflows
> - [05_printing_reports.md](file:///C:/Users/pc%20gamer/Documents/desktop-illyes/docs/spec/05_printing_reports.md) — Printing & Reporting Architecture
> - [06_security_ops.md](file:///C:/Users/pc%20gamer/Documents/desktop-illyes/docs/spec/06_security_ops.md) — Security, Backup, Performance, Roles

---

# 1. EXECUTIVE OVERVIEW

## 1.1 What the Application Is

ParaFarm ERP is a **professional desktop Enterprise Resource Planning** application purpose-built for **pharmacies and parapharmacies** operating in French-speaking markets (primarily Algeria / North Africa). It is a **single-station or multi-station** point-of-sale and back-office management system that unifies sales, purchasing, inventory, deliveries, debt tracking, treasury, reporting, and multi-format printing into a single cohesive desktop application.

## 1.2 Business Purpose

| Concern | Detail |
|---|---|
| **Industry** | Retail Pharmacy / Parapharmacy / Health & Beauty Retail |
| **Core Problem** | Pharmacies need integrated management of regulated products, expiration tracking, supplier debts, client credit, thermal receipt printing, barcode labeling, and financial reporting — all in a fast, offline-capable desktop environment |
| **Value Proposition** | Replace fragmented Excel/paper workflows with a single ERP covering POS → Inventory → Purchasing → Delivery → Accounting → Reporting |

## 1.3 Main Business Operations

1. **Point-of-Sale (POS)** — Fast barcode-driven sales with thermal receipt printing
2. **Purchasing** — Supplier order management, receiving, cost tracking, supplier debt
3. **Inventory** — Real-time stock with expiration tracking, low-stock alerts, batch management
4. **Deliveries (Livraison)** — Delivery note generation, status tracking, route management
5. **Debt Management** — Client & supplier credit/debit ledgers with aging analysis
6. **Treasury / Cash Register** — Daily cash balancing, expense tracking, payment reconciliation
7. **Reporting & Analytics** — Sales, inventory, financial, and operational reports
8. **Document Generation** — Invoices, receipts, delivery notes, labels, statements
9. **Product Labeling** — Barcode/price label generation for shelf and product marking

## 1.4 Target Users

| Role | Description |
|---|---|
| **Owner / Admin** | Full system access, configuration, financial oversight |
| **Cashier (Caissier/ère)** | POS operations, receipt printing, basic client lookup |
| **Inventory Manager (Gestionnaire Stock)** | Stock adjustments, receiving, expiration management |
| **Accountant (Comptable)** | Financial reports, debt management, treasury oversight |
| **Delivery Operator (Livreur)** | Delivery assignment, status updates, route management |
| **Supervisor** | Overrides, void authorizations, report access |

## 1.5 ERP Category

**Vertical ERP** — Pharmacy/Parapharmacy Retail, with modules for:
- Retail POS
- Supply Chain (Purchase → Receive → Stock)
- Distribution (Delivery/Livraison)
- Financial Management (Debts, Treasury, Expenses)
- Compliance (Expiration tracking, audit trails)

## 1.6 Desktop Architecture Type

**Rich Client Desktop Application** — Single-process Python application with:
- Native window management via Qt framework
- Embedded local database (SQLite) with optional PostgreSQL upgrade
- Direct hardware integration (thermal printers, barcode scanners, cash drawers)
- Offline-first operation with optional cloud backup

---

# 2. GLOBAL SOFTWARE ARCHITECTURE

## 2.1 Architecture Pattern

**Layered Architecture with Service-Oriented Modules**

```
┌──────────────────────────────────────────────────┐
│                 PRESENTATION LAYER                │
│         PySide6 / Qt Widgets + QSS Styling        │
├──────────────────────────────────────────────────┤
│               APPLICATION LAYER                   │
│     Controllers / ViewModels / Use Cases          │
├──────────────────────────────────────────────────┤
│                SERVICE LAYER                      │
│   Business Logic Services (Sales, Stock, etc.)    │
├──────────────────────────────────────────────────┤
│              DATA ACCESS LAYER                    │
│       SQLAlchemy ORM / Repository Pattern         │
├──────────────────────────────────────────────────┤
│                  DATABASE                         │
│           SQLite (local) / PostgreSQL             │
└──────────────────────────────────────────────────┘
         ↕               ↕              ↕
   [Printer Engine] [Report Engine] [Export Engine]
```

## 2.2 Project Structure

```
parafarm_erp/
├── main.py                          # Application entry point
├── app/
│   ├── __init__.py
│   ├── config.py                    # App configuration & settings loader
│   ├── constants.py                 # Global constants & enums
│   │
│   ├── core/                        # Core infrastructure
│   │   ├── database.py              # DB engine, session factory
│   │   ├── base_model.py            # SQLAlchemy declarative base + mixins
│   │   ├── event_bus.py             # Application-wide event system
│   │   ├── exceptions.py            # Custom exception hierarchy
│   │   ├── logger.py                # Logging configuration
│   │   └── security.py             # Auth, hashing, session management
│   │
│   ├── models/                      # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── category.py
│   │   ├── client.py
│   │   ├── supplier.py
│   │   ├── sale.py
│   │   ├── purchase.py
│   │   ├── delivery.py
│   │   ├── stock.py
│   │   ├── debt.py
│   │   ├── payment.py
│   │   ├── cash_register.py
│   │   ├── expense.py
│   │   ├── printer_config.py
│   │   ├── setting.py
│   │   ├── notification.py
│   │   ├── audit_log.py
│   │   └── barcode.py
│   │
│   ├── repositories/                # Data access repositories
│   │   ├── base_repository.py       # Generic CRUD repository
│   │   ├── product_repository.py
│   │   ├── sale_repository.py
│   │   ├── purchase_repository.py
│   │   ├── stock_repository.py
│   │   ├── client_repository.py
│   │   ├── supplier_repository.py
│   │   ├── delivery_repository.py
│   │   ├── debt_repository.py
│   │   └── ...
│   │
│   ├── services/                    # Business logic services
│   │   ├── auth_service.py
│   │   ├── product_service.py
│   │   ├── sale_service.py
│   │   ├── purchase_service.py
│   │   ├── stock_service.py
│   │   ├── delivery_service.py
│   │   ├── debt_service.py
│   │   ├── cash_register_service.py
│   │   ├── report_service.py
│   │   ├── backup_service.py
│   │   ├── notification_service.py
│   │   └── expiration_service.py
│   │
│   ├── printing/                    # Printing subsystem
│   │   ├── print_manager.py         # Central print orchestrator
│   │   ├── thermal_printer.py       # ESC/POS thermal printing
│   │   ├── a4_printer.py            # A4 document printing
│   │   ├── label_printer.py         # Barcode/price label printing
│   │   ├── templates/               # Print templates (receipt, invoice, etc.)
│   │   │   ├── receipt_template.py
│   │   │   ├── invoice_template.py
│   │   │   ├── delivery_note_template.py
│   │   │   ├── label_template.py
│   │   │   └── report_template.py
│   │   └── escpos_commands.py       # ESC/POS command builder
│   │
│   ├── reports/                     # Reporting subsystem
│   │   ├── report_generator.py      # Base report generator
│   │   ├── sales_reports.py
│   │   ├── inventory_reports.py
│   │   ├── financial_reports.py
│   │   ├── purchase_reports.py
│   │   ├── delivery_reports.py
│   │   └── charts.py               # Chart generation (matplotlib)
│   │
│   ├── export/                      # Export subsystem
│   │   ├── pdf_exporter.py          # ReportLab PDF generation
│   │   ├── excel_exporter.py        # OpenPyXL Excel export
│   │   └── csv_exporter.py
│   │
│   └── utils/                       # Utilities
│       ├── formatters.py            # Currency, date, number formatting
│       ├── validators.py            # Input validation helpers
│       ├── barcode_generator.py     # Barcode/QR generation
│       └── helpers.py
│
├── ui/                              # Presentation layer
│   ├── __init__.py
│   ├── main_window.py               # Main application window
│   ├── login_window.py              # Login screen
│   ├── styles/
│   │   ├── theme.qss                # Master QSS stylesheet
│   │   ├── colors.py                # Color palette constants
│   │   └── fonts.py                 # Font configuration
│   │
│   ├── components/                  # Reusable UI components
│   │   ├── sidebar.py               # Navigation sidebar
│   │   ├── header_bar.py            # Top header bar
│   │   ├── data_table.py            # Generic sortable/filterable table
│   │   ├── search_bar.py            # Universal search widget
│   │   ├── filter_panel.py          # Multi-criteria filter panel
│   │   ├── stat_card.py             # Dashboard statistic card
│   │   ├── chart_widget.py          # Embeddable chart widget
│   │   ├── notification_bell.py     # Notification indicator
│   │   ├── pagination.py            # Pagination controls
│   │   ├── confirm_dialog.py        # Confirmation dialog
│   │   ├── toast.py                 # Toast notification
│   │   └── loading_spinner.py       # Loading indicator
│   │
│   ├── pages/                       # Application pages
│   │   ├── dashboard_page.py
│   │   ├── pos_page.py              # POS / Sales screen
│   │   ├── products_page.py         # Product management
│   │   ├── categories_page.py
│   │   ├── clients_page.py
│   │   ├── suppliers_page.py
│   │   ├── purchases_page.py
│   │   ├── deliveries_page.py
│   │   ├── stock_page.py
│   │   ├── debt_page.py
│   │   ├── cash_register_page.py
│   │   ├── reports_page.py
│   │   ├── labels_page.py
│   │   ├── users_page.py
│   │   ├── settings_page.py
│   │   ├── printer_config_page.py
│   │   ├── backup_page.py
│   │   ├── expiration_page.py
│   │   └── logs_page.py
│   │
│   └── dialogs/                     # Modal dialogs
│       ├── product_dialog.py
│       ├── client_dialog.py
│       ├── supplier_dialog.py
│       ├── payment_dialog.py
│       ├── sale_detail_dialog.py
│       ├── purchase_dialog.py
│       ├── delivery_dialog.py
│       ├── stock_adjust_dialog.py
│       ├── expense_dialog.py
│       ├── user_dialog.py
│       ├── print_preview_dialog.py
│       └── about_dialog.py
│
├── resources/                       # Static resources
│   ├── icons/                       # SVG/PNG icons
│   ├── images/                      # Logos, backgrounds
│   ├── fonts/                       # Bundled fonts
│   └── translations/               # i18n files (French primary)
│
├── migrations/                      # Alembic database migrations
│   ├── env.py
│   └── versions/
│
├── tests/                           # Test suite
│   ├── test_services/
│   ├── test_repositories/
│   ├── test_models/
│   └── test_ui/
│
├── scripts/
│   ├── seed_data.py                 # Demo/seed data
│   └── build.py                     # PyInstaller build script
│
├── backups/                         # Local backup storage
├── logs/                            # Application logs
├── requirements.txt
├── pyproject.toml
├── alembic.ini
└── README.md
```

## 2.3 Mandatory Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Desktop UI** | PySide6 (Qt 6) | Native desktop widgets, tables, charts |
| **Styling** | QSS (Qt Style Sheets) | Professional ERP theming |
| **ORM** | SQLAlchemy 2.0 | Database abstraction, model definitions |
| **Database** | SQLite (default) / PostgreSQL (enterprise) | Data persistence |
| **Migrations** | Alembic | Schema versioning & migrations |
| **PDF Generation** | ReportLab | Invoices, reports, delivery notes |
| **Excel Export** | OpenPyXL | Spreadsheet report exports |
| **Data Analysis** | Pandas | Report aggregation & analysis |
| **Barcode** | python-barcode + qrcode | EAN-13, Code128, QR code generation |
| **Thermal Printing** | python-escpos / custom ESC/POS | XPrinter receipt printing |
| **Charts** | matplotlib | Dashboard & report charts |
| **Password Hashing** | bcrypt | Secure credential storage |
| **Logging** | Python logging + rotating file handler | Audit & debug logs |
| **Packaging** | PyInstaller | Windows .exe distribution |
| **Icons** | QtAwesome / custom SVG | UI iconography |

## 2.4 Architecture Requirements

| Requirement | Implementation |
|---|---|
| **Modular** | Each business domain is an independent module with its own models, services, repositories, and UI pages |
| **Scalable** | Repository pattern allows swapping SQLite → PostgreSQL without touching business logic |
| **Offline-first** | SQLite embedded DB; no network dependency for core operations |
| **Fast startup** | Lazy-load pages; precompile QSS; connection pooling |
| **Multi-window** | Qt's QMdiArea or detachable QDockWidgets for simultaneous views |
| **Multi-printer** | Printer profiles with named configurations; concurrent print queues via QThreadPool |
| **Thread-safe** | All DB operations via scoped sessions; print jobs on worker threads; UI updates via Qt signals |

---

# 20. FINAL DEVELOPMENT ROADMAP

## Phase 1 — MVP (Weeks 1–6)

| Week | Deliverable | Priority |
|---|---|---|
| 1 | Project scaffold, DB models, migrations, login screen | P0 |
| 2 | Product management CRUD, category management, barcode generation | P0 |
| 3 | POS / Sales screen — barcode scan, cart, payment, receipt printing | P0 |
| 4 | Inventory management, stock movements, low-stock alerts | P0 |
| 5 | Client & Supplier management, basic debt tracking | P0 |
| 6 | Cash register, daily closure, basic sales reports | P0 |

**MVP Outcome**: Operational POS with inventory, basic purchasing, receipt printing.

## Phase 2 — Core ERP (Weeks 7–12)

| Week | Deliverable | Priority |
|---|---|---|
| 7 | Purchase workflow — orders, receiving, supplier invoices | P1 |
| 8 | Delivery module — notes, status tracking, route management | P1 |
| 9 | Debt management — aging, statements, partial payments | P1 |
| 10 | Full reporting suite — sales, inventory, financial reports | P1 |
| 11 | Label printing, A4 invoice templates, print queue management | P1 |
| 12 | Dashboard with charts, analytics widgets, notifications | P1 |

**Phase 2 Outcome**: Full-featured pharmacy ERP with all core modules.

## Phase 3 — Enterprise (Weeks 13–18)

| Week | Deliverable | Priority |
|---|---|---|
| 13 | Role & permission system, multi-user management | P2 |
| 14 | Expiration tracking, batch management, compliance alerts | P2 |
| 15 | Backup/restore system, audit logs, security hardening | P2 |
| 16 | Advanced reports, custom report builder, chart exports | P2 |
| 17 | Performance optimization, caching, lazy loading | P2 |
| 18 | PyInstaller packaging, installer, documentation | P2 |

**Phase 3 Outcome**: Production-ready, enterprise-grade pharmacy ERP.

---

## User Review Required

> [!IMPORTANT]
> **Architecture Decisions Needing Confirmation:**
> 1. **Database**: SQLite (single-station) vs PostgreSQL (multi-station) — which is the primary target?
> 2. **UI Framework**: PySide6 (LGPL, commercial-friendly) vs PyQt6 (GPL) — PySide6 is recommended for commercial use.
> 3. **Language**: French-only UI, or should we build with i18n support for Arabic/English from the start?
> 4. **Video Reference**: No video file was attached to this conversation. The specification is built from the detailed requirements you provided. If you can share the video, I can refine screen-specific details.

## Open Questions

> [!WARNING]
> 1. Is multi-station (network) operation required in MVP, or is single-station sufficient?
> 2. Are there specific Algerian tax/regulatory requirements (e.g., TVA rates, fiscal stamp) to embed?
> 3. Should the system support Arabic text on thermal receipts (RTL ESC/POS)?
> 4. Is cloud backup a requirement, or local-only backup?
> 5. Do you have specific XPrinter models to target (e.g., XP-58, XP-80)?

## Verification Plan

### Automated Tests
- Unit tests for all service layer business logic
- Integration tests for repository layer against test database
- UI smoke tests using pytest-qt

### Manual Verification
- End-to-end POS workflow testing with barcode scanner
- Thermal print output verification on XPrinter hardware
- A4 print template visual inspection
- Daily closure and cash balancing accuracy testing
