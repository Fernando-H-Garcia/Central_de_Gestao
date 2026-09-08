from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QToolButton, QMenu
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction


class BackNavWidget(QWidget):
    """Botão Voltar com setinha à esquerda que abre lista de janelas do histórico.

    Layout: [▾] [← Voltar]  — a setinha fica à ESQUERDA e abre o menu de histórico.
    O botão principal continua emitindo go_back_requested (comportamento atual).
    O menu é populado sob demanda consultando MainWindow.get_history_for_menu().
    """
    go_back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.btn_history = QToolButton()
        self.btn_history.setText("▾")
        self.btn_history.setToolTip("Histórico de janelas — escolher para voltar")
        self.btn_history.setCursor(Qt.PointingHandCursor)
        self.btn_history.setPopupMode(QToolButton.InstantPopup)
        self.btn_history.setFixedSize(22, 26)
        self.btn_history.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                color: #aaa;
                border: 1px solid #555;
                border-radius: 4px;
                font-size: 10px;
                padding: 0px;
            }
            QToolButton:hover {
                background-color: #2d2d55;
                color: #fff;
                border: 1px solid #4a6fe3;
            }
            QToolButton:pressed {
                background-color: #1e1e3a;
            }
            QToolButton::menu-indicator { image: none; }
        """)
        self._menu = QMenu(self.btn_history)
        self._menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e3a;
                color: #fff;
                border: 1px solid #3a3a6a;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2d2d55;
            }
            QMenu::separator {
                height: 1px;
                background: #2a2a3f;
                margin: 4px 8px;
            }
        """)
        self.btn_history.setMenu(self._menu)
        # popula toda vez que abre
        self._menu.aboutToShow.connect(self._populate_menu)

        self.btn_back = QPushButton("← Voltar")
        self.btn_back.setObjectName("secondary")
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self.go_back_requested.emit)

        layout.addWidget(self.btn_history)
        layout.addWidget(self.btn_back)

    def _find_main_window(self):
        # tenta via window() -> MainWindow
        w = self.window()
        if w is not None and hasattr(w, "get_history_for_menu"):
            return w
        # fallback: activeWindow
        from PySide6.QtWidgets import QApplication
        aw = QApplication.activeWindow()
        if aw is not None and hasattr(aw, "get_history_for_menu"):
            return aw
        # varre parents
        p = self.parent()
        while p is not None:
            if hasattr(p, "get_history_for_menu"):
                return p
            p = p.parent() if hasattr(p, "parent") else None
        return None

    def _populate_menu(self):
        self._menu.clear()
        win = self._find_main_window()
        if win is None:
            a = self._menu.addAction("Histórico indisponível")
            a.setEnabled(False)
            return
        items = win.get_history_for_menu()
        if not items:
            a = self._menu.addAction("Nenhuma janela no histórico")
            a.setEnabled(False)
            return
        # items: list[(target, label, is_current)]
        for idx, (target, label, is_current) in enumerate(items):
            # capa: mostra “→ Atual” no topo
            if is_current:
                act = QAction(f"● {label}  — atual", self)
                act.setEnabled(False)
                self._menu.addAction(act)
                self._menu.addSeparator()
                continue
            icon = "📊" if target[0] == "page" else ("📁" if target[0] == "project" else "📋")
            act = QAction(f"{icon}  {label}", self)
            # captura target por valor
            act.triggered.connect(lambda checked, t=target: self._jump_to(t))
            self._menu.addAction(act)

    def _jump_to(self, target):
        win = self._find_main_window()
        if win is not None and hasattr(win, "jump_to_target"):
            win.jump_to_target(target)
