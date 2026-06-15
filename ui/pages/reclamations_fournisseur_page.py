from ui.pages.base_document_page import BaseDocumentPage
from app.models.reclamation import Reclamation
from app.core.database import get_session
from PySide6.QtWidgets import QMessageBox

class ReclamationsFournisseurPage(BaseDocumentPage):
    PAGE_TITLE = "Réclamations Fournisseur"
    STATUS_OPTIONS = ["Tous", "Ouvert", "En cours", "Résolu"]

    def _get_columns(self):
        return ["N°", "Date", "Fournisseur", "Motif", "Statut", "Actions"]

    def _load_data(self, search, status_filter):
        q = self.db_session.query(Reclamation).filter(Reclamation.supplier_id.isnot(None))
        
        # Map UI status to DB status
        status_map = {
            "Ouvert": "PENDING",
            "En cours": "IN_PROGRESS",
            "Résolu": "RESOLVED"
        }
        
        if status_filter and status_filter in status_map:
            q = q.filter(Reclamation.status == status_map[status_filter])
        recs = q.order_by(Reclamation.created_at.desc()).all()
        
        data = []
        for r in recs:
            ent = r.supplier.name if r.supplier else ""
                
            if search and search.lower() not in r.reclamation_number.lower() and search.lower() not in ent.lower():
                continue
                
            # Reverse map DB status to UI status
            ui_status = "Ouvert"
            if r.status == "IN_PROGRESS": ui_status = "En cours"
            elif r.status in ("RESOLVED", "TRANSFORMED_TO_AVOIR"): ui_status = "Résolu"
            elif r.status == "REJECTED": ui_status = "Rejeté"
            else: ui_status = "Ouvert"
                
            data.append({
                "id": r.id,
                "N°": r.reclamation_number,
                "Date": r.created_at[:10] if r.created_at else "",
                "Fournisseur": ent,
                "Motif": r.reason,
                "status": ui_status,
                "_obj": r
            })
        return data

    def _on_add(self):
        from ui.dialogs.reclamation_dialog import ReclamationDialog
        dlg = ReclamationDialog(self.user, parent=self, is_client=False)
        if dlg.exec():
            self.refresh_data()

    def _on_edit(self, row_data):
        from ui.dialogs.reclamation_dialog import ReclamationDialog
        rec = self.db_session.query(Reclamation).get(row_data["id"])
        dlg = ReclamationDialog(self.user, parent=self, is_client=False, reclamation=rec)
        if dlg.exec():
            self.refresh_data()

    def _on_delete(self, row_data):
        rec = self.db_session.query(Reclamation).get(row_data["id"])
        if rec:
            reply = QMessageBox.question(self, "Supprimer", "Voulez-vous supprimer cette réclamation ?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.db_session.delete(rec)
                self.db_session.commit()
                self.refresh_data()

    def open_detail(self, r_id):
        rec = self.db_session.query(Reclamation).get(r_id)
        if not rec: return
        QMessageBox.information(self, "Détail", f"Réclamation N° {rec.reclamation_number}\nMotif : {rec.reason}\nStatut : {rec.status}")
