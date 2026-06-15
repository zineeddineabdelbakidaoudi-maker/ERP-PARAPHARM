from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Route Dialog
"""
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QComboBox, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QWidget, QSplitter
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.models.logistics import Route, RouteStop, Vehicle
from app.models.delivery import Delivery
from ui.pages.base_document_page import make_status_widget


class RouteDialog(QDialog):
    def __init__(self, user, route=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.route = route
        self.db_session = get_session()
        self.setWindowTitle("Modifier Tournée" if route else "Nouvelle Tournée")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        # Temp storage for stops before saving
        self._temp_stops = []
        if self.route:
            for s in self.route.stops:
                if not s.is_deleted:
                    self._temp_stops.append({
                        "id": s.id,
                        "delivery_id": s.delivery_id,
                        "stop_order": s.stop_order,
                        "estimated_arrival": s.estimated_arrival,
                        "actual_arrival": s.actual_arrival,
                        "status": s.status,
                        "delivery_ref": s.delivery.delivery_number if s.delivery else "",
                        "client_name": s.delivery.client.name if s.delivery and s.delivery.client else ""
                    })
                    
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Splitter to divide route info and stops
        splitter = QSplitter(Qt.Vertical)
        
        # --- Top: Route Info ---
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        form.addRow("Nom de la tournée :", self.name_input)
        
        self.desc_input = QLineEdit()
        form.addRow("Description :", self.desc_input)
        
        self.vehicle_input = SearchableComboBox()
        self.vehicles = self.db_session.query(Vehicle).filter_by(is_deleted=0, is_active=1).all()
        for v in self.vehicles:
            self.vehicle_input.addItem(f"{v.name} ({v.plate_number})", v.id)
        form.addRow("Véhicule :", self.vehicle_input)
        
        self.driver_input = QLineEdit()
        form.addRow("Chauffeur :", self.driver_input)
        
        # Use simple text for datetime for MVP, or QDateTimeEdit
        self.start_input = QLineEdit(datetime.now().strftime("%Y-%m-%d %H:%M"))
        form.addRow("Heure de départ (Est.) :", self.start_input)
        
        self.end_input = QLineEdit()
        form.addRow("Heure de fin (Est.) :", self.end_input)
        
        self.status_input = SearchableComboBox()
        self.status_input.addItems(["PLANNED", "IN_PROGRESS", "COMPLETED"])
        form.addRow("Statut de la tournée :", self.status_input)
        
        top_layout.addLayout(form)
        splitter.addWidget(top_widget)
        
        # --- Bottom: Stops ---
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 10, 0, 0)
        
        stops_header = QHBoxLayout()
        stops_lbl = QLabel("Points d'arrêt (Livraisons)")
        stops_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        stops_header.addWidget(stops_lbl)
        stops_header.addStretch()
        add_stop_btn = QPushButton("➕ Ajouter un arrêt")
        add_stop_btn.clicked.connect(self._on_add_stop)
        stops_header.addWidget(add_stop_btn)
        bottom_layout.addLayout(stops_header)
        
        self.stops_table = QTableWidget(0, 8)
        self.stops_table.setHorizontalHeaderLabels([
            "Ordre", "Livraison", "Client", "Arrivée Est.", "Arrivée Act.", "Statut", "Changer Statut", "Actions"
        ])
        header = self.stops_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.stops_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.stops_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.stops_table.verticalHeader().setVisible(False)
        self.stops_table.verticalHeader().setDefaultSectionSize(48)
        bottom_layout.addWidget(self.stops_table)
        
        splitter.addWidget(bottom_widget)
        layout.addWidget(splitter)
        
        # --- Action Buttons ---
        btn_layout = QHBoxLayout()
        
        self.btn_print_fiche = QPushButton("🖨️ Imprimer Fiche d'Expédition")
        self.btn_print_fiche.setStyleSheet("background-color: #F39C12; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        self.btn_print_fiche.clicked.connect(self._print_fiche_expedition)
        btn_layout.addWidget(self.btn_print_fiche)
        
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setProperty("variant", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Enregistrer")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)

    def _print_fiche_expedition(self):
        if not self.route or not self.route.id:
            QMessageBox.warning(self, "Attention", "Veuillez d'abord enregistrer la tournée pour imprimer la fiche d'expédition.")
            return
            
        delivery_ids = [s.delivery_id for s in self.route.stops if not s.is_deleted]
        if not delivery_ids:
            QMessageBox.information(self, "Info", "Aucune livraison dans cette tournée.")
            return
            
        try:
            import os
            from PySide6.QtWidgets import QFileDialog
            from app.utils.pdf_exporter import PDFExporter
            
            d = QFileDialog.getSaveFileName(self, "Enregistrer Fiche d'Expédition", 
                f"Fiche_Expedition_Tournee_{self.route.id}.pdf", "PDF (*.pdf)")
            if d[0]:
                vehicle_str = self.route.vehicle.plate_number if self.route.vehicle else "—"
                PDFExporter.export_fiche_expedition_to_pdf(
                    d[0], self.db_session, delivery_ids,
                    vehicle_name=vehicle_str,
                    driver_name=self.route.driver_name or "—"
                )
                QMessageBox.information(self, "Succès", "Fiche d'expédition générée avec succès.")
                os.startfile(d[0])
        except Exception as e:
            QMessageBox.critical(self, "Erreur PDF", f"Impossible de générer le PDF:\\n{e}")

    def _load_data(self):
        if self.route:
            self.name_input.setText(self.route.name)
            self.desc_input.setText(self.route.description or "")
            self.driver_input.setText(self.route.driver_name or "")
            self.start_input.setText(self.route.start_time or "")
            self.end_input.setText(self.route.end_time or "")
            self.status_input.setCurrentText(self.route.status or "PLANNED")
            
            if self.route.vehicle_id:
                idx = self.vehicle_input.findData(self.route.vehicle_id)
                if idx >= 0:
                    self.vehicle_input.setCurrentIndex(idx)
        self._refresh_stops()

    def _refresh_stops(self):
        self.stops_table.setRowCount(0)
        # Sort by stop_order
        self._temp_stops.sort(key=lambda x: x["stop_order"])
        
        for i, stop in enumerate(self._temp_stops):
            row = self.stops_table.rowCount()
            self.stops_table.insertRow(row)
            
            self.stops_table.setItem(row, 0, QTableWidgetItem(str(stop["stop_order"])))
            self.stops_table.setItem(row, 1, QTableWidgetItem(stop["delivery_ref"]))
            self.stops_table.setItem(row, 2, QTableWidgetItem(stop["client_name"]))
            self.stops_table.setItem(row, 3, QTableWidgetItem(stop["estimated_arrival"] or "—"))
            self.stops_table.setItem(row, 4, QTableWidgetItem(stop["actual_arrival"] or "—"))
            
            # Badge
            self.stops_table.setCellWidget(row, 5, make_status_widget(stop["status"]))
            
            # Change status inline
            status_combo = SearchableComboBox()
            status_combo.addItems(["PENDING", "DELIVERED", "FAILED"])
            status_combo.setCurrentText(stop["status"])
            status_combo.currentTextChanged.connect(lambda txt, s=stop: self._on_stop_status_changed(s, txt))
            self.stops_table.setCellWidget(row, 6, status_combo)
            
            # Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            
            del_btn = QPushButton("🗑️")
            del_btn.setProperty("variant", "icon-delete")
            del_btn.clicked.connect(lambda checked, idx=i: self._remove_stop(idx))
            action_layout.addWidget(del_btn)
            
            self.stops_table.setCellWidget(row, 7, action_widget)

    def _on_stop_status_changed(self, stop, new_status):
        stop["status"] = new_status
        if new_status in ["DELIVERED", "FAILED"]:
            stop["actual_arrival"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        else:
            stop["actual_arrival"] = ""
        # Small trick to refresh badges without losing focus, but for simplicity we refresh all
        self._refresh_stops()

    def _on_add_stop(self):
        # Fetch available deliveries (Pending and not deleted)
        deliveries = self.db_session.query(Delivery).filter_by(is_deleted=0, status="PENDING").all()
        if not deliveries:
            QMessageBox.information(self, "Info", "Aucune livraison en attente disponible.")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Ajouter une livraison à la tournée")
        layout = QVBoxLayout(dialog)
        
        form = QFormLayout()
        
        delivery_combo = SearchableComboBox()
        for d in deliveries:
            # Check if it's already in temp_stops
            if not any(s["delivery_id"] == d.id for s in self._temp_stops):
                delivery_combo.addItem(f"{d.delivery_number} - {d.client.name}", d)
                
        if delivery_combo.count() == 0:
            QMessageBox.information(self, "Info", "Toutes les livraisons en attente sont déjà ajoutées.")
            return
            
        form.addRow("Livraison:", delivery_combo)
        
        order_input = QLineEdit(str(len(self._temp_stops) + 1))
        form.addRow("Ordre de passage:", order_input)
        
        est_input = QLineEdit(datetime.now().strftime("%Y-%m-%d %H:%M"))
        form.addRow("Arrivée Est.:", est_input)
        
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel)
        add_btn = QPushButton("Ajouter")
        btn_layout.addWidget(add_btn)
        layout.addLayout(btn_layout)
        
        def _add():
            d = delivery_combo.currentData()
            self._temp_stops.append({
                "id": None,
                "delivery_id": d.id,
                "stop_order": int(order_input.text() or len(self._temp_stops) + 1),
                "estimated_arrival": est_input.text(),
                "actual_arrival": "",
                "status": "PENDING",
                "delivery_ref": d.delivery_number,
                "client_name": d.client.name
            })
            self._refresh_stops()
            dialog.accept()
            
        add_btn.clicked.connect(_add)
        dialog.exec()

    def _remove_stop(self, index):
        self._temp_stops.pop(index)
        # reorder
        for i, s in enumerate(self._temp_stops):
            s["stop_order"] = i + 1
        self._refresh_stops()

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Erreur", "Le nom de la tournée est requis.")
            return

        if not self.route:
            self.route = Route()
            self.db_session.add(self.route)

        self.route.name = name
        self.route.description = self.desc_input.text().strip()
        self.route.vehicle_id = self.vehicle_input.currentData()
        self.route.driver_name = self.driver_input.text().strip()
        self.route.start_time = self.start_input.text()
        self.route.end_time = self.end_input.text()
        self.route.status = self.status_input.currentText()

        # Update stops
        # First, mark existing stops as deleted if they were removed
        existing_stop_ids = [s["id"] for s in self._temp_stops if s["id"] is not None]
        for s in self.route.stops:
            if s.id not in existing_stop_ids:
                s.is_deleted = 1
                # Remove route_id from delivery so it can be scheduled again
                if s.delivery:
                    s.delivery.route_id = None
                    if s.delivery.status != "COMPLETED":
                        s.delivery.status = "PENDING"

        # Update or add new stops
        for ts in self._temp_stops:
            if ts["id"] is None:
                new_stop = RouteStop(
                    delivery_id=ts["delivery_id"],
                    stop_order=ts["stop_order"],
                    estimated_arrival=ts["estimated_arrival"],
                    actual_arrival=ts["actual_arrival"],
                    status=ts["status"]
                )
                self.route.stops.append(new_stop)
                
                # Link delivery to route
                delivery = self.db_session.query(Delivery).get(ts["delivery_id"])
                if delivery:
                    delivery.route = self.route
                    if self.route.status == "IN_PROGRESS" and ts["status"] == "PENDING":
                        delivery.status = "IN_PROGRESS"
            else:
                for s in self.route.stops:
                    if s.id == ts["id"]:
                        s.stop_order = ts["stop_order"]
                        s.estimated_arrival = ts["estimated_arrival"]
                        s.actual_arrival = ts["actual_arrival"]
                        s.status = ts["status"]
                        
                        # Sync delivery status
                        if s.delivery:
                            if s.status == "DELIVERED":
                                s.delivery.status = "COMPLETED"
                            elif s.status == "FAILED":
                                s.delivery.status = "PENDING" # Can be rescheduled
                            elif self.route.status == "IN_PROGRESS":
                                s.delivery.status = "IN_PROGRESS"
                        break

        try:
            self.db_session.commit()
            self.accept()
        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'enregistrement: {e}")
