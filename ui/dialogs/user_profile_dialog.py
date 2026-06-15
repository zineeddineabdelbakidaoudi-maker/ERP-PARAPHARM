"""
ParaFarm ERP — User Profile Dialog
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFormLayout, QFrame
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.services.auth_service import AuthService
from app.core.exceptions import ValidationError

class UserProfileDialog(QDialog):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.auth_service = AuthService(self.db_session)
        self.setWindowTitle("Mon Profil")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel("Informations du Profil")
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        info_frame = QFrame()
        info_frame.setProperty("class", "card")
        info_layout = QFormLayout(info_frame)

        info_layout.addRow("Nom d'utilisateur:", QLabel(self.user.username))
        info_layout.addRow("Nom Complet:", QLabel(self.user.full_name))
        info_layout.addRow("Rôle:", QLabel(self.user.role.name if self.user.role else "—"))
        info_layout.addRow("Dernière Connexion:", QLabel(self.user.last_login or "Inconnue"))

        layout.addWidget(info_frame)

        pwd_title = QLabel("Changer le Mot de Passe")
        pwd_title.setProperty("class", "sectionTitle")
        layout.addWidget(pwd_title)

        pwd_frame = QFrame()
        pwd_frame.setProperty("class", "card")
        pwd_layout = QFormLayout(pwd_frame)

        self.old_pwd = QLineEdit()
        self.old_pwd.setEchoMode(QLineEdit.Password)
        pwd_layout.addRow("Ancien Mot de passe *", self.old_pwd)

        self.new_pwd = QLineEdit()
        self.new_pwd.setEchoMode(QLineEdit.Password)
        pwd_layout.addRow("Nouveau Mot de passe *", self.new_pwd)

        self.confirm_pwd = QLineEdit()
        self.confirm_pwd.setEchoMode(QLineEdit.Password)
        pwd_layout.addRow("Confirmer *", self.confirm_pwd)

        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setPlaceholderText("Optionnel (4 chiffres)")
        pwd_layout.addRow("Nouveau code PIN", self.pin_input)

        layout.addWidget(pwd_frame)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Fermer")
        cancel_btn.setProperty("variant", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Enregistrer")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _on_save(self):
        old_p = self.old_pwd.text()
        new_p = self.new_pwd.text()
        conf_p = self.confirm_pwd.text()
        new_pin = self.pin_input.text()

        if new_p or conf_p or old_p:
            if not old_p:
                QMessageBox.warning(self, "Erreur", "L'ancien mot de passe est requis.")
                return
            if new_p != conf_p:
                QMessageBox.warning(self, "Erreur", "Les nouveaux mots de passe ne correspondent pas.")
                return
            if len(new_p) < 6:
                QMessageBox.warning(self, "Erreur", "Le nouveau mot de passe doit contenir au moins 6 caractères.")
                return
                
            try:
                # Need to verify old password. We can use authenticate.
                user = self.auth_service.authenticate(self.user.username, old_p)
                if not user:
                    QMessageBox.warning(self, "Erreur", "Ancien mot de passe incorrect.")
                    return
            except Exception as e:
                QMessageBox.warning(self, "Erreur", "Ancien mot de passe incorrect.")
                return

        # Prepare update
        try:
            from app.core.security import get_password_hash
            from app.services.user_service import UserService
            user_svc = UserService(self.db_session)
            
            data = {}
            if new_p:
                data["hashed_password"] = get_password_hash(new_p)
            if new_pin:
                if len(new_pin) != 4 or not new_pin.isdigit():
                    QMessageBox.warning(self, "Erreur", "Le code PIN doit contenir exactement 4 chiffres.")
                    return
                data["pin_code"] = new_pin

            if data:
                user_svc.update_user(self.user.id, data)
                from app.services.audit_service import AuditService
                audit = AuditService(self.db_session)
                audit.log_action(self.user.id, "SECURITY", f"L'utilisateur {self.user.username} a modifié ses identifiants")
                QMessageBox.information(self, "Succès", "Profil mis à jour avec succès.")
                self.accept()
            else:
                self.accept()
                
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
