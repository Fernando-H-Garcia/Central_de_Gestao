import datetime
from typing import Tuple

class TimelineGeometry:
    def __init__(self):
        # Escala: quantidade de pixels para representar 1 dia
        self.pixels_per_day: float = 30.0
        # A data que está ancorada na posição X = 0 (canto esquerdo extremo do canvas)
        # 2 anos no passado — dá folga para navegar datas antigas em qualquer zoom
        self.anchor_date: datetime.date = datetime.date.today() - datetime.timedelta(days=730)
        # Altura de cada linha
        self.row_height: int = 25

    def date_to_x(self, d: datetime.date) -> float:
        """Converte uma data para uma posição X no canvas."""
        delta = (d - self.anchor_date).days
        return delta * self.pixels_per_day

    def x_to_date(self, x: float) -> datetime.date:
        """Converte uma posição X do canvas para uma data."""
        days = x / self.pixels_per_day
        return self.anchor_date + datetime.timedelta(days=days)

    def datetime_to_x(self, dt: datetime.datetime) -> float:
        """Converte um datetime para posição X, incluindo a fração do dia."""
        delta = dt.date() - self.anchor_date
        fraction = (dt.hour + dt.minute / 60.0 + dt.second / 3600.0) / 24.0
        return (delta.days + fraction) * self.pixels_per_day

    def get_date_range(self, width: int) -> Tuple[datetime.date, datetime.date]:
        """Retorna as datas visíveis no intervalo [0, width]."""
        start = self.x_to_date(0)
        end = self.x_to_date(width)
        return start, end

    def set_scale(self, pixels_per_day: float):
        self.pixels_per_day = max(1.0, min(200.0, pixels_per_day))
