"""
ParaFarm ERP — Backup Page
"""
import os
import shutil
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QMessageBox, QFrame, QFileDialog, QListWidget,
    QRadioButton, QComboBox, QCheckBox
)
from PySide6.QtCore import Qt
from app.config import config


class BackupPage(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_path = config.db_path
        self.backup_dir = config.backup_dir
        os.makedirs(self.backup_dir, exist_ok=True)
        self._setup_ui()
        self._load_backups()
        self._load_sync_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Info card
        info_frame = QFrame()
        info_frame.setProperty("class", "card")
        info_layout = QVBoxLayout(info_frame)

        info_label = QLabel(
            "Sauvegardez régulièrement votre base de données pour éviter toute perte de données.\n"
            "Les fichiers de sauvegarde sont stockés dans le dossier 'backups' du projet."
        )
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)

        db_path_label = QLabel(f"<b>Base de données :</b> {self.db_path}")
        db_path_label.setWordWrap(True)
        info_layout.addWidget(db_path_label)

        layout.addWidget(info_frame)

        # --- AUTO SYNC SETTINGS CARD ---
        sync_frame = QFrame()
        sync_frame.setStyleSheet("background-color: #2C3E50; border-radius: 8px; padding: 12px;")
        sync_layout = QVBoxLayout(sync_frame)
        
        sync_title = QLabel("☁️ Synchronisation Automatique (Cloud)")
        sync_title.setStyleSheet("color: #3498DB; font-weight: bold; font-size: 14px;")
        sync_layout.addWidget(sync_title)
        
        options_layout = QHBoxLayout()
        self.radio_local = QRadioButton("Local Uniquement")
        self.radio_drive = QRadioButton("Google Drive")
        self.radio_gmail = QRadioButton("Envoi par Gmail")
        options_layout.addWidget(self.radio_local)
        options_layout.addWidget(self.radio_drive)
        options_layout.addWidget(self.radio_gmail)
        options_layout.addStretch()
        sync_layout.addLayout(options_layout)
        
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Fréquence :"))
        self.sync_freq = QComboBox()
        self.sync_freq.addItems(["À la fermeture", "Chaque heure", "Chaque jour", "Manuelle"])
        freq_layout.addWidget(self.sync_freq)
        
        self.btn_save_sync = QPushButton("Enregistrer les préférences Sync")
        self.btn_save_sync.setStyleSheet("background-color: #2980B9; color: white; padding: 4px 12px; border-radius: 4px;")
        self.btn_save_sync.clicked.connect(self._save_sync_settings)
        freq_layout.addWidget(self.btn_save_sync)
        freq_layout.addStretch()
        sync_layout.addLayout(freq_layout)
        
        layout.addWidget(sync_frame)
        # -------------------------------

        # Actions
        actions_layout = QHBoxLayout()

        backup_btn = QPushButton("💾 Créer une Sauvegarde")
        backup_btn.clicked.connect(self._create_backup)
        actions_layout.addWidget(backup_btn)

        export_btn = QPushButton("📤 Exporter vers...")
        export_btn.setProperty("variant", "secondary")
        export_btn.clicked.connect(self._export_backup)
        actions_layout.addWidget(export_btn)

        restore_btn = QPushButton("⚠️ Restaurer")
        restore_btn.setProperty("variant", "danger")
        restore_btn.clicked.connect(self._restore_backup)
        actions_layout.addWidget(restore_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # Backup list
        list_label = QLabel("Sauvegardes Disponibles:")
        list_label.setProperty("class", "sectionTitle")
        layout.addWidget(list_label)

        self.backup_list = QListWidget()
        layout.addWidget(self.backup_list)

    def _load_sync_settings(self):
        import json
        settings_path = os.path.join(self.backup_dir, "sync_settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    st = json.load(f)
                    meth = st.get("method", "local")
                    if meth == "drive": self.radio_drive.setChecked(True)
                    elif meth == "gmail": self.radio_gmail.setChecked(True)
                    else: self.radio_local.setChecked(True)
                    
                    self.sync_freq.setCurrentText(st.get("frequency", "Manuelle"))
            except Exception:
                self.radio_local.setChecked(True)
        else:
            self.radio_local.setChecked(True)

    def _save_sync_settings(self):
        import json
        settings_path = os.path.join(self.backup_dir, "sync_settings.json")
        meth = "local"
        if self.radio_drive.isChecked(): meth = "drive"
        if self.radio_gmail.isChecked(): meth = "gmail"
        
        st = {
            "method": meth,
            "frequency": self.sync_freq.currentText()
        }
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=4)
        
        if meth != "local":
            QMessageBox.information(self, "Sync", "Préférences sauvegardées.\n\nNote: La synchronisation Cloud nécessite la configuration des API dans config.py.")
        else:
            QMessageBox.information(self, "Sync", "Préférences sauvegardées.")

    def _load_backups(self):
        self.backup_list.clear()
        if os.path.exists(self.backup_dir):
            files = sorted(
                [f for f in os.listdir(self.backup_dir) if f.endswith(".db")],
                reverse=True
            )
            for f in files:
                full_path = os.path.join(self.backup_dir, f)
                size_mb = os.path.getsize(full_path) / (1024 * 1024)
                self.backup_list.addItem(f"{f}  ({size_mb:.2f} MB)")

        if self.backup_list.count() == 0:
            self.backup_list.addItem("Aucune sauvegarde trouvée.")

    def _create_backup(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"parafarm_backup_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_name)
            shutil.copy2(self.db_path, backup_path)
            QMessageBox.information(self, "Succès", f"Sauvegarde créée :\n{backup_name}")
            self._load_backups()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de créer la sauvegarde :\n{e}")

    def _export_backup(self):
        dest = QFileDialog.getExistingDirectory(self, "Choisir le dossier de destination")
        if dest:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"parafarm_backup_{timestamp}.db"
                shutil.copy2(self.db_path, os.path.join(dest, backup_name))
                QMessageBox.information(self, "Succès", f"Base exportée vers :\n{os.path.join(dest, backup_name)}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def _restore_backup(self):
        item = self.backup_list.currentItem()
        if not item or "Aucune" in item.text():
            QMessageBox.warning(self, "Erreur", "Sélectionnez une sauvegarde à restaurer.")
            return

        backup_filename = item.text().split("  (")[0]
        backup_path = os.path.join(self.backup_dir, backup_filename)

        reply = QMessageBox.warning(
            self, "Attention",
            "⚠️ La restauration remplacera toutes les données actuelles !\n\n"
            f"Restaurer : {backup_filename} ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                # Create a safety backup first
                safety = os.path.join(self.backup_dir, f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
                shutil.copy2(self.db_path, safety)
                shutil.copy2(backup_path, self.db_path)
                QMessageBox.information(
                    self, "Succès",
                    "Base de données restaurée.\nRedémarrez l'application pour appliquer les changements."
                )
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))
