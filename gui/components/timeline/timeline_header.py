from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QFont, QPen
from PySide6.QtCore import Qt, QRectF
import datetime

from gui.components.timeline.timeline_geometry import TimelineGeometry
from gui.theme import TEXT_PRIMARY, BORDER_SUBTLE, ACCENT_BLUE

class TimelineHeader(QWidget):
    def __init__(self, geometry: TimelineGeometry, parent=None):
        super().__init__(parent)
        self.geometry = geometry
        self.setFixedHeight(60)
        self._offset_x = 0
        # X inicial (no próprio widget) onde a linha do tempo começa —
        # à esquerda disso ficam as colunas de título/resumo da GanttTree.
        self._left_margin = 0

    def set_offset_x(self, offset_x: int):
        self._offset_x = offset_x
        self.update()

    def set_left_margin(self, margin: int):
        if margin != self._left_margin:
            self._left_margin = margin
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        try:
            # Fundo do Header (preto puro, igual à área da timeline)
            painter.fillRect(event.rect(), QColor("#000000"))
            # Borda inferior
            pen = QPen(QColor(BORDER_SUBTLE))
            painter.setPen(pen)
            painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
            # Determinar intervalo visível
            # offsetX diz respeito ao scroll horizontal; left_margin alinha com a coluna da timeline
            # conteúdo x = view_x - left_margin + offset  →  no início da coluna (view_x=left_margin): x = offset
            start_x_canvas = self._offset_x + (event.rect().left() - self._left_margin)
            end_x_canvas = self._offset_x + (self.width() - self._left_margin)
            start_date = self.geometry.x_to_date(start_x_canvas)
            end_date = self.geometry.x_to_date(end_x_canvas)
            # Arredondar start_date para baixo
            current_date = datetime.date(start_date.year, start_date.month, start_date.day)
            # Escadinha progressiva conforme o zoom (Ctrl+roda ou filtros):
            # diário → 2 em 2 → 3 em 3 → semanal → somente meses
            # (garante ~13px entre números, nada sobrepõe nem some ao rolar)
            pixels = self.geometry.pixels_per_day
            if pixels >= 13:
                day_interval = 1
            elif pixels * 2 >= 13:
                day_interval = 2
            elif pixels * 3 >= 13:
                day_interval = 3
            elif pixels * 7 >= 13:
                day_interval = 7   # mostra às segundas-feiras
            else:
                day_interval = 0   # só o 1º dia de cada mês
            painter.setFont(QFont("Segoe UI", 8))
            # Rótulos de mês/ano em dois níveis (alternando cima/baixo) para
            # nunca sobreporem quando o zoom está muito comprimido
            last_r_level1 = -9999   # borda direita do último rótulo no nível de cima
            last_r_level2 = -9999   # idem, nível de baixo
            while current_date <= end_date + datetime.timedelta(days=1):
                x_view = int(self.geometry.date_to_x(current_date) - self._offset_x + self._left_margin)
                if x_view >= self._left_margin:
                    # Desenha a marca do dia
                    painter.setPen(QColor(BORDER_SUBTLE))
                    painter.drawLine(x_view, self.height() - 10, x_view, self.height())
                    # Número do dia conforme a escadinha do zoom
                    show_day = (
                        day_interval == 0 and current_date.day == 1
                        or day_interval == 1
                        or (0 < day_interval < 7 and current_date.day % day_interval == 0)
                        or (day_interval == 7 and current_date.weekday() == 0)
                    )
                    if show_day:
                        painter.setPen(QColor(TEXT_PRIMARY))
                        day_str = str(current_date.day)
                        text_width = painter.fontMetrics().horizontalAdvance(day_str)
                        painter.drawText(x_view - text_width // 2, 36, day_str)
                    # Se for o dia 1, ou se for o primeiro dia renderizado, desenhar o Mês/Ano
                    if current_date.day == 1 or current_date == datetime.date(start_date.year, start_date.month, start_date.day):
                        months_pt = {
                            1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
                            7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
                        }
                        month_str = f"{months_pt[current_date.month]} {current_date.year}"
                        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
                        fm = painter.fontMetrics()
                        x0 = x_view + 5
                        w = fm.horizontalAdvance(month_str)
                        # nível de cima; se colidir, tenta o de baixo; se colidir, suprime
                        if x0 >= last_r_level1:
                            painter.drawText(x0, 13, month_str)
                            last_r_level1 = x0 + w
                        elif x0 >= last_r_level2:
                            painter.drawText(x0, 25, month_str)
                            last_r_level2 = x0 + w
                        painter.setFont(QFont("Segoe UI", 8)) # volta pra fonte normal
                current_date += datetime.timedelta(days=1)
            # Etiqueta HOJE — faixa INFERIOR do header (abaixo dos dias, acima da 1ª tarefa)
            today = datetime.datetime.now()
            today_x = self.geometry.datetime_to_x(today)
            today_x_view = int(today_x - self._offset_x + self._left_margin)
            if today_x_view >= self._left_margin and event.rect().left() <= today_x_view <= event.rect().right():
                months_pt = {1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
                             7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"}
                label = f"HOJE · {today.day:02d} {months_pt[today.month]}"
                painter.save()
                painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
                fm = painter.fontMetrics()
                tw = fm.horizontalAdvance(label)
                th = fm.height()
                pad = 3
                # faixa inferior do header: abaixo dos números dos dias,
                # acima da primeira linha da timeline
                bg_rect = QRectF(today_x_view - tw//2 - pad, self.height() - 19, tw + pad*2, th + 2)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(ACCENT_BLUE))
                painter.drawRoundedRect(bg_rect, 4, 4)
                painter.setPen(QColor("#ffffff"))
                painter.drawText(bg_rect, Qt.AlignCenter, label)
                painter.restore()
        finally:
            painter.end()
