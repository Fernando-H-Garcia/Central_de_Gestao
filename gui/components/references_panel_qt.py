"""
ReferencePanelQt — Painel de referências entre entidades (Qt).

Exibe dois botões pequenos: "🔗 Referências (N)" e "↩️ Referenciado por (N)".
Ao passar o mouse, mostra um popup flutuante com a lista.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QFont


ENTITY_TYPE_LABELS = {
    "project": "Projeto",
    "task": "Tarefa",
    "idea": "Ideia",
    "note": "Nota",
    "wiki": "Documento",
    "knowledge_page": "Documento",
    "file": "Arquivo",
    "attachment": "Arquivo",
}

ENTITY_ICONS = {
    "project": "📁",
    "task": "📋",
    "idea": "💡",
    "note": "📝",
    "wiki": "📖",
    "knowledge_page": "📖",
    "file": "📎",
    "attachment": "📎",
}

POPUP_STYLE = """
QListWidget {
    background-color: #1c1c2e;
    color: #ffffff;
    border: 1px solid #4a6fe3;
    border-radius: 6px;
    padding: 4px;
    font-size: 12px;
}
QListWidget::item {
    padding: 6px 10px;
    border-radius: 4px;
}
QListWidget::item:selected {
    background-color: #2d2d55;
    color: #ffffff;
}
QListWidget::item:hover {
    background-color: #2a2a3f;
}
"""


class ReferencePopup(QFrame):
    """Popup flutuante exibido ao passar o mouse sobre os botões."""

    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setStyleSheet("background-color: #1c1c2e; border: 1px solid #4a6fe3; border-radius: 8px;")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.lst = QListWidget()
        self.lst.setStyleSheet(POPUP_STYLE)
        self.lst.setMinimumWidth(260)
        self.lst.setMaximumWidth(400)

        if not self.items:
            self.lst.addItem("  Nenhum item encontrado.")
            self.lst.item(0).setFlags(Qt.NoItemFlags)
        else:
            for item in self.items:
                t_type = item.get("target_type") or item.get("source_type", "")
                title = item.get("title", "Sem título")
                icon = ENTITY_ICONS.get(t_type, "🔗")
                label_pt = ENTITY_TYPE_LABELS.get(t_type, t_type.capitalize())
                label = f"{icon} [{label_pt}] {title}"
                wi = QListWidgetItem(label)
                wi.setData(Qt.UserRole, item)
                self.lst.addItem(wi)

        self.lst.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.lst)
        self.setFixedSize(self.lst.sizeHint().width() + 10, min(self.lst.sizeHint().height() + 10, 300))

    def _on_item_clicked(self, item):
        data = item.data(Qt.UserRole)
        if not data:
            return
        self.close()
        self._navigate(data)

    def _navigate(self, data):
        is_out = "target_type" in data
        if is_out:
            e_type = data.get("target_type")
            e_id = data.get("target_id")
        else:
            e_type = data.get("source_type")
            e_id = data.get("source_id")

        if not e_type or not e_id:
            return

        main_win = self.window() if self.parent() else None

        if e_type == "project" and main_win and hasattr(main_win, "show_project_360"):
            main_win.show_project_360(e_id)
        elif e_type == "task" and main_win and hasattr(main_win, "show_task_detail"):
            main_win.show_task_detail(e_id)
        elif e_type in ("wiki", "knowledge_page"):
            from core.event_bus import event_bus
            event_bus.emit("navigate_to", {"type": "wiki", "id": e_id})
        elif e_type in ("file", "attachment"):
            import subprocess, os
            file_path = data.get("file_path", "")
            if file_path and os.path.exists(file_path):
                subprocess.Popen(["explorer", file_path] if os.name == "nt" else ["xdg-open", file_path])
        else:
            from core.event_bus import event_bus
            event_bus.emit("navigate_to", {"type": e_type, "id": e_id})


class ReferencesPanelQt(QWidget):
    """
    Painel compacto de referências: dois botões pequenos lado a lado.

    Uso:
        panel = ReferencesPanelQt(entity_type="wiki", entity_id=5)
        panel.set_entity("wiki", 5)
    """

    def __init__(self, entity_type: str = "", entity_id: int = 0, parent=None):
        super().__init__(parent)
        self.entity_type = entity_type
        self.entity_id = entity_id
        self._out_links = []
        self._in_links = []
        self._popup = None
        self._setup_ui()
        if entity_id:
            self.refresh()

    def set_entity(self, entity_type: str, entity_id: int):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.refresh()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.btn_out = QPushButton("🔗 Referências (0)")
        self.btn_out.setObjectName("secondary")

        self.btn_in = QPushButton("↩️ Referenciado por (0)")
        self.btn_in.setObjectName("secondary")

        self.btn_out.installEventFilter(self)
        self.btn_out.clicked.connect(self._show_out_popup)
        layout.addWidget(self.btn_out)

        self.btn_in.installEventFilter(self)
        self.btn_in.clicked.connect(self._show_in_popup)
        layout.addWidget(self.btn_in)

    def eventFilter(self, obj, event):
        if obj in (self.btn_out, self.btn_in):
            if event.type() == QEvent.Enter:
                QTimer.singleShot(400, lambda: self._on_hover(obj))
            elif event.type() == QEvent.Leave:
                pass
        return super().eventFilter(obj, event)

    def _on_hover(self, btn):
        if self._popup and self._popup.isVisible():
            return
        if btn == self.btn_out:
            self._show_out_popup()
        else:
            self._show_in_popup()

    def _show_out_popup(self):
        if not self._out_links:
            return
        self._show_popup(self._out_links, self.btn_out)

    def _show_in_popup(self):
        if not self._in_links:
            return
        self._show_popup(self._in_links, self.btn_in)

    def _show_popup(self, items, anchor_btn):
        self._popup = ReferencePopup(items, self)
        pos = anchor_btn.mapToGlobal(anchor_btn.rect().bottomLeft())
        screen = self.screen() if hasattr(self, 'screen') else None
        if screen:
            sg = screen.availableGeometry()
            popup_w = self._popup.width()
            popup_h = self._popup.height()
            if pos.x() + popup_w > sg.right():
                pos.setX(sg.right() - popup_w - 5)
            if pos.y() + popup_h > sg.bottom():
                pos.setY(anchor_btn.mapToGlobal(anchor_btn.rect().topLeft()).y() - popup_h)
        self._popup.move(pos)
        self._popup.show()

    def refresh(self):
        if not self.entity_id:
            self.btn_out.setText("🔗 Referências (0)")
            self.btn_in.setText("↩️ Referenciado por (0)")
            return
        try:
            from services.link_service import LinkService
            svc = LinkService()
            self._out_links = svc.get_links_for_entity(self.entity_type, self.entity_id)
            self._in_links = svc.get_backlinks_for_entity(self.entity_type, self.entity_id)

            # Also include file attachments as references
            from services.attachment_service import AttachmentService
            attach_list = AttachmentService().get_attachments_for_entity(self.entity_type, self.entity_id)
            for att in attach_list:
                self._out_links.append({
                    "relationship_type": "references",
                    "target_type": "file",
                    "target_id": att.id,
                    "title": att.file_name,
                    "file_path": att.file_path,
                })

            self.btn_out.setText(f"🔗 Referências ({len(self._out_links)})")
            self.btn_in.setText(f"↩️ Referenciado por ({len(self._in_links)})")
        except Exception:
            self.btn_out.setText("🔗 Referências (0)")
            self.btn_in.setText("↩️ Referenciado por (0)")
