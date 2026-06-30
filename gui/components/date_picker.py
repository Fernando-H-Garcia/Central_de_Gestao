import customtkinter as ctk
from datetime import datetime

class DatePickerFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        # Lists for OptionMenus
        self.days = [f"{i:02d}" for i in range(1, 32)]
        self.months = [f"{i:02d}" for i in range(1, 13)]
        
        current_year = datetime.now().year
        self.years = [str(y) for y in range(current_year - 2, current_year + 10)]
        
        # Frame to hold the 3 dropdowns
        self.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.opt_day = ctk.CTkOptionMenu(self, values=["Dia"] + self.days, width=70)
        self.opt_day.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        self.opt_month = ctk.CTkOptionMenu(self, values=["Mês"] + self.months, width=70)
        self.opt_month.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.opt_year = ctk.CTkOptionMenu(self, values=["Ano"] + self.years, width=80)
        self.opt_year.grid(row=0, column=2, padx=(5, 0), sticky="ew")
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        self.set_date(today_str)

    def get_date(self) -> str:
        """Returns date in YYYY-MM-DD format or None if incomplete."""
        d = self.opt_day.get()
        m = self.opt_month.get()
        y = self.opt_year.get()
        
        if d == "Dia" or m == "Mês" or y == "Ano":
            return None
            
        return f"{y}-{m}-{d}"

    def set_date(self, date_str: str):
        """Sets the date from YYYY-MM-DD string."""
        if not date_str:
            self.opt_day.set("Dia")
            self.opt_month.set("Mês")
            self.opt_year.set("Ano")
            return
            
        try:
            # Assumes YYYY-MM-DD
            parts = str(date_str).split(' ')[0].split('-')
            if len(parts) == 3:
                y, m, d = parts
                self.opt_year.set(y)
                self.opt_month.set(m)
                self.opt_day.set(d)
        except Exception:
            self.opt_day.set("Dia")
            self.opt_month.set("Mês")
            self.opt_year.set("Ano")

    def configure(self, state=None, **kwargs):
        super().configure(**kwargs)
        if state is not None:
            self.opt_day.configure(state=state)
            self.opt_month.configure(state=state)
            self.opt_year.configure(state=state)
