import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QHeaderView, QPushButton, QFrame, QScrollArea, QGridLayout
)
from PySide6.QtCore import Qt
from ui.components.stat_card import StatCard
from app.core.database import get_session
from app.models.sale import Sale, SaleItem
from app.models.stock import Stock
from app.models.product import Product
from app.models.report import SavedReport
from sqlalchemy import func
from datetime import datetime, timedelta
from app.core.worker import Worker


class DashboardPage(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area for the whole dashboard
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        container = QWidget()
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(24)

        # ── Header ──
        header_layout = QHBoxLayout()
        title = QLabel("Tableau de Bord")
        title.setProperty("class", "pageTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Actualiser")
        self.refresh_btn.setProperty("variant", "refresh")
        self.refresh_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.refresh_btn)
        self.main_layout.addLayout(header_layout)

        # ── KPI Cards ──
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.revenue_card = StatCard("Revenu Aujourd'hui", "0.00 DA", "💰", "#1B5E20")
        self.sales_card = StatCard("Nombre de Ventes", "0", "🛒", "#1565C0")
        self.alerts_card = StatCard("Alertes Stock", "0", "⚠️", "#F9A825")
        
        # Link low stock alert to inventory
        self.alerts_card.setCursor(Qt.PointingHandCursor)
        self.alerts_card.mousePressEvent = self._on_alerts_clicked
        
        self.debts_card = StatCard("Dettes en Cours", "0.00 DA", "🧾", "#C62828")

        cards_layout.addWidget(self.revenue_card)
        cards_layout.addWidget(self.sales_card)
        cards_layout.addWidget(self.alerts_card)
        cards_layout.addWidget(self.debts_card)

        self.main_layout.addLayout(cards_layout)

        # ── Main Content Grid ──
        content_grid = QGridLayout()
        content_grid.setSpacing(24)
        
        # Left side: Charts
        self.chart1_container = QVBoxLayout()
        self.chart1_lbl = QLabel("CA par Famille (30j)")
        self.chart1_lbl.setProperty("class", "sectionTitle")
        self.chart1_container.addWidget(self.chart1_lbl)
        self.fig1 = plt.Figure(figsize=(5, 3), dpi=100)
        self.canvas1 = FigureCanvasQTAgg(self.fig1)
        self.chart1_container.addWidget(self.canvas1)
        
        self.chart2_container = QVBoxLayout()
        self.chart2_lbl = QLabel("Revenus (7 derniers jours)")
        self.chart2_lbl.setProperty("class", "sectionTitle")
        self.chart2_container.addWidget(self.chart2_lbl)
        self.fig2 = plt.Figure(figsize=(5, 3), dpi=100)
        self.canvas2 = FigureCanvasQTAgg(self.fig2)
        self.chart2_container.addWidget(self.canvas2)
        
        charts_widget = QWidget()
        charts_layout = QVBoxLayout(charts_widget)
        charts_layout.addLayout(self.chart1_container)
        charts_layout.addLayout(self.chart2_container)
        
        content_grid.addWidget(charts_widget, 0, 0)
        
        # Right side: Quick Reports + Recent Sales
        right_panel = QVBoxLayout()
        
        qr_lbl = QLabel("Rapports Rapides")
        qr_lbl.setProperty("class", "sectionTitle")
        right_panel.addWidget(qr_lbl)
        
        self.quick_reports_layout = QVBoxLayout()
        right_panel.addLayout(self.quick_reports_layout)
        
        rs_lbl = QLabel("Dernières Ventes")
        rs_lbl.setProperty("class", "sectionTitle")
        right_panel.addWidget(rs_lbl)
        
        self.sales_table = QTableWidget(0, 4)
        self.sales_table.setHorizontalHeaderLabels(["Heure", "N°", "Total", "Méthode"])
        self.sales_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sales_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.sales_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sales_table.verticalHeader().setVisible(False)
        self.sales_table.verticalHeader().setDefaultSectionSize(48)
        self.sales_table.setMaximumHeight(250)
        right_panel.addWidget(self.sales_table)
        
        content_grid.addWidget(QWidget(), 0, 1) # dummy
        content_grid.setColumnStretch(0, 2)
        content_grid.setColumnStretch(1, 1)
        
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        content_grid.addWidget(right_widget, 0, 1)
        
        self.main_layout.addLayout(content_grid)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _on_alerts_clicked(self, event):
        # Notify main window to change page to stock or inventory
        main_win = self.window()
        if hasattr(main_win, "_navigate_to"):
            main_win._navigate_to("stock")

    def refresh_data(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("⏳ Chargement...")
        
        # Load simple quick things immediately
        self._load_quick_reports()
        
        # Load heavy things in background
        self.worker = Worker(self._fetch_data_bg)
        self.worker.signals.finished.connect(self._on_data_loaded)
        self.worker.signals.error.connect(lambda e: print(f"Dash Error: {e}"))
        self.worker.start()

    def _load_quick_reports(self):
        # Clear existing
        for i in reversed(range(self.quick_reports_layout.count())):
            w = self.quick_reports_layout.itemAt(i).widget()
            if w: w.deleteLater()
            
        reports = self.db_session.query(SavedReport).filter_by(is_deleted=0).order_by(SavedReport.created_at.desc()).limit(3).all()
        
        if not reports:
            lbl = QLabel("Aucun rapport sauvegardé.")
            lbl.setStyleSheet("color: gray;")
            self.quick_reports_layout.addWidget(lbl)
            return
            
        for r in reports:
            btn = QPushButton(f"📄 {r.name}")
            btn.setStyleSheet("text-align: left; padding: 8px;")
            btn.clicked.connect(lambda checked, rep=r: self._open_report(rep))
            self.quick_reports_layout.addWidget(btn)

    def _open_report(self, report):
        main_win = self.window()
        if hasattr(main_win, "_navigate_to"):
            main_win._navigate_to("report_builder")
            # We would ideally signal the report_builder to load this specific report
            # but navigation is sufficient for now

    def _fetch_data_bg(self):
        """Runs in separate thread. Must create own session to avoid SQLite thread errors."""
        from app.core.database import get_session
        session = get_session()
        try:
            today = datetime.now().date()
            today_str = today.strftime("%Y-%m-%d")
            
            # 1. KPIs
            sales_today = session.query(Sale).filter(Sale.sale_date >= today_str, Sale.status == "COMPLETED").all()
            revenue = sum(s.total_amount for s in sales_today)
            sales_count = len(sales_today)
            
            from app.models.stock import Stock
            alerts_count = session.query(Product).join(Stock).filter(Stock.quantity <= Product.min_stock_level, Product.is_deleted == 0).count()
            
            # 2. Recent Sales
            recent_sales = session.query(Sale).filter(Sale.status == "COMPLETED").order_by(Sale.sale_date.desc()).limit(10).all()
            recent_sales_data = []
            for s in recent_sales:
                time_str = s.sale_date.split(" ")[1][:5] if " " in s.sale_date else s.sale_date
                recent_sales_data.append({
                    "time": time_str,
                    "num": s.sale_number,
                    "total": f"{s.total_amount:.2f} DA",
                    "method": s.payment_method
                })
                
            # 3. Chart 1: CA par Famille (Last 30 days)
            from app.models.product import Category
            thirty_days_ago = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            
            family_sales = session.query(
                Category.name, func.sum(SaleItem.line_total).label('revenue')
            ).join(Product, Product.category_id == Category.id) \
             .join(SaleItem, SaleItem.product_id == Product.id) \
             .join(Sale, Sale.id == SaleItem.sale_id) \
             .filter(Sale.sale_date >= thirty_days_ago, Sale.status == "COMPLETED") \
             .group_by(Category.name).all()
            
            fam_names = [f[0] for f in family_sales]
            fam_revenues = [f[1] for f in family_sales]
            
            # Debts
            from app.models.debt import Debt
            total_debts = session.query(func.sum(Debt.remaining_amount)).filter(
                Debt.status.in_(["UNPAID", "PARTIAL"]), Debt.is_deleted == 0
            ).scalar() or 0.0
            
            # 4. Chart 2: Revenue last 7 days
            seven_days_ago = today - timedelta(days=6)
            days = []
            revenues = []
            
            for i in range(7):
                d = seven_days_ago + timedelta(days=i)
                d_str = d.strftime("%Y-%m-%d")
                d_rev = session.query(func.sum(Sale.total_amount)).filter(
                    Sale.sale_date >= d_str + " 00:00:00",
                    Sale.sale_date <= d_str + " 23:59:59",
                    Sale.status == "COMPLETED"
                ).scalar()
                
                days.append(d.strftime("%a")) # Mon, Tue, etc
                revenues.append(d_rev or 0.0)

            return {
                "kpis": {
                    "revenue": revenue,
                    "sales_count": sales_count,
                    "alerts_count": alerts_count,
                    "debts": total_debts,
                },
                "recent_sales": recent_sales_data,
                "chart1": {"names": fam_names, "revenues": fam_revenues},
                "chart2": {"days": days, "revenues": revenues}
            }
        finally:
            session.close()

    def _on_data_loaded(self, data):
        # Update KPIs
        kpis = data["kpis"]
        self.revenue_card.set_value(f"{kpis['revenue']:,.2f} DA".replace(",", " "))
        self.sales_card.set_value(str(kpis['sales_count']))
        self.debts_card.set_value(f"{kpis['debts']:,.2f} DA".replace(",", " "))
        self.alerts_card.set_value(str(kpis['alerts_count']))
        if kpis['alerts_count'] > 0:
            self.alerts_card.setStyleSheet("QFrame { background-color: #FFEBEE; border: 1px solid #EF5350; border-radius: 8px; }")
        else:
            self.alerts_card.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; }")

        # Update Recent Sales Table
        self.sales_table.setRowCount(0)
        for s in data["recent_sales"]:
            row = self.sales_table.rowCount()
            self.sales_table.insertRow(row)
            self.sales_table.setItem(row, 0, QTableWidgetItem(s["time"]))
            self.sales_table.setItem(row, 1, QTableWidgetItem(s["num"]))
            self.sales_table.setItem(row, 2, QTableWidgetItem(s["total"]))
            self.sales_table.setItem(row, 3, QTableWidgetItem(s["method"]))

        # Draw Chart 1 (Pie Chart)
        self.fig1.clear()
        if data["chart1"]["names"]:
            ax1 = self.fig1.add_subplot(111)
            # Use a colorful colormap
            colors = plt.cm.Set3(range(len(data["chart1"]["names"])))
            ax1.pie(data["chart1"]["revenues"], labels=data["chart1"]["names"], autopct='%1.1f%%', startangle=140, colors=colors)
            ax1.axis('equal')
        else:
            # Handle empty data
            ax1 = self.fig1.add_subplot(111)
            ax1.text(0.5, 0.5, "Aucune donnée", ha='center', va='center')
            ax1.axis('off')
        
        self.fig1.tight_layout()
        self.canvas1.draw()

        # Draw Chart 2
        self.fig2.clear()
        ax2 = self.fig2.add_subplot(111)
        ax2.plot(data["chart2"]["days"], data["chart2"]["revenues"], marker='o', color="#1565C0", linestyle='-', linewidth=2)
        ax2.set_ylabel("Revenu (DA)")
        self.fig2.tight_layout()
        self.canvas2.draw()
        
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 Actualiser")
