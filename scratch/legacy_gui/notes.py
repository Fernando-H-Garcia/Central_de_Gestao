import customtkinter as ctk
import tkinter.messagebox as messagebox
from services.note_service import NoteService
from services.project_service import ProjectService
from models.entities import Note
from core.event_bus import event_bus

class NotesView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.note_service = NoteService()
        self.project_service = ProjectService()
        self.current_note = None
        self.show_archived = False
        self.save_timer = None
        self.dirty = False
        event_bus.subscribe("snapshot_updated", lambda _: self.on_entity_updated())
        self.bind("<Map>", lambda e: self.on_map(e))
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1, minsize=250) # Left panel (List)
        self.grid_columnconfigure(1, weight=3)             # Right panel (Editor)

        # ==========================================
        # LEFT PANEL: Search, List, Add
        # ==========================================
        self.left_panel = ctk.CTkFrame(self, corner_radius=0)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.left_panel.grid_rowconfigure(2, weight=1)
        self.left_panel.grid_columnconfigure(0, weight=1)

        # Header of List
        self.list_header = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.list_header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.btn_new_note = ctk.CTkButton(self.list_header, text="+ Nova Nota", fg_color="#2B8C52", hover_color="#1E663B", command=self.create_new_note)
        self.btn_new_note.pack(fill="x", pady=(0, 5))

        self.ent_search = ctk.CTkEntry(self.list_header, placeholder_text="Filtrar notas...")
        self.ent_search.pack(fill="x")
        self.ent_search.bind("<KeyRelease>", lambda e: self.load_notes_list())

        # Scrollable Notes List
        self.notes_scroll = ctk.CTkScrollableFrame(self.left_panel, fg_color="transparent")
        self.notes_scroll.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)

        # Footer of List
        self.list_footer = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.list_footer.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        
        self.btn_toggle_archived = ctk.CTkButton(self.list_footer, text="Ver Arquivadas", fg_color="transparent", border_width=1, text_color=("black", "white"), command=self.toggle_archived)
        self.btn_toggle_archived.pack(fill="x")

        # ==========================================
        # RIGHT PANEL: Toolbar, Textbox Editor
        # ==========================================
        self.right_panel = ctk.CTkFrame(self, corner_radius=0)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.right_panel.grid_rowconfigure(1, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

        # Toolbar
        self.toolbar = ctk.CTkFrame(self.right_panel, height=50, fg_color="transparent")
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        
        self.lbl_status = ctk.CTkLabel(self.toolbar, text="Nenhuma nota selecionada", font=ctk.CTkFont(size=12, slant="italic"), text_color="gray")
        self.lbl_status.pack(side="left", padx=5)

        self.btn_delete = ctk.CTkButton(self.toolbar, text="🗑️ Excluir", width=80, fg_color="#C23616", hover_color="#8C250E", command=self.delete_note)
        self.btn_delete.pack(side="right", padx=5)

        self.btn_archive = ctk.CTkButton(self.toolbar, text="📦 Arquivar", width=85, fg_color="#B8860B", hover_color="#8B6508", command=self.archive_note)
        self.btn_archive.pack(side="right", padx=5)

        self.btn_favorite = ctk.CTkButton(self.toolbar, text="⭐ Favoritar", width=90, fg_color="transparent", border_width=1, text_color=("black", "white"), command=self.toggle_favorite)
        self.btn_favorite.pack(side="right", padx=5)

        self.project_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.project_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 5))
        self.lbl_proj = ctk.CTkLabel(self.project_frame, text="Projeto Vinculado:")
        self.lbl_proj.pack(side="left", padx=(0, 10))
        self.opt_proj = ctk.CTkOptionMenu(self.project_frame, values=["Nenhum"], command=self.on_project_change)
        self.opt_proj.pack(side="left", fill="x", expand=True)

        # Editor Textbox
        self.txt_editor = ctk.CTkTextbox(self.right_panel, font=ctk.CTkFont(size=15), activate_scrollbars=True)
        self.txt_editor.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.txt_editor.bind("<KeyRelease>", self.on_key_release)
        
        # Disable editor initially
        self.set_editor_state(False)
        self.load_notes_list()

    def set_editor_state(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.txt_editor.configure(state=state)
        self.opt_proj.configure(state=state)
        if not enabled:
            self.txt_editor.delete("0.0", "end")
            self.lbl_status.configure(text="Nenhuma nota selecionada")
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

    def on_project_change(self, value):
        if not self.current_note:
            return
        proj_id = self.proj_dict.get(value)
        if self.current_note.project_id != proj_id:
            self.current_note.project_id = proj_id
            self.note_service.update(self.current_note)
            event_bus.emit("entity_updated")
            self.lbl_status.configure(text="Salvo")

    def load_notes_list(self, trigger="init"):
        import time
        from utils.instrumentation import log_perf_data, count_widgets_recursive
        start_time = time.time()
        widgets_before = count_widgets_recursive(self.notes_scroll)
        for w in self.notes_scroll.winfo_children():
            w.destroy()

        search_query = self.ent_search.get().lower().strip()
        all_notes = self.note_service.list(include_archived=self.show_archived)

        # Filter query
        if search_query:
            all_notes = [n for n in all_notes if search_query in n.content.lower()]

        # Sort: favorites first, then newest
        all_notes = sorted(all_notes, key=lambda n: (not n.is_favorite, n.id), reverse=True)

        if not all_notes:
            ctk.CTkLabel(self.notes_scroll, text="Nenhuma nota encontrada.", text_color="gray").pack(pady=20)
            return

        for note in all_notes:
            is_current = self.current_note and self.current_note.id == note.id
            bg_color = "#3a3a3a" if is_current else ("#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#e0e0e0")
            
            card = ctk.CTkFrame(self.notes_scroll, fg_color=bg_color, cursor="hand2")
            card.pack(fill="x", pady=4, padx=5)
            card.bind("<Button-1>", lambda e, n=note: self.select_note(n))

            # Preview content (first 40 chars)
            preview = note.content.strip().split("\n")[0][:40] if note.content.strip() else "(Nota vazia)"
            lbl_title = ctk.CTkLabel(card, text=preview, font=ctk.CTkFont(weight="bold" if is_current else "normal"), anchor="w")
            lbl_title.pack(side="left", fill="x", expand=True, padx=10, pady=8)
            lbl_title.bind("<Button-1>", lambda e, n=note: self.select_note(n))

            # Favorite star icon
            if note.is_favorite:
                lbl_fav = ctk.CTkLabel(card, text="⭐", text_color="gold")
                lbl_fav.pack(side="right", padx=5)
                lbl_fav.bind("<Button-1>", lambda e, n=note: self.select_note(n))

        duration = time.time() - start_time
        widgets_after = count_widgets_recursive(self.notes_scroll)
        log_perf_data("NotesView", "load_notes_list", duration, widgets_before, widgets_after, loaded_items=len(all_notes), trigger=trigger)

    def select_note(self, note: Note):
        # Save current note before switching
        if self.save_timer:
            self.after_cancel(self.save_timer)
            self.auto_save()

        self.current_note = note
        self.load_projects_menu()
        self.set_editor_state(True)
        self.txt_editor.delete("0.0", "end")
        self.txt_editor.insert("0.0", note.content)
        
        self.opt_proj.set("Nenhum")
        if note.project_id:
            for k, v in self.proj_dict.items():
                if v == note.project_id:
                    self.opt_proj.set(k)
                    break
        
        self.lbl_status.configure(text="Salvo")
        
        # Update buttons
        fav_text = "★ Desfavoritar" if note.is_favorite else "⭐ Favoritar"
        self.btn_favorite.configure(text=fav_text)
        
        arch_text = "Restaurar" if note.is_archived else "📦 Arquivar"
        self.btn_archive.configure(text=arch_text)
        
        self.load_notes_list()

    def create_new_note(self):
        new_note = Note(content="")
        created = self.note_service.create(new_note)
        event_bus.emit("entity_updated")
        self.select_note(created)

    def on_key_release(self, event=None):
        if not self.current_note:
            return
        self.lbl_status.configure(text="Digitando...")
        if self.save_timer:
            self.after_cancel(self.save_timer)
        self.save_timer = self.after(800, self.auto_save)

    def auto_save(self):
        self.save_timer = None
        if not self.current_note:
            return
        
        new_content = self.txt_editor.get("0.0", "end-1c")
        if self.current_note.content != new_content:
            self.current_note.content = new_content
            self.note_service.update(self.current_note)
            self.lbl_status.configure(text="Salvo")
            event_bus.emit("entity_updated")
            self.load_notes_list()

    def toggle_favorite(self):
        if not self.current_note:
            return
        self.current_note.is_favorite = not self.current_note.is_favorite
        self.note_service.update(self.current_note)
        event_bus.emit("entity_updated")
        self.select_note(self.current_note)

    def archive_note(self):
        if not self.current_note:
            return
        if self.current_note.is_archived:
            self.note_service.restore(self.current_note.id)
            self.current_note.is_archived = False
            self.select_note(self.current_note)
        else:
            self.note_service.archive(self.current_note.id)
            self.current_note = None
            self.set_editor_state(False)
            event_bus.emit("entity_updated")
            self.load_notes_list()

    def delete_note(self):
        if not self.current_note:
            return
        if messagebox.askyesno("Excluir", "Enviar esta nota para a lixeira?"):
            self.note_service.soft_delete(self.current_note.id)
            self.current_note = None
            self.set_editor_state(False)
            event_bus.emit("entity_updated")
            self.load_notes_list()

    def toggle_archived(self):
        self.show_archived = not self.show_archived
        self.btn_toggle_archived.configure(text="Ocultar Arquivadas" if self.show_archived else "Ver Arquivadas")
        self.load_notes_list()

    def on_entity_updated(self):
        if not self.winfo_ismapped():
            self._is_dirty = True
            return
        self._is_dirty = False
        if not self.winfo_viewable():
            self.dirty = True
        else:
            self.load_notes_list(trigger="entity_updated")

    def on_map(self, event=None):
        if event and event.widget != self and str(event.widget) != f"{self}.!ctkcanvas":
            return
        if self.dirty:
            self.dirty = False
            self.load_notes_list(trigger="<Map>")
