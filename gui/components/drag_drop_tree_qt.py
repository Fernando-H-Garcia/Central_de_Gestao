from PySide6.QtWidgets import QTreeWidget, QAbstractItemView, QTreeWidgetItem, QTreeWidgetItemIterator
from PySide6.QtCore import Qt, Signal, QTimer, QPoint, QMimeData, QRect
from PySide6.QtGui import QDrag, QPainter, QPixmap, QRegion, QFontMetrics


class SortableTreeWidgetItem(QTreeWidgetItem):
    def __init__(self, parent=None, sort_values=None):
        super().__init__(parent)
        self.sort_values = sort_values or {}

    def __lt__(self, other):
        tree = self.treeWidget()
        column = tree.sortColumn() if tree is not None else 0
        val1 = self.sort_values.get(column)
        val2 = getattr(other, 'sort_values', {}).get(column) if isinstance(other, SortableTreeWidgetItem) else None

        if val1 is not None and val2 is not None:
            try:
                return val1 < val2
            except TypeError:
                return str(val1) < str(val2)
        return self.text(column) < other.text(column)


class TranslucentDragMixin:
    """Fantasma de drag translúcido para QTreeWidget.

    O fantasma padrão do Qt só aplica transparência em legendas/badges (status,
    prioridade) e deixa título/período sólidos. Esta mixin renderiza a linha
    arrastada inteira com um alpha único (opacidade global) e desloca o hotspot
    à direita do cursor, para não tapar a área de destino do drop.

    Use como primeira base: class MeuTree(TranslucentDragMixin, QTreeWidget).
    """

    def startDrag(self, actions):
        items = self.selectedItems()
        if not items:
            super().startDrag(actions)
            return

        item = items[0]
        rect = self.visualItemRect(item).intersected(self.viewport().rect())
        if rect.isNull() or rect.width() <= 0 or rect.height() <= 0:
            super().startDrag(actions)
            return

        sel_idx = self.indexFromItem(item)

        mime = None
        try:
            mime = self.model().mimeData([sel_idx]) if sel_idx.isValid() else None
        except Exception:
            mime = None

        pixmap = QPixmap(rect.size())
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setOpacity(0.55)
        self.viewport().render(painter, QPoint(0, 0), QRegion(rect))
        painter.end()

        drag = QDrag(self)
        if mime is not None:
            drag.setMimeData(mime)
        drag.setPixmap(pixmap)
        # Desloca o fantasma para a direita (x=60) e centraliza verticalmente
        drag.setHotSpot(QPoint(60, rect.height() // 2))
        drag.exec(actions, Qt.MoveAction)


class DragDropTreeWidget(TranslucentDragMixin, QTreeWidget):
    item_moved = Signal(int, object)  # task_id, new_parent_id (ou None para raiz)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setDropIndicatorShown(True)
        self.setDragDropOverwriteMode(False)

        # Word wrap for title column
        self.setWordWrap(True)
        self.setTextElideMode(Qt.ElideNone)

        # Custom tooltip system
        self._tooltip_timer = QTimer(self)
        self._tooltip_timer.setSingleShot(True)
        self._tooltip_timer.setInterval(1300)  # 1.3s
        self._tooltip_timer.timeout.connect(self._show_custom_tooltip)
        self._tooltip_item = None
        self._tooltip_pos = None
        self.setMouseTracking(True)

        # Em árvores "locais" (ex.: detalhe de tarefa) os itens do topo são filhos
        # de uma tarefa âncora e NÃO devem virar tarefa raiz do projeto no drop.
        # None = a raiz da árvore é a raiz do projeto (comportamento padrão em
        # Project360/Tasks). Use set_drop_root_parent para limitar o drop.
        self._drop_root_parent_id = None

    def _show_custom_tooltip(self):
        if not self._tooltip_item or not self._tooltip_pos:
            return
        item = self._tooltip_item
        task = item.data(0, Qt.UserRole)
        if not task or not hasattr(task, 'title') or not task.title:
            return

        title = task.title
        # Format: max 6 words of 6 chars = ~42 chars per line, wrap lines
        words = title.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= 42:
                current_line += (" " if current_line else "") + word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        tooltip_text = "\n".join(lines)

        # Position tooltip offset from cursor, constrained to viewport
        global_pos = self.viewport().mapToGlobal(self._tooltip_pos)
        global_pos += QPoint(20, 20)  # Offset from mouse pointer

        # Ensure tooltip stays within widget bounds
        widget_rect = self.viewport().rect()
        widget_global = self.viewport().mapToGlobal(QPoint(0, 0))
        max_x = widget_global.x() + widget_rect.width() - 300
        max_y = widget_global.y() + widget_rect.height() - 100
        if global_pos.x() > max_x:
            global_pos.setX(max_x)
        if global_pos.y() > max_y:
            global_pos.setY(max_y)

        from PySide6.QtWidgets import QToolTip
        QToolTip.showText(global_pos, tooltip_text, self)

    def mouseMoveEvent(self, event):
        item = self.itemAt(event.pos())
        if item != self._tooltip_item:
            self._tooltip_timer.stop()
            self._tooltip_item = item
            self._tooltip_pos = event.pos()
            if item:
                self._tooltip_timer.start()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._tooltip_timer.stop()
        self._tooltip_item = None
        self._tooltip_pos = None
        from PySide6.QtWidgets import QToolTip
        QToolTip.hideText()
        super().leaveEvent(event)

    def set_drop_root_parent(self, task_id):
        """Define a tarefa que é o 'pai' dos itens de nível topo desta árvore.
        Drops no vazio/topo mantêm o item dentro dessa tarefa (não promovem à raiz)."""
        self._drop_root_parent_id = task_id

    def _nearest_row_item(self, pos):
        """Retorna o item cuja linha (visualItemRect) está mais próxima ACIMA do ponto.
        Serve de contexto para drops em espaço vazio da viewport."""
        best = None
        best_bottom = -1
        it = QTreeWidgetItemIterator(self)
        while it.value() is not None:
            item = it.value()
            if not item.isHidden():
                rect = self.visualItemRect(item)
                if rect.top() <= pos.y() <= rect.bottom():
                    return item
                if rect.bottom() <= pos.y() and rect.bottom() > best_bottom:
                    best_bottom = rect.bottom()
                    best = item
            it += 1
        return best

    def dropEvent(self, event):
        source_item = self.currentItem()
        if not source_item:
            event.ignore()
            return

        pos = event.position().toPoint()
        target_item = self.itemAt(pos)
        drop_pos = self.dropIndicatorPosition()

        # Determina o pai pretendido:
        # - ON um item  → vira filho desse item
        # - ENTRE itens (acima/abaixo) → vira irmão no nível do alvo
        # - No vazio da subárvore → mantém o contexto do item vizinho mais próximo
        # - Vazio abaixo de tudo na raiz → vira tarefa raiz (None)
        new_parent = None
        if target_item is not None:
            target_task = target_item.data(0, Qt.UserRole)
            if drop_pos == QAbstractItemView.OnItem:
                if target_task:
                    new_parent = target_task.id
            elif drop_pos in (QAbstractItemView.AboveItem, QAbstractItemView.BelowItem):
                parent_item = target_item.parent()
                if parent_item is not None:
                    parent_task = parent_item.data(0, Qt.UserRole)
                    if parent_task:
                        new_parent = parent_task.id
                elif self._drop_root_parent_id is not None:
                    # o alvo é item de topo e esta árvore tem pai âncora
                    # (ex.: detalhe de tarefa) → mantém dentro desse pai
                    new_parent = self._drop_root_parent_id
        else:
            # drop em espaço vazio da viewport → usar o contexto do item mais próximo
            anchor = self._nearest_row_item(pos)
            if anchor is not None:
                anchor_parent = anchor.parent()
                if anchor_parent is not None:
                    anchor_task = anchor_parent.data(0, Qt.UserRole)
                    if anchor_task:
                        new_parent = anchor_task.id
                elif self._drop_root_parent_id is not None:
                    # o âncora é item de topo e esta árvore tem um pai âncora
                    # (ex.: detalhe de tarefa) → mantém dentro desse pai
                    new_parent = self._drop_root_parent_id

        # Deixa o QTreeWidget fazer o movimento visual (InternalMove)
        super().dropEvent(event)

        task = source_item.data(0, Qt.UserRole)
        if task:
            # Deixa a UI atualizar e então o handler persiste o novo pai
            QTimer.singleShot(0, lambda: self.item_moved.emit(task.id, new_parent))


def fit_branch_arrows(tree):
    """Ajusta indentacao e largura da coluna 0 para as setas de expansao nao
    serem recortadas em arvores profundas. Qt desenha a seta no inicio da
    1a coluna, deslocada pela indentacao acumulada; se a coluna 0 for estreita,
    a seta some (clipping horizontal). Reduz a indentacao e alarga a coluna 0
    proporcional a profundidade maxima da arvore.
    """
    root = tree.invisibleRootItem()
    max_depth = 0

    def _measure(parent, depth):
        nonlocal max_depth
        for i in range(parent.childCount()):
            _measure(parent.child(i), depth + 1)
        if depth > max_depth:
            max_depth = depth

    _measure(root, 0)

    indent = 20
    if max_depth > 1:
        indent = 16
    if max_depth > 3:
        indent = 14
    if max_depth > 5:
        indent = 12
    tree.setIndentation(indent)

    header = tree.header()
    arrow_space = indent * max_depth + 30
    if header.sectionSize(0) < arrow_space:
        header.resizeSection(0, arrow_space)