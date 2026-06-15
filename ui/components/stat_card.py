"""
ParaFarm ERP — Stat Card Component
"""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class StatCard(QFrame):
    """A card displaying a KPI statistic."""

    def __init__(self, title: str, value: str, icon: str, color: str = "#1B5E20", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setProperty("class", "card")
        self.setStyleSheet(f"""
            QFrame#statCard {{
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }}
            QFrame#statCard:hover {{
                border: 1px solid {color};
                background-color: #FAFAFA;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Title & Icon
        title_label = QLabel(f"{icon}  {title}")
        title_label.setProperty("class", "statLabel")
        layout.addWidget(title_label)

        # Value
        self.value_label = QLabel(value)
        self.value_label.setProperty("class", "statValue")
        self.value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        self.value_label.setText(value)
