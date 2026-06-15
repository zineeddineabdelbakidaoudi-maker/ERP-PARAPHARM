"""
ParaFarm ERP — Main Window
QMainWindow with sidebar navigation and stacked content area.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTabWidget, QPushButton, QLabel, QFrame,
    QStatusBar, QSizePolicy, QScrollArea,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon, QAction

from app.services.auth_service import get_current_session, clear_session


# ── Sidebar Navigation Items ────────────────────────────
SIDEBAR_ITEMS = []

# ── Top Menu Items ─────────────────────────────────────────
MENU_ITEMS = {
    "Général": [
        ("dashboard",    "📊", "Tableau de Bord"),
        ("pos",          "🛒", "Point de Vente (F1)"),
    ],
    "Articles": [
        ("products",     "📦", "Produits"),
        ("categories",   "📂", "Catégories"),
        ("labels",       "🏷️", "Étiquettes"),
    ],
    "Ventes": [
        ("clients",      "👥", "Clients"),
        ("deliveries",   "🚚", "Bons de Livraison (BL)"),
        ("invoices",     "🧾", "Factures"),
        ("preparations", "📦", "Commandes Client"),
        ("credit_notes", "💸", "Avoirs Client"),
        ("reclamations_client", "⚠️", "Réclamations Client"),
        ("expeditions",  "🚛", "Expéditions"),
        ("decharge",     "📝", "Décharges"),
        ("etat_creance", "📊", "État de Créance"),
    ],
    "Achats": [
        ("suppliers",    "🏭", "Fournisseurs"),
        ("factures_fournisseur", "📥", "Factures Fournisseur"),
        ("purchase_orders","📋", "Commandes Fournisseur"),
        ("purchases",    "📦", "Réceptions (BR)"),
        ("supplier_returns","🔙", "Retours Fournisseur"),
        ("reclamations_fournisseur", "⚠️", "Réclamations Fournisseur"),
    ],
    "Finances": [
        ("cash_register","💵", "Caisse (F12)"),
        ("debts",        "💰", "Créances / Dettes"),
        ("reports",      "📈", "Rapports & Dépenses"),
        ("bank_accounts",   "🏦", "Comptes Bancaires"),
        ("bank_deposits",   "💳", "Versements (Ctrl+F6)"),
        ("bank_withdrawals","🏧", "Retraits Bancaires"),
        ("bank_transfers",  "🔄", "Transferts Inter-Comptes"),
        ("bank_statements", "📋", "Relevés de Comptes"),
    ],
    "Entrepôt": [
        ("stock",        "📦", "État du Stock"),
        ("lots",         "📅", "Lots & Péremptions"),
        ("inventory",    "📋", "Inventaire"),
        ("vehicles",     "🚚", "Véhicules"),
    ],
    "Facturation": [
        ("factures_vente",  "🧾", "Factures Vente"),
        ("factures_avoir",  "📝", "Factures Avoir"),
        ("factures_compl",  "📄", "Factures Complémentaires"),
        ("factures_achat",  "📥", "Factures Achat"),
        ("prix_facturation","💲", "Prix Facturation"),
        ("attachements",    "📎", "Attachements"),
        ("bordereau_envoi", "📨", "Bordereau d'Envoi"),
        ("journal_ventes",  "📒", "Journal Ventes Facturées"),
    ],
    "Fiscal": [
        ("tva_declaration", "📉", "TVA & Fiscalité"),
        ("etat_104",        "📋", "État 104"),
        ("annexe_5",        "📋", "Annexe 5"),
        ("declaration_g50", "📋", "Déclaration G50"),
        ("declaration_g12", "📋", "Déclaration G12"),
        ("declaration_g12c","📋", "G12 Complémentaire"),
        ("exoneration_tva", "📋", "Exonération TVA"),
        ("ca_fiscal",       "📊", "CA Fiscal"),
        ("fiche_client_fiscal","👤", "Fiche Client Fiscal"),
        ("rappel_clients",  "📧", "Rappels Clients"),
    ],
    "Options": [
        ("audit_log", "📖", "Historique des Actions (Audit)"),
    ],
    "Système": [
        ("expiration",   "⏰", "Péremption"),
        ("users",        "👤", "Utilisateurs"),
        ("settings",     "⚙️", "Paramètres"),
        ("backup",       "💾", "Sauvegarde"),
        ("logs",         "📝", "Journal Système"),
    ]
}


class MainWindow(QMainWindow):
    """Main application window with sidebar + content area."""

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("ParaFarm ERP — Gestion Pharmacie")
        self.setMinimumSize(1024, 768)
        self.showMaximized()

        self._sidebar_expanded = True
        self._sidebar_buttons = {}
        self._pages = {}

        self._setup_ui()
        self._setup_menubar()
        self._setup_statusbar()
        self._setup_shortcuts()

        # Navigate to dashboard
        self._navigate_to("dashboard")

    def _setup_shortcuts(self):
        from PySide6.QtGui import QShortcut, QKeySequence
        QShortcut(QKeySequence("Ctrl+F6"), self).activated.connect(
            lambda: self._navigate_to("bank_deposits")
        )

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # (Sidebar has been removed, all navigation is now in the top menu)

        # ── Content Area ─────────────────────────────────
        content_container = QVBoxLayout()
        content_container.setContentsMargins(0, 0, 0, 0)
        content_container.setSpacing(0)

        # Header
        self.header = QFrame()
        self.header.setObjectName("headerBar")
        self.header.setMinimumHeight(50)
        self.header.setMaximumHeight(50)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(16, 0, 16, 0)

        self.page_title = QLabel("Tableau de Bord")
        self.page_title.setObjectName("headerTitle")
        header_layout.addWidget(self.page_title)

        header_layout.addStretch()

        # Help (?) button
        help_btn = QPushButton("❓")
        help_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                font-size: 18px; padding: 4px 8px;
            }
            QPushButton:hover { background-color: #E3F2FD; border-radius: 4px; }
        """)
        help_btn.setCursor(Qt.PointingHandCursor)
        help_btn.clicked.connect(self._show_page_help)
        header_layout.addWidget(help_btn)

        # Notification bell placeholder
        notif_btn = QPushButton("🔔")
        notif_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                font-size: 18px; padding: 4px 8px;
            }
            QPushButton:hover { background-color: #E8F5E9; border-radius: 4px; }
        """)
        notif_btn.setCursor(Qt.PointingHandCursor)
        notif_btn.clicked.connect(self._open_notifications)
        header_layout.addWidget(notif_btn)
        
        # User details in header
        user_info_label = QLabel(f"👤 {self.user.full_name} ({self.user.role.name if self.user.role else '—'})")
        user_info_label.setStyleSheet("color: #37474F; font-size: 13px; font-weight: bold; margin-left: 15px;")
        header_layout.addWidget(user_info_label)
        
        profile_btn = QPushButton("⚙️ Profil")
        profile_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                font-size: 13px; font-weight: bold; padding: 4px 8px; color: #37474F;
            }
            QPushButton:hover { background-color: #ECEFF1; border-radius: 4px; }
        """)
        profile_btn.setCursor(Qt.PointingHandCursor)
        profile_btn.clicked.connect(self._open_profile)
        header_layout.addWidget(profile_btn)
        
        logout_btn = QPushButton("🚪 Déconnexion")
        logout_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                font-size: 13px; font-weight: bold; padding: 4px 8px; color: #D32F2F;
            }
            QPushButton:hover { background-color: #FFEBEE; border-radius: 4px; }
        """)
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.clicked.connect(self._logout)
        header_layout.addWidget(logout_btn)

        content_container.addWidget(self.header)

        # Tabbed content
        self.content_stack = QTabWidget()
        self.content_stack.setTabsClosable(True)
        self.content_stack.tabCloseRequested.connect(self._close_tab)
        self.content_stack.currentChanged.connect(self._on_tab_changed)
        
        # Style the tabs to look modern
        self.content_stack.setStyleSheet("""
            QTabWidget::pane { border: none; background: #F5F5F5; }
            QTabBar::tab {
                background: #E0E0E0;
                color: #424242;
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                color: #1B5E20;
                border-bottom: 2px solid #2E7D32;
            }
        """)
        content_container.addWidget(self.content_stack)

        content_widget = QWidget()
        content_widget.setLayout(content_container)
        main_layout.addWidget(content_widget)

    def _setup_statusbar(self):
        status = QStatusBar()
        self.setStatusBar(status)

        self.db_status = QLabel("🟢 Base de données connectée")
        status.addWidget(self.db_status)

        status.addPermanentWidget(QLabel(f"👤 {self.user.full_name}"))

        from datetime import datetime
        self.clock_label = QLabel(datetime.now().strftime("%H:%M"))
        status.addPermanentWidget(self.clock_label)

        # Update clock every minute
        from PySide6.QtCore import QTimer
        timer = QTimer(self)
        timer.timeout.connect(self._update_clock)
        timer.start(60000)

    def _update_clock(self):
        from datetime import datetime
        self.clock_label.setText(datetime.now().strftime("%H:%M"))

    def _navigate_to(self, page_key: str):
        """Navigate to a page by key, lazy-loading into a new tab if needed."""
        if page_key == "help_definitions":
            self._show_page_help(force_full=True)
            if "help_definitions" in self._sidebar_buttons:
                self._sidebar_buttons["help_definitions"].setChecked(False)
            return
            
        if page_key == "users" and (not self.user.role or self.user.role.name != "ADMIN"):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Accès Refusé", "Seul l'administrateur peut accéder à la gestion des utilisateurs.")
            return
            
        # Find the label for the tab
        tab_label = "Onglet"
        found = False
        for key, icon, label in SIDEBAR_ITEMS:
            if key == page_key:
                tab_label = f"{icon} {label}"
                self.page_title.setText(label)
                found = True
                break
                
        if not found:
            for cat, items in MENU_ITEMS.items():
                for key, icon, label in items:
                    if key == page_key:
                        tab_label = f"{icon} {label}"
                        self.page_title.setText(label)
                        found = True
                        break
                if found:
                    break

        # Check if tab already exists
        if page_key in self._pages:
            tab_widget = self._pages[page_key]
            index = self.content_stack.indexOf(tab_widget)
            if index != -1:
                self.content_stack.setCurrentIndex(index)
                return

        # Lazy-load page into a new tab
        page_widget = self._create_page(page_key)
        page_widget.setProperty("page_key", page_key) # Store key for tracking
        index = self.content_stack.addTab(page_widget, tab_label)
        self._pages[page_key] = page_widget
        
        # Disable close button for Dashboard
        if page_key == "dashboard":
            self.content_stack.tabBar().setTabButton(index, self.content_stack.tabBar().ButtonPosition.RightSide, None)

        self.content_stack.setCurrentIndex(index)

    def _close_tab(self, index):
        """Handle tab closing."""
        widget = self.content_stack.widget(index)
        page_key = widget.property("page_key")
        
        if page_key == "dashboard":
            return # Prevent closing dashboard
            
        self.content_stack.removeTab(index)
        if page_key in self._pages:
            del self._pages[page_key]
        widget.deleteLater()

    def _on_tab_changed(self, index):
        """Update the header and sidebar based on active tab."""
        if index == -1: return
        widget = self.content_stack.widget(index)
        page_key = widget.property("page_key")
        
        # Update header
        found = False
        for key, icon, label in SIDEBAR_ITEMS:
            if key == page_key:
                self.page_title.setText(label)
                found = True
                break
                
        if not found:
            for cat, items in MENU_ITEMS.items():
                for key, icon, label in items:
                    if key == page_key:
                        self.page_title.setText(label)
                        found = True
                        break
                if found:
                    break
                
        # Update sidebar highlighting
        for key, btn in self._sidebar_buttons.items():
            btn.setChecked(key == page_key)

    def _setup_menubar(self):
        menubar = self.menuBar()
        # Ensure it has a somewhat distinct styling matching the dark theme if needed
        # but native menubars usually follow OS. We can style it briefly.
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #1B2631;
                color: #ECEFF1;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 10px;
            }
            QMenuBar::item:selected {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QMenu {
                background-color: #2C3E50;
                color: #ECEFF1;
                border: 1px solid #1B2631;
            }
            QMenu::item:selected {
                background-color: #34495E;
            }
        """)

        from app.services.auth_service import get_current_session
        session = get_current_session()
        for cat, items in MENU_ITEMS.items():
            menu = menubar.addMenu(cat)
            for key, icon, label in items:
                module = key.upper()
                if not session.has_permission(module, "READ"):
                    continue
                action = QAction(f"{icon} {label}", self)
                action.triggered.connect(lambda checked=False, k=key: self._navigate_to(k))
                menu.addAction(action)
            # Hide menu category if it has no actions
            if menu.isEmpty():
                menu.menuAction().setVisible(False)

    def _create_page(self, page_key: str) -> QWidget:
        """Create a page widget based on the key."""
        if page_key == "dashboard":
            from ui.pages.dashboard_page import DashboardPage
            return DashboardPage(self.user)
        elif page_key == "products":
            from ui.pages.products_page import ProductsPage
            return ProductsPage(self.user)
        elif page_key == "categories":
            from ui.pages.categories_page import CategoriesPage
            return CategoriesPage(self.user)
        elif page_key == "pos":
            from ui.pages.pos_page import POSPage
            return POSPage(self.user)
        elif page_key == "cash_register":
            from ui.pages.cash_register_page import CashRegisterPage
            return CashRegisterPage(self.user)
        elif page_key == "debts":
            from ui.pages.debts_page import DebtsPage
            return DebtsPage(self.user)
        elif page_key == "clients":
            from ui.pages.clients_page import ClientsPage
            return ClientsPage(self.user)
        elif page_key == "suppliers":
            from ui.pages.suppliers_page import SuppliersPage
            return SuppliersPage(self.user)
        elif page_key == "stock":
            from ui.pages.stock_page import StockPage
            return StockPage(self.user)
        elif page_key == "tracabilite":
            from ui.pages.tracabilite_page import TracabilitePage
            return TracabilitePage(self.user)
        elif page_key == "purchases":
            from ui.pages.purchases_page import PurchasesPage
            return PurchasesPage(self.user)
        elif page_key == "deliveries":
            from ui.pages.deliveries_page import DeliveriesPage
            return DeliveriesPage(self.user)
        elif page_key == "labels":
            from ui.pages.labels_page import LabelsPage
            return LabelsPage(self.user)
        elif page_key == "expiration":
            from ui.pages.expiration_page import ExpirationPage
            return ExpirationPage(self.user)
        elif page_key == "reports":
            from ui.pages.reports_page import ReportsPage
            return ReportsPage(self.user)
        elif page_key == "report_builder":
            from ui.pages.report_builder_page import ReportBuilderPage
            return ReportBuilderPage(self.user)
        elif page_key == "users":
            from ui.pages.users_page import UsersPage
            return UsersPage(self.user)
        elif page_key == "settings":
            from ui.pages.settings_page import SettingsPage
            return SettingsPage(self.user)
        elif page_key == "backup":
            from ui.pages.backup_page import BackupPage
            return BackupPage(self.user)
        elif page_key == "factures_fournisseur":
            from ui.pages.factures_fournisseur_page import FacturesFournisseurPage
            return FacturesFournisseurPage(self.user)
        elif page_key == "tva_declaration":
            # Stub for now
            return QLabel("Module TVA & Fiscalité en cours de développement...")
        # ── Phase 2: New Document Pages ──────────────────────
        elif page_key == "preparations":
            from ui.pages.preparations_page import PreparationsPage
            return PreparationsPage(self.user)
        elif page_key == "invoices":
            from ui.pages.invoices_page import InvoicesPage
            return InvoicesPage(self.user)
        elif page_key == "credit_notes":
            from ui.pages.credit_notes_page import CreditNotesPage
            return CreditNotesPage(self.user)
        elif page_key == "reclamations_client":
            from ui.pages.reclamations_client_page import ReclamationsClientPage
            return ReclamationsClientPage(self.user)
        elif page_key == "expeditions":
            from ui.pages.expeditions_page import ExpeditionsPage
            return ExpeditionsPage(self.user)
        elif page_key == "decharge":
            from ui.pages.decharge_page import DechargePage
            return DechargePage(self.user)
        elif page_key == "etat_creance":
            from ui.pages.etat_creance_page import EtatCreancePage
            return EtatCreancePage(self.user)
        elif page_key == "reclamations_fournisseur":
            from ui.pages.reclamations_fournisseur_page import ReclamationsFournisseurPage
            return ReclamationsFournisseurPage(self.user)
        elif page_key == "supplier_returns":
            from ui.pages.supplier_returns_page import SupplierReturnsPage
            return SupplierReturnsPage(self.user)
        elif page_key == "tva_declaration":
            from ui.pages.tva_declaration_page import TvaDeclarationPage
            return TvaDeclarationPage(self.user)
        elif page_key == "purchase_orders":
            from ui.pages.purchase_orders_page import PurchaseOrdersPage
            return PurchaseOrdersPage(self.user)
        elif page_key == "supplier_returns":
            from ui.pages.supplier_returns_page import SupplierReturnsPage
            return SupplierReturnsPage(self.user)
        elif page_key == "warehouses":
            from ui.pages.warehouses_page import WarehousesPage
            return WarehousesPage(self.user)
        elif page_key == "inventory":
            from ui.pages.inventory_count_page import InventoryCountPage
            return InventoryCountPage(self.user)
        elif page_key == "lots":
            from ui.pages.lots_page import LotsPage
            return LotsPage(self.user)
        # ── Phase 3: Logistics ──────────────────
        elif page_key == "vehicles":
            from ui.pages.vehicles_page import VehiclesPage
            return VehiclesPage(self.user)
        elif page_key == "routes":
            from ui.pages.routes_page import RoutesPage
            return RoutesPage(self.user)
        # ── Phase 5: Banking Module ──────────────────────────
        elif page_key == "bank_accounts":
            from ui.pages.bank_accounts_page import ComptesBancairesPage
            return ComptesBancairesPage(self.user)
        elif page_key == "bank_deposits":
            from ui.pages.bank_deposits_page import VersementsBancairesPage
            return VersementsBancairesPage(self.user)
        elif page_key == "bank_withdrawals":
            from ui.pages.bank_withdrawals_page import RetraitsBancairesPage
            return RetraitsBancairesPage(self.user)
        elif page_key == "bank_transfers":
            from ui.pages.bank_transfers_page import TransfertInterComptesPage
            return TransfertInterComptesPage(self.user)
        elif page_key == "bank_statements":
            from ui.pages.bank_statements_page import RelevesComptesPage
            return RelevesComptesPage(self.user)
        # ── Facturation Module ───────────────────────────────
        elif page_key == "factures_vente":
            from ui.pages.fiscal_pages import JournalVentesFactureesPage
            return JournalVentesFactureesPage(self.user)
        elif page_key == "factures_avoir":
            from ui.pages.fiscal_pages import FacturesAvoirPage
            return FacturesAvoirPage(self.user)
        elif page_key == "factures_compl":
            from ui.pages.fiscal_pages import FacturesComplementairePage
            return FacturesComplementairePage(self.user)
        elif page_key == "factures_achat":
            from ui.pages.fiscal_pages import FacturesAchatPage
            return FacturesAchatPage(self.user)
        elif page_key == "prix_facturation":
            from ui.pages.fiscal_pages import PrixFacturationPage
            return PrixFacturationPage(self.user)
        elif page_key == "attachements":
            from ui.pages.fiscal_pages import AttachementsPage
            return AttachementsPage(self.user)
        elif page_key == "bordereau_envoi":
            from ui.pages.fiscal_pages import BordereauEnvoiPage
            return BordereauEnvoiPage(self.user)
        elif page_key == "journal_ventes":
            from ui.pages.fiscal_pages import JournalVentesFactureesPage
            return JournalVentesFactureesPage(self.user)
        # ── Fiscal Pages ─────────────────────────────────────
        elif page_key == "etat_104":
            from ui.pages.fiscal_pages import Etat104Page
            return Etat104Page(self.user)
        elif page_key == "annexe_5":
            from ui.pages.fiscal_pages import Annexe5Page
            return Annexe5Page(self.user)
        elif page_key == "declaration_g50":
            from ui.pages.fiscal_pages import DeclarationG50Page
            return DeclarationG50Page(self.user)
        elif page_key == "declaration_g12":
            from ui.pages.fiscal_pages import DeclarationG12Page
            return DeclarationG12Page(self.user)
        elif page_key == "declaration_g12c":
            from ui.pages.fiscal_pages import DeclarationG12ComplementairePage
            return DeclarationG12ComplementairePage(self.user)
        elif page_key == "exoneration_tva":
            from ui.pages.fiscal_pages import DemandesExonerationTVAPage
            return DemandesExonerationTVAPage(self.user)
        elif page_key == "ca_fiscal":
            from ui.pages.fiscal_pages import ChiffreAffaireFiscalPage
            return ChiffreAffaireFiscalPage(self.user)
        elif page_key == "fiche_client_fiscal":
            from ui.pages.fiscal_pages import FicheClientFiscalPage
            return FicheClientFiscalPage(self.user)
        elif page_key == "rappel_clients":
            from ui.pages.fiscal_pages import RappelConvocationClientsPage
            return RappelConvocationClientsPage(self.user)
        # ── Options Module ───────────────────────────────────
        elif page_key == "audit_log":
            from ui.pages.audit_log_page import AuditLogPage
            return AuditLogPage(self.user)
        # ── Additional Modules ───────────────────────────────
        elif page_key == "production":
            from ui.pages.additional_pages import ProductionPage
            return ProductionPage(self.user)
        elif page_key == "personnel":
            from ui.pages.additional_pages import PersonnelPage
            return PersonnelPage(self.user)
        elif page_key == "journal_comptable":
            from ui.pages.additional_pages import JournalComptablePage
            return JournalComptablePage(self.user)
        elif page_key == "statistiques":
            from ui.pages.additional_pages import StatistiquesPage
            return StatistiquesPage(self.user)
        # Placeholder pages — will be replaced with real implementations
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel(f"Page: {page_key}")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet("color: #1B5E20;")
        layout.addWidget(title)

        desc = QLabel("Cette page est en cours de développement...")
        desc.setStyleSheet("color: #757575; font-size: 14px;")
        layout.addWidget(desc)

        layout.addStretch()
        return page

    def _logout(self):
        """Logout and close the main window."""
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Déconnexion",
            "Êtes-vous sûr de vouloir vous déconnecter ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            clear_session()
            self.close()

    def _open_profile(self):
        from ui.dialogs.user_profile_dialog import UserProfileDialog
        dialog = UserProfileDialog(self.user, self)
        dialog.exec()

    def _open_notifications(self):
        from ui.dialogs.notifications_dialog import NotificationsDialog
        dialog = NotificationsDialog(self)
        dialog.exec()

    def _show_page_help(self, force_full=False):
        """Show definition help dialog depending on current page."""
        from PySide6.QtWidgets import QMessageBox
        
        page_key = "help_definitions" if force_full else None
        
        if not force_full:
            idx = self.content_stack.currentIndex()
            if idx != -1:
                page_key = self.content_stack.widget(idx).property("page_key")
                
        title = "Aide & Définitions"
        bl_text = "<b>Bon de Livraison (BL) — بون التسليم</b><br><br>C'est le document qui accompagne physiquement la marchandise livrée au client<br>• Il prouve que les produits ont quitté votre stock et ont été remis au client<br>• Il génère une dette client si le paiement est en 'Terme' (crédit)<br>• Il décrémente le stock immédiatement à la validation<br>• Il peut être converti en Facture officielle ultérieurement<br><i>Équivalent à : Delivery Note / Bon de sortie</i>"
        bc_text = "<b>Bon de Commande (BC) — بون الطلب</b><br><br>C'est le document qui enregistre l'intention d'achat ou de vente AVANT la livraison<br>• Pour client (BC Client) : le client réserve des produits — aucun stock touché, aucune dette créée<br>• Pour fournisseur (BC Fournisseur) : vous commandez auprès d'un fournisseur — aucun stock touché jusqu'à la réception<br>• Il devient un BL (côté vente) ou un BR (côté achat) quand la marchandise est effectivement livrée/reçue<br><i>Équivalent à : Purchase Order / Sales Order</i>"
        facture_text = "<b>Facture — فاتورة</b><br><br>C'est le document fiscal et légal officiel de la transaction<br>• Elle a une valeur juridique et fiscale — elle doit être déclarée à la DGI (TVA, IFU)<br>• Elle est émise APRÈS la livraison (souvent depuis un BL existant)<br>• Elle remplace la dette du BL (le BL est marqué 'ABSORBED_BY_INVOICE')<br>• Elle inclut obligatoirement : NIF, NIS, RC du vendeur ET de l'acheteur<br>• Elle apparaît dans l'État 104, G50, Annexe 5<br><i>Équivalent à : Invoice / Facture commerciale</i>"
        flux_text = "<b>Résumé du flux normal :</b><br>• BC Client → BL (livraison + dette) → Facture (officialisation fiscale)<br>• BC Fournisseur → BR (réception + dette fournisseur) → Facture Achat"
        
        if page_key in ["deliveries"]:
            help_text = f"{bl_text}<br><br>{flux_text}"
        elif page_key in ["purchase_orders", "preparations"]:
            help_text = f"{bc_text}<br><br>{flux_text}"
        elif page_key in ["invoices", "factures_vente", "factures_achat", "factures_avoir", "factures_compl"]:
            help_text = f"{facture_text}<br><br>{flux_text}"
        else:
            help_text = f"{bl_text}<br><br><hr><br>{bc_text}<br><br><hr><br>{facture_text}<br><br><hr><br>{flux_text}"
            
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(help_text)
        msg.setStyleSheet("QLabel { min-width: 500px; font-size: 13px; line-height: 1.5; }")
        msg.exec()
