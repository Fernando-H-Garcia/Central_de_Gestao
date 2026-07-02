from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QSplitter, QFrame,
    QTreeWidget, QTreeWidgetItem, QHeaderView,
    QLineEdit, QComboBox, QMenu, QMessageBox,
    QScrollArea, QDialog, QTextBrowser, QListWidget,
    QListWidgetItem, QFileDialog, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer, QEvent, QRect, QSize
from PySide6.QtGui import QAction, QFont, QFontMetrics, QTextCursor, QKeyEvent, QPainter
from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from services.knowledge_page_service import KnowledgePageService

ENTITY_TYPE_LABELS = {
    "project": "Projeto", "task": "Tarefa", "idea": "Ideia",
    "wiki": "Documento", "knowledge_page": "Documento", "note": "Nota",
}
ENTITY_ICONS = {
    "project": "📁", "task": "📋", "idea": "💡",
    "wiki": "📖", "knowledge_page": "📖", "note": "📝",
}


class WordWrapDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        text = index.data(Qt.DisplayRole) or ""
        rect = option.rect
        if option.state & QStyle.State_Selected:
            painter.fillRect(rect, option.palette.highlight())
        rect.adjust(4, 2, -4, -2)
        painter.setPen(option.palette.windowText().color())
        painter.drawText(rect, Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignVCenter, text)
        painter.restore()

    def sizeHint(self, option, index):
        text = index.data(Qt.DisplayRole) or ""
        fm = QFontMetrics(option.font)
        tw = option.rect.width() - 8
        if tw < 50:
            tw = 200
        r = fm.boundingRect(QRect(0, 0, tw, 0), Qt.TextWordWrap, text)
        return QSize(tw + 8, r.height() + 10)


class WikiQt(QWidget):
    def __init__(self):
        super().__init__()
        self.page_service = KnowledgePageService()
        self.current_page = None
        self._original_page = None
        self._is_preview = True
        self.show_archived = False

        self.setup_ui()
        self.load_pages()

        from core.event_bus import event_bus
        event_bus.subscribe("snapshot_updated", self._safe_reload)
        event_bus.subscribe("navigate_to", self._on_navigate_to)
        self.destroyed.connect(self._cleanup_snapshot)

    def _cleanup_snapshot(self):
        from core.event_bus import event_bus
        event_bus.unsubscribe("snapshot_updated", self._safe_reload)
        event_bus.unsubscribe("navigate_to", self._on_navigate_to)

    def _safe_reload(self, _=None):
        try:
            self.load_pages()
        except RuntimeError:
            pass

    def hideEvent(self, event):
        if self._has_unsaved_changes():
            self._confirm_save_before_leave()
        super().hideEvent(event)

    def _on_navigate_to(self, payload: dict):
        if payload.get("type") in ("wiki", "knowledge_page"):
            pid = payload.get("id")
            if pid:
                self._open_page_by_id(pid)

    def setup_ui(self):
        if not hasattr(self.__class__, '_tooltip_styled'):
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.setStyleSheet(app.styleSheet() + """
                    QToolTip {
                        background-color: #1e1e3a;
                        color: #ffffff;
                        border: 1px solid #3a3a6a;
                        border-radius: 4px;
                        padding: 8px;
                        font-size: 12px;
                    }
                """)
            self.__class__._tooltip_styled = True
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)

        sidebar = QFrame()
        sidebar.setObjectName("wiki_sidebar")
        sidebar.setStyleSheet("""
            QFrame#wiki_sidebar {
                background-color: #13131f;
                border-right: 1px solid #2a2a3f;
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 14, 10, 10)
        sidebar_layout.setSpacing(8)

        lbl = QLabel("📚 Documentação")
        lbl.setStyleSheet("font-size: 17px; font-weight: bold;")
        sidebar_layout.addWidget(lbl)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Buscar página...")
        self.search_bar.textChanged.connect(self._filter_tree)
        sidebar_layout.addWidget(self.search_bar)

        btn_new = QPushButton("📄 + Nova Página")
        btn_new.setObjectName("secondary")
        btn_new.clicked.connect(self._new_page)
        sidebar_layout.addWidget(btn_new)

        self.btn_archived = QPushButton("📦 Arquivados: OFF")
        self.btn_archived.setObjectName("secondary")
        self.btn_archived.setCheckable(True)
        self.btn_archived.clicked.connect(self.toggle_archived)
        sidebar_layout.addWidget(self.btn_archived)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setItemDelegate(WordWrapDelegate(self.tree))
        self.tree.setIndentation(14)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.installEventFilter(self)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: transparent;
                border: none;
            }
            QTreeWidget::item {
                padding: 3px 2px;
                border-radius: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #2d2d55;
            }
        """)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_context_menu)
        sidebar_layout.addWidget(self.tree, stretch=1)

        editor_container = QWidget()
        editor_container.setStyleSheet("background-color: #0b0b14;")
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(20, 20, 20, 20)
        editor_layout.setSpacing(8)

        # Title row (editable title + archived badge)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self.title_edit = QLineEdit("Selecione ou crie uma página")
        self.title_edit.setReadOnly(True)
        self.title_edit.setStyleSheet("""
            QLineEdit {
                font-size: 22px; font-weight: bold; color: #fff;
                background-color: transparent; border: none; padding: 2px 4px;
            }
            QLineEdit:focus {
                border: 1px solid #4a6fe3; border-radius: 4px;
                background-color: #1c1c2e;
            }
        """)
        title_row.addWidget(self.title_edit, stretch=1)

        self.lbl_archived_badge = QLabel("📦 ARQUIVADO")
        self.lbl_archived_badge.setStyleSheet("""
            background-color: #444466;
            color: #666666;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 10px;
            border-radius: 4px;
        """)
        self.lbl_archived_badge.setVisible(False)
        title_row.addWidget(self.lbl_archived_badge)

        editor_layout.addLayout(title_row)

        # ── Reference buttons + toolbar ──
        ref_bar = QHBoxLayout()
        from gui.components.references_panel_qt import ReferencesPanelQt
        self.refs_panel = ReferencesPanelQt(entity_type="wiki", entity_id=0, parent=self)
        ref_bar.addWidget(self.refs_panel)
        ref_bar.addStretch()

        self.btn_read = QPushButton("📖 Leitura")
        self.btn_read.setCheckable(True)
        self.btn_read.setChecked(True)
        self.btn_read.setStyleSheet("""
            QPushButton {
                padding: 6px 14px; border-radius: 5px; font-weight: bold;
                background-color: #4a6fe3; color: #fff; border: none;
            }
            QPushButton:hover { background-color: #6384f5; }
            QPushButton:!checked { background-color: transparent; color: #aaa; border: 1px solid #555; }
            QPushButton:!checked:hover { background-color: #2d2d55; color: #fff; border: 1px solid #4a6fe3; }
        """)
        self.btn_read.clicked.connect(self._set_read_mode)
        ref_bar.addWidget(self.btn_read)

        self.btn_edit_mode = QPushButton("✏️ Editar")
        self.btn_edit_mode.setCheckable(True)
        self.btn_edit_mode.setStyleSheet("""
            QPushButton {
                padding: 6px 14px; border-radius: 5px; font-weight: bold;
                background-color: #4a6fe3; color: #fff; border: none;
            }
            QPushButton:hover { background-color: #6384f5; }
            QPushButton:!checked { background-color: transparent; color: #aaa; border: 1px solid #555; }
            QPushButton:!checked:hover { background-color: #2d2d55; color: #fff; border: 1px solid #4a6fe3; }
        """)
        self.btn_edit_mode.clicked.connect(self._set_edit_mode)
        ref_bar.addWidget(self.btn_edit_mode)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.btn_read)
        self.mode_group.addButton(self.btn_edit_mode)

        self.btn_save = QPushButton("💾 Salvar")
        self.btn_save.setStyleSheet("""
            QPushButton {
                padding: 6px 14px; border-radius: 5px; font-weight: bold;
                background-color: #2b8c52; color: #fff; border: none;
            }
            QPushButton:hover { background-color: #3bbf6e; }
        """)
        self.btn_save.clicked.connect(self.save_page)
        ref_bar.addWidget(self.btn_save)
        editor_layout.addLayout(ref_bar)

        # ── Meta data bar ──
        meta_frame = QFrame()
        meta_frame.setStyleSheet("QFrame { background-color: #1c1c2e; border-radius: 8px; padding: 6px; }")
        meta_layout = QHBoxLayout(meta_frame)
        meta_layout.setContentsMargins(10, 8, 10, 8)
        meta_layout.setSpacing(14)

        meta_layout.addWidget(QLabel("Pai:"))
        self.cmb_parent = QComboBox()
        self.cmb_parent.setMinimumWidth(160)
        self.cmb_parent.setStyleSheet("font-size: 12px;")
        meta_layout.addWidget(self.cmb_parent)

        meta_layout.addWidget(QLabel("Categoria:"))
        self.ent_category = QLineEdit()
        self.ent_category.setPlaceholderText("Ex: Processos")
        self.ent_category.setMinimumWidth(130)
        self.ent_category.setStyleSheet("font-size: 12px;")
        meta_layout.addWidget(self.ent_category)

        meta_layout.addWidget(QLabel("Tags:"))
        self.ent_tags = QLineEdit()
        self.ent_tags.setPlaceholderText("Ex: api, backend, v2")
        self.ent_tags.setMinimumWidth(150)
        self.ent_tags.setStyleSheet("font-size: 12px;")
        meta_layout.addWidget(self.ent_tags)

        meta_layout.addStretch()
        editor_layout.addWidget(meta_frame)

        # ── Content area: editor + attachments sidebar ──
        content_row = QHBoxLayout()
        content_row.setSpacing(10)

        # Left: editor column
        editor_col = QVBoxLayout()
        editor_col.setContentsMargins(0, 0, 0, 0)
        editor_col.setSpacing(8)

        # ── Top formatting toolbar (font size, color) ──
        def _sep_v():
            line = QFrame()
            line.setFrameShape(QFrame.VLine)
            line.setStyleSheet("color: #2a2a3f; margin: 0 2px; max-width: 1px;")
            return line

        top_fmt = QFrame()
        top_fmt.setObjectName("top_fmt_toolbar")
        top_fmt.setStyleSheet("""
            QFrame#top_fmt_toolbar {
                background-color: #1c1c2e;
                border: 1px solid #2a2a3f;
                border-radius: 6px;
                padding: 4px 6px;
            }
            QPushButton {
                background-color: #2a2a3f; color: #ccc;
                border: none; border-radius: 4px;
                font-size: 11px; min-height: 24px; max-height: 24px;
                padding: 2px 8px;
            }
            QPushButton:hover { background-color: #4a6fe3; color: #fff; }
            QPushButton:pressed { background-color: #6384f5; }
            QComboBox {
                background-color: #2a2a3f; color: #ccc;
                border: none; border-radius: 4px;
                font-size: 11px; min-height: 24px; max-height: 24px;
                padding: 2px 6px;
            }
            QComboBox:hover { background-color: #3a3a5f; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #1c1c2e; color: #ccc;
                selection-background-color: #4a6fe3;
                border: 1px solid #2a2a3f;
            }
        """)
        top_fmt_layout = QHBoxLayout(top_fmt)
        top_fmt_layout.setContentsMargins(6, 4, 6, 4)
        top_fmt_layout.setSpacing(6)
        top_fmt_layout.setAlignment(Qt.AlignLeft)

        # Font size
        lbl_tamanho = QLabel("Tamanho:")
        lbl_tamanho.setStyleSheet("background: transparent; color: #ccc;")
        top_fmt_layout.addWidget(lbl_tamanho)
        self.cmb_font_size = QComboBox()
        self.cmb_font_size.addItems(["12", "14", "16", "18", "24", "32"])
        self.cmb_font_size.setCurrentText("14")
        self.cmb_font_size.currentTextChanged.connect(self._fmt_apply_size)
        top_fmt_layout.addWidget(self.cmb_font_size)

        top_fmt_layout.addWidget(_sep_v())

        # Text color
        self.btn_fmt_color = QPushButton("Cor")
        self.btn_fmt_color.setToolTip("Alterar cor do texto selecionado")
        self.btn_fmt_color.clicked.connect(self._fmt_color)
        top_fmt_layout.addWidget(self.btn_fmt_color)

        top_fmt_layout.addWidget(_sep_v())

        # Inline style quick buttons
        self.btn_fmt_bold_top = QPushButton("B")
        self.btn_fmt_bold_top.setToolTip("Negrito (**)")
        self.btn_fmt_bold_top.setStyleSheet("font-weight: bold;")
        self.btn_fmt_bold_top.clicked.connect(self._fmt_bold)
        top_fmt_layout.addWidget(self.btn_fmt_bold_top)

        self.btn_fmt_italic_top = QPushButton("I")
        self.btn_fmt_italic_top.setToolTip("Itálico (*)")
        self.btn_fmt_italic_top.setStyleSheet("font-style: italic;")
        self.btn_fmt_italic_top.clicked.connect(self._fmt_italic)
        top_fmt_layout.addWidget(self.btn_fmt_italic_top)

        self.btn_fmt_underline_top = QPushButton("U")
        self.btn_fmt_underline_top.setToolTip("Sublinhado (<u>)")
        self.btn_fmt_underline_top.setStyleSheet("text-decoration: underline;")
        self.btn_fmt_underline_top.clicked.connect(self._fmt_underline)
        top_fmt_layout.addWidget(self.btn_fmt_underline_top)

        top_fmt_layout.addStretch()
        self._fmt_topbar = top_fmt
        editor_col.addWidget(top_fmt)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "Escreva sua documentação em Markdown...\n\n"
            "# Título\n## Sub-título\n**negrito**, *itálico*, `código`\n"
            "- lista\n\n[[ para referenciar tarefa/projeto/doc\n{{ para referenciar arquivo"
        )
        font = QFont("Consolas", 12)
        self.text_edit.setFont(font)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1c1c2e;
                color: #e0e0e0;
                border: 1px solid #2a2a3f;
                border-radius: 6px;
                padding: 12px;
            }
        """)
        self.text_edit.textChanged.connect(self._on_text_changed)
        self.text_edit.installEventFilter(self)
        editor_col.addWidget(self.text_edit, stretch=1)

        self.preview_area = QTextBrowser()
        self.preview_area.setOpenLinks(False)
        self.preview_area.anchorClicked.connect(self._on_link_clicked)
        self.preview_area.setReadOnly(True)
        self.preview_area.setStyleSheet("""
            QTextBrowser {
                background-color: #1a1a2e;
                color: #e0e0e0;
                border: 1px solid #2a2a3f;
                border-radius: 6px;
                padding: 16px;
                font-size: 14px;
            }
        """)
        editor_col.addWidget(self.preview_area, stretch=1)

        content_row.addLayout(editor_col, stretch=1)

        # Center: formatting toolbar (visible only in edit mode)
        fmt_panel = QFrame()
        fmt_panel.setFixedWidth(95)
        fmt_panel.setObjectName("fmt_toolbar")
        fmt_panel.setStyleSheet("""
            QFrame#fmt_toolbar {
                background-color: #1c1c2e;
                border: 1px solid #2a2a3f;
                border-radius: 6px;
            }
        """)
        fmt_layout = QVBoxLayout(fmt_panel)
        fmt_layout.setContentsMargins(4, 6, 4, 6)
        fmt_layout.setSpacing(3)
        fmt_layout.setAlignment(Qt.AlignTop)

        fmt_btn_style = """
            QPushButton {
                background-color: #2a2a3f;
                color: #ccc;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                min-height: 26px;
                max-height: 26px;
                padding: 2px 4px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #4a6fe3;
                color: #fff;
            }
            QPushButton:pressed {
                background-color: #6384f5;
            }
        """

        def _fmt_btn(text, tooltip, slot):
            btn = QPushButton(text)
            btn.setToolTip(tooltip)
            btn.setStyleSheet(fmt_btn_style)
            btn.clicked.connect(slot)
            return btn

        def _sep():
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setStyleSheet("color: #2a2a3f; margin: 0 2px;")
            return line

        # Heading group
        fmt_layout.addWidget(_fmt_btn("# Título 1",
            "Título nível 1 (#)\n\nInsere '#' no início da linha para criar um título principal.\nUse para o nome da página ou seções principais.", self._fmt_heading1))
        fmt_layout.addWidget(_fmt_btn("## Título 2",
            "Título nível 2 (##)\n\nInsere '##' no início da linha para criar um subtítulo.\nUse para agrupar seções dentro de um Título 1.", self._fmt_heading2))
        fmt_layout.addWidget(_fmt_btn("### Título 3",
            "Título nível 3 (###)\n\nInsere '###' no início da linha para criar um sub-subtítulo.\nUse para detalhar seções dentro de um Título 2.", self._fmt_heading3))
        fmt_layout.addSpacing(2)
        fmt_layout.addWidget(_sep())

        # Inline group
        fmt_layout.addWidget(_fmt_btn("B Negrito",
            "Negrito (**)\n\nEnvolve o texto selecionado com ** ** para destacar em negrito.\nSe não houver seleção, insere os marcadores vazios.", self._fmt_bold))
        fmt_layout.addWidget(_fmt_btn("I Itálico",
            "Itálico (*)\n\nEnvolve o texto selecionado com * * para destacar em itálico.\nSe não houver seleção, insere os marcadores vazios.", self._fmt_italic))
        fmt_layout.addWidget(_fmt_btn("S Riscado",
            "Riscado (~~)\n\nEnvolve o texto selecionado com ~~ ~~ para texto riscado.\nSe não houver seleção, insere os marcadores vazios.", self._fmt_strikethrough))
        fmt_layout.addSpacing(2)
        fmt_layout.addWidget(_sep())

        # List group
        fmt_layout.addWidget(_fmt_btn("• Lista",
            "Lista não ordenada (-)\n\nInsere '- ' no início da linha para criar uma lista com marcadores.\nUse para listar itens sem ordem específica.", self._fmt_bullet_list))
        fmt_layout.addWidget(_fmt_btn("1. Lista Num.",
            "Lista numerada (1.)\n\nInsere '1. ' no início da linha para criar uma lista numerada.\nUse para passos ou itens com ordem definida.", self._fmt_numbered_list))
        fmt_layout.addWidget(_fmt_btn("☐ Tarefa",
            "Lista de tarefas (- [ ])\n\nInsere '- [ ] ' no início da linha para criar uma checklist.\nMarque manualmente o [ ] com [x] para concluir.", self._fmt_task_list))
        fmt_layout.addSpacing(2)
        fmt_layout.addWidget(_sep())

        # Block group
        fmt_layout.addWidget(_fmt_btn("❝ Citação",
            "Citação (>)\n\nInsere '> ' no início da linha para criar uma citação ou blockquote.\nUse para destacar citações externas ou observações.", self._fmt_quote))
        fmt_layout.addWidget(_fmt_btn("` Código",
            "Código inline (`)\n\nEnvolve o texto selecionado com ` ` para código monoespaçado.\nUse para trechos curtos de código ou comandos.", self._fmt_code))
        fmt_layout.addWidget(_fmt_btn("⎔ Bloco Cód.",
            "Bloco de código (```)\n\nInsere um bloco de código multilinha delimitado por ```.\nSe houver texto selecionado, envolve-o no bloco.\nUse para trechos maiores de código.", self._fmt_code_block))
        fmt_layout.addSpacing(2)
        fmt_layout.addWidget(_sep())

        # Insert group
        fmt_layout.addWidget(_fmt_btn("🔗 Link",
            "Inserir link: [texto](url)\n\nCria um link clicável.\nSe houver texto selecionado, ele vira o texto âncora.\nSubstitua '(url)' pelo endereço de destino.", self._fmt_link))
        fmt_layout.addWidget(_fmt_btn("🖼 Imagem",
            "Inserir imagem: ![descrição](url)\n\nInsere uma imagem com descrição alternativa.\nSubstitua '(url)' pelo endereço da imagem.\nA descrição é exibida se a imagem não carregar.", self._fmt_image))
        fmt_layout.addWidget(_fmt_btn("— Linha",
            "Linha horizontal (---)\n\nInsere '---' em uma nova linha para criar uma linha horizontal.\nUse para separar visualmente seções do documento.", self._fmt_hr))

        fmt_layout.addStretch()
        self._fmt_panel = fmt_panel
        content_row.addWidget(fmt_panel)

        # Right: attachments sidebar
        attach_frame = QFrame()
        attach_frame.setFixedWidth(280)
        attach_frame.setStyleSheet("QFrame { background-color: #1c1c2e; border-radius: 6px; padding: 6px; }")
        attach_layout = QVBoxLayout(attach_frame)
        attach_layout.setContentsMargins(10, 8, 10, 8)
        attach_layout.setSpacing(6)

        attach_header = QHBoxLayout()
        lbl_attach = QLabel("📎 Anexos")
        lbl_attach.setStyleSheet("font-weight: bold; font-size: 13px;")
        attach_header.addWidget(lbl_attach)
        attach_header.addStretch()

        self.btn_attach = QPushButton("📎 Anexar")
        self.btn_attach.setStyleSheet("""
            QPushButton {
                padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 12px;
                background-color: #4a6fe3; color: #fff; border: none;
            }
            QPushButton:hover { background-color: #6384f5; }
        """)
        self.btn_attach.clicked.connect(self._attach_file_dialog)
        attach_header.addWidget(self.btn_attach)

        attach_layout.addLayout(attach_header)

        self.lst_attachments = QListWidget()
        self.lst_attachments.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: 1px solid #2a2a3f;
                border-radius: 4px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 4px 6px;
            }
        """)
        self.lst_attachments.setAcceptDrops(True)
        self.lst_attachments.installEventFilter(self)
        self.lst_attachments.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lst_attachments.customContextMenuRequested.connect(self._attach_context_menu)
        self.lst_attachments.itemDoubleClicked.connect(self._open_attachment)
        attach_layout.addWidget(self.lst_attachments, stretch=1)

        content_row.addWidget(attach_frame)
        editor_layout.addLayout(content_row, stretch=1)

        splitter.addWidget(sidebar)
        splitter.addWidget(editor_container)
        splitter.setSizes([260, 840])
        root.addWidget(splitter)

        self._set_editor_enabled(False)

    # ─── Autocomplete state ──────────────────────────────────────────
    _autocomplete_popup = None
    _autocomplete_list = None
    _autocomplete_trigger = None
    _autocomplete_type = None

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
        from PySide6.QtWidgets import QListWidget, QFrame, QVBoxLayout
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
            label = c["label"]
            wi = QListWidgetItem(label)
            wi.setData(Qt.UserRole, c)
            lst.addItem(wi)
        lst.setMinimumWidth(300)
        lst.setMaximumWidth(450)
        lst.setMaximumHeight(250)
        lst.itemClicked.connect(self._autocomplete_select)

        layout.addWidget(lst)
        self._autocomplete_popup = popup
        self._autocomplete_list = lst
        self._autocomplete_trigger = cursor_pos

        cursor_rect = self.text_edit.cursorRect(self.text_edit.textCursor())
        global_pos = self.text_edit.viewport().mapToGlobal(cursor_rect.bottomLeft())
        popup.move(global_pos)
        popup.show()
        lst.setFocus()
        lst.setCurrentRow(0)

    def _get_linkable_entities(self):
        candidates = []
        try:
            from services.link_service import LinkService
            items = LinkService().get_all_linkable_entities()
            for it in items:
                icon = ENTITY_ICONS.get(it["type"], "🔗")
                label_pt = ENTITY_TYPE_LABELS.get(it["type"], it["type"].capitalize())
                candidates.append({
                    "type": it["type"],
                    "id": it["id"],
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

            parent_cache = {}
            def _parent_exists(etype, eid):
                key = (etype, eid)
                if key not in parent_cache:
                    table_map = {
                        "project": "projects",
                        "task": "tasks",
                        "idea": "ideas",
                        "knowledge_page": "knowledge_pages",
                        "note": "notes",
                        "event": "events",
                    }
                    tbl = table_map.get(etype)
                    if not tbl:
                        parent_cache[key] = False
                        return False
                    with get_db_cursor() as cursor:
                        cursor.execute(f"SELECT 1 FROM {tbl} WHERE id = ? AND deleted_at IS NULL", (eid,))
                        parent_cache[key] = cursor.fetchone() is not None
                return parent_cache[key]

            seen_uuids = set()
            for row in rows:
                att = Attachment(**dict(row))
                if att.uuid in seen_uuids:
                    continue
                if not _parent_exists(att.entity_type, att.entity_id):
                    continue
                seen_uuids.add(att.uuid)
                page_id = att.entity_id if att.entity_type == "knowledge_page" else None
                location = f" (pg #{page_id})" if page_id else ""
                candidates.append({
                    "type": "file",
                    "id": att.id,
                    "title": att.file_name,
                    "uuid": att.uuid,
                    "file_path": att.file_path,
                    "label": f"📎 {att.file_name}{location}",
                })
        except Exception:
            pass
        return candidates

    def _autocomplete_select(self, item):
        data = item.data(Qt.UserRole)
        if not data:
            self._close_autocomplete()
            return

        cursor = self.text_edit.textCursor()
        pos = cursor.position()
        cursor.setPosition(self._autocomplete_trigger)
        cursor.setPosition(pos, QTextCursor.KeepAnchor)
        selected_text = cursor.selectedText()

        if self._autocomplete_type == "link":
            replacement = f"[[{data['type']}:{data['id']}|{data['title']}]]"
        else:
            replacement = f"{{{{{data['uuid']}|{data['title']}}}}}"

        cursor.insertText(replacement)
        self._close_autocomplete()

    def _update_autocomplete_filter(self):
        if not self._autocomplete_popup or not self._autocomplete_list or self._autocomplete_trigger is None:
            return
        text = self.text_edit.toPlainText()
        pos = self.text_edit.textCursor().position()
        query = text[self._autocomplete_trigger + 2:pos].lower().strip()
        lst = self._autocomplete_list
        for i in range(lst.count()):
            item = lst.item(i)
            data = item.data(Qt.UserRole)
            if data:
                title = data.get("title", "").lower()
                item.setHidden(query not in title)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QKeyEvent

        if not hasattr(self, 'text_edit'):
            return super().eventFilter(obj, event)

        if obj == self.text_edit:
            if event.type() == QEvent.KeyRelease:
                ke = event
                key = ke.key()
                if key in (Qt.Key_BracketLeft, Qt.Key_BraceLeft):
                    cursor = self.text_edit.textCursor()
                    pos = cursor.position()
                    text = self.text_edit.toPlainText()
                    start = max(0, pos - 2)
                    snippet = text[start:pos]
                    if snippet == "[[" or snippet == "{{":
                        self._show_autocomplete(snippet, pos - 2)
                elif key == Qt.Key_Escape:
                    self._close_autocomplete()
                elif self._autocomplete_popup:
                    self._update_autocomplete_filter()

            if self._autocomplete_popup and event.type() == QEvent.KeyPress:
                ke = event
                lst = self._autocomplete_list
                if ke.key() == Qt.Key_Down:
                    row = lst.currentRow()
                    lst.setCurrentRow(min(row + 1, lst.count() - 1))
                    return True
                elif ke.key() == Qt.Key_Up:
                    row = lst.currentRow()
                    lst.setCurrentRow(max(row - 1, 0))
                    return True
                elif ke.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                    item = lst.currentItem()
                    if item:
                        self._autocomplete_select(item)
                    return True

        # Drag-drop for attachments (both text area and list)
        if obj in (self.text_edit, self.lst_attachments):
            if event.type() in (QEvent.DragEnter, QEvent.DragMove):
                if event.mimeData().hasUrls():
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Drop:
                from services.attachment_service import AttachmentService
                urls = event.mimeData().urls()
                if urls and self.current_page:
                    for url in urls:
                        file_path = url.toLocalFile()
                        if file_path:
                            try:
                                AttachmentService().add_attachment(file_path, "knowledge_page", self.current_page.id)
                                self._load_attachments()
                            except Exception as e:
                                QMessageBox.warning(self, "Erro ao anexar", f"Não foi possível anexar o arquivo:\n{e}")
                    event.acceptProposedAction()
                    return True

        return super().eventFilter(obj, event)

    # ─── Attachments ──────────────────────────────────────────────────
    def _attach_file_dialog(self):
        if not self.current_page:
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo")
        if not file_path:
            return
        from services.attachment_service import AttachmentService
        try:
            att = AttachmentService().add_attachment(file_path, "knowledge_page", self.current_page.id)
            self._load_attachments()
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível anexar:\n{e}")

    def _load_attachments(self):
        self.lst_attachments.clear()
        if not self.current_page:
            return
        from services.attachment_service import AttachmentService
        attach_list = AttachmentService().get_attachments_for_entity("knowledge_page", self.current_page.id)
        for att in attach_list:
            wi = QListWidgetItem(f"📎 {att.file_name} ({att.file_size} bytes)")
            wi.setData(Qt.UserRole, att)
            self.lst_attachments.addItem(wi)

    def _attach_context_menu(self, pos):
        item = self.lst_attachments.itemAt(pos)
        if not item:
            return
        att = item.data(Qt.UserRole)
        if not att:
            return
        menu = QMenu(self)

        open_f = QAction("📂 Abrir Arquivo", self)
        open_f.triggered.connect(lambda: self._open_attachment(item))
        menu.addAction(open_f)

        open_d = QAction("📂 Abrir Pasta", self)
        open_d.triggered.connect(lambda: self._open_attachment_folder(item))
        menu.addAction(open_d)

        menu.addSeparator()

        del_a = QAction("🗑️ Excluir", self)
        del_a.triggered.connect(lambda: self._remove_attachment(att))
        menu.addAction(del_a)

        menu.exec_(self.lst_attachments.viewport().mapToGlobal(pos))

    def _open_attachment(self, item):
        att = item.data(Qt.UserRole)
        if not att or not att.file_path:
            return
        import subprocess, os
        if os.path.exists(att.file_path):
            subprocess.Popen(["explorer", att.file_path] if os.name == "nt" else ["xdg-open", att.file_path])

    def _open_attachment_folder(self, item):
        att = item.data(Qt.UserRole)
        if not att or not att.file_path:
            return
        import subprocess, os
        folder = os.path.dirname(att.file_path)
        if os.path.isdir(folder):
            subprocess.Popen(["explorer", folder] if os.name == "nt" else ["xdg-open", folder])

    def _remove_attachment(self, att):
        from services.link_service import LinkService
        refs = LinkService().find_references_to_entity("attachment", att.id)
        if refs:
            from gui.dialogs_qt.reference_warning_dialog_qt import ReferenceWarningDialog
            dlg = ReferenceWarningDialog("arquivo", att.file_name, refs, self, show_archive=False)
            dlg.exec()
            if dlg.action == "delete_all":
                LinkService().delete_all_references_to("attachment", att.id)
            else:
                return
        from PySide6.QtWidgets import QMessageBox
        resp = QMessageBox.question(self, "Confirmar Exclusão", f"Deseja excluir o arquivo '{att.file_name}'?")
        if resp == QMessageBox.Yes:
            LinkService().delete_all_references_to("attachment", att.id)
            from services.attachment_service import AttachmentService
            AttachmentService().delete_attachment(att.id)
            self._load_attachments()

    # ─── Leitura / Edição ────────────────────────────────────────────
    def _set_read_mode(self):
        if self._has_unsaved_changes():
            if not self._confirm_save_before_leave():
                self.btn_edit_mode.setChecked(True)
                return
        self._is_preview = True
        self.btn_read.setChecked(True)
        self._render_preview()
        self.text_edit.setVisible(False)
        self.preview_area.setVisible(True)
        self._fmt_panel.setVisible(False)
        self._fmt_topbar.setVisible(False)
        self.title_edit.setReadOnly(True)
        self.cmb_parent.setEnabled(False)
        self.ent_category.setReadOnly(True)
        self.ent_tags.setReadOnly(True)

    def _set_edit_mode(self):
        self._is_preview = False
        self.btn_edit_mode.setChecked(True)
        self.text_edit.setVisible(True)
        self.preview_area.setVisible(False)
        self._fmt_panel.setVisible(True)
        self._fmt_topbar.setVisible(True)
        self.title_edit.setReadOnly(False)
        self.cmb_parent.setEnabled(True)
        self.ent_category.setReadOnly(False)
        self.ent_tags.setReadOnly(False)
        self.title_edit.setFocus()
        self.title_edit.selectAll()

    def _has_unsaved_changes(self):
        if not self.current_page or not self._original_page:
            return False
        current_text = self.text_edit.toPlainText()
        if current_text != (self._original_page.content or ""):
            return True
        if self.ent_category.text().strip() != (self._original_page.category or ""):
            return True
        if self.title_edit.text().strip() != (self._original_page.title or ""):
            return True
        return False

    def _confirm_save_before_leave(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Alterações não salvas")
        msg.setText("Deseja salvar as alterações antes de sair?")
        btn_save = msg.addButton("Salvar", QMessageBox.YesRole)
        btn_discard = msg.addButton("Descartar", QMessageBox.NoRole)
        msg.setDefaultButton(btn_save)
        from PySide6.QtWidgets import QDialogButtonBox
        dbb = msg.findChild(QDialogButtonBox)
        if dbb:
            dbb.setCenterButtons(True)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked == btn_save:
            self.save_page(silent=True)
            return True
        elif clicked == btn_discard:
            if self.current_page and self._original_page:
                import copy
                reverted = copy.deepcopy(self._original_page)
                self.text_edit.blockSignals(True)
                self.text_edit.setPlainText(reverted.content or "")
                self.title_edit.setText(reverted.title or "")
                self.ent_category.setText(reverted.category or "")
                self.text_edit.blockSignals(False)
                self.current_page.content = reverted.content
                self.current_page.title = reverted.title
                self.current_page.category = reverted.category
                self.page_service.update_page(self.current_page, self._original_page)
                self._original_page = reverted
            return True
        return False

    # ─── Load / Filter ───────────────────────────────────────────────
    def toggle_archived(self):
        self.show_archived = self.btn_archived.isChecked()
        self.btn_archived.setText(f"📦 Arquivados: {'ON' if self.show_archived else 'OFF'}")
        self.load_pages()

    def load_pages(self):
        self.tree.clear()
        if self.show_archived:
            pages = self.page_service.get_all_archived()
        else:
            pages = self.page_service.get_all_active()

        self._populate_parent_combo()

        # Build a dict of page_id -> QTreeWidgetItem
        items = {}
        for page in pages:
            arch = " 📦ARQUIVADO" if getattr(page, 'is_archived', False) else ""
            label = ("⭐ " if page.is_favorite else "📄 ") + page.title + arch
            item = QTreeWidgetItem([label])
            item.setData(0, Qt.UserRole, page)
            items[page.id] = item

        # Attach children to parents or to the tree root
        for page in pages:
            item = items[page.id]
            if page.parent_id and page.parent_id in items:
                items[page.parent_id].addChild(item)
            else:
                self.tree.addTopLevelItem(item)

        # Sort children of each parent
        for item in items.values():
            if item.childCount() > 0:
                item.sortChildren(0, Qt.AscendingOrder)

        self.tree.expandAll()
        self._filter_tree(self.search_bar.text())

        # Auto-select first page if none is selected
        if not self.current_page and self.tree.topLevelItemCount() > 0:
            first = self.tree.topLevelItem(0)
            if first.childCount() > 0:
                first = first.child(0)
            page = first.data(0, Qt.UserRole)
            if page:
                self._open_page(page)

    def _filter_tree(self, text: str):
        t = text.strip().lower()
        def set_visibility(item):
            match = t in item.text(0).lower()
            for i in range(item.childCount()):
                child_match = set_visibility(item.child(i))
                match = match or child_match
            item.setHidden(not match)
            if match and t:
                item.setExpanded(True)
            return match

        for i in range(self.tree.topLevelItemCount()):
            set_visibility(self.tree.topLevelItem(i))

    def _on_tree_item_clicked(self, item):
        page = item.data(0, Qt.UserRole)
        if page:
            self._open_page(page)

    def _open_page_by_id(self, page_id: int, edit_mode=False):
        pages = self.page_service.get_all_active()
        for p in pages:
            if p.id == page_id:
                self._open_page(p, edit_mode)
                return

    def _open_page(self, page, edit_mode=False):
        if self._has_unsaved_changes():
            if not self._confirm_save_before_leave():
                return

        # Re-fetch from DB so content reflects any background modifications
        fresh = self.page_service.get_by_id(page.id)
        if fresh:
            page = fresh

        import copy
        self.current_page = page
        self._original_page = copy.deepcopy(page)

        self.title_edit.setText(page.title)
        self.lbl_archived_badge.setVisible(getattr(page, 'is_archived', False))
        self.text_edit.blockSignals(True)
        self.text_edit.setPlainText(page.content or "")
        self.text_edit.blockSignals(False)

        self.ent_category.setText(page.category or "")

        tags = self.page_service.get_tags(page.id)
        self.ent_tags.setText(", ".join(tags))

        self._populate_parent_combo()

        self.refs_panel.set_entity("wiki", page.id)
        self._load_attachments()

        self._set_editor_enabled(True)

        if edit_mode:
            self._set_edit_mode()
        else:
            self._set_read_mode()

    def _set_editor_enabled(self, enabled: bool):
        self.text_edit.setEnabled(enabled)
        self.btn_save.setEnabled(enabled)
        self.btn_read.setEnabled(enabled)
        self.btn_edit_mode.setEnabled(enabled)
        self.cmb_parent.setEnabled(enabled)
        self.ent_category.setEnabled(enabled)
        self.ent_tags.setEnabled(enabled)
        self.btn_attach.setEnabled(enabled)
        self._fmt_panel.setEnabled(enabled)

    def _populate_parent_combo(self):
        current_id = self.current_page.id if self.current_page else None
        self.cmb_parent.clear()
        self.cmb_parent.addItem("— Sem página pai —", 0)
        pages = self.page_service.get_all_archived() if self.show_archived else self.page_service.get_all_active()
        for p in pages:
            if current_id is not None and p.id == current_id:
                continue
            self.cmb_parent.addItem(p.title, p.id)
        if self.current_page and self.current_page.parent_id:
            idx = self.cmb_parent.findData(self.current_page.parent_id)
            if idx >= 0:
                self.cmb_parent.setCurrentIndex(idx)

    # ─── Formatting helpers ──────────────────────────────────────────

    def _fmt_around(self, before: str, after: str):
        tc = self.text_edit.textCursor()
        text = tc.selectedText()
        if text:
            tc.insertText(f"{before}{text}{after}")
        else:
            tc.insertText(f"{before}{after}")
            tc.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, len(after))
        self.text_edit.setFocus()

    def _fmt_line_prefix(self, prefix: str):
        tc = self.text_edit.textCursor()
        tc.movePosition(QTextCursor.StartOfLine)
        tc.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        text = tc.selectedText()
        if text.startswith(prefix):
            tc.insertText(text[len(prefix):])
        else:
            tc.insertText(f"{prefix}{text}")
        self.text_edit.setFocus()

    def _fmt_bold(self): self._fmt_around("**", "**")
    def _fmt_italic(self): self._fmt_around("*", "*")
    def _fmt_strikethrough(self): self._fmt_around("~~", "~~")
    def _fmt_code(self): self._fmt_around("`", "`")

    def _fmt_heading1(self): self._fmt_line_prefix("# ")
    def _fmt_heading2(self): self._fmt_line_prefix("## ")
    def _fmt_heading3(self): self._fmt_line_prefix("### ")
    def _fmt_quote(self): self._fmt_line_prefix("> ")
    def _fmt_bullet_list(self): self._fmt_line_prefix("- ")
    def _fmt_numbered_list(self): self._fmt_line_prefix("1. ")
    def _fmt_task_list(self): self._fmt_line_prefix("- [ ] ")

    def _fmt_underline(self):
        self._fmt_around("<u>", "</u>")

    def _fmt_apply_size(self, size_str):
        if not size_str:
            return
        self._fmt_around(f'<span style="font-size: {size_str}px;">', "</span>")

    def _fmt_color(self):
        from PySide6.QtWidgets import QColorDialog
        color = QColorDialog.getColor()
        if color.isValid():
            self._fmt_around(f'<span style="color: {color.name()};" >', "</span>")

    def _fmt_code_block(self):
        tc = self.text_edit.textCursor()
        text = tc.selectedText()
        if text:
            tc.insertText(f"```\n{text}\n```")
        else:
            tc.insertText("```\n\n```")
            tc.movePosition(QTextCursor.Up)
        self.text_edit.setFocus()

    def _fmt_hr(self):
        tc = self.text_edit.textCursor()
        tc.movePosition(QTextCursor.EndOfLine)
        tc.insertText("\n---\n")
        self.text_edit.setFocus()

    def _fmt_link(self):
        tc = self.text_edit.textCursor()
        text = tc.selectedText()
        if text:
            tc.insertText(f"[{text}](url)")
            # Select the url placeholder for quick replace
            start = tc.position() - 6
            tc.setPosition(start)
            tc.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 3)
        else:
            tc.insertText("[texto](url)")
        self.text_edit.setFocus()

    def _fmt_image(self):
        tc = self.text_edit.textCursor()
        tc.insertText("![descrição](url)")
        self.text_edit.setFocus()

    # ─── Edit / Save ─────────────────────────────────────────────────
    def _on_text_changed(self):
        pass

    def save_page(self, silent=False):
        if not self.current_page:
            return
        import copy
        self.current_page.content = self.text_edit.toPlainText()
        self.current_page.category = self.ent_category.text().strip() or None
        new_title = self.title_edit.text().strip()
        if new_title and new_title != self.current_page.title:
            self.current_page.title = new_title

        parent_id = self.cmb_parent.currentData()
        if parent_id and parent_id == self.current_page.id:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Erro", "Uma página não pode ser pai dela mesma.")
            return
        self.current_page.parent_id = parent_id if parent_id else None

        self.page_service.update_page(self.current_page, self._original_page)
        if not silent:
            self._original_page = copy.deepcopy(self.current_page)

        raw_tags = [t.strip() for t in self.ent_tags.text().split(",") if t.strip()]
        self.page_service.set_tags(self.current_page.id, raw_tags)

        try:
            from services.link_service import LinkService
            LinkService().update_links_from_text("wiki", self.current_page.id, self.current_page.content)
        except Exception:
            pass

        if not silent:
            self.load_pages()
            self._set_read_mode()

    # ─── Preview ─────────────────────────────────────────────────────
    def _render_preview(self):
        text = self.text_edit.toPlainText()

        import re

        def link_repl(m):
            t_type = m.group(1)
            t_id = m.group(2)
            t_title = m.group(3)
            if t_type and t_id:
                return f'<a href="app://{t_type}/{t_id}">{t_title.strip()}</a>'
            else:
                return f'<a href="app://search/{t_title.strip()}">{t_title.strip()}</a>'

        text = re.sub(r'\[\[(?:([a-zA-Z0-9_]+):(\d+)\|)?(.*?)\]\]', link_repl, text)

        def file_repl(m):
            f_uuid = m.group(1)
            f_name = m.group(2)
            return f'<a href="file:///{f_uuid}">📎 {f_name.strip()}</a>'

        text = re.sub(r'\{\{(.*?)\|(.*?)\}\}', file_repl, text)

        try:
            import markdown as md_lib
            html = md_lib.markdown(text, extensions=["tables", "fenced_code", "nl2br"])
        except ImportError:
            html = self._simple_markdown(text)

        dark_css = """
        <style>
        body { background:#1a1a2e; color:#e0e0e0; font-family:'Segoe UI',sans-serif; font-size:14px; }
        h1,h2,h3 { color:#7b9fe0; }
        code { background:#2a2a3f; padding:2px 5px; border-radius:3px; }
        pre { background:#2a2a3f; padding:10px; border-radius:6px; }
        a { color:#4a6fe3; }
        blockquote { border-left:3px solid #4a6fe3; margin-left:0; padding-left:12px; color:#aaa; }
        table { border-collapse:collapse; width:100%; }
        th,td { border:1px solid #2a2a3f; padding:6px 10px; }
        th { background:#2d2d55; }
        </style>
        """
        self.preview_area.setHtml(dark_css + html)

    def _simple_markdown(self, text: str) -> str:
        import re
        lines = text.split("\n")
        result = []
        for line in lines:
            m = re.match(r'^(#{1,6})\s+(.*)', line)
            if m:
                n = len(m.group(1))
                result.append(f"<h{n}>{m.group(2)}</h{n}>")
                continue
            line = re.sub(r'\*\*\*(.*?)\*\*\*', r'<b><i>\1</i></b>', line)
            line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
            line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', line)
            line = re.sub(r'`(.*?)`', r'<code>\1</code>', line)
            if re.match(r'^[-*+]\s', line):
                line = "<li>" + line[2:] + "</li>"
            result.append(line)
        return "<br>".join(result)

    def _on_link_clicked(self, url):
        scheme = url.scheme()
        if scheme == "app":
            t_type = url.host()
            t_id_str = url.path().strip("/")
            if t_id_str.isdigit():
                from core.event_bus import event_bus
                event_bus.emit("navigate_to", {"type": t_type, "id": int(t_id_str)})
            elif t_type == "search":
                self.search_bar.setText(t_id_str)
        elif scheme == "file":
            f_uuid = url.path().strip("/")
            if not f_uuid:
                return
            from services.attachment_service import AttachmentService
            from database.repositories.attachment_repository import AttachmentRepository
            repo = AttachmentRepository()
            try:
                all_attach = repo.get_by_entity("knowledge_page", self.current_page.id) if self.current_page else []
                for att in all_attach:
                    if att.uuid == f_uuid:
                        import subprocess, os
                        if os.path.exists(att.file_path):
                            subprocess.Popen(["explorer", att.file_path] if os.name == "nt" else ["xdg-open", att.file_path])
                        break
            except Exception:
                pass

    # ─── Tree context menu ───────────────────────────────────────────
    def _tree_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        menu = QMenu(self)

        if item:
            page = item.data(0, Qt.UserRole)
            is_archived = getattr(page, "is_archived", False)

            if is_archived:
                rest_a = QAction("📦 Desarquivar", self)
                rest_a.triggered.connect(lambda: self._restore_page(page))
                menu.addAction(rest_a)

                menu.addSeparator()

                del_a = QAction("🗑️ Excluir", self)
                del_a.triggered.connect(lambda: self._delete_page(page))
                menu.addAction(del_a)
            else:
                open_a = QAction("📖 Abrir", self)
                open_a.triggered.connect(lambda: self._open_page(page))
                menu.addAction(open_a)

                rename_a = QAction("✏️ Renomear", self)
                rename_a.triggered.connect(lambda: self._rename_page(page, item))
                menu.addAction(rename_a)

                sub_a = QAction("📋 Nova sub-página", self)
                sub_a.triggered.connect(lambda: self._new_page(parent_page=page))
                menu.addAction(sub_a)

                fav_label = "⭐ Remover favorito" if page.is_favorite else "⭐ Favoritar"
                fav_a = QAction(fav_label, self)
                fav_a.triggered.connect(lambda: self._toggle_favorite(page))
                menu.addAction(fav_a)

                menu.addSeparator()

                arch_a = QAction("📦 Arquivar", self)
                arch_a.triggered.connect(lambda: self._archive_page(page))
                menu.addAction(arch_a)

                menu.addSeparator()

                del_a = QAction("🗑️ Excluir", self)
                del_a.triggered.connect(lambda: self._delete_page(page))
                menu.addAction(del_a)
        else:
            new_a = QAction("+ Nova Página", self)
            new_a.triggered.connect(self._new_page)
            menu.addAction(new_a)

        menu.exec_(self.tree.viewport().mapToGlobal(pos))

    def _new_page(self, parent_page=None):
        dlg = _NewPageDialog(self, parent_page=parent_page)
        if dlg.exec() == QDialog.Accepted:
            title = dlg.title
            parent_id = parent_page.id if parent_page else None
            page = self.page_service.create_page(title=title, parent_id=parent_id)
            self.load_pages()
            self._open_page_by_id(page.id, edit_mode=True)

    def _rename_page(self, page, item):
        dlg = _NewPageDialog(self, rename_mode=True, current_title=page.title)
        if dlg.exec() == QDialog.Accepted:
            import copy
            original = copy.deepcopy(page)
            page.title = dlg.title
            self.page_service.update_page(page, original)
            self.load_pages()

    def _toggle_favorite(self, page):
        import copy
        original = copy.deepcopy(page)
        page.is_favorite = not page.is_favorite
        self.page_service.update_page(page, original)
        self.load_pages()

    def _archive_page(self, page):
        msg = QMessageBox(self)
        msg.setWindowTitle("Arquivar Página")
        msg.setText(f"Deseja arquivar '{page.title}'?")
        btn_sim = msg.addButton("Sim", QMessageBox.YesRole)
        msg.addButton("Não", QMessageBox.NoRole)
        msg.exec()
        if msg.clickedButton() == btn_sim:
            self.page_service.archive_page(page.id)
            if self.current_page and self.current_page.id == page.id:
                self.current_page = None
                self.title_edit.setText("Selecione ou crie uma página")
                self.text_edit.clear()
                self.lbl_archived_badge.setVisible(False)
                self._set_editor_enabled(False)
            self.load_pages()

    def _restore_page(self, page):
        self.page_service.restore_page(page.id)
        if self.current_page and self.current_page.id == page.id:
            self.lbl_archived_badge.setVisible(False)
        self.load_pages()

    def _delete_page(self, page):
        # Check for references first
        from services.link_service import LinkService
        refs = LinkService().find_references_to_entity("wiki", page.id)
        if refs:
            from gui.dialogs_qt.reference_warning_dialog_qt import ReferenceWarningDialog
            dlg = ReferenceWarningDialog("documento", page.title, refs, self, show_archive=True)
            dlg.exec()
            action = dlg.action
            if action == "archive":
                self.page_service.archive_page(page.id)
                if self.current_page and self.current_page.id == page.id:
                    self.current_page = None
                    self.title_edit.setText("Selecione ou crie uma página")
                    self.text_edit.clear()
                    self.lbl_archived_badge.setVisible(False)
                    self._set_editor_enabled(False)
                self.load_pages()
                return
            elif action == "delete_all":
                LinkService().delete_all_references_to("wiki", page.id)
                # fall through to regular delete
            else:  # cancel
                return

        msg = QMessageBox(self)
        msg.setWindowTitle("Excluir Página")
        msg.setText(f"Deseja excluir permanentemente '{page.title}'?\nEsta ação não pode ser desfeita.")
        btn_sim = msg.addButton("Sim, Excluir", QMessageBox.YesRole)
        msg.addButton("Cancelar", QMessageBox.NoRole)
        msg.exec()
        if msg.clickedButton() == btn_sim:
            LinkService().delete_all_references_to("wiki", page.id)
            self.page_service.soft_delete_page(page.id)
            if self.current_page and self.current_page.id == page.id:
                self.current_page = None
                self.title_edit.setText("Selecione ou crie uma página")
                self.text_edit.clear()
                self.lbl_archived_badge.setVisible(False)
                self._set_editor_enabled(False)
            self.load_pages()


class _NewPageDialog(QDialog):
    def __init__(self, parent=None, parent_page=None, rename_mode=False, current_title=""):
        super().__init__(parent)
        self.title = ""
        if rename_mode:
            self.setWindowTitle("Renomear Página")
        elif parent_page:
            self.setWindowTitle(f"Nova sub-página de '{parent_page.title}'")
        else:
            self.setWindowTitle("Nova Página")
        self.resize(380, 130)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(QLabel("Título:"))
        self.ent = QLineEdit(current_title)
        self.ent.selectAll()
        layout.addWidget(self.ent)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("✅ Confirmar")
        btn_ok.setObjectName("primary")
        btn_ok.clicked.connect(self._confirm)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

        self.ent.returnPressed.connect(self._confirm)

    def _confirm(self):
        t = self.ent.text().strip()
        if not t:
            QMessageBox.warning(self, "Aviso", "O título não pode estar vazio.")
            return
        self.title = t
        self.accept()