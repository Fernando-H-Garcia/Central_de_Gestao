from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QScrollArea, QFrame,
    QSizePolicy, QGridLayout, QMenu
)
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QFont, QAction, QCursor
from gui.components.page_header import PageHeader
from gui.components.collapsible_section_qt import CollapsibleSection
import json
from datetime import datetime
from collections import defaultdict

ACTION_TRANSLATION = {
    "CREATED": "CRIADO",
    "UPDATED": "ATUALIZADO",
    "STATUS_CHANGED": "MUDANÇA DE STATUS",
    "MANUAL": "COMENTÁRIO",
    "MANUAL_NOTE": "COMENTÁRIO",
    "ARCHIVED": "ARQUIVADO",
    "RESTORED": "RESTAURADO",
    "DEADLINE_CREATED": "PRAZO ESTIMADO",
    "DEADLINE_UPDATED": "PRAZO ESTIMADO",
    "DEADLINE_REMOVED": "PRAZO ESTIMADO",
}
COLOR_MAPPING = {
    "CRIADO": "#4caf50",
    "ATUALIZADO": "#2196f3",
    "MUDANÇA DE STATUS": "#ff9800",
    "COMENTÁRIO": "#e91e63",
    "ARQUIVADO": "#ff9800",
    "RESTAURADO": "#4caf50",
    "PRAZO ESTIMADO": "#f44336",
}

# Cores alternadas por nível de aninhamento: cada filho usa cor diferente do
# pai. Tupla (cor do destaque, cor de fundo).
DEPTH_PALETTE = [
    ("#D99A3E", "#211A14"),  # Pai
    ("#5B9BD5", "#111A23"),  # Filho 1
    ("#62B58A", "#121E19"),  # Filho 2
    ("#A77BC7", "#1B1620"),  # Filho 3
    ("#C47A72", "#211716"),  # Filho 4
    ("#5FAFAF", "#121D1D"),  # Filho 5
]

FIELD_TRANSLATIONS = {
    "title": "título",
    "due_date": "prazo",
    "energy_level": "prioridade",
    "status": "status",
    "alert_date": "data do alerta",
    "alert_message": "mensagem do alerta",
    "context": "contexto",
    "project_id": "projeto",
    "parent_task_id": "tarefa pai",
}

def _parent_task_title(task_id):
    # Converte um id de tarefa pai (ou None) em um rótulo amigável.
    if not task_id:
        return "tarefa raiz"
    try:
        from database.repositories.task_repository import TaskRepository
        parent = TaskRepository().get_by_id(int(task_id))
        if parent:
            return f"'{parent.title}'"
    except Exception:
        pass
    return f"id {task_id}"

def fmt_val(val):
    if val is None or val == "None" or str(val).strip() == "":
        return "vazio"
    return str(val)


class ActivitySummaryQt(QWidget):
    go_back = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.installEventFilter(self)
        self.setup_ui()

        from core.event_bus import event_bus
        event_bus.subscribe("snapshot_updated", self._safe_load_data)
        event_bus.subscribe("entity_updated", self._safe_load_data)
        self.destroyed.connect(self._on_destroyed)

    def _on_destroyed(self):
        from core.event_bus import event_bus
        event_bus.unsubscribe("snapshot_updated", self._safe_load_data)
        event_bus.unsubscribe("entity_updated", self._safe_load_data)

    def _safe_load_data(self, _=None):
        if self.isVisible():
            self._buscar()


    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # Header
        self.header = PageHeader("Resumo das Atividades")
        btn_back = QPushButton("← Voltar")
        btn_back.setObjectName("secondary")
        btn_back.clicked.connect(self.go_back.emit)
        self.header.add_left_widget(btn_back)
        main_layout.addWidget(self.header)

        # Command panel
        panel = QFrame()
        panel.setObjectName("card")
        panel_layout = QHBoxLayout(panel)
        panel_layout.setContentsMargins(16, 12, 16, 12)
        panel_layout.setSpacing(16)

        col_proj = QVBoxLayout()
        col_proj.setSpacing(4)
        lbl_proj = QLabel("Projeto")
        lbl_proj.setStyleSheet("font-weight: bold; color: #888; font-size: 11px;")
        self.cmb_project = QComboBox()
        self.cmb_project.setFixedWidth(260)
        self._load_projects()
        col_proj.addWidget(lbl_proj)
        col_proj.addWidget(self.cmb_project)

        col_reg = QVBoxLayout()
        col_reg.setSpacing(4)
        lbl_reg = QLabel("Número de Registros")
        lbl_reg.setStyleSheet("font-weight: bold; color: #888; font-size: 11px;")
        self.spin_count = QSpinBox()
        self.spin_count.setRange(1, 100)
        self.spin_count.setValue(4)
        self.spin_count.setFixedWidth(140)
        col_reg.addWidget(lbl_reg)
        col_reg.addWidget(self.spin_count)

        btn_concluidos = QPushButton("✅ Exibir concluídos: OFF")
        btn_concluidos.setCheckable(True)
        btn_concluidos.setObjectName("secondary")
        btn_concluidos.setFixedWidth(180)
        btn_concluidos.setStyleSheet("""
            QPushButton {
                padding: 6px 14px; border-radius: 5px; font-weight: bold;
                background-color: #2b8c52; color: #fff; border: none;
            }
            QPushButton:hover { background-color: #3bbf6e; }
            QPushButton:checked { background-color: #2b8c52; color: #fff; border: none; }
            QPushButton:checked:hover { background-color: #3bbf6e; }
            QPushButton:!checked { background-color: transparent; color: #aaa; border: 1px solid #555; }
            QPushButton:!checked:hover { background-color: #2d2d55; color: #fff; border: 1px solid #4a6fe3; }
            QPushButton:pressed { background-color: #3bbf6e; }
        """)
        btn_concluidos.clicked.connect(self._toggle_concluidos)
        self.btn_concluidos = btn_concluidos

        btn_comentarios = QPushButton("💬 Somente Comentários: ON")
        btn_comentarios.setCheckable(True)
        btn_comentarios.setChecked(True)
        btn_comentarios.setObjectName("secondary")
        btn_comentarios.setFixedWidth(210)
        btn_comentarios.setStyleSheet("""
            QPushButton {
                padding: 6px 14px; border-radius: 5px; font-weight: bold;
                background-color: #c2185b; color: #fff; border: none;
            }
            QPushButton:hover { background-color: #e91e63; }
            QPushButton:checked { background-color: #c2185b; color: #fff; border: none; }
            QPushButton:checked:hover { background-color: #e91e63; }
            QPushButton:!checked { background-color: transparent; color: #aaa; border: 1px solid #555; }
            QPushButton:!checked:hover { background-color: #2d2d55; color: #fff; border: 1px solid #4a6fe3; }
            QPushButton:pressed { background-color: #e91e63; }
        """)
        btn_comentarios.clicked.connect(self._toggle_comentarios)
        self.btn_comentarios = btn_comentarios

        btn_buscar = QPushButton("🔍 Buscar")
        btn_buscar.setObjectName("secondary")
        btn_buscar.setFixedWidth(120)
        btn_buscar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        btn_buscar.clicked.connect(self._buscar)

        # Center the controls horizontally
        panel_layout.addStretch()
        panel_layout.addLayout(col_proj)
        panel_layout.addLayout(col_reg)
        panel_layout.addWidget(btn_concluidos)
        panel_layout.addWidget(btn_comentarios)
        panel_layout.addWidget(btn_buscar)
        panel_layout.addStretch()

        main_layout.addWidget(panel)

        # Results area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setSpacing(12)
        scroll.setWidget(self.results_container)
        main_layout.addWidget(scroll, stretch=1)

        # Initial hint
        hint = QLabel("Selecione um projeto e clique em Buscar.")
        hint.setStyleSheet("color: #888; font-size: 14px; padding: 40px;")
        hint.setAlignment(Qt.AlignCenter)
        self.results_layout.addWidget(hint)
        self.results_layout.addStretch()

    def _toggle_concluidos(self):
        on = self.btn_concluidos.isChecked()
        self.btn_concluidos.setText(f"✅ Exibir concluídos: {'ON' if on else 'OFF'}")
        self._buscar()

    def _toggle_comentarios(self):
        on = self.btn_comentarios.isChecked()
        self.btn_comentarios.setText(f"💬 Somente Comentários: {'ON' if on else 'OFF'}")
        self._buscar()

    def _load_projects(self):
        self.cmb_project.clear()
        self.cmb_project.addItem("— Todos os projetos —", 0)
        try:
            from services.project_service import ProjectService
            projects = ProjectService().get_all_active()
            for p in projects:
                self.cmb_project.addItem(f"{p.name} (ID {p.id})", p.id)
        except Exception:
            pass

    def _format_details(self, log_action: str, changed_json: str, task_title: str) -> str:
        if log_action in ("MANUAL", "MANUAL_NOTE", "COMENTÁRIO"):
            if not changed_json:
                return ""
            try:
                parsed = json.loads(changed_json)
                values = []
                for v in parsed.values():
                    if isinstance(v, str):
                        values.append(v)
                    elif isinstance(v, dict):
                        for sv in v.values():
                            values.append(str(sv))
                    else:
                        values.append(str(v))
                return " | ".join(values)
            except Exception:
                return changed_json or ""

        if not changed_json:
            if log_action == "ARCHIVED":
                return "Tarefa arquivada"
            if log_action == "RESTORED":
                return "Tarefa restaurada"
            return ""

        try:
            parsed = json.loads(changed_json)
        except Exception:
            return changed_json or ""

        if log_action == "CREATED":
            parts = []
            title_val = task_title
            for k, v in parsed.items():
                if k == "title":
                    title_val = fmt_val(v.get('to'))
                    continue
                parts.append(f"{FIELD_TRANSLATIONS.get(k, k)} {fmt_val(v.get('to'))}")
            if parts:
                return f"Criação da tarefa '{title_val}' com " + ", ".join(parts)
            return f"Criação da tarefa '{title_val}'"

        elif log_action == "UPDATED":
            parts = []
            for k, v in parsed.items():
                if k == "parent_task_id":
                    to_val = v.get('to') if isinstance(v, dict) else v
                    parts.append(f"virou {_parent_task_title(to_val)}")
                    continue
                k_pt = FIELD_TRANSLATIONS.get(k, k)
                from_v = fmt_val(v.get('from'))
                to_v = fmt_val(v.get('to'))
                parts.append(f"{k_pt} de '{from_v}' para '{to_v}'")
            return f"Alteração - " + ", ".join(parts)

        elif log_action == "STATUS_CHANGED":
            if "status" in parsed:
                from_v = fmt_val(parsed["status"].get('from'))
                to_v = fmt_val(parsed["status"].get('to'))
                return f"Mudança de status de '{from_v}' para '{to_v}'"
            return "Mudança de status"

        elif log_action in ("DEADLINE_CREATED", "DEADLINE_UPDATED"):
            date_val = fmt_val(parsed.get("estimated_deadline", {}).get('to')) if "estimated_deadline" in parsed else ""
            desc_val = (parsed.get("estimated_deadline_desc", {}) or {}).get('to') or ""
            verb = "Criação" if log_action == "DEADLINE_CREATED" else "Alteração"
            if date_val:
                text = f"{verb} do Prazo Estimado para {date_val}"
            else:
                text = f"{verb} do Prazo Estimado"
            if desc_val:
                text += f" — descrição: {desc_val}"
            return text

        elif log_action == "DEADLINE_REMOVED":
            date_val = fmt_val(parsed.get("estimated_deadline", {}).get('to')) if "estimated_deadline" in parsed else ""
            desc_val = (parsed.get("estimated_deadline_desc", {}) or {}).get('to') or ""
            text = f"Remoção do Prazo Estimado"
            if date_val:
                text += f" ({date_val})"
            if desc_val:
                text += f" — descrição: {desc_val}"
            return text

        else:
            parts = []
            for k, v in parsed.items():
                k_pt = FIELD_TRANSLATIONS.get(k, k)
                from_v = fmt_val(v.get('from'))
                to_v = fmt_val(v.get('to'))
                parts.append(f"{k_pt} de '{from_v}' para '{to_v}'")
            return ", ".join(parts)

    def _buscar(self):
        # Clear previous results
        for i in reversed(range(self.results_layout.count())):
            item = self.results_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        project_id = self.cmb_project.currentData()
        limit = self.spin_count.value()

        from database.connection import get_db_cursor
        from gui.widgets.wiki_text_edit import render_links_as_html

        try:
            with get_db_cursor() as cursor:
                if project_id:
                    cursor.execute("SELECT id, name FROM projects WHERE id = ?", (project_id,))
                    projetos = cursor.fetchall()
                else:
                    cursor.execute("SELECT id, name FROM projects WHERE deleted_at IS NULL AND is_archived = 0 ORDER BY name")
                    projetos = cursor.fetchall()

                has_any = False
                for proj_data in projetos:
                    pid = proj_data["id"]
                    pname = proj_data["name"]

                    cursor.execute("""
                        SELECT t.id as task_id, t.title as task_title, t.parent_task_id, t.status as task_status,
                               al.id, al.action, al.changed_fields_json, al.created_at
                        FROM activity_logs al
                        JOIN tasks t ON t.id = al.entity_id AND al.entity_type = 'task'
                        WHERE t.project_id = ? AND t.deleted_at IS NULL AND t.is_archived = 0
                        ORDER BY t.id, al.created_at DESC
                    """, (pid,))
                    rows = cursor.fetchall()

                    if not rows:
                        continue

                    # Filtro: se "Exibir concluídos" estiver OFF, remove tarefas concluídas
                    show_concluidos = self.btn_concluidos.isChecked()
                    if not show_concluidos:
                        rows = [r for r in rows if (r["task_status"] or "").strip() != "Concluído"]

                    if not rows:
                        continue

                    # Filtro: se "Somente Comentários" estiver ON, mantém só COMENTÁRIO
                    if self.btn_comentarios.isChecked():
                        rows = [r for r in rows if ACTION_TRANSLATION.get(str(r["action"] or "").upper(), str(r["action"] or "").upper()) == "COMENTÁRIO"]

                    if not rows:
                        continue

                    # Group by task, preserving hierarquia
                    task_groups = defaultdict(list)
                    task_parent = {}
                    task_title = {}
                    task_status = {}
                    for row in rows:
                        task_groups[row["task_id"]].append(row)
                        task_parent[row["task_id"]] = row["parent_task_id"]
                        task_title[row["task_id"]] = row["task_title"]
                        task_status[row["task_id"]] = row["task_status"]

                    has_any = True

                    # Project collapsible section
                    proj_section = CollapsibleSection(f"📁 Projeto: {pname}", default_collapsed=False, accent="#e3a84a")
                    proj_section.header.setProperty("project_id", pid)
                    proj_section.header.setContextMenuPolicy(Qt.CustomContextMenu)
                    proj_section.header.customContextMenuRequested.connect(lambda pos, l=proj_section.header: self._show_project_menu(l, pos))
                    proj_section.header.installEventFilter(self)
                    self.results_layout.addWidget(proj_section)

                    children = defaultdict(list)
                    roots = []
                    for tid in task_groups.keys():
                        pid_par = task_parent.get(tid)
                        if pid_par is not None and pid_par in task_groups:
                            children[pid_par].append(tid)
                        else:
                            roots.append(tid)

                    def render_task(tid, depth):
                        logs = task_groups[tid][:limit]
                        title = task_title[tid]

                        accent, bg_color = DEPTH_PALETTE[depth % len(DEPTH_PALETTE)]
                        is_concluida = (task_status.get(tid, "") or "").strip() == "Concluído"
                        if is_concluida:
                            accent = "#27ae60"
                            bg_color = "#12241A"

                        task_section = CollapsibleSection(title, default_collapsed=False, accent=accent, depth=depth, bg=bg_color)
                        task_section.header.setProperty("task_id", tid)
                        task_section.header.setContextMenuPolicy(Qt.CustomContextMenu)
                        task_section.header.customContextMenuRequested.connect(lambda pos, l=task_section.header: self._show_task_menu(l, pos))
                        task_section.header.installEventFilter(self)
                        if is_concluida:
                            task_section.setObjectName("task_concluida")
                            task_section.body.setObjectName("task_concluida_body")
                            task_section.setStyleSheet(
                                "QWidget#task_concluida { background: transparent; }"
                                "QWidget#task_concluida_body { background: rgba(39, 174, 96, 0.10);"
                                " border-left: 3px solid #27ae60; border-radius: 6px;"
                                " padding: 4px 6px 6px 6px; }"
                            )
                        else:
                            task_section.body.setStyleSheet(
                                f"QWidget {{ background: {bg_color}; border-radius: 6px;"
                                f" border-left: 3px solid {accent}; padding: 4px 6px 6px 6px; }}"
                            )
                        block_layout = task_section.body_layout

                        for log in logs:
                            action = log["action"]
                            action_pt = ACTION_TRANSLATION.get(action.upper(), action)
                            color = COLOR_MAPPING.get(action_pt, "#ffffff")
                            raw_details = log["changed_fields_json"] or ""
                            details = self._format_details(log["action"], raw_details, title)

                            # Format date as Brazilian
                            try:
                                dt = datetime.fromisoformat(str(log["created_at"]).split('.')[0])
                                date_str = dt.strftime("%d/%m/%Y %H:%M")
                            except Exception:
                                date_str = str(log["created_at"])

                            # Render with active links
                            html = render_links_as_html(details) or details
                            styled_html = (
                                f'<div style="padding: 2px 0 2px 6px;'
                                f' border-left: 3px solid {color}; border-radius: 2px;">'
                                f'<span style="color: #9aa0a6;">[{date_str}]</span> '
                                f'<span style="color: {color}; font-weight: bold;">{action_pt}</span>: '
                                f'<span style="color: #cdd3dc;">{html}</span>'
                                f'</div>'
                            )

                            lbl = QLabel(styled_html)
                            lbl.setTextFormat(Qt.RichText)
                            lbl.setWordWrap(True)
                            lbl.linkActivated.connect(self._on_link_clicked_str)
                            lbl.setStyleSheet("color: #e0e0e0; font-size: 12px; padding: 0px; margin: 0px; background: transparent;")
                            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                            block_layout.addWidget(lbl)

                        for sub in sorted(children.get(tid, []), key=lambda x: task_title.get(x, "")):
                            block_layout.addWidget(render_task(sub, depth + 1))

                        return task_section

                    for t_root in sorted(roots, key=lambda x: task_title.get(x, "")):
                        proj_section.body_layout.addWidget(render_task(t_root, 0))

                if not has_any:
                    no_data = QLabel("Nenhum registro encontrado.")
                    no_data.setStyleSheet("color: #888; font-size: 14px; padding: 40px;")
                    no_data.setAlignment(Qt.AlignCenter)
                    self.results_layout.addWidget(no_data)

                self.results_layout.addStretch()

        except Exception as e:
            import traceback
            err_lbl = QLabel(f"Erro ao buscar: {str(e)}")
            err_lbl.setStyleSheet("color: #e53935; padding: 20px;")
            self.results_layout.addWidget(err_lbl)
            self.results_layout.addStretch()
            traceback.print_exc()

    def _on_link_clicked_str(self, url_str):
        from PySide6.QtCore import QUrl
        self._on_link_clicked(QUrl(url_str))

    def _show_project_menu(self, label, pos):
        pid = label.property("project_id")
        if not pid:
            return
        menu = QMenu(self)
        act = QAction("📁 Abrir Projeto", self)
        act.triggered.connect(lambda: self._navigate_to("project", pid))
        menu.addAction(act)
        menu.exec(label.mapToGlobal(pos))

    def _show_task_menu(self, label, pos):
        tid = label.property("task_id")
        if not tid:
            return
        menu = QMenu(self)
        act = QAction("📋 Abrir Tarefa", self)
        act.triggered.connect(lambda: self._navigate_to("task", tid))
        menu.addAction(act)
        menu.exec(label.mapToGlobal(pos))

    def _navigate_to(self, t_type, t_id):
        from core.event_bus import event_bus
        event_bus.emit("navigate_to", {"type": t_type, "id": t_id})

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonDblClick and isinstance(obj, QWidget):
            pid = obj.property("project_id")
            tid = obj.property("task_id")
            if pid:
                self._navigate_to("project", pid)
                return True
            if tid:
                self._navigate_to("task", tid)
                return True
        return super().eventFilter(obj, event)

    def _on_link_clicked(self, url):
        scheme = url.scheme()
        if scheme == "app":
            t_type = url.host()
            t_id_str = url.path().strip("/")
            if t_id_str.isdigit():
                from core.event_bus import event_bus
                event_bus.emit("navigate_to", {"type": t_type, "id": int(t_id_str)})
        elif scheme == "file":
            f_uuid = url.path().strip("/")
            if not f_uuid:
                return
            from database.connection import get_db_cursor
            from models.entities import Attachment
            try:
                with get_db_cursor() as cursor:
                    cursor.execute("SELECT * FROM attachments WHERE deleted_at IS NULL")
                    for row in cursor.fetchall():
                        att = Attachment(**dict(row))
                        if att.uuid == f_uuid:
                            import subprocess, os
                            if os.path.exists(att.file_path):
                                subprocess.Popen(["explorer", att.file_path] if os.name == "nt" else ["xdg-open", att.file_path])
                            break
            except Exception:
                pass
