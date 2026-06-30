"""
AlarmPopupQt — Popup de alarmes ativos.

Exibe a lista de alarmes disparados ao abrir um projeto.
Toca um som de aviso e permite Concluir ou Adiar cada alarme.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QWidget, QFrame, QMenu
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
import os
import traceback

from gui.theme import ENERGY_COLORS, get_energy_color, style_calendar_today
from services.alert_service import AlertService
from services.task_service import TaskService

# Mapeamento BD → exibição PT
PRIORITY_LABELS = {
    "low":      ("Baixa",  "#4a6fe3"),
    "medium":   ("Média",  "#2b8c52"),
    "high":     ("Alta",   "#e3a84a"),
    "critical": ("Máxima", "#e53935"),
}

SNOOZE_OPTIONS = [
    ("⏱ 10 minutos",  "10min"),
    ("⏱ 30 minutos",  "30min"),
    ("⏱ 1 hora",      "1h"),
    ("📅 1 dia",       "1dia"),
    ("📆 1 semana",    "1semana"),
    ("⚙️ Personalizado...", "custom"),
]


def play_alarm_sound():
    """Toca o som de aviso do sistema. Funciona no Windows."""
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception:
        try:
            import os
            os.system("printf '\\a'")  # fallback UNIX
        except Exception:
            pass  # silencia se nenhum método funcionar


class AlarmCard(QFrame):
    """Card visual para um único alarme no popup."""

    def __init__(self, alarm, task_title: str, on_complete, on_snooze, parent=None):
        super().__init__(parent)
        self.alarm = alarm
        self.on_complete = on_complete
        self.on_snooze = on_snooze
        self.setObjectName("alarm_card")
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame#alarm_card {
                background-color: #1e1e3a;
                border: 1px solid #3a3a6a;
                border-radius: 8px;
                margin: 4px 0px;
                padding-bottom: 6px;
            }
        """)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(6)

        # Linha superior: badge de prioridade + título
        top = QHBoxLayout()
        label_pt, color_hex = PRIORITY_LABELS.get(self.alarm.priority, ("Média", "#2b8c52"))
        badge = QLabel(f" {label_pt} ")
        badge.setStyleSheet(
            f"background-color: {color_hex}; color: white; border-radius: 4px; "
            f"padding: 1px 6px; font-size: 11px; font-weight: bold;"
        )
        badge.setFixedHeight(20)
        top.addWidget(badge)
        top.addSpacing(8)

        lbl_title = QLabel(self.alarm.title)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        lbl_title.setFont(font)
        lbl_title.setWordWrap(True)
        top.addWidget(lbl_title, stretch=1)
        layout.addLayout(top)

        # Tarefa vinculada
        lbl_task = QLabel(f"📋 Tarefa: <i>{self.alarm._task_title}</i>")
        lbl_task.setStyleSheet("color: #aaa; font-size: 11px;")
        lbl_task.setWordWrap(True)
        layout.addWidget(lbl_task)

        # Descrição
        if self.alarm.description:
            lbl_desc = QLabel(self.alarm.description)
            lbl_desc.setStyleSheet("color: #ccc; font-size: 12px;")
            lbl_desc.setWordWrap(True)
            layout.addWidget(lbl_desc)

        # Data/hora
        date_display = self.alarm.alert_date
        try:
            from datetime import datetime
            dt = datetime.strptime(self.alarm.alert_date, "%Y-%m-%d")
            date_display = dt.strftime("%d/%m/%Y")
        except Exception:
            pass
        hora = f" às {self.alarm.alert_time}" if self.alarm.alert_time else " (dia todo)"
        lbl_date = QLabel(f"🗓 {date_display}{hora}")
        lbl_date.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(lbl_date)

        # Botões de ação
        btn_row = QHBoxLayout()
        btn_complete = QPushButton("✅ Concluir")
        btn_complete.setObjectName("primary")
        btn_complete.setMinimumHeight(36)
        btn_complete.clicked.connect(lambda: self.on_complete(self.alarm.id))

        btn_snooze = QPushButton("⏰ Adiar por ▾")
        btn_snooze.setMinimumHeight(36)
        btn_snooze.clicked.connect(self._show_snooze_menu)

        btn_row.addWidget(btn_complete)
        btn_row.addWidget(btn_snooze)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _show_snooze_menu(self):
        menu = QMenu(self)
        for label, key in SNOOZE_OPTIONS:
            action = menu.addAction(label)
            action.triggered.connect(lambda checked=False, k=key: self.on_snooze(self.alarm.id, k))
        menu.exec(self.cursor().pos())


class AlarmPopupQt(QDialog):
    """Popup principal que exibe todos os alarmes ativos de um projeto."""

    def __init__(self, alarms: list, task_map: dict, parent=None):
        """
        :param alarms: lista de Alert com attr _task_title injetado
        :param task_map: dict task_id → Task (para referência futura)
        """
        super().__init__(parent)
        self.alarms = alarms
        self.task_map = task_map
        self.alert_service = AlertService()
        self._cards = {}

        self.setWindowTitle("🔔 Alarmes Ativos")
        self.setMinimumWidth(520)
        self.setWindowModality(Qt.ApplicationModal)
        self.setup_ui()
        # Toca som após renderizar
        QTimer.singleShot(100, play_alarm_sound)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # Cabeçalho
        n = len(self.alarms)
        plural = "alarme ativo" if n == 1 else "alarmes ativos"
        lbl_header = QLabel(f"🔔  {n} {plural}")
        lbl_header.setStyleSheet("font-size: 15px; font-weight: bold; color: #e3a84a;")
        main_layout.addWidget(lbl_header)

        # Scroll com cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        self.cards_layout = QVBoxLayout(container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(6)

        for alarm in self.alarms:
            card = AlarmCard(
                alarm=alarm,
                task_title=alarm._task_title,
                on_complete=self._handle_complete,
                on_snooze=self._handle_snooze,
            )
            self._cards[alarm.id] = card
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Botão fechar
        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)
        main_layout.addWidget(btn_close, alignment=Qt.AlignRight)

    def _remove_card(self, alarm_id: int):
        """Remove visualmente o card."""
        card = self._cards.pop(alarm_id, None)
        if card:
            card.setVisible(False)
            self.cards_layout.removeWidget(card)
            card.deleteLater()

    def _handle_complete(self, alarm_id: int):
        try:
            self.alert_service.complete_alert_silent(alarm_id)
            card = self._cards.get(alarm_id)
            if card:
                card.setStyleSheet("background-color: #1b5e20; border: 2px solid #4caf50; border-radius: 8px;")
                for btn in card.findChildren(QPushButton):
                    btn.setEnabled(False)
                from PySide6.QtWidgets import QLabel
                done_label = QLabel("✅ CONCLUÍDO")
                done_label.setAlignment(Qt.AlignCenter)
                done_label.setStyleSheet("color: #81c784; font-size: 14px; font-weight: bold; padding: 4px;")
                card.layout().addWidget(done_label)
            QTimer.singleShot(1500, lambda: self._remove_card_after(alarm_id))
        except Exception:
            from config import LOGS_DIR
            log_path = os.path.join(LOGS_DIR, "app_errors.log")
            try:
                with open(log_path, "a") as f:
                    f.write("\nCRASH IN _handle_complete:\n")
                    traceback.print_exc(file=f)
            except:
                pass
            QTimer.singleShot(0, self.accept)

    def _remove_card_after(self, alarm_id: int):
        self._remove_card(alarm_id)
        if not self._cards:
            self.accept()

    def _handle_snooze(self, alarm_id: int, snooze_option: str):
        if snooze_option == "custom":
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDateTimeEdit, QPushButton, QMessageBox
            from PySide6.QtCore import QDateTime
            dlg = QDialog(self)
            dlg.setWindowTitle("Adiar Alarme")
            dlg.setFixedSize(300, 150)
            layout = QVBoxLayout(dlg)
            layout.addWidget(QLabel("Escolha a nova data e hora:"))
            dt_edit = QDateTimeEdit(QDateTime.currentDateTime())
            dt_edit.setCalendarPopup(True)
            dt_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
            style_calendar_today(dt_edit)
            layout.addWidget(dt_edit)
            btn_layout = QHBoxLayout()
            btn_cancel = QPushButton("Cancelar")
            btn_cancel.clicked.connect(dlg.reject)
            btn_ok = QPushButton("Confirmar")
            btn_ok.setObjectName("primary")
            btn_ok.clicked.connect(dlg.accept)
            btn_layout.addWidget(btn_cancel)
            btn_layout.addWidget(btn_ok)
            layout.addLayout(btn_layout)
            if dlg.exec() == QDialog.Accepted:
                new_dt = dt_edit.dateTime()
                new_date = new_dt.toString("yyyy-MM-dd")
                new_time = new_dt.toString("HH:mm")
                self._remove_card(alarm_id)
                if not self._cards:
                    QTimer.singleShot(0, self.accept)
                QTimer.singleShot(0, lambda aid=alarm_id, nd=new_date, nt=new_time: self._apply_custom_snooze(aid, nd, nt))
        else:
            self._remove_card(alarm_id)
            if not self._cards:
                QTimer.singleShot(0, self.accept)
            self.alert_service.snooze_alert_silent(alarm_id, snooze_option)

    def _apply_custom_snooze(self, alarm_id: int, new_date: str, new_time: str):
        """Callback diferido para evitar crash durante fechamento do popup."""
        try:
            alarm = self.alert_service.get_alert(alarm_id)
            if alarm:
                alarm.alert_date = new_date
                alarm.alert_time = new_time
                alarm.status = 'pending'
                self.alert_service.alert_repo.update(alarm)
        except Exception:
            from config import LOGS_DIR
            log_path = os.path.join(LOGS_DIR, "app_errors.log")
            try:
                with open(log_path, "a") as f:
                    f.write("\nCRASH IN _apply_custom_snooze:\n")
                    traceback.print_exc(file=f)
            except:
                pass
