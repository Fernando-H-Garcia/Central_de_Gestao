import customtkinter as ctk
from datetime import datetime, date, timedelta
import calendar

class CTkCalendar(ctk.CTkFrame):
    def __init__(self, master, on_date_select=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_date_select = on_date_select
        self.selected_date = date.today()
        self.current_month = self.selected_date.replace(day=1)
        self.events = {} # dict mapping date_str to priority tag

        self.meses_pt = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                         "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        self.dias_pt = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]

        # Header: Prev - Month/Year - Next
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, 10))

        self.btn_prev = ctk.CTkButton(self.header_frame, text="<", width=30, command=self._prev_month)
        self.btn_prev.pack(side="left")

        self.lbl_month_year = ctk.CTkLabel(self.header_frame, text="", font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_month_year.pack(side="left", expand=True)

        self.btn_next = ctk.CTkButton(self.header_frame, text=">", width=30, command=self._next_month)
        self.btn_next.pack(side="right")

        # Grid for days
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True)

        for c in range(7):
            self.grid_frame.grid_columnconfigure(c, weight=1)
        for r in range(7):
            self.grid_frame.grid_rowconfigure(r, weight=1)

        self.day_buttons = []
        self._build_grid()
        self._render()

    def set_events(self, events_dict):
        """events_dict: { 'YYYY-MM-DD': 'high'|'medium'|'low' }"""
        self.events = events_dict
        self._render()

    def get_date(self):
        return self.selected_date.strftime("%Y-%m-%d")

    def _build_grid(self):
        # Weekday headers
        for c, day_name in enumerate(self.dias_pt):
            lbl = ctk.CTkLabel(self.grid_frame, text=day_name, font=ctk.CTkFont(weight="bold"))
            lbl.grid(row=0, column=c, pady=5)

        for r in range(1, 7):
            for c in range(7):
                btn = ctk.CTkButton(self.grid_frame, text="", width=30, height=30, 
                                    fg_color="transparent", text_color="white", corner_radius=15,
                                    command=lambda r=r, c=c: self._on_click(r, c))
                btn.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
                self.day_buttons.append((r, c, btn))

    def _prev_month(self):
        first_day = self.current_month
        last_day_prev = first_day - timedelta(days=1)
        self.current_month = last_day_prev.replace(day=1)
        self._render()

    def _next_month(self):
        # find next month
        year = self.current_month.year
        month = self.current_month.month
        if month == 12:
            self.current_month = date(year + 1, 1, 1)
        else:
            self.current_month = date(year, month + 1, 1)
        self._render()

    def _on_click(self, r, c):
        for br, bc, btn in self.day_buttons:
            if br == r and bc == c and hasattr(btn, 'date_obj'):
                self.selected_date = btn.date_obj
                self._render()
                if self.on_date_select:
                    self.on_date_select()
                break

    def _render(self):
        year = self.current_month.year
        month = self.current_month.month
        self.lbl_month_year.configure(text=f"{self.meses_pt[month-1]} {year}")

        cal = calendar.Calendar(firstweekday=6) # Sunday first
        days = cal.monthdatescalendar(year, month)

        is_dark = ctk.get_appearance_mode() == "Dark"
        bg_normal = "transparent"
        bg_selected = "#1f538d"
        text_other_month = "#555555" if is_dark else "#aaaaaa"
        text_current_month = "#ffffff" if is_dark else "#000000"
        
        colors = {
            'high': '#8c2b2b',
            'medium': '#8c6c2b',
            'low': '#2b5c8c'
        }

        idx = 0
        for week in days:
            for day_obj in week:
                if idx < len(self.day_buttons):
                    btn = self.day_buttons[idx][2]
                    btn.configure(text=str(day_obj.day))
                    btn.date_obj = day_obj
                    
                    is_other_month = day_obj.month != month
                    is_selected = day_obj == self.selected_date
                    date_str = day_obj.strftime("%Y-%m-%d")
                    has_event = self.events.get(date_str)
                    
                    text_col = text_other_month if is_other_month else text_current_month
                    if is_selected:
                        btn.configure(fg_color=bg_selected, text_color="white")
                    else:
                        if has_event:
                            btn.configure(fg_color=colors.get(has_event, '#2b2b2b'), text_color="white")
                        else:
                            btn.configure(fg_color=bg_normal, text_color=text_col)
                idx += 1
