"""
ParaFarm ERP — Vehicles Page
"""
from PySide6.QtWidgets import QMessageBox
from app.core.database import get_session
from app.models.logistics import Vehicle
from ui.pages.base_document_page import BaseDocumentPage
from ui.dialogs.vehicle_dialog import VehicleDialog


class VehiclesPage(BaseDocumentPage):
    PAGE_TITLE = "Véhicules"
    STATUS_OPTIONS = ["Tous", "Actif", "Inactif"]

    def __init__(self, user, parent=None):
        self.db_session = get_session()
        super().__init__(user, parent)

    def _get_columns(self) -> list:
        return ["ID", "Nom / Marque", "Immatriculation", "Type", "Capacité", "Statut", "Actions"]

    def _load_data(self, search: str, status_filter: str) -> list:
        q = self.db_session.query(Vehicle).filter_by(is_deleted=0)

        if search:
            search_str = f"%{search}%"
            q = q.filter(
                (Vehicle.name.ilike(search_str)) |
                (Vehicle.plate_number.ilike(search_str))
            )

        if status_filter == "Actif":
            q = q.filter(Vehicle.is_active == 1)
        elif status_filter == "Inactif":
            q = q.filter(Vehicle.is_active == 0)

        vehicles = q.order_by(Vehicle.name).all()

        data = []
        for v in vehicles:
            data.append({
                "obj": v,
                "ID": str(v.id),
                "Nom / Marque": v.name,
                "Immatriculation": v.plate_number,
                "Type": v.vehicle_type or "—",
                "Capacité": str(v.capacity),
                "status": "COMPLETED" if v.is_active else "CANCELLED"  # COMPLETED renders green, CANCELLED renders red
            })
        return data

    def _on_add(self):
        dialog = VehicleDialog(self.user, parent=self)
        if dialog.exec():
            self.refresh_data()

    def _on_edit(self, row_data):
        v = row_data["obj"]
        dialog = VehicleDialog(self.user, vehicle=v, parent=self)
        if dialog.exec():
            self.refresh_data()

    def _on_delete(self, row_data):
        v = row_data["obj"]
        reply = QMessageBox.question(
            self, "Supprimer", f"Voulez-vous vraiment supprimer le véhicule {v.name} ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            v.is_deleted = 1
            self.db_session.commit()
            self.refresh_data()
