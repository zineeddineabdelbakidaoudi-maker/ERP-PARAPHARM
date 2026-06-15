"""
ParaFarm ERP — Login Window
Frameless login dialog with username/password authentication.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal
from PySide6.QtGui import QFont, QPixmap

from app.core.database import get_session
from app.services.auth_service import AuthService
from app.core.exceptions import AuthenticationError


class LoginWindow(QDialog):
    """Frameless login window."""

    login_successful = Signal(object)  # Emits User object

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ParaFarm ERP — Connexion")
        self.setFixedSize(440, 480)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self._setup_ui()
        self._drag_pos = None

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main card
        card = QFrame()
        card.setObjectName("loginCard")
        card.setStyleSheet("""
            #loginCard {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 32, 40, 32)
        card_layout.setSpacing(16)

        # Logo / App Name
        logo_label = QLabel("🏥")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setFont(QFont("Segoe UI Emoji", 40))
        card_layout.addWidget(logo_label)

        title = QLabel("ParaFarm ERP")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet("color: #1B5E20; margin-bottom: 4px;")
        card_layout.addWidget(title)

        subtitle = QLabel("Gestion de Pharmacie & Parapharmacie")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #757575; font-size: 12px; margin-bottom: 20px;")
        card_layout.addWidget(subtitle)

        # Username
        user_label = QLabel("Nom d'utilisateur")
        user_label.setStyleSheet("font-weight: 600; color: #424242; font-size: 13px;")
        card_layout.addWidget(user_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Entrez votre nom d'utilisateur")
        self.username_input.setMinimumHeight(40)
        self.username_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                background: #FAFAFA;
            }
            QLineEdit:focus {
                border: 2px solid #1B5E20;
                background: #FFFFFF;
            }
        """)
        card_layout.addWidget(self.username_input)

        # Password
        pass_label = QLabel("Mot de passe")
        pass_label.setStyleSheet("font-weight: 600; color: #424242; font-size: 13px;")
        card_layout.addWidget(pass_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Entrez votre mot de passe")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(40)
        self.password_input.setStyleSheet(self.username_input.styleSheet())
        card_layout.addWidget(self.password_input)

        # Error label (hidden by default)
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("""
            color: #C62828;
            font-size: 12px;
            font-weight: 500;
            padding: 4px;
        """)
        self.error_label.hide()
        card_layout.addWidget(self.error_label)

        card_layout.addSpacing(8)

        # Login button
        self.login_btn = QPushButton("Se Connecter")
        self.login_btn.setMinimumHeight(44)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #1B5E20;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2E7D32;
            }
            QPushButton:pressed {
                background-color: #0D3B14;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.login_btn.clicked.connect(self._on_login)
        card_layout.addWidget(self.login_btn)

        card_layout.addStretch()

        # Version
        version = QLabel("v1.0.0")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color: #BDBDBD; font-size: 11px;")
        card_layout.addWidget(version)

        layout.addWidget(card)

        # Keyboard shortcuts
        self.username_input.returnPressed.connect(lambda: self.password_input.setFocus())
        self.password_input.returnPressed.connect(self._on_login)

        # Focus
        self.username_input.setFocus()

    def _on_login(self):
        """Handle login button click."""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            self._show_error("Veuillez remplir tous les champs.")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Connexion...")

        try:
            session = get_session()
            auth = AuthService(session)
            user = auth.authenticate(username, password)

            self.error_label.hide()
            self.login_successful.emit(user)
            self.accept()

        except AuthenticationError as e:
            self._show_error(str(e))
        except Exception as e:
            self._show_error(f"Erreur système: {str(e)}")
        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Se Connecter")

    def _show_error(self, message: str):
        """Display error message."""
        self.error_label.setText(message)
        self.error_label.show()

    # ── Frameless window dragging ────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
