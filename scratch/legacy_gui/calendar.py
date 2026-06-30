import customtkinter as ctk
import tkinter.messagebox as messagebox
import copy
from datetime import datetime
from collections import defaultdict
from services.event_service import EventService
from services.project_service import ProjectService
from models.entities import Event

class CalendarView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.event_service = EventService()
        self.project_service = ProjectService()
        self.current_event = None
        self.show_archived = False
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1, minsize=320)
        self.grid_columnconfigure(1, weight=2)

        # ==========================================
        # LEFT PANEL: Timeline List
        # ==========================================
        self.left_panel = ctk.CTkFrame(self, corner_radius=0)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.left_panel.grid_rowconfigure(2, weight=1)
        self.left_panel.grid_columnconfigure(0, weight=1)

        self.list_header = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.list_header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.btn_new = ctk.CTkButton(self.list_header, text="+ Novo Evento", fg_color="#2B8C52", hover_color="#1E663B", command=self.create_new_event)
        self.btn_new.pack(fill="x", pady=(0, 5))

        self.ent_search = ctk.CTkEntry(self.list_header, placeholder_text="Buscar eventos...")
        self.ent_search.pack(fill="x", pady=2)
        self.ent_search.bind("<KeyRelease>", lambda e: self.load_events_list())

        self.events_scroll = ctk.CTkScrollableFrame(self.left_panel, fg_color="transparent")
        self.events_scroll.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)

        self.list_footer = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.list_footer.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        
        self.btn_toggle_archived = ctk.CTkButton(self.list_footer, text="Ver Arquivados", fg_color="transparent", border_width=1, text_color=("black", "white"), command=self.toggle_archived)
        self.btn_toggle_archived.pack(fill="x")

        # ==========================================
        # RIGHT PANEL: Event Form
        # ==========================================
        self.right_panel = ctk.CTkFrame(self, corner_radius=0)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.right_panel.grid_rowconfigure(1, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

        # Toolbar
        self.toolbar = ctk.CTkFrame(self.right_panel, height=50, fg_color="transparent")
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        
        self.lbl_status = ctk.CTkLabel(self.toolbar, text="Nenhum evento selecionado", font=ctk.CTkFont(size=12, slant="italic"), text_color="gray")
        self.lbl_status.pack(side="left", padx=5)

        self.btn_delete = ctk.CTkButton(self.toolbar, text="🗑️ Excluir", width=80, fg_color="#C23616", hover_color="#8C250E", command=self.delete_event)
        self.btn_delete.pack(side="right", padx=5)

        self.btn_archive = ctk.CTkButton(self.toolbar, text="📦 Arquivar", width=85, fg_color="#B8860B", hover_color="#8B6508", command=self.archive_event)
        self.btn_archive.pack(side="right", padx=5)

        # Form Area
        self.form_frame = ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent")
        self.form_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.form_frame.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(self.form_frame, text="Título do Evento:").pack(anchor="w", pady=(10, 2))
        self.ent_title = ctk.CTkEntry(self.form_frame)
        self.ent_title.pack(fill="x", pady=(0, 10))

        # Row: Start & End datetime
        self.row_datetime = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.row_datetime.pack(fill="x", pady=5)
        self.row_datetime.grid_columnconfigure((0, 1), weight=1)

        self.start_frame = ctk.CTkFrame(self.row_datetime, fg_color="transparent")
        self.start_frame.grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkLabel(self.start_frame, text="Início (AAAA-MM-DD HH:MM):").pack(anchor="w")
        self.ent_start = ctk.CTkEntry(self.start_frame, placeholder_text="2026-06-10 09:00")
        self.ent_start.pack(fill="x")

        self.end_frame = ctk.CTkFrame(self.row_datetime, fg_color="transparent")
        self.end_frame.grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkLabel(self.end_frame, text="Término (AAAA-MM-DD HH:MM):").pack(anchor="w")
        self.ent_end = ctk.CTkEntry(self.end_frame, placeholder_text="2026-06-10 10:00")
        self.ent_end.pack(fill="x")

        # Row: Location & Project
        self.row_loc = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.row_loc.pack(fill="x", pady=5)
        self.row_loc.grid_columnconfigure((0, 1), weight=1)

        self.loc_frame = ctk.CTkFrame(self.row_loc, fg_color="transparent")
        self.loc_frame.grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkLabel(self.loc_frame, text="Localização:").pack(anchor="w")
        self.ent_location = ctk.CTkEntry(self.loc_frame, placeholder_text="Sala de reuniões, online...")
        self.ent_location.pack(fill="x")

        self.proj_frame = ctk.CTkFrame(self.row_loc, fg_color="transparent")
        self.proj_frame.grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkLabel(self.proj_frame, text="Projeto Vinculado:").pack(anchor="w")
        self.opt_proj = ctk.CTkOptionMenu(self.proj_frame, values=["Nenhum"])
        self.opt_proj.pack(fill="x")

        # Description
        ctk.CTkLabel(self.form_frame, text="Descrição:").pack(anchor="w", pady=(10, 2))
        self.ent_description = ctk.CTkEntry(self.form_frame)
        self.ent_description.pack(fill="x", pady=(0, 10))

        # Notes (meeting notes)
        ctk.CTkLabel(self.form_frame, text="Notas de Reunião:").pack(anchor="w", pady=(5, 2))
        self.txt_notes = ctk.CTkTextbox(self.form_frame, height=180, font=ctk.CTkFont(size=14))
        self.txt_notes.pack(fill="x", pady=(0, 15))

        self.btn_save = ctk.CTkButton(self.form_frame, text="Salvar Alterações", fg_color="#2B8C52", hover_color="#1E663B", command=self.save_changes)
        self.btn_save.pack(pady=10)

        self.set_form_state(False)
        self.load_events_list()

    def set_form_state(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.ent_title.configure(state=state)
        self.ent_start.configure(state=state)
        self.ent_end.configure(state=state)
        self.ent_location.configure(state=state)
        self.opt_proj.configure(state=state)
        self.ent_description.configure(state=state)
        self.txt_notes.configure(state=state)
        self.btn_save.configure(state=state)
        
        if not enabled:
            self.ent_title.delete(0, "end")
            self.ent_start.delete(0, "end")
            self.ent_end.delete(0, "end")
            self.ent_location.delete(0, "end")
            self.ent_description.delete(0, "end")
            self.txt_notes.delete("0.0", "end")
            self.lbl_status.configure(text="Nenhum evento selecionado")
            self.btn_archive.pack_forget()
            self.btn_delete.pack_forget()
        else:
            self.btn_archive.pack(side="right", padx=5)
            self.btn_delete.pack(side="right", padx=5)

    def load_projects_menu(self):
        self.projects = self.project_service.get_all_active()
        self.proj_dict = {"Nenhum": None}
        for p in self.projects:
            self.proj_dict[f"{p.id} - {p.name}"] = p.id
        self.opt_proj.configure(values=list(self.proj_dict.keys()))

    def _format_date_label(self, dt_str):
        """Format a datetime string for display in group headers."""
        if not dt_str:
            return "Sem data"
        try:
            dt = datetime.strptime(dt_str[:10], "%Y-%m-%d")
            today = datetime.now().date()
            delta = (dt.date() - today).days
            
            weekdays = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
            day_name = weekdays[dt.weekday()]
            formatted = dt.strftime(f"%d/%m/%Y ({day_name})")
            
            if delta == 0:
                return f"📅 Hoje - {formatted}"
            elif delta == 1:
                return f"📅 Amanhã - {formatted}"
            elif delta < 0:
                return f"⏰ Passado - {formatted}"
            else:
                return f"📅 {formatted}"
        except (ValueError, TypeError):
            return str(dt_str)[:10]

    def _format_time(self, dt_str):
        """Extract time portion from a datetime string."""
        if not dt_str or len(dt_str) < 16:
            return ""
        return dt_str[11:16]

    def load_events_list(self):
        for w in self.events_scroll.winfo_children():
            w.destroy()

        search_query = self.ent_search.get().lower().strip()
        all_events = self.event_service.list_archived() if self.show_archived else self.event_service.list_active()

        if search_query:
            all_events = [e for e in all_events if 
                          search_query in e.title.lower() or
                          (e.description and search_query in e.description.lower()) or
                          (e.location and search_query in e.location.lower())]

        # Sort chronologically by start_datetime
        def sort_key(ev):
            if ev.start_datetime:
                return str(ev.start_datetime)
            return "9999-12-31"
        
        all_events.sort(key=sort_key)

        if not all_events:
            ctk.CTkLabel(self.events_scroll, text="Nenhum evento encontrado.", text_color="gray").pack(pady=20)
            return

        # Group by date
        grouped = defaultdict(list)
        for ev in all_events:
            date_key = str(ev.start_datetime)[:10] if ev.start_datetime else "Sem data"
            grouped[date_key].append(ev)

        for date_key, events in grouped.items():
            # Date group header
            header_label = self._format_date_label(date_key)
            lbl_header = ctk.CTkLabel(self.events_scroll, text=header_label, font=ctk.CTkFont(size=13, weight="bold"), text_color=("#1a5c2e", "#6fd08c"))
            lbl_header.pack(anchor="w", padx=10, pady=(12, 4))

            for ev in events:
                is_current = self.current_event and self.current_event.id == ev.id
                bg_color = "#3a3a3a" if is_current else ("#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#e0e0e0")
                
                card = ctk.CTkFrame(self.events_scroll, fg_color=bg_color, cursor="hand2")
                card.pack(fill="x", pady=3, padx=5)
                card.bind("<Button-1>", lambda e, ev=ev: self.select_event(ev))

                time_str = self._format_time(str(ev.start_datetime)) if ev.start_datetime else ""
                display_title = f"🕐 {time_str}  {ev.title}" if time_str else ev.title
                
                lbl_title = ctk.CTkLabel(card, text=display_title, font=ctk.CTkFont(weight="bold" if is_current else "normal"), anchor="w", wraplength=280)
                lbl_title.pack(fill="x", padx=10, pady=(6, 2))
                lbl_title.bind("<Button-1>", lambda e, ev=ev: self.select_event(ev))

                if ev.location:
                    lbl_loc = ctk.CTkLabel(card, text=f"📍 {ev.location}", text_color="gray", font=ctk.CTkFont(size=11), anchor="w")
                    lbl_loc.pack(fill="x", padx=10, pady=(0, 6))
                    lbl_loc.bind("<Button-1>", lambda e, ev=ev: self.select_event(ev))

    def select_event(self, event: Event):
        self.current_event = event
        self.load_projects_menu()
        self.set_form_state(True)

        self.ent_title.delete(0, "end")
        self.ent_title.insert(0, event.title)

        self.ent_start.delete(0, "end")
        if event.start_datetime:
            self.ent_start.insert(0, str(event.start_datetime))

        self.ent_end.delete(0, "end")
        if event.end_datetime:
            self.ent_end.insert(0, str(event.end_datetime))

        self.ent_location.delete(0, "end")
        if event.location:
            self.ent_location.insert(0, event.location)

        self.ent_description.delete(0, "end")
        if event.description:
            self.ent_description.insert(0, event.description)

        self.txt_notes.delete("0.0", "end")
        if event.notes:
            self.txt_notes.insert("0.0", event.notes)

        # Project combo
        self.opt_proj.set("Nenhum")
        if event.project_id:
            for k, v in self.proj_dict.items():
                if v == event.project_id:
                    self.opt_proj.set(k)
                    break

        # Toolbar state
        self.lbl_status.configure(text=f"Evento ID: {event.id}")
        arch_text = "Restaurar" if event.is_archived else "📦 Arquivar"
        self.btn_archive.configure(text=arch_text)

        self.load_events_list()

    def create_new_event(self):
        now = datetime.now()
        start_str = now.strftime("%Y-%m-%d %H:00")
        event = self.event_service.create(title="Novo Evento", start=start_str)
        self.select_event(event)

    def save_changes(self):
        if not self.current_event:
            return
        
        title = self.ent_title.get().strip()
        if not title:
            messagebox.showwarning("Aviso", "O título do evento é obrigatório.")
            return

        original = copy.deepcopy(self.current_event)

        self.current_event.title = title
        self.current_event.start_datetime = self.ent_start.get().strip() or None
        self.current_event.end_datetime = self.ent_end.get().strip() or None
        self.current_event.location = self.ent_location.get().strip() or None
        self.current_event.description = self.ent_description.get().strip() or None
        self.current_event.notes = self.txt_notes.get("0.0", "end-1c").strip() or None

        proj_key = self.opt_proj.get()
        self.current_event.project_id = self.proj_dict.get(proj_key)

        self.event_service.update(self.current_event, original)
        self.lbl_status.configure(text="Alterações salvas!")
        self.load_events_list()

    def archive_event(self):
        if not self.current_event:
            return
        if self.current_event.is_archived:
            self.event_service.restore(self.current_event.id)
            self.current_event.is_archived = False
            self.select_event(self.current_event)
        else:
            self.event_service.archive(self.current_event.id)
            self.current_event = None
            self.set_form_state(False)
            self.load_events_list()

    def delete_event(self):
        if not self.current_event:
            return
        if messagebox.askyesno("Excluir", "Enviar este evento para a lixeira?"):
            self.event_service.delete(self.current_event.id)
            self.current_event = None
            self.set_form_state(False)
            self.load_events_list()

    def toggle_archived(self):
        self.show_archived = not self.show_archived
        self.btn_toggle_archived.configure(text="Ocultar Arquivados" if self.show_archived else "Ver Arquivados")
        self.load_events_list()
