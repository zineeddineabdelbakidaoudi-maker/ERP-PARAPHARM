import re

with open('ui/pages/deliveries_page.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_func = """    def _show_delivery_history(self):
        \"\"\"Show recent BL history for the selected client or all BLs.\"\"\"
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QWidget, QHBoxLayout
        
        client_id = self.selected_client.id if self.selected_client else None
        query = self.db_session.query(Delivery).order_by(Delivery.id.desc())
        if client_id:
            query = query.filter(Delivery.client_id == client_id)
            
        deliveries = query.limit(50).all()
        
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Historique BL — {self.selected_client.name if self.selected_client else 'Tous les clients'}")
        dlg.setMinimumSize(850, 450)
        
        layout = QVBoxLayout(dlg)
        
        tbl = QTableWidget(len(deliveries), 5)
        tbl.setHorizontalHeaderLabels(["N° BL", "Date", "Client", "Statut", "Actions"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        for col in range(4):
            tbl.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        tbl.setColumnWidth(4, 280)
        tbl.verticalHeader().setVisible(False)
        tbl.verticalHeader().setDefaultSectionSize(48)
        
        for i, d in enumerate(deliveries):
            tbl.setItem(i, 0, QTableWidgetItem(d.delivery_number))
            tbl.setItem(i, 1, QTableWidgetItem(d.scheduled_date or "—"))
            tbl.setItem(i, 2, QTableWidgetItem(d.client.name if d.client else "—"))
            tbl.setItem(i, 3, QTableWidgetItem(d.status or "—"))
            
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(6)
            
            # Copy btn
            copy_btn = QPushButton("📋 Copier")
            copy_btn.setStyleSheet("background-color: #F39C12; color: white; padding: 4px 8px; font-size: 11px; border-radius: 3px; font-weight: bold; min-height: 28px; max-height: 28px;")
            copy_btn.setMinimumWidth(75)
            copy_btn.clicked.connect(lambda checked, delivery=d: (
                self._apply_copy_from_delivery(delivery),
                dlg.accept()
            ))
            actions_layout.addWidget(copy_btn)
            
            # View btn
            view_btn = QPushButton("👁️ Voir")
            view_btn.setStyleSheet("background-color: #2980B9; color: white; padding: 4px 8px; font-size: 11px; border-radius: 3px; font-weight: bold; min-height: 28px; max-height: 28px;")
            view_btn.setMinimumWidth(65)
            view_btn.clicked.connect(lambda checked, delivery=d: self._view_saved_delivery(delivery))
            actions_layout.addWidget(view_btn)
            
            # Print btn
            print_btn = QPushButton("🖨️ Imprimer")
            print_btn.setStyleSheet("background-color: #27AE60; color: white; padding: 4px 8px; font-size: 11px; border-radius: 3px; font-weight: bold; min-height: 28px; max-height: 28px;")
            print_btn.setMinimumWidth(85)
            print_btn.clicked.connect(lambda checked, delivery=d: self._print_saved_delivery(delivery))
            actions_layout.addWidget(print_btn)
            
            tbl.setCellWidget(i, 4, actions_widget)
            
        layout.addWidget(tbl)
        
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(dlg.reject)
        layout.addWidget(close_btn)
        
        dlg.exec()"""

new_func = """    def _show_delivery_history(self):
        \"\"\"Show recent BL history for the selected client or all BLs.\"\"\"
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QWidget, QHBoxLayout
        from app.models.sale import Sale
        
        client_id = self.selected_client.id if self.selected_client else None
        query = self.db_session.query(Delivery).order_by(Delivery.id.desc())
        if client_id:
            query = query.filter(Delivery.client_id == client_id)
            
        deliveries = query.limit(50).all()
        
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Historique BL — {self.selected_client.name if self.selected_client else 'Tous les clients'}")
        dlg.setMinimumSize(950, 450)
        
        layout = QVBoxLayout(dlg)
        
        tbl = QTableWidget(len(deliveries), 6)
        tbl.setHorizontalHeaderLabels(["N° BL", "Date", "Client", "Statut", "Créateur", "Actions"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        for col in range(5):
            tbl.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        tbl.setColumnWidth(5, 280)
        tbl.verticalHeader().setVisible(False)
        tbl.verticalHeader().setDefaultSectionSize(48)
        
        for i, d in enumerate(deliveries):
            tbl.setItem(i, 0, QTableWidgetItem(d.delivery_number))
            tbl.setItem(i, 1, QTableWidgetItem(d.scheduled_date or "—"))
            tbl.setItem(i, 2, QTableWidgetItem(d.client.name if d.client else "—"))
            tbl.setItem(i, 3, QTableWidgetItem(d.status or "—"))
            
            # Fetch creator name from Sale
            creator_name = "—"
            if d.sale_id:
                sale = self.db_session.query(Sale).get(d.sale_id)
                if sale and sale.user:
                    creator_name = sale.user.full_name or sale.user.username
            tbl.setItem(i, 4, QTableWidgetItem(creator_name))
            
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(6)
            
            # Copy btn
            copy_btn = QPushButton("📋 Copier")
            copy_btn.setStyleSheet("background-color: #F39C12; color: white; padding: 4px 8px; font-size: 11px; border-radius: 3px; font-weight: bold; min-height: 28px; max-height: 28px;")
            copy_btn.setMinimumWidth(75)
            copy_btn.clicked.connect(lambda checked, delivery=d: (
                self._apply_copy_from_delivery(delivery),
                dlg.accept()
            ))
            actions_layout.addWidget(copy_btn)
            
            # View btn
            view_btn = QPushButton("👁️ Voir")
            view_btn.setStyleSheet("background-color: #2980B9; color: white; padding: 4px 8px; font-size: 11px; border-radius: 3px; font-weight: bold; min-height: 28px; max-height: 28px;")
            view_btn.setMinimumWidth(65)
            view_btn.clicked.connect(lambda checked, delivery=d: self._view_saved_delivery(delivery))
            actions_layout.addWidget(view_btn)
            
            # Print btn
            print_btn = QPushButton("🖨️ Imprimer")
            print_btn.setStyleSheet("background-color: #27AE60; color: white; padding: 4px 8px; font-size: 11px; border-radius: 3px; font-weight: bold; min-height: 28px; max-height: 28px;")
            print_btn.setMinimumWidth(85)
            print_btn.clicked.connect(lambda checked, delivery=d: self._print_saved_delivery(delivery))
            actions_layout.addWidget(print_btn)
            
            tbl.setCellWidget(i, 5, actions_widget)
            
        layout.addWidget(tbl)
        
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(dlg.reject)
        layout.addWidget(close_btn)
        
        dlg.exec()"""

if old_func in text:
    text = text.replace(old_func, new_func)
else:
    print("WARNING: Could not find exact old_func match")
    # Will try regex substitution instead if exact match fails
    text = re.sub(r'def _show_delivery_history\(self\):.*?dlg\.exec\(\)', new_func, text, flags=re.DOTALL)

with open('ui/pages/deliveries_page.py', 'w', encoding='utf-8') as f:
    f.write(text)
