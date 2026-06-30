import customtkinter as ctk
import tkinter.messagebox as messagebox
import copy
from services.idea_service import IdeaService
from services.project_service import ProjectService
from models.entities import Idea
from core.event_bus import event_bus
from gui.components.date_picker import DatePickerFrame

class IdeasView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.idea_service = IdeaService()
        self.project_service = ProjectService()
        
        self.current_idea = None
        self.show_archived = False
        self.dirty = False
        event_bus.subscribe("snapshot_updated", lambda _: self.on_entity_updated())
        self.bind("<Map>", lambda e: self.on_map(e))
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1, minsize=320) # Left Panel (List)
        self.grid_columnconfigure(1, weight=2)             # Right Panel (Form Editor)

        # ==========================================
        # LEFT PANEL: Filters, List, Add
        # ==========================================
        self.left_panel = ctk.CTkFrame(self, corner_radius=0)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.left_panel.grid_rowconfigure(2, weight=1)
        self.left_panel.grid_columnconfigure(0, weight=1)

        # Header with Add Button and Search
        self.list_header = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.list_header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.btn_new = ctk.CTkButton(self.list_header, text="+ Nova Ideia", fg_color="#2B8C52", hover_color="#1E663B", command=self.create_new_idea)
        self.btn_new.pack(fill="x", pady=(0, 5))

        self.ent_search = ctk.CTkEntry(self.list_header, placeholder_text="Buscar ideias...")
        self.ent_search.pack(fill="x", pady=2)
        self.ent_search.bind("<KeyRelease>", lambda e: self.load_ideas_list())

        # Scrollable Ideas List
        self.ideas_scroll = ctk.CTkScrollableFrame(self.left_panel, fg_color="transparent")
        self.ideas_scroll.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)

        # Footer
        self.list_footer = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.list_footer.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        
        self.btn_toggle_archived = ctk.CTkButton(self.list_footer, text="Ver Arquivadas", fg_color="transparent", border_width=1, text_color=("black", "white"), command=self.toggle_archived)
        self.btn_toggle_archived.pack(fill="x")

        # ==========================================
        # RIGHT PANEL: Toolbar & Detailed Form
        # ==========================================
        self.right_panel = ctk.CTkFrame(self, corner_radius=0)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.right_panel.grid_rowconfigure(1, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

        # Toolbar
        self.toolbar = ctk.CTkFrame(self.right_panel, height=50, fg_color="transparent")
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        
        self.lbl_status = ctk.CTkLabel(self.toolbar, text="Nenhuma ideia selecionada", font=ctk.CTkFont(size=12, slant="italic"), text_color="gray")
        self.lbl_status.pack(side="left", padx=5)

        self.btn_delete = ctk.CTkButton(self.toolbar, text="🗑️ Excluir", width=80, fg_color="#C23616", hover_color="#8C250E", command=self.delete_idea)
        self.btn_delete.pack(side="right", padx=5)

        self.btn_archive = ctk.CTkButton(self.toolbar, text="📦 Arquivar", width=85, fg_color="#B8860B", hover_color="#8B6508", command=self.archive_idea)
        self.btn_archive.pack(side="right", padx=5)

        self.btn_favorite = ctk.CTkButton(self.toolbar, text="⭐ Favoritar", width=90, fg_color="transparent", border_width=1, text_color=("black", "white"), command=self.toggle_favorite)
        self.btn_favorite.pack(side="right", padx=5)

        # Form Scrollable Area
        self.form_frame = ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent")
        self.form_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.form_frame.grid_columnconfigure(0, weight=1)

        # Form Widgets
        self.lbl_title = ctk.CTkLabel(self.form_frame, text="Título da Ideia:")
        self.lbl_title.pack(anchor="w", pady=(10, 2))
        self.ent_title = ctk.CTkEntry(self.form_frame)
        self.ent_title.pack(fill="x", pady=(0, 10))

        self.lbl_category = ctk.CTkLabel(self.form_frame, text="Categoria:")
        self.lbl_category.pack(anchor="w", pady=(5, 2))
        self.ent_category = ctk.CTkEntry(self.form_frame)
        self.ent_category.pack(fill="x", pady=(0, 10))

        self.lbl_proj = ctk.CTkLabel(self.form_frame, text="Projeto Vinculado:")
        self.lbl_proj.pack(anchor="w", pady=(5, 2))
        self.opt_proj = ctk.CTkOptionMenu(self.form_frame, values=["Nenhum"])
        self.opt_proj.pack(fill="x", pady=(0, 10))

        # Horizontal layouts for dropdowns
        self.row1 = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.row1.pack(fill="x", pady=5)
        self.row1.grid_columnconfigure((0, 1, 2), weight=1)

        # Priority
        self.prio_frame = ctk.CTkFrame(self.row1, fg_color="transparent")
        self.prio_frame.grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkLabel(self.prio_frame, text="Prioridade:").pack(anchor="w")
        self.opt_priority = ctk.CTkOptionMenu(self.prio_frame, values=["Baixa", "Média", "Alta", "Crítica"])
        self.opt_priority.pack(fill="x")

        # Interest Level
        self.interest_frame = ctk.CTkFrame(self.row1, fg_color="transparent")
        self.interest_frame.grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkLabel(self.interest_frame, text="Interesse (1-5):").pack(anchor="w")
        self.opt_interest = ctk.CTkOptionMenu(self.interest_frame, values=["1", "2", "3", "4", "5"])
        self.opt_interest.pack(fill="x")

        # Status
        self.status_frame = ctk.CTkFrame(self.row1, fg_color="transparent")
        self.status_frame.grid(row=0, column=2, padx=5, sticky="ew")
        ctk.CTkLabel(self.status_frame, text="Status:").pack(anchor="w")
        self.opt_status = ctk.CTkOptionMenu(self.status_frame, values=["Nova", "Em Análise", "Aprovada", "Descartada"])
        self.opt_status.pack(fill="x")

        self.lbl_review = ctk.CTkLabel(self.form_frame, text="Próxima Revisão:")
        self.lbl_review.pack(anchor="w", pady=(10, 2))
        self.dp_review = DatePickerFrame(self.form_frame)
        self.dp_review.pack(fill="x", pady=(0, 10))

        self.lbl_desc = ctk.CTkLabel(self.form_frame, text="Descrição / Detalhes:")
        self.lbl_desc.pack(anchor="w", pady=(10, 2))
        self.txt_desc = ctk.CTkTextbox(self.form_frame, height=120)
        self.txt_desc.pack(fill="x", pady=(0, 15))

        self.btn_save = ctk.CTkButton(self.form_frame, text="Salvar Alterações", fg_color="#2B8C52", hover_color="#1E663B", command=self.save_changes)
        self.btn_save.pack(pady=10)

        # Autocomplete dropdowns
        from utils.dropdown_autocomplete import DropdownAutocompleteHelper, get_unique_categories
        self.category_autocomplete = DropdownAutocompleteHelper(self.ent_category, get_unique_categories)

        self.set_form_state(False)
        self.load_ideas_list()

    def set_form_state(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.ent_title.configure(state=state)
        self.ent_category.configure(state=state)
        self.opt_proj.configure(state=state)
        self.opt_priority.configure(state=state)
        self.opt_interest.configure(state=state)
        self.opt_status.configure(state=state)
        self.dp_review.configure(state=state)
        self.txt_desc.configure(state=state)
        self.btn_save.configure(state=state)
        
        if not enabled:
            self.ent_title.delete(0, "end")
            self.ent_category.delete(0, "end")
            self.dp_review.set_date(None)
            self.txt_desc.delete("0.0", "end")
            self.lbl_status.configure(text="Nenhuma ideia selecionada")
            self.btn_favorite.pack_forget()
            self.btn_archive.pack_forget()
            self.btn_delete.pack_forget()
        else:
            self.btn_favorite.pack(side="right", padx=5)
            self.btn_archive.pack(side="right", padx=5)
            self.btn_delete.pack(side="right", padx=5)

    def load_projects_menu(self):
        self.projects = self.project_service.get_all_active()
        self.proj_dict = {"Nenhum": None}
        for p in self.projects:
            self.proj_dict[f"{p.id} - {p.name}"] = p.id
        self.opt_proj.configure(values=list(self.proj_dict.keys()))

    def load_ideas_list(self, trigger="init"):
        import time
        from utils.instrumentation import log_perf_data, count_widgets_recursive
        start_time = time.time()
        widgets_before = count_widgets_recursive(self.ideas_scroll)
        # Clear scroll list
        for w in self.ideas_scroll.winfo_children():
            w.destroy()

        search_query = self.ent_search.get().lower().strip()
        all_ideas = self.idea_service.get_all_archived() if self.show_archived else self.idea_service.get_all_active()

        # Filtering
        if search_query:
            all_ideas = [i for i in all_ideas if search_query in i.title.lower() or (i.description and search_query in i.description.lower()) or (i.category and search_query in i.category.lower())]

        # Sorting: favorites first, then newest
        all_ideas = sorted(all_ideas, key=lambda i: (not i.is_favorite, i.id), reverse=True)

        if not all_ideas:
            ctk.CTkLabel(self.ideas_scroll, text="Nenhuma ideia encontrada.", text_color="gray").pack(pady=20)
            return

        for idea in all_ideas:
            is_current = self.current_idea and self.current_idea.id == idea.id
            bg_color = "#3a3a3a" if is_current else ("#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#e0e0e0")
            
            card = ctk.CTkFrame(self.ideas_scroll, fg_color=bg_color, cursor="hand2")
            card.pack(fill="x", pady=4, padx=5)
            card.bind("<Button-1>", lambda e, i=idea: self.select_idea(i))

            # Header inside card
            lbl_title = ctk.CTkLabel(card, text=idea.title, font=ctk.CTkFont(weight="bold" if is_current else "normal"), anchor="w", wraplength=280)
            lbl_title.pack(fill="x", padx=10, pady=(8, 2))
            lbl_title.bind("<Button-1>", lambda e, i=idea: self.select_idea(i))

            # Meta line: Priority & stars
            meta_frame = ctk.CTkFrame(card, fg_color="transparent")
            meta_frame.pack(fill="x", padx=10, pady=(0, 8))
            meta_frame.bind("<Button-1>", lambda e, i=idea: self.select_idea(i))

            prio_colors = {"Baixa": "gray", "Média": "#2B8C52", "Alta": "#B8860B", "Crítica": "#C23616"}
            prio_color = prio_colors.get(idea.priority, "gray")
            
            lbl_prio = ctk.CTkLabel(meta_frame, text=idea.priority.upper(), text_color=prio_color, font=ctk.CTkFont(size=10, weight="bold"))
            lbl_prio.pack(side="left")
            lbl_prio.bind("<Button-1>", lambda e, i=idea: self.select_idea(i))

            stars = "⭐" * idea.interest_level
            lbl_stars = ctk.CTkLabel(meta_frame, text=f"  {stars}", font=ctk.CTkFont(size=10))
            lbl_stars.pack(side="left")
            lbl_stars.bind("<Button-1>", lambda e, i=idea: self.select_idea(i))

            if idea.is_favorite:
                lbl_fav = ctk.CTkLabel(meta_frame, text="★", text_color="gold", font=ctk.CTkFont(size=14))
                lbl_fav.pack(side="right")
                lbl_fav.bind("<Button-1>", lambda e, i=idea: self.select_idea(i))

        duration = time.time() - start_time
        widgets_after = count_widgets_recursive(self.ideas_scroll)
        log_perf_data("IdeasView", "load_ideas_list", duration, widgets_before, widgets_after, loaded_items=len(all_ideas), trigger=trigger)

    def select_idea(self, idea: Idea):
        self.current_idea = idea
        self.load_projects_menu()
        self.set_form_state(True)

        self.ent_title.delete(0, "end")
        self.ent_title.insert(0, idea.title)

        self.ent_category.delete(0, "end")
        if idea.category:
            self.ent_category.insert(0, idea.category)

        self.opt_priority.set(idea.priority)
        self.opt_interest.set(str(idea.interest_level))
        self.opt_status.set(idea.status)

        self.dp_review.set_date(idea.next_review_date if idea.next_review_date else None)

        self.txt_desc.delete("0.0", "end")
        if idea.description:
            self.txt_desc.insert("0.0", idea.description)

        # Linked project selection
        self.opt_proj.set("Nenhum")
        if idea.project_id:
            for k, v in self.proj_dict.items():
                if v == idea.project_id:
                    self.opt_proj.set(k)
                    break

        # Toolbar
        self.lbl_status.configure(text=f"Ideia ID: {idea.id}")
        fav_text = "★ Desfavoritar" if idea.is_favorite else "⭐ Favoritar"
        self.btn_favorite.configure(text=fav_text)
        
        arch_text = "Restaurar" if idea.is_archived else "📦 Arquivar"
        self.btn_archive.configure(text=arch_text)

        self.load_ideas_list()

    def create_new_idea(self):
        new_idea = self.idea_service.create_idea(title="Nova Ideia", status="Nova", priority="Média", interest_level=3)
        self.select_idea(new_idea)

    def save_changes(self):
        if not self.current_idea:
            return
        
        title = self.ent_title.get().strip()
        if not title:
            messagebox.showwarning("Aviso", "O título da ideia é obrigatório.")
            return

        original = copy.deepcopy(self.current_idea)
        
        self.current_idea.title = title
        self.current_idea.category = self.ent_category.get().strip() or None
        self.current_idea.priority = self.opt_priority.get()
        self.current_idea.interest_level = int(self.opt_interest.get())
        self.current_idea.status = self.opt_status.get()
        self.current_idea.description = self.txt_desc.get("0.0", "end-1c").strip() or None
        self.current_idea.next_review_date = self.dp_review.get_date()
        
        proj_key = self.opt_proj.get()
        self.current_idea.project_id = self.proj_dict.get(proj_key)

        self.idea_service.update_idea(self.current_idea, original)
        self.lbl_status.configure(text="Alterações salvas!")
        event_bus.emit("entity_updated")
        self.load_ideas_list()

    def toggle_favorite(self):
        if not self.current_idea:
            return
        original = copy.deepcopy(self.current_idea)
        self.current_idea.is_favorite = not self.current_idea.is_favorite
        self.idea_service.update_idea(self.current_idea, original)
        event_bus.emit("entity_updated")
        self.select_idea(self.current_idea)

    def archive_idea(self):
        if not self.current_idea:
            return
        if self.current_idea.is_archived:
            self.idea_service.restore_idea(self.current_idea.id)
            self.current_idea.is_archived = False
            self.select_idea(self.current_idea)
        else:
            self.idea_service.archive_idea(self.current_idea.id)
            self.current_idea = None
            self.set_form_state(False)
            event_bus.emit("entity_updated")
            self.load_ideas_list()

    def delete_idea(self):
        if not self.current_idea:
            return
        if messagebox.askyesno("Excluir", "Deseja enviar esta ideia para a lixeira?"):
            self.idea_service.soft_delete_idea(self.current_idea.id)
            self.current_idea = None
            self.set_form_state(False)
            event_bus.emit("entity_updated")
            self.load_ideas_list()

    def toggle_archived(self):
        self.show_archived = not self.show_archived
        self.btn_toggle_archived.configure(text="Ocultar Arquivadas" if self.show_archived else "Ver Arquivadas")
        self.load_ideas_list()

    def on_entity_updated(self):
        if not self.winfo_ismapped():
            self._is_dirty = True
            return
        self._is_dirty = False
        if not self.winfo_viewable():
            self.dirty = True
        else:
            self.load_ideas_list(trigger="entity_updated")

    def on_map(self, event=None):
        if event and event.widget != self and str(event.widget) != f"{self}.!ctkcanvas":
            return
        if self.dirty:
            self.dirty = False
            self.load_ideas_list(trigger="<Map>")
