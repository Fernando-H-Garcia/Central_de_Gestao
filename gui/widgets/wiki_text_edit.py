from PySide6.QtWidgets import QTextEdit, QListWidget, QListWidgetItem, QFrame, QVBoxLayout
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent, QTextCursor

ENTITY_ICONS = {"wiki": "\U0001f4c4", "project": "\U0001f4c1", "task": "\U0001f4cb", "idea": "\U0001f4a1", "note": "\U0001f4dd"}
ENTITY_TYPE_LABELS = {"wiki": "Documento", "project": "Projeto", "task": "Tarefa", "idea": "Ideia", "note": "Nota"}


class WikiTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)

        self._autocomplete_popup = None
        self._autocomplete_list = None
        self._autocomplete_trigger = None
        self._autocomplete_type = None

    def _get_linkable_entities(self):
        candidates = []
        try:
            from services.link_service import LinkService
            items = LinkService().get_all_linkable_entities()
            for it in items:
                icon = ENTITY_ICONS.get(it["type"], "\U0001f517")
                label_pt = ENTITY_TYPE_LABELS.get(it["type"], it["type"].capitalize())
                candidates.append({
                    "type": it["type"], "id": it["id"],
                    "title": it["title"],
                    "label": f"{icon} [{label_pt}] {it['title']}",
                })
        except Exception:
            pass
        return candidates

    def _get_attachable_files(self):
        candidates = []
        try:
            from database.connection import get_db_cursor
            from models.entities import Attachment
            with get_db_cursor() as cursor:
                cursor.execute("SELECT * FROM attachments WHERE deleted_at IS NULL ORDER BY created_at DESC")
                rows = cursor.fetchall()
            seen_uuids = set()
            for row in rows:
                att = Attachment(**dict(row))
                if att.uuid in seen_uuids:
                    continue
                seen_uuids.add(att.uuid)
                page_id = att.entity_id if att.entity_type == "knowledge_page" else None
                location = f" (pg #{page_id})" if page_id else ""
                candidates.append({
                    "type": "file", "id": att.id,
                    "title": att.file_name, "uuid": att.uuid,
                    "file_path": att.file_path,
                    "label": f"\U0001f4ce {att.file_name}{location}",
                })
        except Exception:
            pass
        return candidates

    def _close_autocomplete(self):
        if self._autocomplete_popup:
            try:
                self._autocomplete_popup.close()
                self._autocomplete_popup.deleteLater()
            except RuntimeError:
                pass
            self._autocomplete_popup = None
            self._autocomplete_list = None
            self._autocomplete_trigger = None
            self._autocomplete_type = None

    def _show_autocomplete(self, trigger_text, cursor_pos):
        self._close_autocomplete()

        if trigger_text == "[[":
            candidates = self._get_linkable_entities()
            self._autocomplete_type = "link"
        elif trigger_text == "{{":
            candidates = self._get_attachable_files()
            self._autocomplete_type = "file"
        else:
            return

        if not candidates:
            return

        popup = QFrame(self, Qt.Popup | Qt.FramelessWindowHint)
        popup.setStyleSheet("""
            QFrame { background-color: #1c1c2e; border: 1px solid #4a6fe3; border-radius: 6px; }
            QListWidget { background: transparent; border: none; color: #fff; font-size: 12px; }
            QListWidget::item { padding: 5px 10px; border-radius: 3px; }
            QListWidget::item:selected { background-color: #2d2d55; }
        """)
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(0, 0, 0, 0)

        lst = QListWidget()
        for c in candidates:
            wi = QListWidgetItem(c["label"])
            wi.setData(Qt.UserRole, c)
            lst.addItem(wi)
        lst.setMinimumWidth(300)
        lst.setMaximumWidth(450)
        lst.setMaximumHeight(250)

        lst.itemClicked.connect(self._autocomplete_select)
        lst.itemActivated.connect(self._autocomplete_select)

        layout.addWidget(lst)
        self._autocomplete_popup = popup
        self._autocomplete_list = lst
        self._autocomplete_trigger = cursor_pos

        cursor_rect = self.cursorRect(self.textCursor())
        global_pos = self.viewport().mapToGlobal(cursor_rect.bottomLeft())
        popup.move(global_pos)
        popup.show()
        lst.setFocus()
        lst.setCurrentRow(0)

    def _autocomplete_select(self, item):
        data = item.data(Qt.UserRole)
        if not data:
            self._close_autocomplete()
            return

        cursor = self.textCursor()
        pos = cursor.position()
        cursor.setPosition(self._autocomplete_trigger)
        cursor.setPosition(pos, QTextCursor.KeepAnchor)

        if self._autocomplete_type == "link":
            replacement = f"[[{data['type']}:{data['id']}|{data['title']}]]"
        else:
            replacement = f"{{{{{data['uuid']}|{data['title']}}}}}"

        cursor.insertText(replacement)
        self._close_autocomplete()
        self.setFocus()

    def _update_autocomplete_filter(self):
        if not self._autocomplete_popup or not self._autocomplete_list or self._autocomplete_trigger is None:
            return
        text = self.toPlainText()
        pos = self.textCursor().position()
        query = text[self._autocomplete_trigger + 2:pos].lower().strip()
        lst = self._autocomplete_list
        for i in range(lst.count()):
            item = lst.item(i)
            data = item.data(Qt.UserRole)
            if data:
                title = data.get("title", "").lower()
                item.setHidden(query not in title)

    def keyPressEvent(self, event: QKeyEvent):
        if self._autocomplete_popup and event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Return, Qt.Key_Enter):
            lst = self._autocomplete_list
            if event.key() == Qt.Key_Up:
                row = lst.currentRow()
                lst.setCurrentRow((row - 1) % lst.count())
                return
            elif event.key() == Qt.Key_Down:
                row = lst.currentRow()
                lst.setCurrentRow((row + 1) % lst.count())
                return
            elif event.key() in (Qt.Key_Return, Qt.Key_Enter) and lst.currentItem():
                self._autocomplete_select(lst.currentItem())
                return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_BracketLeft, Qt.Key_BraceLeft):
            cursor = self.textCursor()
            pos = cursor.position()
            text = self.toPlainText()
            start = max(0, pos - 2)
            snippet = text[start:pos]
            if snippet in ("[[", "{{"):
                self._show_autocomplete(snippet, pos - 2)
        elif event.key() == Qt.Key_Escape:
            self._close_autocomplete()
        elif self._autocomplete_popup:
            self._update_autocomplete_filter()
        super().keyReleaseEvent(event)


def render_links_as_html(text: str) -> str:
    import re
    def link_repl(m):
        t_type = m.group(1)
        t_id = m.group(2)
        t_title = m.group(3)
        if t_type and t_id:
            return f'<a href="app://{t_type}/{t_id}" style="color:#4a6fe3;">{t_title.strip()}</a>'
        else:
            return f'<a href="app://search/{t_title.strip()}" style="color:#e3a84a;">{t_title.strip()}</a>'
    text = re.sub(r'\[\[(?:([a-zA-Z0-9_]+):(\d+)\|)?(.*?)\]\]', link_repl, text)

    def file_repl(m):
        f_uuid = m.group(1)
        f_name = m.group(2)
        return f'<a href="file:///{f_uuid}" style="color:#4a6fe3;">\U0001f4ce {f_name.strip()}</a>'
    text = re.sub(r'\{\{(.*?)\|(.*?)\}\}', file_repl, text)

    return text.replace("\n", "<br>")
