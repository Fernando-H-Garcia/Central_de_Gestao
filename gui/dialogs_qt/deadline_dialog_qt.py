"""Prazos Estimados da tarefa -- lista e edicao.

Antes era um unico dialogo, montado por inteiro dentro de
`Project360Qt._edit_estimated_deadline` (gui/views/project_360_qt.py), com
lista + campos de edicao + botoes Adicionar/Atualizar/Remover todos no
mesmo rodape. Três problemas:

  1. o unico caminho de criacao era clicar em "Adicionar" com os campos
     abaixo da lista -- nao havia um "+ Novo Prazo" explicito;
  2. editar exigia selecionar o item na lista e clicar em "Atualizar", sem
     qualquer indicacao de qual prazo estava em edicao;
  3. os botoes nao seguiam o Design System (misturavam `objectName="primary"`
     com QPushButton cru).

Agora sao dois dialogos, como o resto do programa:

  - `DeadlineListDialog`: cabecalho com "+ Novo Prazo" no topo direito,
    lista, menu de contexto (Editar / Excluir / + Novo Prazo) e Fechar;
  - `DeadlineEditDialog`: Descricao e Data, com Salvar / Cancelar.

Nenhum dos dois conhece o banco. Quem cria, edita, exclui e registra a
atividade e a view (project_360_qt), via os callbacks do `controller`:

    controller.list()                        -> [TaskDeadline]
    controller.create(description, date)     -> TaskDeadline
    controller.update(deadline_id, desc, dt) -> None
    controller.delete(deadline_id)           -> None
"""

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
)

from gui.components.buttons import PrimaryButton, SecondaryButton
from gui.components.card import Card
from gui.components.context_menu_qt import ContextMenuQt
from gui.components.page_header import PageHeader
from gui.theme import fit_dialog_to_content, style_calendar_today
from gui.widgets.title_edit import TitleEdit


class DeadlineEditDialog(QDialog):
    """Criacao ou edicao de um Prazo Estimado.

    Ordem dos campos conforme combinado: Descricao primeiro, Data segundo.
    A Descricao e obrigatoria -- ela e o que identifica o prazo na lista
    (a data vira apenas o complemento "dd/mm/yyyy - descricao").
    """

    def __init__(self, parent=None, task_title="", deadline=None, initial_date=None):
        super().__init__(parent)
        self._deadline = deadline
        self.setWindowTitle("Editar Prazo" if deadline else "Novo Prazo")
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(16)

        header = PageHeader(
            "Editar Prazo" if deadline else "Novo Prazo",
            task_title,
            title_font=True,
        )
        root.addWidget(header)

        # Card ja nasce com layout proprio (gui/components/card.py) e o Qt
        # RECUSA setLayout() quando ja existe um -- usar setLayout() aqui
        # deixava os campos orfaos, invisiveis. Pegue o layout dele.
        card = Card()
        form = card.layout()
        form.setSpacing(8)

        form.addWidget(QLabel("Descricao *"))
        self.edit_description = TitleEdit(
            placeholder="Ex.: Revisao do texto com o cliente")
        if deadline is not None:
            self.edit_description.setText(deadline.description or "")
        form.addWidget(self.edit_description)

        form.addWidget(QLabel("Data"))
        self.edit_date = _DateEdit()
        # Ordem de precedencia: prazo em edicao > data sob o mouse (timeline)
        # > hoje. Sem o primeiro caso, editar um prazo antigo sobrescrevia a
        # data dele pela data de hoje.
        if deadline is not None:
            date_value = deadline.deadline_date
        else:
            date_value = initial_date
        self.edit_date.setDate(_to_qdate(date_value))
        form.addWidget(self.edit_date)

        hint = QLabel("A data e usada para marcar a bandeira e gerar os 2 alarmes automaticos.")
        hint.setObjectName("formHint")
        hint.setWordWrap(True)
        form.addWidget(hint)

        root.addWidget(card)
        root.addStretch(1)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        footer.addStretch(1)
        self.btn_cancel = SecondaryButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = PrimaryButton("Salvar")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._on_save)
        footer.addWidget(self.btn_cancel)
        footer.addWidget(self.btn_save)
        root.addLayout(footer)

        # Foco no primeiro campo: o usuario quase sempre comeca digitando.
        self.edit_description.setFocus()

    def _on_save(self):
        if not self.description():
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("Descricao obrigatoria")
            box.setText("Informe a descricao do prazo.")
            box.exec()
            self.edit_description.setFocus()
            return
        self.accept()

    def description(self) -> str:
        return self.edit_description.toPlainText().strip()

    def deadline_date(self):
        qd = self.edit_date.date()
        return _to_date(qd)


class DeadlineListDialog(QDialog):
    """Lista dos Prazos Estimados de uma tarefa."""

    new_requested = Signal()

    def __init__(self, parent=None, task=None, controller=None):
        super().__init__(parent)
        self._task = task
        self._controller = controller
        self.setWindowTitle("Prazos Estimados")
        self.setModal(True)

        task_title = getattr(task, "title", "") or ""

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(16)

        header = PageHeader("Prazos Estimados", task_title, title_font=True)
        self.btn_new = PrimaryButton("+ Novo Prazo")
        header.add_button(self.btn_new)
        root.addWidget(header)

        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._on_context_menu)
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        root.addWidget(self.list_widget, 1)

        self.empty_label = QLabel(
            "Nenhum prazo cadastrado.\nUse + Novo Prazo para criar o primeiro.")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setWordWrap(True)
        # Ocupa a MESMA area da lista: abaixo dela o aviso ficava pendurado
        # no rodape, com um retangulo vazio em cima.
        self.empty_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.empty_label.setVisible(False)
        root.addWidget(self.empty_label, 1)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        footer.addStretch(1)
        btn_close = SecondaryButton("Fechar")
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)
        root.addLayout(footer)

        self.btn_new.clicked.connect(self._request_new)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self.refresh()
        fit_dialog_to_content(self, min_w=520, min_h=440)

    # -- lista ------------------------------------------------------------

    def refresh(self):
        """Recarrega os prazos a partir do controller."""
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for d in self._controller.list():
            date_txt = d.deadline_date.strftime("%d/%m/%Y") if d.deadline_date else "—"
            item = QListWidgetItem(f"{date_txt} — {d.description or '(sem descrição)'}")
            item.setData(Qt.UserRole, d.id)
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)
        vazio = self.list_widget.count() == 0
        self.empty_label.setVisible(vazio)
        self.list_widget.setVisible(not vazio)

    def current_deadline_id(self):
        item = self.list_widget.currentItem()
        return item.data(Qt.UserRole) if item else None

    def select_deadline(self, deadline_id):
        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).data(Qt.UserRole) == deadline_id:
                self.list_widget.setCurrentItem(self.list_widget.item(i))
                return True
        return False

    def selected_deadline(self):
        did = self.current_deadline_id()
        if did is None:
            return None
        return next((d for d in self._controller.list() if d.id == did), None)

    # -- acoes ------------------------------------------------------------

    def _request_new(self):
        self.new_requested.emit()

    def _on_double_click(self, _item=None):
        self._edit_selected()

    def _on_selection_changed(self):
        # Sinto do duplo clique: mantem selecionado o item certo no menu
        # de contexto sem precisar descobrir qual estava selecionado antes.
        pass

    def _edit_selected(self):
        deadline = self.selected_deadline()
        if deadline is None:
            return
        dlg = DeadlineEditDialog(self, task_title=getattr(self._task, "title", ""),
                                 deadline=deadline)
        if dlg.exec() != QDialog.Accepted:
            return
        self._controller.update(deadline.id, dlg.description(), dlg.deadline_date())
        self.refresh()

    def _delete_selected(self):
        deadline = self.selected_deadline()
        if deadline is None:
            return
        date_txt = deadline.deadline_date.strftime("%d/%m/%Y") if deadline.deadline_date else "—"
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("Excluir prazo")
        box.setText(f"Excluir o prazo <b>{deadline.description or '(sem descrição)'}</b> "
                    f"de {date_txt}?")
        box.setInformativeText("Os 2 alarmes automaticos deste prazo tambem serao removidos.")
        btn_yes = box.addButton("Excluir", QMessageBox.DestructiveRole)
        box.addButton("Cancelar", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() != btn_yes:
            return
        self._controller.delete(deadline.id)
        self.refresh()

    def _on_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if item is not None:
            self.list_widget.setCurrentItem(item)

        menu = ContextMenuQt(self)
        has_selection = item is not None
        act_edit = menu.add_command("✏️ Editar Prazo", enabled=has_selection)
        act_del = menu.add_command("🗑️ Excluir", danger=True, enabled=has_selection)
        menu.add_separator()
        act_new = menu.add_command("➕ Novo Prazo")

        # `pos` JA vem em coordenadas do viewport (é o que o
        # customContextMenuRequested emite) e o popup_at faz o mapToGlobal
        # internamente. Converter aqui ALSO convertia duas vezes e o menu
        # aparecia longe do cursor.
        chosen = menu.popup_at(self.list_widget, pos)
        if chosen is None:
            return
        if chosen is act_edit:
            self._edit_selected()
        elif chosen is act_del:
            self._delete_selected()
        elif chosen is act_new:
            self._request_new()

    def open_new(self, initial_date=None):
        """Abre o formulario de criacao. Devolve True se salvou."""
        dlg = DeadlineEditDialog(self, task_title=getattr(self._task, "title", ""),
                                 initial_date=initial_date)
        if dlg.exec() != QDialog.Accepted:
            return False
        self._controller.create(dlg.description(), dlg.deadline_date())
        self.refresh()
        return True


def _DateEdit():
    """Factory: QDateEdit com popup de calendario e hoje destacado."""
    from PySide6.QtWidgets import QDateEdit
    edit = QDateEdit()
    edit.setCalendarPopup(True)
    edit.setDisplayFormat("dd/MM/yyyy")
    style_calendar_today(edit)
    return edit


def _to_qdate(value):
    if value is None:
        return QDate.currentDate()
    try:
        return QDate(value.year, value.month, value.day)
    except (AttributeError, TypeError):
        return QDate.currentDate()


def _to_date(qdate):
    import datetime
    return datetime.date(qdate.year(), qdate.month(), qdate.day())