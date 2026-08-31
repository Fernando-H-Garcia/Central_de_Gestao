"""
Base class for Qt views that automatically listen to global entity updates.
"""
from typing import List, Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer
from core.refresh_manager import refresh_manager


class BaseRefreshView(QWidget):
    """
    Base view widget with built-in subscription to global entity updates.
    Subclasses should define `entity_types` (e.g. ['task', 'project']) and `load_data()`.
    """
    entity_types: List[str] = ["task"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_refresh_pending = False
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._exec_scheduled_reload)
        self._register_refresh()

    def _register_refresh(self):
        if self.entity_types:
            refresh_manager.register(self.entity_types, self._on_entity_updated)

    def _on_entity_updated(self, payload: dict):
        """Called when a matching entity is updated anywhere in the system."""
        # Debounce reload requests slightly to prevent UI lag on rapid edits
        if not self._is_refresh_pending:
            self._is_refresh_pending = True
            self._refresh_timer.start(50)

    def _exec_scheduled_reload(self):
        self._is_refresh_pending = False
        if not self.isVisible() and hasattr(self, "_lazy_reload_needed"):
            # Mark for reload when shown
            self._lazy_reload_needed = True
            return
        try:
            self.reload_data()
        except Exception as e:
            import logging
            logging.exception(f"Error reloading data in {self.__class__.__name__}: {e}")

    def reload_data(self):
        """Override in subclasses to reload view data."""
        if hasattr(self, "load_data"):
            self.load_data()

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_lazy_reload_needed", False):
            self._lazy_reload_needed = False
            self.reload_data()

    def closeEvent(self, event):
        refresh_manager.unregister(self._on_entity_updated)
        super().closeEvent(event)
