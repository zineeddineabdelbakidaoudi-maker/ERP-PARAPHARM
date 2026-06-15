from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Users Management Page
With checkbox-based permission management.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QFrame, QComboBox, QTabWidget, QScrollArea,
    QGridLayout, QCheckBox, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from app.core.database import get_session
from app.repositories.base_repository import BaseRepository
from app.models.user import User, Role, Permission
from app.services.auth_service import AuthService
from app.constants import RoleName


# ── Module / Action definitions ───────────────────────────────────

ALL_MODULES = [
    ("DASHBOARD", "Tableau de Bord"),
    ("POS", "Point de Vente (F1)"),
    ("PRODUCTS", "Produits"),
    ("CATEGORIES", "Catégories"),
    ("LABELS", "Étiquettes"),
    ("CLIENTS", "Clients"),
    ("DELIVERIES", "Bons de Livraison (BL)"),
    ("INVOICES", "Factures"),
    ("PREPARATIONS", "Commandes Client"),
    ("CREDIT_NOTES", "Avoirs Client"),
    ("RECLAMATIONS_CLIENT", "Réclamations Client"),
    ("EXPEDITIONS", "Expéditions"),
    ("DECHARGE", "Décharges"),
    ("ETAT_CREANCE", "État de Créance"),
    ("SUPPLIERS", "Fournisseurs"),
    ("FACTURES_FOURNISSEUR", "Factures Fournisseur"),
    ("PURCHASE_ORDERS", "Commandes Fournisseur"),
    ("PURCHASES", "Réceptions (BR)"),
    ("SUPPLIER_RETURNS", "Retours Fournisseur"),
    ("RECLAMATIONS_FOURNISSEUR", "Réclamations Fournisseur"),
    ("CASH_REGISTER", "Caisse (F12)"),
    ("DEBTS", "Créances / Dettes"),
    ("REPORTS", "Rapports & Dépenses"),
    ("BANK_ACCOUNTS", "Comptes Bancaires"),
    ("BANK_DEPOSITS", "Versements (Ctrl+F6)"),
    ("BANK_WITHDRAWALS", "Retraits Bancaires"),
    ("BANK_TRANSFERS", "Transferts Inter-Comptes"),
    ("BANK_STATEMENTS", "Relevés de Comptes"),
    ("STOCK", "État du Stock"),
    ("INVENTORY", "Inventaire"),
    ("VEHICLES", "Véhicules"),
    ("FACTURES_VENTE", "Factures Vente"),
    ("FACTURES_AVOIR", "Factures Avoir"),
    ("FACTURES_COMPL", "Factures Complémentaires"),
    ("FACTURES_ACHAT", "Factures Achat"),
    ("PRIX_FACTURATION", "Prix Facturation"),
    ("ATTACHEMENTS", "Attachements"),
    ("BORDEREAU_ENVOI", "Bordereau d'Envoi"),
    ("JOURNAL_VENTES", "Journal Ventes Facturées"),
    ("TVA_DECLARATION", "TVA & Fiscalité"),
    ("ETAT_104", "État 104"),
    ("ANNEXE_5", "Annexe 5"),
    ("DECLARATION_G50", "Déclaration G50"),
    ("DECLARATION_G12", "Déclaration G12"),
    ("DECLARATION_G12C", "G12 Complémentaire"),
    ("EXONERATION_TVA", "Exonération TVA"),
    ("CA_FISCAL", "CA Fiscal"),
    ("FICHE_CLIENT_FISCAL", "Fiche Client Fiscal"),
    ("RAPPEL_CLIENTS", "Rappels Clients"),
    ("AUDIT_LOG", "Historique des Actions (Audit)"),
    ("EXPIRATION", "Péremption"),
    ("USERS", "Utilisateurs"),
    ("SETTINGS", "Paramètres"),
    ("BACKUP", "Sauvegarde"),
    ("LOGS", "Journal Système"),
]

ALL_ACTIONS = [
    ("READ",   "Lire"),
    ("WRITE",  "Écrire"),
    ("DELETE",  "Supprimer"),
]

# ── Styles ────────────────────────────────────────────────────────

DIALOG_STYLE = """
QDialog {
    background-color: #2C3E50;
    color: #ECF0F1;
}
QTabWidget::pane {
    border: 1px solid #3E5063;
    border-radius: 6px;
    background-color: #2C3E50;
}
QTabBar::tab {
    background-color: #1B2631;
    color: #BDC3C7;
    padding: 10px 24px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-size: 13px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: #2C3E50;
    color: #FFFFFF;
    border-bottom: 2px solid #3498DB;
}
QTabBar::tab:hover:!selected {
    background-color: #34495E;
}
QLabel {
    color: #ECF0F1;
    font-size: 13px;
}
QLineEdit {
    background-color: #34495E;
    color: #ECF0F1;
    border: 1px solid #3E5063;
    border-radius: 4px;
    padding: 8px 10px;
    font-size: 13px;
}
QLineEdit:focus {
    border: 1px solid #3498DB;
}
QComboBox {
    background-color: #34495E;
    color: #ECF0F1;
    border: 1px solid #3E5063;
    border-radius: 4px;
    padding: 8px 10px;
    font-size: 13px;
}
QComboBox QAbstractItemView {
    background-color: #34495E;
    color: #ECF0F1;
    selection-background-color: #3498DB;
}
QPushButton {
    padding: 8px 18px;
    border-radius: 4px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#saveBtn {
    background-color: #27AE60;
    color: white;
    border: none;
}
QPushButton#saveBtn:hover {
    background-color: #2ECC71;
}
QPushButton#cancelBtn {
    background-color: #7F8C8D;
    color: white;
    border: none;
}
QPushButton#cancelBtn:hover {
    background-color: #95A5A6;
}
QPushButton#selectAllBtn, QPushButton#deselectAllBtn {
    background-color: #2980B9;
    color: white;
    border: none;
    padding: 6px 14px;
    font-size: 12px;
}
QPushButton#selectAllBtn:hover, QPushButton#deselectAllBtn:hover {
    background-color: #3498DB;
}
QPushButton#deselectAllBtn {
    background-color: #E74C3C;
}
QPushButton#deselectAllBtn:hover {
    background-color: #EC7063;
}
QCheckBox {
    color: #ECF0F1;
    spacing: 6px;
    font-size: 13px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 3px;
    border: 2px solid #5D6D7E;
    background-color: #34495E;
}
QCheckBox::indicator:checked {
    background-color: #27AE60;
    border-color: #27AE60;
}
QCheckBox::indicator:disabled {
    background-color: #5D6D7E;
    border-color: #5D6D7E;
}
QCheckBox::indicator:checked:disabled {
    background-color: #1E8449;
    border-color: #1E8449;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
"""

ROW_EVEN_BG = "#283747"
ROW_ODD_BG  = "#2C3E50"
HEADER_BG   = "#1B2631"


# ── Permission Panel Widget ──────────────────────────────────────

class PermissionPanel(QWidget):
    """A grid of checkboxes: rows=modules, columns=actions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checkboxes: dict[tuple[str, str], QCheckBox] = {}
        self._is_admin = False
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        # ── Toolbar: Select All / Deselect All ─────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.select_all_btn = QPushButton("✅ Tout Sélectionner")
        self.select_all_btn.setObjectName("selectAllBtn")
        self.select_all_btn.setCursor(Qt.PointingHandCursor)
        self.select_all_btn.clicked.connect(self._select_all)
        toolbar.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("❌ Tout Désélectionner")
        self.deselect_all_btn.setObjectName("deselectAllBtn")
        self.deselect_all_btn.setCursor(Qt.PointingHandCursor)
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        toolbar.addWidget(self.deselect_all_btn)

        toolbar.addStretch()

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #7F8C8D; font-size: 12px;")
        toolbar.addWidget(self.status_label)

        outer.addLayout(toolbar)

        # ── Scroll area for the grid ───────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background-color: transparent;")

        grid = QGridLayout(scroll_widget)
        grid.setSpacing(0)
        grid.setContentsMargins(0, 0, 0, 0)

        # Header row
        corner = QLabel("")
        corner.setFixedHeight(42)
        corner.setStyleSheet(
            f"background-color: {HEADER_BG}; padding: 8px 12px;"
            "font-weight: bold; font-size: 13px; color: #ECF0F1;"
            "border-bottom: 2px solid #3498DB;"
        )
        grid.addWidget(corner, 0, 0)

        for col_idx, (action_key, action_label) in enumerate(ALL_ACTIONS):
            hdr = QLabel(action_label)
            hdr.setAlignment(Qt.AlignCenter)
            hdr.setFixedHeight(42)
            hdr.setStyleSheet(
                f"background-color: {HEADER_BG}; padding: 8px 6px;"
                "font-weight: bold; font-size: 13px; color: #ECF0F1;"
                "border-bottom: 2px solid #3498DB;"
            )
            grid.addWidget(hdr, 0, col_idx + 1)

        # Data rows
        for row_idx, (mod_key, mod_label) in enumerate(ALL_MODULES):
            bg = ROW_EVEN_BG if row_idx % 2 == 0 else ROW_ODD_BG
            row_in_grid = row_idx + 1

            # Module label
            lbl = QLabel(f"  {mod_label}")
            lbl.setFixedHeight(38)
            lbl.setStyleSheet(
                f"background-color: {bg}; padding: 6px 12px;"
                "font-size: 13px; color: #ECF0F1; font-weight: 500;"
            )
            grid.addWidget(lbl, row_in_grid, 0)

            for col_idx, (action_key, _action_label) in enumerate(ALL_ACTIONS):
                cb = QCheckBox()
                cb.setStyleSheet(f"background-color: {bg}; padding: 6px 0px;")
                cb.stateChanged.connect(self._update_status)

                # Container to center the checkbox
                container = QWidget()
                container.setStyleSheet(f"background-color: {bg};")
                container_layout = QHBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setAlignment(Qt.AlignCenter)
                container_layout.addWidget(cb)
                container.setFixedHeight(38)

                grid.addWidget(container, row_in_grid, col_idx + 1)
                self._checkboxes[(mod_key, action_key)] = cb

        # Column stretch
        grid.setColumnStretch(0, 3)
        for i in range(len(ALL_ACTIONS)):
            grid.setColumnStretch(i + 1, 1)

        scroll.setWidget(scroll_widget)
        outer.addWidget(scroll)

        self._update_status()

    # ── Public API ─────────────────────────────────────────────

    def set_permissions(self, perm_set: set[tuple[str, str]]):
        """Load a set of (module, action) tuples and check matching boxes."""
        for (mod, act), cb in self._checkboxes.items():
            cb.setChecked((mod, act) in perm_set)
        self._update_status()

    def get_permissions(self) -> list[tuple[str, str, bool]]:
        """Return list of (module, action, is_allowed) for ALL checkboxes."""
        result = []
        for (mod, act), cb in self._checkboxes.items():
            result.append((mod, act, cb.isChecked()))
        return result

    def set_admin_mode(self, is_admin: bool):
        """If admin, check all and disable editing."""
        self._is_admin = is_admin
        for cb in self._checkboxes.values():
            if is_admin:
                cb.setChecked(True)
                cb.setEnabled(False)
            else:
                cb.setEnabled(True)
        self.select_all_btn.setEnabled(not is_admin)
        self.deselect_all_btn.setEnabled(not is_admin)
        self._update_status()

    # ── Slots ──────────────────────────────────────────────────

    def _select_all(self):
        for cb in self._checkboxes.values():
            if cb.isEnabled():
                cb.setChecked(True)

    def _deselect_all(self):
        for cb in self._checkboxes.values():
            if cb.isEnabled():
                cb.setChecked(False)

    def _update_status(self):
        total = len(self._checkboxes)
        checked = sum(1 for cb in self._checkboxes.values() if cb.isChecked())
        self.status_label.setText(f"{checked}/{total} permissions activées")


# ── User Dialog (with tabs) ──────────────────────────────────────

class UserDialog(QDialog):
    """Dialog to create or edit a user, with Informations + Permissions tabs."""

    def __init__(self, user_obj=None, parent=None):
        super().__init__(parent)
        self.user_obj = user_obj
        self.db_session = get_session()
        self.user_repo = BaseRepository(self.db_session, User)
        self.role_repo = BaseRepository(self.db_session, Role)

        self.setWindowTitle("Modifier l'Utilisateur" if user_obj else "Nouvel Utilisateur")
        self.setMinimumSize(680, 620)
        self.setStyleSheet(DIALOG_STYLE)
        self._setup_ui()

        if self.user_obj:
            self._load_data()

    # ── UI Setup ───────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Title
        title = QLabel(self.windowTitle())
        title_font = QFont()
        title_font.setPointSize(15)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ECF0F1; padding-bottom: 4px;")
        layout.addWidget(title)

        # ── Tab Widget ─────────────────────────────────────────
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Informations
        info_tab = QWidget()
        self._build_info_tab(info_tab)
        self.tabs.addTab(info_tab, "👤  Informations")

        # Tab 2: Permissions
        perm_tab = QWidget()
        self._build_perm_tab(perm_tab)
        self.tabs.addTab(perm_tab, "🔐  Permissions")

        # ── Bottom buttons ─────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 8, 0, 0)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("💾  Enregistrer")
        save_btn.setObjectName("saveBtn")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _build_info_tab(self, tab: QWidget):
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)
        layout.setContentsMargins(12, 16, 12, 12)

        form_frame = QFrame()
        form_frame.setStyleSheet(
            "QFrame { background-color: #34495E; border-radius: 8px; padding: 16px; }"
        )
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(14)
        form_layout.setLabelAlignment(Qt.AlignRight)

        self.fullname_input = QLineEdit()
        self.fullname_input.setPlaceholderText("Nom et prénom")
        form_layout.addRow("Nom Complet *", self.fullname_input)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Identifiant de connexion")
        form_layout.addRow("Nom d'Utilisateur *", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText(
            "Laisser vide pour ne pas changer" if self.user_obj else "Mot de passe requis"
        )
        label_pwd = "Mot de Passe" if self.user_obj else "Mot de Passe *"
        form_layout.addRow(label_pwd, self.password_input)

        self.pin_input = QLineEdit()
        self.pin_input.setMaxLength(4)
        self.pin_input.setPlaceholderText("4 chiffres (optionnel)")
        form_layout.addRow("Code PIN", self.pin_input)

        self.role_combo = SearchableComboBox()
        self._populate_roles()
        self.role_combo.currentIndexChanged.connect(self._on_role_changed)
        form_layout.addRow("Rôle *", self.role_combo)

        layout.addWidget(form_frame)
        layout.addStretch()

    def _build_perm_tab(self, tab: QWidget):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(8)

        hint = QLabel("Définissez les permissions pour le rôle de cet utilisateur.")
        hint.setStyleSheet("color: #95A5A6; font-size: 12px; padding-bottom: 4px;")
        layout.addWidget(hint)

        self.perm_panel = PermissionPanel()
        layout.addWidget(self.perm_panel)

        # Set initial admin mode based on current role selection
        self._on_role_changed()

    # ── Helpers ────────────────────────────────────────────────

    def _populate_roles(self):
        res = self.role_repo.get_all()
        roles = res.get("items", []) if isinstance(res, dict) else res
        for r in roles:
            self.role_combo.addItem(r.name, r.id)

    def _get_selected_role_name(self) -> str:
        idx = self.role_combo.currentIndex()
        if idx < 0:
            return ""
        return self.role_combo.currentText()

    def _on_role_changed(self):
        """Update permission panel when role changes."""
        if not hasattr(self, "perm_panel"):
            return

        role_name = self._get_selected_role_name()
        is_admin = role_name.upper() == RoleName.ADMIN.value

        # Load existing permissions for this role
        role_id = self.role_combo.currentData()
        if role_id:
            perms = (
                self.db_session.query(Permission)
                .filter(Permission.role_id == role_id, Permission.is_allowed == 1)
                .all()
            )
            perm_set = {(p.module, p.action) for p in perms}
        else:
            perm_set = set()

        self.perm_panel.set_admin_mode(False)  # temporarily enable to set values
        self.perm_panel.set_permissions(perm_set)
        self.perm_panel.set_admin_mode(is_admin)

    # ── Load existing data (edit mode) ─────────────────────────

    def _load_data(self):
        self.fullname_input.setText(self.user_obj.full_name)
        self.username_input.setText(self.user_obj.username)
        self.pin_input.setPlaceholderText("Laisser vide pour ne pas changer")

        # Set role combo
        for i in range(self.role_combo.count()):
            if self.role_combo.itemData(i) == self.user_obj.role_id:
                self.role_combo.setCurrentIndex(i)
                break

        # Permissions are loaded via _on_role_changed signal

    # ── Save ───────────────────────────────────────────────────

    def _on_save(self):
        full_name = self.fullname_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        role_id = self.role_combo.currentData()

        if not full_name or not username:
            QMessageBox.warning(self, "Erreur", "Le nom et le nom d'utilisateur sont obligatoires.")
            return

        if not self.user_obj and not password:
            QMessageBox.warning(self, "Erreur", "Le mot de passe est obligatoire pour un nouvel utilisateur.")
            return

        if not role_id:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un rôle.")
            return

        try:
            pin_raw = self.pin_input.text().strip()
            pin_hashed = AuthService.hash_pin(pin_raw) if pin_raw else None

            if self.user_obj:
                # ── Update existing user ───────────────────────
                self.user_obj.full_name = full_name
                self.user_obj.username = username
                self.user_obj.role_id = role_id
                if pin_raw:
                    self.user_obj.pin_code = pin_hashed
                if password:
                    self.user_obj.password_hash = AuthService.hash_password(password)
            else:
                # ── Create new user ────────────────────────────
                password_hash = AuthService.hash_password(password)
                self.user_repo.create(
                    full_name=full_name,
                    username=username,
                    password_hash=password_hash,
                    role_id=role_id,
                    pin_code=pin_hashed,
                )

            # ── Save permissions for the role ──────────────────
            self._save_permissions(role_id)

            self.user_repo.commit()
            self.accept()
        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Erreur système", str(e))

    def _save_permissions(self, role_id: int):
        """Persist permission checkboxes to the database for the given role."""
        role_name = self._get_selected_role_name()
        if role_name.upper() == RoleName.ADMIN.value:
            # Admin always has all permissions — ensure they exist
            self._ensure_admin_permissions(role_id)
            return

        # Get current state from the panel
        panel_perms = self.perm_panel.get_permissions()

        # Fetch existing permission records for this role
        existing = (
            self.db_session.query(Permission)
            .filter(Permission.role_id == role_id)
            .all()
        )
        existing_map: dict[tuple[str, str], Permission] = {
            (p.module, p.action): p for p in existing
        }

        for module, action, is_allowed in panel_perms:
            key = (module, action)
            if key in existing_map:
                # Update existing record
                existing_map[key].is_allowed = 1 if is_allowed else 0
            else:
                # Create new record
                new_perm = Permission(
                    role_id=role_id,
                    module=module,
                    action=action,
                    is_allowed=1 if is_allowed else 0,
                )
                self.db_session.add(new_perm)

    def _ensure_admin_permissions(self, role_id: int):
        """Make sure admin role has all permissions enabled."""
        existing = (
            self.db_session.query(Permission)
            .filter(Permission.role_id == role_id)
            .all()
        )
        existing_map = {(p.module, p.action): p for p in existing}

        for mod_key, _ in ALL_MODULES:
            for act_key, _ in ALL_ACTIONS:
                key = (mod_key, act_key)
                if key in existing_map:
                    existing_map[key].is_allowed = 1
                else:
                    self.db_session.add(Permission(
                        role_id=role_id,
                        module=mod_key,
                        action=act_key,
                        is_allowed=1,
                    ))


# ── Users Page ────────────────────────────────────────────────────

class UsersPage(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.user_repo = BaseRepository(self.db_session, User)
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher un utilisateur...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input)

        toolbar.addStretch()

        add_btn = QPushButton("➕ Nouvel Utilisateur")
        add_btn.clicked.connect(self._on_add_user)
        toolbar.addWidget(add_btn)

        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "Nom Complet", "Utilisateur", "Rôle", "Actif", "Actions"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 220)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

    def refresh_data(self, query: str = ""):
        self.table.setRowCount(0)

        res = self.user_repo.get_all()
        users = res.get("items", []) if isinstance(res, dict) else res

        if query:
            q = query.lower()
            users = [u for u in users if q in u.full_name.lower() or q in u.username.lower()]

        for u in users:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(u.full_name))
            self.table.setItem(row, 1, QTableWidgetItem(u.username))

            role_name = u.role.name if u.role else "—"
            self.table.setItem(row, 2, QTableWidgetItem(role_name))

            active_item = QTableWidgetItem("Oui" if u.is_active else "Non")
            active_item.setForeground(Qt.darkGreen if u.is_active else Qt.red)
            self.table.setItem(row, 3, active_item)

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 0, 4, 0)
            action_layout.setSpacing(4)

            edit_btn = QPushButton("✏️ Modifier")
            edit_btn.setProperty("variant", "icon-edit")
            edit_btn.clicked.connect(lambda checked, usr=u: self._on_edit_user(usr))
            action_layout.addWidget(edit_btn)

            del_btn = QPushButton("🗑️ Supprimer")
            del_btn.setProperty("variant", "icon-delete")
            del_btn.clicked.connect(lambda checked, usr=u: self._on_delete_user(usr))
            action_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 4, action_widget)

    def _on_search(self, text):
        self.refresh_data(text)

    def _on_add_user(self):
        dialog = UserDialog(parent=self)
        if dialog.exec():
            self.refresh_data(self.search_input.text())

    def _on_edit_user(self, user_obj):
        dialog = UserDialog(user_obj=user_obj, parent=self)
        if dialog.exec():
            self.refresh_data(self.search_input.text())

    def _on_delete_user(self, user_obj):
        if user_obj.id == self.user.id:
            QMessageBox.warning(self, "Erreur", "Vous ne pouvez pas supprimer votre propre compte.")
            return
        reply = QMessageBox.question(
            self, "Supprimer", f"Voulez-vous supprimer l'utilisateur {user_obj.full_name} ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.user_repo.soft_delete(user_obj.id)
            self.user_repo.commit()
            self.refresh_data(self.search_input.text())
