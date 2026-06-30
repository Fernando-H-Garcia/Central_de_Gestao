import tkinter as tk
import customtkinter as ctk
import tkinter.messagebox as messagebox
from datetime import datetime, timedelta
import calendar
from services.agenda_service import AgendaService
from services.project_service import ProjectService
from services.task_service import TaskService
from gui.components.date_picker import DatePickerFrame
from database.connection import get_db_cursor
from core.event_bus import event_bus

class ScheduleEditDialog(ctk.CTkToplevel):
    def __init__(self, master, agenda_service: AgendaService, task_service: TaskService, entity_type: str, entity_id: int, agenda_item=None, on_save=None):
        super().__init__(master)
        self.agenda_service = agenda_service
        self.task_service = task_service
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.agenda_item = agenda_item
        self.on_save = on_save

        self.title("Programar Período de Trabalho" if not agenda_item else "Editar Período de Trabalho")
        self.geometry("480x600")
        self.resizable(False, False)
        
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 480) // 2
        y = (self.winfo_screenheight() - 600) // 2
        self.geometry(f"+{x}+{y}")
        self.transient(master)
        self.grab_set()

        # Load entity title
        title_text = f"{entity_type.capitalize()} ID: {entity_id}"
        default_effort = "0.0"
        if entity_type == 'task':
            t = self.task_service.task_repo.get_by_id(entity_id)
            if t:
                title_text = f"Tarefa: {t.title}"
                default_effort = str(getattr(t, "estimated_hours", 0.0))
        elif entity_type == 'project':
            from services.project_service import ProjectService
            p = ProjectService().project_repo.get_by_id(entity_id)
            if p:
                title_text = f"Projeto: {p.name}"

        lbl_header = ctk.CTkLabel(self, text=title_text, font=ctk.CTkFont(size=16, weight="bold"), wraplength=440)
        lbl_header.pack(pady=15, padx=20)

        # Form scroll
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)

        lp = dict(padx=20, pady=(10, 2), anchor="w")
        wp = dict(padx=20, pady=(0, 8), fill="x")

        ctk.CTkLabel(self.scroll, text="Data Inicial:", font=ctk.CTkFont(weight="bold")).pack(**lp)
        self.dp_start = DatePickerFrame(self.scroll)
        self.dp_start.pack(**wp)

        ctk.CTkLabel(self.scroll, text="Data Final:", font=ctk.CTkFont(weight="bold")).pack(**lp)
        self.dp_end = DatePickerFrame(self.scroll)
        self.dp_end.pack(**wp)

        ctk.CTkLabel(self.scroll, text="Esforço Estimado (Horas):", font=ctk.CTkFont(weight="bold")).pack(**lp)
        self.ent_effort = ctk.CTkEntry(self.scroll, placeholder_text="Ex: 8.5")
        self.ent_effort.pack(**wp)
        self.ent_effort.insert(0, default_effort)

        ctk.CTkLabel(self.scroll, text="Status do Agendamento:", font=ctk.CTkFont(weight="bold")).pack(**lp)
        self.opt_status = ctk.CTkOptionMenu(self.scroll, values=["planejado", "em_andamento", "pausado", "cancelado", "concluido"])
        self.opt_status.pack(**wp)
        self.opt_status.set("planejado")

        # Task Dependencies UI (Only for Tasks)
        if self.entity_type == 'task':
            ctk.CTkLabel(self.scroll, text="Dependência (Requer que a tarefa abaixo termine):", font=ctk.CTkFont(weight="bold")).pack(**lp)
            
            # Dropdown of all other active tasks
            all_tasks = self.task_service.get_all_active()
            other_tasks = [t for t in all_tasks if t.id != self.entity_id]
            self.task_choices = {"Nenhuma": None}
            for ot in other_tasks:
                self.task_choices[f"{ot.id} - {ot.title}"] = ot.id

            self.opt_dep = ctk.CTkOptionMenu(self.scroll, values=list(self.task_choices.keys()))
            self.opt_dep.pack(**wp)
            self.opt_dep.set("Nenhuma")

            # Dependency Strength
            ctk.CTkLabel(self.scroll, text="Força da Dependência:", font=ctk.CTkFont(weight="bold")).pack(**lp)
            self.opt_dep_strength = ctk.CTkOptionMenu(self.scroll, values=["obrigatória", "recomendada", "informativa"])
            self.opt_dep_strength.pack(**wp)
            self.opt_dep_strength.set("obrigatória")

            # Check if dependency already exists
            curr_deps = self.agenda_service.dep_repo.get_dependencies_for_task(self.entity_id)
            if curr_deps:
                for k, v in self.task_choices.items():
                    if v == curr_deps[0].depends_on_task_id:
                        self.opt_dep.set(k)
                        self.opt_dep_strength.set(getattr(curr_deps[0], "dependency_strength", "obrigatória"))
                        break

        # Load existing values
        if self.agenda_item:
            if self.agenda_item.start_date:
                self.dp_start.set_date(self.agenda_item.start_date)
            if self.agenda_item.end_date:
                self.dp_end.set_date(self.agenda_item.end_date)
            self.ent_effort.delete(0, "end")
            self.ent_effort.insert(0, str(self.agenda_item.effort_hours))
            self.opt_status.set(self.agenda_item.schedule_status)

        # Actions
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", pady=15, padx=20)

        if self.agenda_item:
            self.btn_del = ctk.CTkButton(btn_frame, text="🗑 Excluir", fg_color="#C23616", hover_color="#8C250E", command=self.delete, width=100)
            self.btn_del.pack(side="left", padx=5)

        self.btn_save = ctk.CTkButton(btn_frame, text="Salvar Agendamento", fg_color="#2B8C52", hover_color="#1E663B", command=self.save)
        self.btn_save.pack(side="right", padx=5, fill="x", expand=True)

    def save(self):
        start = self.dp_start.get_date()
        end = self.dp_end.get_date()
        if not start or not end:
            messagebox.showwarning("Aviso", "As datas de início e fim são obrigatórias.")
            return

        try:
            effort = float(self.ent_effort.get().strip() or 0)
        except ValueError:
            messagebox.showwarning("Aviso", "O esforço em horas deve ser um valor numérico.")
            return

        status = self.opt_status.get()

        if self.agenda_item:
            self.agenda_item.start_date = start
            self.agenda_item.end_date = end
            self.agenda_item.effort_hours = effort
            self.agenda_item.schedule_status = status
            self.agenda_service.update_schedule(self.agenda_item)
        else:
            self.agenda_item = self.agenda_service.create_schedule(
                self.entity_type, self.entity_id, start, end, effort, status
            )

        # Save dependency (only for tasks)
        if self.entity_type == 'task':
            selected_dep = self.opt_dep.get()
            dep_id = self.task_choices[selected_dep]
            strength = self.opt_dep_strength.get()
            
            # Clear old dependencies first
            curr_deps = self.agenda_service.dep_repo.get_dependencies_for_task(self.entity_id)
            for d in curr_deps:
                self.agenda_service.remove_dependency(self.entity_id, d.depends_on_task_id)

            if dep_id:
                try:
                    self.agenda_service.add_dependency(self.entity_id, dep_id, "finish_to_start", strength)
                except ValueError as ve:
                    messagebox.showerror("Erro de Dependência", str(ve))

        event_bus.emit("entity_updated")
        if self.on_save:
            self.on_save()
        self.destroy()

    def delete(self):
        if messagebox.askyesno("Excluir", "Deseja remover este período agendado?"):
            # Se for uma tarefa, limpar também as dependências vinculadas a este
            # agendamento, evitando que o status "Bloqueado" persista no banco.
            if self.entity_type == 'task':
                curr_deps = self.agenda_service.dep_repo.get_dependencies_for_task(self.entity_id)
                for d in curr_deps:
                    self.agenda_service.remove_dependency(self.entity_id, d.depends_on_task_id)

            self.agenda_service.delete_schedule(self.agenda_item.id)
            event_bus.emit("entity_updated")
            if self.on_save:
                self.on_save()
            self.destroy()


class CollapsibleSection(ctk.CTkFrame):
    def __init__(self, master, title, text_color, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.collapsed = False
        
        self.header = ctk.CTkButton(
            self, 
            text=f"▼ {title}", 
            fg_color="transparent", 
            text_color=text_color,
            anchor="w", 
            font=ctk.CTkFont(size=12, weight="bold"),
            hover_color=("#e0e0e0", "#2b2b2b"),
            command=self.toggle
        )
        self.header.pack(fill="x", pady=2)
        
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=5)
        
    def toggle(self):
        if self.collapsed:
            self.container.pack(fill="both", expand=True, padx=5)
            self.header.configure(text=self.header.cget("text").replace("▶", "▼"))
            self.collapsed = False
        else:
            self.container.pack_forget()
            self.header.configure(text=self.header.cget("text").replace("▼", "▶"))
            self.collapsed = True


class AgendaView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.agenda_service = AgendaService()
        self.project_service = ProjectService()
        self.task_service = TaskService()

        # Date & view state
        self.current_date = datetime.now()
        self.active_range = 'semana' # 'dia', 'semana', 'proxima_semana', 'mes'
        self.selected_project_filters = {}

        # Project color mapping palette
        self.proj_colors = ["#2ecc71", "#3498db", "#e67e22", "#9b59b6", "#e74c3c", "#1abc9c", "#f1c40f", "#34495e", "#95a5a6", "#d35400"]

        event_bus.subscribe("snapshot_updated", lambda _: self.on_entity_updated())
        self.bind("<Map>", lambda e: self.on_map(e))

        # Drag & Drop states
        self.drag_window = None
        self.drag_task_id = None
        
        self.drag_bar_item = None
        self.drag_bar_schedule = None
        self.drag_bar_start_x = 0

        # Main Layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1, minsize=260)  # Left panel (Filters & Backlog)
        self.grid_columnconfigure(1, weight=4)              # Right panel (Timeline & metrics)

        # ==========================================
        # LEFT PANEL (Filtros & Backlog)
        # ==========================================
        self.left_panel = ctk.CTkFrame(self, corner_radius=0)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.left_panel.grid_rowconfigure(2, weight=1)

        # Left header
        ctk.CTkLabel(self.left_panel, text="Planejador", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(15, 5), padx=15, anchor="w")

        # Filters Title & Collapsible Scroll
        ctk.CTkLabel(self.left_panel, text="📁 Filtrar por Projeto", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 2), padx=15, anchor="w")
        self.filter_scroll = ctk.CTkScrollableFrame(self.left_panel, fg_color="transparent", height=120)
        self.filter_scroll.pack(fill="x", padx=10, pady=2)

        # Backlog Section
        ctk.CTkLabel(self.left_panel, text="🗂️ Backlog (Sem Agenda)", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 2), padx=15, anchor="w")
        self.backlog_scroll = ctk.CTkScrollableFrame(self.left_panel, fg_color="transparent")
        self.backlog_scroll.pack(fill="both", expand=True, padx=10, pady=5)

        # ==========================================
        # RIGHT PANEL (Timeline)
        # ==========================================
        self.right_panel = ctk.CTkFrame(self, corner_radius=0)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.right_panel.grid_rowconfigure(2, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

        # Metrics Panel (Junho 2026, Planejado: 86h...)
        self.metrics_frame = ctk.CTkFrame(self.right_panel, fg_color=("#f0f0f0", "#202020"))
        self.metrics_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        
        self.lbl_metrics_title = ctk.CTkLabel(self.metrics_frame, text="", font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_metrics_title.pack(side="left", padx=15, pady=8)

        self.lbl_metrics_summary = ctk.CTkLabel(self.metrics_frame, text="", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_metrics_summary.pack(side="right", padx=15, pady=8)

        # Header Navigation & Quick Filters
        self.header_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.header_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        
        # Navigation
        self.btn_prev = ctk.CTkButton(self.header_frame, text="◀ Anterior", width=80, command=self.prev_period)
        self.btn_prev.pack(side="left", padx=5)

        self.btn_today = ctk.CTkButton(self.header_frame, text="Hoje", width=60, command=self.go_today)
        self.btn_today.pack(side="left", padx=2)

        self.btn_next = ctk.CTkButton(self.header_frame, text="Próximo ▶", width=80, command=self.next_period)
        self.btn_next.pack(side="left", padx=5)

        # Quick Range Filter
        self.range_buttons_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.range_buttons_frame.pack(side="right", padx=5)

        self.btn_range_today = ctk.CTkButton(self.range_buttons_frame, text="Hoje", width=60, command=lambda: self.set_range('dia'))
        self.btn_range_today.pack(side="left", padx=2)

        self.btn_range_week = ctk.CTkButton(self.range_buttons_frame, text="Esta Semana", width=90, command=lambda: self.set_range('semana'))
        self.btn_range_week.pack(side="left", padx=2)

        self.btn_range_next_week = ctk.CTkButton(self.range_buttons_frame, text="Próx. Semana", width=90, command=lambda: self.set_range('proxima_semana'))
        self.btn_range_next_week.pack(side="left", padx=2)

        self.btn_range_month = ctk.CTkButton(self.range_buttons_frame, text="Este Mês", width=80, command=lambda: self.set_range('mes'))
        self.btn_range_month.pack(side="left", padx=2)

        # Timeline Containers (Split frozen and scrolling days using Canvas)
        self.timeline_container = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.timeline_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        
        self.timeline_container.grid_rowconfigure(0, weight=1)
        self.timeline_container.grid_columnconfigure(0, weight=0, minsize=240) # Frozen Task Canvas
        self.timeline_container.grid_columnconfigure(1, weight=1)               # Days Timeline Canvas
        self.timeline_container.grid_columnconfigure(2, weight=0)               # Shared vertical scrollbar
        self.timeline_container.grid_rowconfigure(1, weight=0)                  # Shared horizontal scrollbar

        # Left Canvas (Frozen Task List)
        self.left_canvas = tk.Canvas(self.timeline_container, highlightthickness=0, bg="#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0", width=240)
        self.left_canvas.grid(row=0, column=0, sticky="nsew")

        # Right Canvas (Gantt days grid)
        self.right_canvas = tk.Canvas(self.timeline_container, highlightthickness=0, bg="#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0")
        self.right_canvas.grid(row=0, column=1, sticky="nsew")

        # Shared vertical scrollbar
        self.timeline_v_scrollbar = ctk.CTkScrollbar(self.timeline_container, orientation="vertical", command=self.sync_scrolls)
        self.timeline_v_scrollbar.grid(row=0, column=2, sticky="ns")

        # Shared horizontal scrollbar
        self.timeline_h_scrollbar = ctk.CTkScrollbar(self.timeline_container, orientation="horizontal", command=self.right_canvas.xview)
        self.timeline_h_scrollbar.grid(row=1, column=1, sticky="ew")

        # Configure scrollbar updates
        self.right_canvas.configure(xscrollcommand=self.timeline_h_scrollbar.set, yscrollcommand=self.on_right_y_scroll)
        self.left_canvas.configure(yscrollcommand=self.on_left_y_scroll)

        # Bind mousewheel for synced vertical scroll
        self.left_canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.right_canvas.bind("<MouseWheel>", self.on_mousewheel)

        self.refresh()

    def sync_scrolls(self, *args):
        self.left_canvas.yview(*args)
        self.right_canvas.yview(*args)

    def on_right_y_scroll(self, *args):
        self.timeline_v_scrollbar.set(*args)
        self.left_canvas.yview_moveto(args[0])

    def on_left_y_scroll(self, *args):
        self.timeline_v_scrollbar.set(*args)
        self.right_canvas.yview_moveto(args[0])

    def on_mousewheel(self, event):
        self.left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.right_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def get_project_color(self, project_id: int) -> str:
        if not project_id:
            return "#7f8c8d"
        return self.proj_colors[project_id % len(self.proj_colors)]

    def go_today(self):
        self.current_date = datetime.now()
        self.refresh()
        self.scroll_to_today()

    def scroll_to_today(self):
        self.after(50, self._do_scroll_to_today)

    def _do_scroll_to_today(self):
        dates = self.get_date_range()
        if not dates:
            return
        today_dt = datetime.now().date()
        col_width = 80
        total_width = len(dates) * col_width
        if total_width <= 0:
            return
        for idx, dt in enumerate(dates):
            if dt.date() == today_dt:
                canvas_width = self.right_canvas.winfo_width()
                target_x = (idx * col_width) - (canvas_width / 2) + (col_width / 2)
                fraction = max(0.0, min(1.0, target_x / total_width))
                self.right_canvas.xview_moveto(fraction)
                break

    def set_range(self, range_mode: str):
        self.active_range = range_mode
        self.refresh()

    def prev_period(self):
        if self.active_range == 'dia':
            self.current_date -= timedelta(days=1)
        elif self.active_range == 'semana':
            self.current_date -= timedelta(days=7)
        elif self.active_range == 'proxima_semana':
            self.current_date -= timedelta(days=7)
        elif self.active_range == 'mes':
            # subtract 1 month
            first = self.current_date.replace(day=1)
            prev = first - timedelta(days=1)
            self.current_date = prev
        self.refresh()

    def next_period(self):
        if self.active_range == 'dia':
            self.current_date += timedelta(days=1)
        elif self.active_range == 'semana':
            self.current_date += timedelta(days=7)
        elif self.active_range == 'proxima_semana':
            self.current_date += timedelta(days=7)
        elif self.active_range == 'mes':
            # add 1 month
            days = calendar.monthrange(self.current_date.year, self.current_date.month)[1]
            self.current_date = self.current_date.replace(day=1) + timedelta(days=days)
        self.refresh()

    def get_date_range(self):
        """Returns list of datetime objects matching self.active_range around self.current_date."""
        dates = []
        if self.active_range == 'dia':
            start = self.current_date
            for i in range(3):
                dates.append(start + timedelta(days=i))
        elif self.active_range == 'semana':
            # Monday to Sunday of the current week
            monday = self.current_date - timedelta(days=self.current_date.weekday())
            for i in range(7):
                dates.append(monday + timedelta(days=i))
        elif self.active_range == 'proxima_semana':
            # Monday to Sunday of next week
            monday = self.current_date - timedelta(days=self.current_date.weekday()) + timedelta(days=7)
            for i in range(7):
                dates.append(monday + timedelta(days=i))
        elif self.active_range == 'mes':
            today_dt = datetime.now()
            if self.current_date.year == today_dt.year and self.current_date.month == today_dt.month:
                # Start from the Sunday of the current week containing today
                offset = (today_dt.weekday() + 1) % 7
                start_date = today_dt - timedelta(days=offset)
                # Last day of current month
                num_days = calendar.monthrange(self.current_date.year, self.current_date.month)[1]
                last_day = self.current_date.replace(day=num_days)
                
                # Append days from start_date to last_day
                curr = start_date
                while curr.date() <= last_day.date():
                    dates.append(curr)
                    curr += timedelta(days=1)
            else:
                # All days of that month
                num_days = calendar.monthrange(self.current_date.year, self.current_date.month)[1]
                first = self.current_date.replace(day=1)
                for i in range(num_days):
                    dates.append(first + timedelta(days=i))
        return dates

    def on_filter_change(self):
        self.render_timeline()

    def render_filters(self):
        for w in self.filter_scroll.winfo_children():
            w.destroy()

        active_projects = self.project_service.get_all_active()
        for p in active_projects:
            if p.id not in self.selected_project_filters:
                self.selected_project_filters[p.id] = tk.BooleanVar(value=True)

            color = self.get_project_color(p.id)
            chk = ctk.CTkCheckBox(
                self.filter_scroll, 
                text=p.name, 
                text_color=color,
                variable=self.selected_project_filters[p.id],
                command=self.on_filter_change
            )
            chk.pack(anchor="w", pady=3, padx=5)

    def render_backlog(self):
        import customtkinter as ctk
        
        # Iniciar Object Pool na primeira vez
        if not hasattr(self, '_backlog_pool_ui'):
            self._backlog_pool_ui = {
                'Alta/Máxima': {'sec': None, 'cards': []},
                'Média': {'sec': None, 'cards': []},
                'Baixa': {'sec': None, 'cards': []}
            }
            self.lbl_empty_backlog = ctk.CTkLabel(self.backlog_scroll, text="Backlog vazio!", font=ctk.CTkFont(slant="italic"), text_color="gray")

        all_tasks = self.task_service.get_all_active()
        scheduled_task_ids = {item.entity_id for item in self.agenda_service.get_all_schedules() if item.entity_type == 'task'}
        backlog_tasks = [t for t in all_tasks if t.id not in scheduled_task_ids]

        # Esconde tudo primeiro
        self.lbl_empty_backlog.pack_forget()
        for cat_data in self._backlog_pool_ui.values():
            if cat_data['sec']:
                cat_data['sec'].pack_forget()

        if not backlog_tasks:
            self.lbl_empty_backlog.pack(pady=20)
            return

        # Group by priority
        grouped = {"Alta/Máxima": [], "Média": [], "Baixa": []}
        for t in backlog_tasks:
            energy = getattr(t, "energy_level", "Média")
            if energy in ("Alta", "Máxima"):
                grouped["Alta/Máxima"].append(t)
            elif energy == "Baixa":
                grouped["Baixa"].append(t)
            else:
                grouped["Média"].append(t)

        projects_dict = {p.id: p.name for p in self.project_service.get_all_active()}

        priority_colors = {
            "Alta/Máxima": "#E11D48",
            "Média": "#EAB308",
            "Baixa": "#22C55E"
        }

        for category, tasks in grouped.items():
            pool = self._backlog_pool_ui[category]
            
            if not tasks:
                continue

            if not pool['sec']:
                
                # Actually, CollapsibleSection is defined in this module or imported globally
                pool['sec'] = CollapsibleSection(self.backlog_scroll, f"{category} ({len(tasks)})", priority_colors[category])
            else:
                arrow = "▶" if pool['sec'].collapsed else "▼"
                pool['sec'].header.configure(text=f"{arrow} {category} ({len(tasks)})")

                
            pool['sec'].pack(fill="x", pady=2)
            
            # Cards pool
            cards_pool = pool['cards']
            for c_idx in range(len(tasks), len(cards_pool)):
                cards_pool[c_idx].pack_forget()

            for idx, task in enumerate(tasks):
                proj_name = projects_dict.get(task.project_id, "Sem Projeto")
                est_text = f"{getattr(task, 'estimated_hours', 0.0):.1f}h"
                is_milestone = getattr(task, "is_milestone", False)
                if is_milestone:
                    est_text = "💎 Marco"
                
                desc = f"Projeto: {proj_name} | {est_text}"

                if idx >= len(cards_pool):
                    card = ctk.CTkFrame(pool['sec'].container, fg_color=("#e6e6e6", "#2b2b2b"), border_width=1, border_color=priority_colors[category])
                    lbl_title = ctk.CTkLabel(card, text="", wraplength=210, anchor="w", justify="left", font=ctk.CTkFont(weight="bold"))
                    lbl_title.pack(fill="x", padx=8, pady=(4, 2))
                    lbl_desc = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=10), text_color="gray", anchor="w")
                    lbl_desc.pack(fill="x", padx=8, pady=(0, 4))
                    
                    card.lbl_title = lbl_title
                    card.lbl_desc = lbl_desc
                    
                    def on_enter(e, c=card):
                        c._is_hovered = True
                        if hasattr(c, '_leave_after_id'):
                            c.after_cancel(c._leave_after_id)
                            delattr(c, '_leave_after_id')
                        if not hasattr(c, '_enter_after_id'):
                            def apply_hover():
                                if getattr(c, '_is_hovered', False):
                                    try: c.configure(fg_color=("#d5e5ff", "#22354f"))
                                    except: pass
                                if hasattr(c, '_enter_after_id'): delattr(c, '_enter_after_id')
                            c._enter_after_id = c.after(25, apply_hover)

                    def on_leave(e, c=card):
                        c._is_hovered = False
                        if hasattr(c, '_enter_after_id'):
                            c.after_cancel(c._enter_after_id)
                            delattr(c, '_enter_after_id')
                        if not hasattr(c, '_leave_after_id'):
                            def apply_leave():
                                if not getattr(c, '_is_hovered', False):
                                    try: c.configure(fg_color=("#e6e6e6", "#2b2b2b"))
                                    except: pass
                                if hasattr(c, '_leave_after_id'): delattr(c, '_leave_after_id')
                            c._leave_after_id = c.after(25, apply_leave)
                    for widget in (card, lbl_title, lbl_desc):
                        widget.bind("<Enter>", on_enter)
                        widget.bind("<Leave>", on_leave)

                    cards_pool.append(card)
                
                card = cards_pool[idx]
                card.pack(fill="x", pady=3)
                
                card.lbl_title.configure(text=task.title)
                card.lbl_desc.configure(text=desc)

                # Update dynamic bindings
                def bind_dc(widget, t_id=task.id, t_title=task.title):
                    widget.bind("<Double-Button-1>", lambda e, tid=t_id: self.open_schedule_dialog(tid))
                    widget.bind("<ButtonPress-1>", lambda e, tid=t_id, tname=t_title: self.on_backlog_drag_start(e, tid, tname))
                    widget.bind("<B1-Motion>", self.on_backlog_drag_motion)
                    widget.bind("<ButtonRelease-1>", self.on_backlog_drag_release)
                
                bind_dc(card)
                bind_dc(card.lbl_title)
                bind_dc(card.lbl_desc)

    def on_backlog_drag_start(self, event, task_id, task_title):
        self.drag_task_id = task_id
        
        self.drag_window = ctk.CTkToplevel(self)
        self.drag_window.overrideredirect(True)
        self.drag_window.attributes("-alpha", 0.8)
        self.drag_window.configure(fg_color="#333333")
        
        lbl = ctk.CTkLabel(self.drag_window, text=f"📅 {task_title}", font=ctk.CTkFont(size=12, weight="bold"), text_color="white", padx=10, pady=5)
        lbl.pack()
        
        self.drag_window.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

    def on_backlog_drag_motion(self, event):
        if self.drag_window:
            self.drag_window.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

    def on_backlog_drag_release(self, event):
        if self.drag_window:
            self.drag_window.destroy()
            self.drag_window = None

        # Check drop coordinates on self.right_canvas
        rx = event.x_root - self.right_canvas.winfo_rootx()
        ry = event.y_root - self.right_canvas.winfo_rooty()

        if 0 <= rx <= self.right_canvas.winfo_width() and 0 <= ry <= self.right_canvas.winfo_height():
            # Translate relative to scroll coordinates
            canvas_x = self.right_canvas.canvasx(rx)
            col_width = 80
            col_idx = int((canvas_x) // col_width)
            dates = self.get_date_range()
            if 0 <= col_idx < len(dates):
                target_date_str = dates[col_idx].strftime("%Y-%m-%d")
                
                # Fetch task estimated hours
                task = self.task_service.task_repo.get_by_id(self.drag_task_id)
                effort = getattr(task, "estimated_hours", 0.0) or 8.0
                
                # Automatically create schedule record
                self.agenda_service.create_schedule(
                    entity_type='task',
                    entity_id=self.drag_task_id,
                    start_date=target_date_str,
                    end_date=target_date_str,
                    effort_hours=effort,
                    schedule_status='planejado'
                )
                event_bus.emit("entity_updated")

    def open_schedule_dialog(self, task_id: int, agenda_item=None):
        ScheduleEditDialog(
            self.winfo_toplevel(), 
            self.agenda_service, 
            self.task_service, 
            "task", 
            task_id, 
            agenda_item=agenda_item, 
            on_save=self.refresh
        )

    def _show_gantt_context_menu(self, event, task_id: int, agenda_item):
        """Exibe menu de contexto (botão direito) na barra do Gantt ou no rótulo da tarefa."""
        from gui.components.context_menu import ContextMenu
        menu = ContextMenu(self.winfo_toplevel())
        menu.add_command("✏️  Editar",
                         command=lambda: self.open_schedule_dialog(task_id, agenda_item))
        menu.add_separator()
        menu.add_header("Gerenciar")
        menu.add_command("🗑️  Excluir Agendamento",
                         command=lambda: self._delete_gantt_item(task_id, agenda_item),
                         danger=True)
        menu.tk_popup(event.x_root, event.y_root)

    def _delete_gantt_item(self, task_id: int, agenda_item):
        """Exclui o agendamento (e dependências vinculadas) com confirmação."""
        import tkinter.messagebox as messagebox

        if not messagebox.askyesno(
            "Excluir Agendamento",
            "Deseja remover este período agendado?\n\n"
            "As dependências vinculadas a esta tarefa também serão removidas."
        ):
            return

        # Limpar dependências da tarefa antes de excluir o agendamento
        try:
            curr_deps = self.agenda_service.dep_repo.get_dependencies_for_task(task_id)
            for d in curr_deps:
                self.agenda_service.remove_dependency(task_id, d.depends_on_task_id)
        except Exception as e:
            print(f"[Agenda] Aviso ao limpar dependências: {e}")

        self.agenda_service.delete_schedule(agenda_item.id)
        from core.event_bus import event_bus
        event_bus.emit("entity_updated")


    def render_timeline(self):
        # Clear Canvas items
        self.left_canvas.delete("all")
        self.right_canvas.delete("all")


        dates = self.get_date_range()
        if not dates:
            return

        # Update metrics title based on range in Portuguese
        MONTHS_PT = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }
        if self.active_range == 'dia':
            title_text = self.current_date.strftime("%d/%m/%Y")
        elif self.active_range in ('semana', 'proxima_semana'):
            monday = self.current_date - timedelta(days=self.current_date.weekday())
            if self.active_range == 'proxima_semana':
                monday += timedelta(days=7)
            sunday = monday + timedelta(days=6)
            title_text = f"Semana: {monday.strftime('%d/%m/%Y')} - {sunday.strftime('%d/%m/%Y')}"
        elif self.active_range == 'mes':
            month_name = MONTHS_PT[self.current_date.month]
            title_text = f"{month_name} {self.current_date.year}"
        else:
            title_text = ""
        self.lbl_metrics_title.configure(text=title_text)

        # Timeline Layout constants
        col_width = 80
        header_height = 80
        row_height = 36
        bar_height = 24

        # Light/Dark styles
        is_dark = ctk.get_appearance_mode() == "Dark"
        line_color = "#3a3a3a" if is_dark else "#d0d0d0"
        bg_weekend = "#232323" if is_dark else "#e5e5e5"
        text_color = "white" if is_dark else "black"
        meta_color = "#aaaaaa" if is_dark else "#666666"

        # Today highlight colors (uniform color for the entire column)
        today_header_bg = "#1f4068" if is_dark else "#a3c9ff"
        today_body_bg = today_header_bg

        from utils.instrumentation import PerfContext

        with PerfContext("Buscar tarefas", module="Agenda", category="Banco"):
            # Batch load all needed database info at once to avoid O(N) queries during rendering
            task_statuses = {}
            pending_alerts_task_ids = set()
            task_dependency_ids = set()
            blocked_task_ids = set()
            
            try:
                with get_db_cursor() as cursor:
                    # 1. Task statuses
                    cursor.execute("SELECT id, status FROM tasks WHERE deleted_at IS NULL")
                    task_statuses = {row['id']: row['status'] for row in cursor.fetchall()}
                    
                    # 2. Pending alerts for tasks
                    cursor.execute("SELECT entity_id FROM alerts WHERE entity_type = 'task' AND status = 'pending'")
                    pending_alerts_task_ids = {row['entity_id'] for row in cursor.fetchall()}
                    
                    # 3. Tasks with active dependencies
                    cursor.execute("""
                        SELECT DISTINCT td.task_id FROM task_dependencies td
                        JOIN tasks t1 ON t1.id = td.task_id AND t1.deleted_at IS NULL
                        JOIN tasks t2 ON t2.id = td.depends_on_task_id AND t2.deleted_at IS NULL
                    """)
                    task_dependency_ids = {row['task_id'] for row in cursor.fetchall()}
                    
                    # 4. Blocked tasks
                    cursor.execute("""
                        SELECT td.task_id, td.depends_on_task_id, td.dependency_strength
                        FROM task_dependencies td
                        JOIN tasks t1 ON t1.id = td.task_id AND t1.deleted_at IS NULL
                        JOIN tasks t2 ON t2.id = td.depends_on_task_id AND t2.deleted_at IS NULL
                    """)
                    all_deps = cursor.fetchall()
                    deps_by_task = {}
                    for d in all_deps:
                        tid = d['task_id']
                        if tid not in deps_by_task:
                            deps_by_task[tid] = []
                        deps_by_task[tid].append(d)
                    for tid, deps in deps_by_task.items():
                        for dep in deps:
                            if dep['dependency_strength'] in ('obrigatória', 'obrigatria'):
                                dep_status = task_statuses.get(dep['depends_on_task_id'])
                                if dep_status and dep_status != 'Concluído' and dep_status != 'Concludo':
                                    blocked_task_ids.add(tid)
                                    break
            except Exception as e:
                print(f"Error preloading timeline batch info: {e}")

        with PerfContext("Buscar eventos", module="Agenda", category="Banco"):
            # Get planned tasks
            schedules = self.agenda_service.get_all_schedules()
            range_start_str = dates[0].strftime("%Y-%m-%d")
            range_end_str = dates[-1].strftime("%Y-%m-%d")

        # Filter and sort visible schedules
        visible_schedules = []
        for item in schedules:
            if item.entity_type != 'task' or item.schedule_status == 'cancelado':
                continue
            if item.end_date < range_start_str or item.start_date > range_end_str:
                continue
            task = self.task_service.task_repo.get_by_id(item.entity_id)
            if not task:
                continue
            if task.project_id and task.project_id in self.selected_project_filters:
                if not self.selected_project_filters[task.project_id].get():
                    continue
            visible_schedules.append((item, task))

        # Stacking logic to prevent overlaps
        schedules_sorted = sorted(visible_schedules, key=lambda pair: (pair[0].start_date, pair[0].end_date))
        lanes = [] # Lists of schedules per lane
        schedule_lanes = {} # item.id -> lane_index

        for pair in schedules_sorted:
            item, task = pair
            allocated = False
            for lane_idx, lane_pairs in enumerate(lanes):
                overlap = False
                for lp_item, lp_task in lane_pairs:
                    if not (item.end_date < lp_item.start_date or item.start_date > lp_item.end_date):
                        overlap = True
                        break
                if not overlap:
                    lane_pairs.append(pair)
                    schedule_lanes[item.id] = lane_idx
                    allocated = True
                    break
            if not allocated:
                lanes.append([pair])
                schedule_lanes[item.id] = len(lanes) - 1

        # Render rows helper metadata
        total_rows = len(lanes)
        total_canvas_height = max(500, header_height + total_rows * row_height)
        total_width = len(dates) * col_width

        # First, draw background grid on right canvas
        with PerfContext("Renderizar grade", module="Agenda", category="Renderização"):
            today_dt = datetime.now()
            for idx, dt in enumerate(dates):
                date_str = dt.strftime("%Y-%m-%d")
                
                # Destaque de fim de semana (Sábado e Domingo)
                is_weekend = dt.weekday() >= 5
                x0 = idx * col_width
                x1 = x0 + col_width

                is_today = (dt.date() == today_dt.date())

                if is_today:
                    # Highlight today's column body
                    self.right_canvas.create_rectangle(x0, 25, x1, total_canvas_height, fill=today_body_bg, outline="")
                elif is_weekend:
                    self.right_canvas.create_rectangle(x0, 0, x1, total_canvas_height, fill=bg_weekend, outline="")

                # Draw day vertical grids
                self.right_canvas.create_line(x1, 0, x1, total_canvas_height, fill=line_color, width=1)

        # Draw weeks grouping header row
        # Group days by calendar week (Monday to Sunday)
        weeks = []
        current_week = []
        for idx, dt in enumerate(dates):
            current_week.append((idx, dt))
            # If Sunday or last date, flush week
            if dt.weekday() == 6 or idx == len(dates) - 1:
                weeks.append(current_week)
                current_week = []

        for w in weeks:
            first_idx = w[0][0]
            last_idx = w[-1][0]
            wx0 = first_idx * col_width
            wx1 = (last_idx + 1) * col_width

            # Draw week header rectangle
            self.right_canvas.create_rectangle(wx0, 0, wx1, 25, fill="#1f538d" if is_dark else "#d0e0f5", outline=line_color)
            
            # Format week text
            first_dt = w[0][1]
            last_dt = w[-1][1]
            week_title = f"Semana: {first_dt.strftime('%d/%m')} - {last_dt.strftime('%d/%m')}"
            self.right_canvas.create_text(wx0 + 10, 12, text=week_title, font=("Arial", 9, "bold"), fill="white" if is_dark else "black", anchor="w")

        # Batch load capacities and planned hours in one go
        date_strs = [dt.strftime("%Y-%m-%d") for dt in dates]
        metrics_dict = self.agenda_service.get_agenda_metrics_for_dates(date_strs)

        # Draw Day labels and Capacities header rows
        for idx, dt in enumerate(dates):
            date_str = date_strs[idx]
            m = metrics_dict.get(date_str, {"capacity": 8.0, "planned": 0.0})
            cap = m["capacity"]
            planned = m["planned"]
            
            # Color based on capacity load
            ratio = (planned / max(1.0, cap))
            if ratio == 0:
                occup_color = "gray"
            elif ratio <= 0.6:
                occup_color = "#27ae60" # Green
            elif ratio <= 0.9:
                occup_color = "#f1c40f" # Yellow
            elif ratio <= 1.0:
                occup_color = "#e67e22" # Orange
            else:
                occup_color = "#c0392b" # Red
                
            x_mid = idx * col_width + (col_width / 2)
            x0 = idx * col_width
            x1 = x0 + col_width
            
            is_today = (dt.date() == today_dt.date())
            WEEKDAYS_PT = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
            day_text = f"{dt.day:02d} {WEEKDAYS_PT[dt.weekday()]}"
            
            if is_today:
                # Highlight today's header background
                self.right_canvas.create_rectangle(x0, 25, x1, header_height, fill=today_header_bg, outline="")
                self.right_canvas.create_text(x_mid, 32, text="HOJE", font=("Arial", 8, "bold"), fill="#1f538d" if not is_dark else "#a6c8ff")
                self.right_canvas.create_text(x_mid, 44, text=day_text, font=("Arial", 9, "bold"), fill=text_color)
            else:
                self.right_canvas.create_text(x_mid, 40, text=day_text, font=("Arial", 9, "bold"), fill=text_color)
            
            # Line 3: Capacities
            cap_text = f"{planned:.0f}h/{cap:.0f}h"
            cap_rect = self.right_canvas.create_rectangle(idx * col_width + 4, 52, (idx+1)*col_width - 4, 72, fill=occup_color, outline="")
            cap_txt = self.right_canvas.create_text(x_mid, 62, text=cap_text, font=("Arial", 8, "bold"), fill="white")

            # Interactive click and hover for capacity setting
            def bind_cap(target_id, d_str=date_str, c_cap=cap):
                self.right_canvas.tag_bind(target_id, "<Button-1>", lambda e: self.prompt_capacity_setting(d_str, c_cap))
                self.right_canvas.tag_bind(target_id, "<Enter>", lambda e: self.right_canvas.itemconfig(cap_rect, outline="white" if is_dark else "black", width=1))
                self.right_canvas.tag_bind(target_id, "<Leave>", lambda e: self.right_canvas.itemconfig(cap_rect, outline="", width=1))
            bind_cap(cap_rect)
            bind_cap(cap_txt)

        # Header horizontal division line
        self.right_canvas.create_line(0, header_height, total_width, header_height, fill=line_color, width=2)
        self.left_canvas.create_line(0, header_height, 240, header_height, fill=line_color, width=2)

        # Render rows
        with PerfContext("Renderizar cards", module="Agenda", category="Renderização"):
            for lane_idx, lane_pairs in enumerate(lanes):
                y_top = header_height + lane_idx * row_height
                y_mid = y_top + (row_height / 2)
                
                # Row horizontal divisions
                self.left_canvas.create_line(0, y_top + row_height, 240, y_top + row_height, fill=line_color, width=1)
                self.right_canvas.create_line(0, y_top + row_height, total_width, y_top + row_height, fill=line_color, width=1)

                # Left Pane: render frozen task name
                first_item, first_task = lane_pairs[0]
                badges = []
                if first_task.id in pending_alerts_task_ids:
                    badges.append("🔔")
                if first_task.id in blocked_task_ids:
                    badges.append("⛔")
                if first_task.id in task_dependency_ids:
                    badges.append("🔗")
                if getattr(first_task, 'originated_from_idea_id', None) is not None:
                    badges.append("💡")

                badge_str = " ".join(badges) + " " if badges else ""
                task_label_text = f"{badge_str}{first_task.title}"
            
                lbl_id = self.left_canvas.create_text(10, y_mid, text=task_label_text, font=("Arial", 9, "bold"), fill=text_color, anchor="w", width=220)
                self.left_canvas.tag_bind(lbl_id, "<Button-1>", lambda e, tid=first_task.id, it=first_item: self.open_schedule_dialog(tid, it))
                self.left_canvas.tag_bind(lbl_id, "<Button-3>", lambda e, tid=first_task.id, it=first_item: self._show_gantt_context_menu(e, tid, it))
                self.left_canvas.tag_bind(lbl_id, "<Enter>", lambda e, lid=lbl_id: self.left_canvas.itemconfig(lid, fill="#1f538d" if not is_dark else "#3498db"))
                self.left_canvas.tag_bind(lbl_id, "<Leave>", lambda e, lid=lbl_id: self.left_canvas.itemconfig(lid, fill=text_color))

                # Right Pane: draw Gantt bars for each schedule in this lane
                for item, task in lane_pairs:
                    start_dt = max(datetime.strptime(item.start_date, "%Y-%m-%d"), dates[0])
                    end_dt = min(datetime.strptime(item.end_date, "%Y-%m-%d"), dates[-1])

                    # Locate columns range
                    start_col = None
                    end_col = None
                    for d_idx, dt in enumerate(dates):
                        if dt.date() == start_dt.date():
                            start_col = d_idx
                        if dt.date() == end_dt.date():
                            end_col = d_idx

                    if start_col is not None and end_col is not None:
                        bx0 = start_col * col_width + 4
                        bx1 = (end_col + 1) * col_width - 4
                        by0 = y_top + 6
                        by1 = y_top + 6 + bar_height

                        proj_color = self.get_project_color(task.project_id)
                    
                        # Draw visual bar
                        bar_id = self.right_canvas.create_rectangle(bx0, by0, bx1, by1, fill=proj_color, outline="white" if is_dark else "black", width=1)
                    
                        bar_text = f"{task.title} ({item.effort_hours:.1f}h)"
                        if getattr(task, "is_milestone", False):
                            bar_text = f"💎 Marco: {task.title}"

                        # Text inside bar
                        text_id = self.right_canvas.create_text(bx0 + 10, by0 + (bar_height/2), text=bar_text, font=("Arial", 8, "bold"), fill="white", anchor="w")

                        # Synced dragging events (Agenda -> Agenda)
                        def make_drag_binds(b_id, t_id, s_item):
                            self.right_canvas.tag_bind(b_id, "<ButtonPress-1>", lambda e, s=s_item, bid=bar_id: self.on_bar_drag_start(e, s, bid))
                            self.right_canvas.tag_bind(b_id, "<B1-Motion>", self.on_bar_drag_motion)
                            self.right_canvas.tag_bind(b_id, "<ButtonRelease-1>", self.on_bar_drag_release)
                            self.right_canvas.tag_bind(b_id, "<Double-Button-1>", lambda e, tid=t_id, it=s_item: self.open_schedule_dialog(tid, it))
                            self.right_canvas.tag_bind(b_id, "<Button-3>", lambda e, tid=t_id, it=s_item: self._show_gantt_context_menu(e, tid, it))
                            # Hover outline styling
                            self.right_canvas.tag_bind(b_id, "<Enter>", lambda e, bar=bar_id: self.right_canvas.itemconfig(bar, outline="#3498db" if is_dark else "#1f538d", width=2))
                            self.right_canvas.tag_bind(b_id, "<Leave>", lambda e, bar=bar_id: self.right_canvas.itemconfig(bar, outline="white" if is_dark else "black", width=1))
                        
                        make_drag_binds(bar_id, task.id, item)
                        make_drag_binds(text_id, task.id, item)

        # Canvas scroll regions
        self.left_canvas.configure(scrollregion=(0, 0, 240, total_canvas_height))
        self.right_canvas.configure(scrollregion=(0, 0, total_width, total_canvas_height))

        # Metrics updates using pre-calculated in-memory dict
        total_capacity_hours = sum(metrics_dict[d]["capacity"] for d in date_strs)
        total_planned_hours = sum(metrics_dict[d]["planned"] for d in date_strs)
        blocked_count = sum(1 for item, task in visible_schedules if task.id in blocked_task_ids)

        util_pct = (total_planned_hours / max(1.0, total_capacity_hours)) * 100
        overload_hours = 0.0
        for d in date_strs:
            cap = metrics_dict[d]["capacity"]
            planned = metrics_dict[d]["planned"]
            if planned > cap:
                overload_hours += (planned - cap)

        metrics_txt = (
            f"Planejado: {total_planned_hours:.1f}h | "
            f"Capacidade: {total_capacity_hours:.1f}h | "
            f"Utilização: {util_pct:.0f}% | "
            f"Sobrecarga: {overload_hours:.1f}h | "
            f"Bloqueadas: {blocked_count}"
        )
        self.lbl_metrics_summary.configure(text=metrics_txt)

    def on_bar_drag_start(self, event, schedule_item, bar_id):
        self.drag_bar_item = bar_id
        self.drag_bar_schedule = schedule_item
        # Record horizontal scroll coordinate
        self.drag_bar_start_x = self.right_canvas.canvasx(event.x)
        
        # Get coordinates of the dragged rectangle to draw a ghost reference
        coords = self.right_canvas.coords(bar_id)
        if coords and len(coords) == 4:
            self.drag_bar_coords = coords
            is_dark = ctk.get_appearance_mode() == "Dark"
            self.drag_ghost_id = self.right_canvas.create_rectangle(
                coords[0], coords[1], coords[2], coords[3],
                outline="#3498db" if is_dark else "#1f538d", width=2, dash=(4, 2)
            )

    def on_bar_drag_motion(self, event):
        if not self.drag_bar_item or not hasattr(self, 'drag_ghost_id') or not self.drag_ghost_id:
            return
        current_x = self.right_canvas.canvasx(event.x)
        dx = current_x - self.drag_bar_start_x
        
        # Calculate snapped delta columns
        col_width = 80
        delta_cols = int(round(dx / col_width))
        snapped_dx = delta_cols * col_width
        
        if hasattr(self, 'drag_bar_coords'):
            new_x0 = self.drag_bar_coords[0] + snapped_dx
            new_x1 = self.drag_bar_coords[2] + snapped_dx
            self.right_canvas.coords(
                self.drag_ghost_id,
                new_x0, self.drag_bar_coords[1],
                new_x1, self.drag_bar_coords[3]
            )

    def on_bar_drag_release(self, event):
        # Delete visual ghost reference
        if hasattr(self, 'drag_ghost_id') and self.drag_ghost_id:
            self.right_canvas.delete(self.drag_ghost_id)
            self.drag_ghost_id = None

        if not self.drag_bar_schedule:
            return

        end_x = self.right_canvas.canvasx(event.x)
        dx = end_x - self.drag_bar_start_x
        col_width = 80
        delta_cols = int(round(dx / col_width))

        if delta_cols != 0:
            try:
                start_dt = datetime.strptime(self.drag_bar_schedule.start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(self.drag_bar_schedule.end_date, "%Y-%m-%d")

                new_start = (start_dt + timedelta(days=delta_cols)).strftime("%Y-%m-%d")
                new_end = (end_dt + timedelta(days=delta_cols)).strftime("%Y-%m-%d")

                self.drag_bar_schedule.start_date = new_start
                self.drag_bar_schedule.end_date = new_end
                
                self.agenda_service.update_schedule(self.drag_bar_schedule)
                event_bus.emit("entity_updated")
            except Exception as ex:
                messagebox.showerror("Erro", f"Erro ao atualizar agendamento: {str(ex)}")

        self.drag_bar_item = None
        self.drag_bar_schedule = None

    def prompt_capacity_setting(self, date_str: str, current_cap: float):
        # Input dialog for capacity
        dialog = ctk.CTkInputDialog(text=f"Definir Capacidade para {date_str} (Atual: {current_cap}h):", title="Capacidade")
        val = dialog.get_input()
        if val is not None:
            try:
                hours = float(val.strip())
                self.agenda_service.set_user_capacity(date_str, hours)
                self.refresh()
            except ValueError:
                messagebox.showwarning("Aviso", "Digite um valor numérico válido.")

    def refresh(self, trigger="init"):
        from utils.instrumentation import PerfContext, count_widgets_recursive, log_perf_data
        import time
        import traceback
        
        stack = traceback.extract_stack()[:-1]
        caller = stack[-1] if stack else None
        # print(f"\n[REFRESH] AgendaView.refresh | Trigger: {trigger}")
        for s in stack[-4:]:
            fn = s.filename.replace('\\', '/').split('/')[-1]
            print(f"  -> {fn}:{s.lineno} in {s.name}")
            
        start_time = time.time()
        widgets_before = count_widgets_recursive(self.left_canvas) + count_widgets_recursive(self.right_canvas)
        
        with PerfContext("Processar calendário", module="Agenda", category="Processamento"):
            self.render_filters()

        with PerfContext("Buscar tarefas", module="Agenda", category="Banco"):
            self.render_backlog()

        with PerfContext("Buscar eventos e Renderizar", module="Agenda", category="Renderização"):
            self.render_timeline()

        duration = time.time() - start_time
        widgets_after = count_widgets_recursive(self.left_canvas) + count_widgets_recursive(self.right_canvas)
        # Assuming typical elements count as loaded: we don't know exactly here, we can pass 0 or guess.
        log_perf_data("AgendaView", "refresh", duration, widgets_before, widgets_after, loaded_items=0, trigger=trigger)


    def on_entity_updated(self):
        if not self.winfo_ismapped():
            self._is_dirty = True
            return
        self._is_dirty = False
        if self.winfo_viewable():
            if hasattr(self, '_refresh_after_id'):
                try: self.after_cancel(self._refresh_after_id)
                except Exception: pass
            self._refresh_after_id = self.after(60, self.refresh)
        else:
            self.dirty = True

    def on_map(self, event=None):
        if event and event.widget != self and str(event.widget) != f"{self}.!ctkcanvas":
            return
        # Adia 1ms: view é exibida imediatamente, dados carregam logo após
        self.after(1, self._deferred_map_refresh)

    def _deferred_map_refresh(self):
        if getattr(self, 'dirty', False):
            self.dirty = False
        self.refresh()
        self.scroll_to_today()
