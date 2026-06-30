from PySide6.QtWidgets import QTableWidget, QAbstractItemView
from PySide6.QtCore import Qt, Signal, QTimer

class DragDropTableWidget(QTableWidget):
    row_moved = Signal(int, int) # task_id, target_row

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setDropIndicatorShown(True)
        self.setDragDropOverwriteMode(False)

    def setItem(self, row, column, item):
        if item:
            # Remover a flag ItemIsDropEnabled impede que o Qt tente soltar "DENTRO" 
            # da célula (o que causava a seleção do retângulo inteiro).
            # Com isso, ele só permite soltar "ENTRE" as linhas, exibindo a linha indicadora.
            item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled)
        super().setItem(row, column, item)
        
    def dropEvent(self, event):
        source_row = self.currentRow()
        if source_row < 0:
            event.ignore()
            return
            
        pos = event.position().toPoint()
        target_index = self.indexAt(pos)
        
        if target_index.isValid():
            target_row = target_index.row()
            rect = self.visualRect(target_index)
            # Se o mouse está na metade inferior da linha, inserimos DEPOIS dela
            if pos.y() > rect.center().y():
                target_row += 1
        else:
            target_row = self.rowCount()
            
        # Evitar recarregar se arrastar e soltar no mesmo lugar
        if source_row == target_row or source_row == target_row - 1:
            event.ignore()
            return
            
        task_id_item = self.item(source_row, 0)
        if not task_id_item:
            event.ignore()
            return
            
        task = task_id_item.data(Qt.UserRole)
        if not task:
            event.ignore()
            return
            
        # IgnoreAction impede que o QTableWidget delete ou troque a célula automaticamente
        # (o que causa linhas em branco ou fantasmas). Aceitamos o evento visualmente.
        event.setDropAction(Qt.IgnoreAction)
        event.accept()
        
        # Avisar o parent para atualizar no banco e recarregar os dados assincronamente,
        # garantindo que o QTableWidget já finalizou a operação de drag interna.
        QTimer.singleShot(0, lambda: self.row_moved.emit(task.id, target_row))
