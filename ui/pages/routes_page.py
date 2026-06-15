"""
ParaFarm ERP — Routes Page
"""
from PySide6.QtWidgets import QMessageBox
from app.core.database import get_session
from app.models.logistics import Route
from ui.pages.base_document_page import BaseDocumentPage
from ui.dialogs.route_dialog import RouteDialog


class RoutesPage(BaseDocumentPage):
    PAGE_TITLE = "Tournées"
    STATUS_OPTIONS = ["Tous", "PLANNED", "IN_PROGRESS", "COMPLETED"]

    def __init__(self, user, parent=None):
        self.db_session = get_session()
        super().__init__(user, parent)

    def _get_columns(self) -> list:
        return ["ID", "Nom de la Tournée", "Véhicule", "Chauffeur", "Statut", "Actions"]

    def _load_data(self, search: str, status_filter: str) -> list:
        q = self.db_session.query(Route).filter_by(is_deleted=0)

        if search:
            search_str = f"%{search}%"
            q = q.filter(
                (Route.name.ilike(search_str)) |
                (Route.driver_name.ilike(search_str))
            )

        if status_filter and status_filter != "Tous":
            q = q.filter(Route.status == status_filter)

        routes = q.order_by(Route.start_time.desc()).all()

        data = []
        for r in routes:
            v_str = f"{r.vehicle.name} ({r.vehicle.plate_number})" if r.vehicle else "—"
            data.append({
                "obj": r,
                "ID": str(r.id),
                "Nom de la Tournée": r.name,
                "Véhicule": v_str,
                "Chauffeur": r.driver_name or "—",
                "status": r.status or "PLANNED"
            })
        return data

    def _on_add(self):
        dialog = RouteDialog(self.user, parent=self)
        if dialog.exec():
            self.refresh_data()

    def _on_edit(self, row_data):
        r = row_data["obj"]
        dialog = RouteDialog(self.user, route=r, parent=self)
        if dialog.exec():
            self.refresh_data()

    def _on_delete(self, row_data):
        r = row_data["obj"]
        reply = QMessageBox.question(
            self, "Supprimer", f"Voulez-vous vraiment supprimer la tournée {r.name} ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            r.is_deleted = 1
            # Free deliveries
            for s in r.stops:
                s.is_deleted = 1
                if s.delivery:
                    s.delivery.route_id = None
                    if s.delivery.status != "COMPLETED":
                        s.delivery.status = "PENDING"
            self.db_session.commit()
            self.refresh_data()
