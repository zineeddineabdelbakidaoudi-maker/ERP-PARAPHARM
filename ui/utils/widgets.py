# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QComboBox, QCompleter
from PySide6.QtCore import Qt

class SearchableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.completer().setFilterMode(Qt.MatchContains)
        
    def focusInEvent(self, e):
        super().focusInEvent(e)
        self.lineEdit().selectAll()

    def focusOutEvent(self, e):
        # When focus is lost, ensure the text matches an existing item or reset to current valid item
        text = self.currentText()
        idx = self.findText(text, Qt.MatchContains)
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            # If not found, revert to the first item or empty if empty
            if getattr(self, 'allow_new', False):
                # Don't revert if new text is allowed
                pass
            elif self.count() > 0:
                self.setCurrentIndex(0)
            else:
                self.setCurrentText("")
        super().focusOutEvent(e)
