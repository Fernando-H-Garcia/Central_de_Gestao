from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QScrollArea, QFrame,
    QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from gui.components.page_header import PageHeader
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
}
COLOR_MAPPING = {
    "CRIADO": "#4caf50",
    "ATUALIZADO": "#2196f3",
    "MUDANÇA DE STATUS": "#ff9800",
    "COMENTÁRIO": "#e91e63",
    "ARQUIVADO": "#ff9800",
    "RESTAURADO": "#4caf50",
}

FIELD_TRANSLATIONS = {
    "title": "título",
    "due_date": "prazo",
    "energy_level": "prioridade",
    "status": "status",
    "alert_date": "data do alerta",
    "alert_message": "mensagem do alerta",
    "context": "contexto",
    "project_id": "projeto",
}

def fmt_val(val):
    if val is None or val == "None" or str(val).strip() == "":
        return "vazio"
    return str(val)


class ActivitySummaryQt(QWidget):
    go_back = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

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

        btn_buscar = QPushButton("🔍 Buscar")
        btn_buscar.setObjectName("secondary")
        btn_buscar.setFixedWidth(120)
        btn_buscar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        btn_buscar.clicked.connect(self._buscar)

        # Center the controls horizontally
        panel_layout.addStretch()
        panel_layout.addLayout(col_proj)
        panel_layout.addLayout(col_reg)
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
                    cursor.execute("SELECT id, name FROM projects WHERE deleted_at IS NULL ORDER BY name")
                    projetos = cursor.fetchall()

                has_any = False
                for proj_data in projetos:
                    pid = proj_data["id"]
                    pname = proj_data["name"]

                    cursor.execute("""
                        SELECT t.id as task_id, t.title as task_title, 
                               al.id, al.action, al.changed_fields_json, al.created_at
                        FROM activity_logs al
                        JOIN tasks t ON t.id = al.entity_id AND al.entity_type = 'task'
                        WHERE t.project_id = ? AND t.deleted_at IS NULL
                        ORDER BY t.id, al.created_at DESC
                    """, (pid,))
                    rows = cursor.fetchall()

                    if not rows:
                        continue

                    # Group by task
                    task_groups = defaultdict(list)
                    for row in rows:
                        task_groups[row["task_id"]].append(row)

                    has_any = True

                    # Project header
                    proj_header = QLabel(f"Projeto: {pname}")
                    proj_font = QFont()
                    proj_font.setPointSize(14)
                    proj_font.setBold(True)
                    proj_header.setFont(proj_font)
                    proj_header.setStyleSheet("color: #e3a84a; padding: 8px 0 4px 0;")
                    self.results_layout.addWidget(proj_header)

                    for task_id in sorted(task_groups.keys()):
                        logs = task_groups[task_id][:limit]
                        task_title = logs[0]["task_title"]

                        # Task header
                        task_lbl = QLabel(task_title)
                        task_font = QFont()
                        task_font.setPointSize(12)
                        task_font.setBold(True)
                        task_lbl.setFont(task_font)
                        task_lbl.setStyleSheet("color: #e67e22; padding: 2px 0 2px 20px;")
                        self.results_layout.addWidget(task_lbl)

                        for log in logs:
                            action = log["action"]
                            action_pt = ACTION_TRANSLATION.get(action.upper(), action)
                            color = COLOR_MAPPING.get(action_pt, "#ffffff")
                            raw_details = log["changed_fields_json"] or ""
                            details = self._format_details(log["action"], raw_details, task_title)

                            # Format date as Brazilian
                            try:
                                dt = datetime.fromisoformat(str(log["created_at"]).split('.')[0])
                                date_str = dt.strftime("%d/%m/%Y %H:%M")
                            except Exception:
                                date_str = str(log["created_at"])

                            # Render with active links
                            html = render_links_as_html(details) or details
                            styled_html = (
                                f'<div style="padding: 2px 40px;">'
                                f'<span style="color: #2ecc71;">[{date_str}]</span> '
                                f'<span style="color: {color}; font-weight: bold;">{action_pt}</span>: '
                                f'<span style="color: #e0e0e0;">{html}</span>'
                                f'</div>'
                            )

                            lbl = QLabel(styled_html)
                            lbl.setTextFormat(Qt.RichText)
                            lbl.setWordWrap(True)
                            lbl.linkActivated.connect(self._on_link_clicked_str)
                            lbl.setStyleSheet("color: #e0e0e0; font-size: 12px; padding: 0px; margin: 0px; background: transparent;")
                            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                            self.results_layout.addWidget(lbl)

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
