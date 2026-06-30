import customtkinter as ctk
import tkinter as tk
import tkinter.messagebox as messagebox
import copy
from services.project_service import ProjectService
from models.entities import Project
from core.event_bus import event_bus
from gui.components.date_picker import DatePickerFrame

class ProjectDialog(ctk.CTkToplevel):
    def __init__(self, master, project: Project = None, on_save=None):
        super().__init__(master)
        self.title("Novo Projeto" if not project else "Editar Projeto")
        self.geometry("450x460")
        self.project = project
        self.on_save = on_save
        
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self.transient(master)
        self.grab_set()

        # Scrollable content frame to allow handling more fields or smaller resolutions
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)

        self.lbl_name = ctk.CTkLabel(self.scroll, text="Nome do Projeto:")
        self.lbl_name.pack(pady=(10, 5), padx=20, anchor="w")
        self.ent_name = ctk.CTkEntry(self.scroll, width=380)
        self.ent_name.pack(pady=5, padx=20)
        
        self.lbl_obj = ctk.CTkLabel(self.scroll, text="Objetivo:")
        self.lbl_obj.pack(pady=(10, 5), padx=20, anchor="w")
        self.ent_obj = ctk.CTkEntry(self.scroll, width=380)
        self.ent_obj.pack(pady=5, padx=20)
        
        self.lbl_prio = ctk.CTkLabel(self.scroll, text="Prioridade:")
        self.lbl_prio.pack(pady=(10, 5), padx=20, anchor="w")
        self.opt_prio = ctk.CTkOptionMenu(self.scroll, values=["Baixa", "Média", "Alta", "Crítica"], width=380)
        self.opt_prio.pack(pady=5, padx=20)
        
        self.lbl_due = ctk.CTkLabel(self.scroll, text="Prazo:")
        self.lbl_due.pack(pady=(10, 5), padx=20, anchor="w")
        self.ent_due = DatePickerFrame(self.scroll)
        self.ent_due.pack(pady=5, padx=20, fill="x")
        
        if self.project:
            self.ent_name.insert(0, self.project.name)
            if self.project.objective:
                self.ent_obj.insert(0, self.project.objective)
            self.opt_prio.set(self.project.priority)
            if self.project.due_date:
                self.ent_due.set_date(self.project.due_date)
        else:
            self.opt_prio.set("Média")

        self.btn_save = ctk.CTkButton(self, text="Salvar", command=self.save)
        self.btn_save.pack(pady=(5, 15))

    def save(self):
        name = self.ent_name.get().strip()
        if not name:
            messagebox.showwarning("Aviso", "O nome do projeto é obrigatório.")
            return
            
        obj = self.ent_obj.get().strip()
        prio = self.opt_prio.get()
        due_date = self.ent_due.get_date()
        alert_date = None
        alert_msg = None
        
        if self.project:
            self.project.name = name
            self.project.objective = obj
            self.project.priority = prio
            self.project.due_date = due_date
            self.project.alert_date = alert_date
            self.project.alert_message = alert_msg
            if self.on_save:
                self.on_save(self.project, is_new=False)
        else:
            new_proj = Project(name=name, objective=obj, priority=prio, due_date=due_date, alert_date=alert_date, alert_message=alert_msg)
            if self.on_save:
                self.on_save(new_proj, is_new=True)
                
        self.destroy()

class ProjectsView(ctk.CTkFrame):
    def __init__(self, master, open_360_callback=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.open_360_callback = open_360_callback
        self.service = ProjectService()
        self.show_archived = False
        self.dirty = False
        self._cached_projects_count = 0
        self.visible_projects_limit = 15
        event_bus.subscribe("snapshot_updated", lambda _: self.on_entity_updated())
        self.bind("<Map>", lambda e: self.on_map(e))
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(30, 20), padx=30)
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        self.header = ctk.CTkLabel(self.header_frame, text="Projetos", font=ctk.CTkFont(size=28, weight="bold"))
        self.header.grid(row=0, column=0, sticky="w")
        
        self.btn_toggle_archived = ctk.CTkButton(self.header_frame, text="Arquivados", fg_color="transparent", border_width=1, text_color=("black", "white"), command=self.toggle_archived)
        self.btn_toggle_archived.grid(row=0, column=1, sticky="e", padx=10)

        self.btn_new = ctk.CTkButton(self.header_frame, text="+ Novo Projeto", command=self.open_new_dialog)
        self.btn_new.grid(row=0, column=2, sticky="e")
        
        # List
        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        
        self.load_projects()
        self._check_scroll_loop()

    def toggle_archived(self):
        self.show_archived = not self.show_archived
        self.visible_projects_limit = 15
        if self.show_archived:
            self.btn_toggle_archived.configure(fg_color="#1f538d", hover_color="#14375e")
        else:
            self.btn_toggle_archived.configure(fg_color="transparent")
        self.load_projects()

    def open_new_dialog(self):
        ProjectDialog(self.winfo_toplevel(), on_save=self.handle_save)

    def open_edit_dialog(self, project: Project):
        orig_proj = copy.deepcopy(project)
        
        def save_edit(edited_proj, is_new):
            self.service.update_project(edited_proj, orig_proj)
            event_bus.emit("entity_updated")
            self.load_projects()
            
        ProjectDialog(self.winfo_toplevel(), project=project, on_save=save_edit)

    def handle_save(self, project: Project, is_new: bool):
        if is_new:
            self.service.create_project(name=project.name, objective=project.objective, priority=project.priority, due_date=project.due_date, alert_date=project.alert_date, alert_message=project.alert_message)
        event_bus.emit("entity_updated")
        self.load_projects()

    def delete_project(self, project_id: int):
        if messagebox.askyesno("Excluir", "Deseja enviar este projeto para a lixeira? Ele não aparecerá mais nesta lista."):
            self.service.soft_delete_project(project_id)
            event_bus.emit("entity_updated")
            self.load_projects()

    def archive_project(self, project_id: int):
        if messagebox.askyesno("Arquivar", "Deseja arquivar este projeto? Ele ficará oculto da lista principal."):
            self.service.archive_project(project_id)
            event_bus.emit("entity_updated")
            self.load_projects()

    def restore_project(self, project_id: int):
        if messagebox.askyesno("Restaurar", "Deseja restaurar este projeto para a lista ativa?"):
            self.service.restore_project(project_id)
            event_bus.emit("entity_updated")
            self.load_projects()

    def load_projects(self, trigger="init"):
        import time
        from utils.instrumentation import log_perf_data, count_widgets_recursive
        start_time = time.time()
        widgets_before = count_widgets_recursive(self.scrollable_frame)

        projects = self.service.get_all_archived() if self.show_archived else self.service.get_all_active()

        # Limpa tudo (layout mudou — recriar é mais seguro que reusar)
        for w in self.scrollable_frame.winfo_children():
            w.destroy()

        if not projects:
            text = "Nenhum projeto arquivado." if self.show_archived else "Nenhum projeto ativo. Clique em + Novo Projeto."
            ctk.CTkLabel(self.scrollable_frame, text=text,
                         text_color="gray", font=ctk.CTkFont(size=13, slant="italic")).pack(pady=40)
            duration = time.time() - start_time
            widgets_after = count_widgets_recursive(self.scrollable_frame)
            log_perf_data("ProjectsView", "load_projects", duration, widgets_before, widgets_after, loaded_items=0, trigger=trigger)
            return

        dark = ctk.get_appearance_mode() == "Dark"
        card_bg  = "#1e1e2e" if dark else "#f8f9fc"
        card_hov = "#2a2a3e" if dark else "#eef0f8"

        status_colors = {
            "Concluído":    "#15803D", "Em Andamento": "#0369A1",
            "Pausado":      "#B45309", "Aguardando":   "#6D28D9",
            "Bloqueado":    "#B91C1C",
        }
        prio_colors = {
            "Máxima": "#E11D48", "Alta": "#F97316",
            "Média":  "#EAB308", "Baixa": "#22C55E",
        }

        def fmt_date(d):
            if not d:
                return "Sem prazo"
            try:
                parts = str(d).split(" ")[0].split("-")
                if len(parts) == 3:
                    return f"{parts[2]}/{parts[1]}/{parts[0]}"
            except Exception:
                pass
            return str(d)

        visible_projects = projects[:self.visible_projects_limit]
        self._cached_projects_count = len(projects)

        for p in visible_projects:
            stripe_color = status_colors.get(p.status, "#374151")

            # ── Card principal ──────────────────────────────────────────
            card = ctk.CTkFrame(self.scrollable_frame, fg_color=card_bg, corner_radius=8)
            card.pack(fill="x", pady=4, padx=10)
            card.is_project_card = True
            card.grid_columnconfigure(1, weight=1)

            # Faixa lateral colorida (4px)
            ctk.CTkFrame(card, width=4, height=10, corner_radius=2,
                         fg_color=stripe_color).grid(
                row=0, column=0, rowspan=2, sticky="ns", padx=(4, 0), pady=6)

            # Título (row 0)
            title = f"{p.name}  (Arquivado)" if p.is_archived else p.name
            ctk.CTkLabel(
                card, text=title,
                font=ctk.CTkFont(size=16, weight="bold"), anchor="w",
                text_color=("black" if not dark else "white")
            ).grid(row=0, column=1, sticky="w", padx=(10, 8), pady=(10, 2))

            # Meta row: status badge + prioridade + prazo + objetivo (row 1)
            meta_f = ctk.CTkFrame(card, fg_color="transparent")
            meta_f.grid(row=1, column=1, sticky="w", padx=(10, 8), pady=(0, 10))

            # Badge de status
            ctk.CTkLabel(
                meta_f, text=p.status or "Aguardando",
                font=ctk.CTkFont(size=10),
                fg_color=stripe_color, text_color="white",
                corner_radius=6, padx=5, pady=1
            ).pack(side="left", padx=(0, 6))

            # Prioridade
            p_color = prio_colors.get(p.priority, "gray")
            ctk.CTkLabel(
                meta_f, text=f"⚡ {p.priority or '—'}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=p_color
            ).pack(side="left", padx=(0, 6))

            # Prazo
            ctk.CTkLabel(
                meta_f, text=f"📅 {fmt_date(p.due_date)}",
                font=ctk.CTkFont(size=11), text_color="gray"
            ).pack(side="left", padx=(0, 6))

            # Objetivo (truncado)
            if p.objective:
                obj = p.objective[:60] + "…" if len(p.objective) > 60 else p.objective
                ctk.CTkLabel(
                    meta_f, text=f"• {obj}",
                    font=ctk.CTkFont(size=11), text_color="gray"
                ).pack(side="left")

            # Botões (column 2, rows 0-1)
            btn_f = ctk.CTkFrame(card, fg_color="transparent")
            btn_f.grid(row=0, column=2, rowspan=2, sticky="e", padx=(0, 10), pady=8)

            if p.is_archived:
                ctk.CTkButton(
                    btn_f, text="Restaurar", width=82, height=24,
                    fg_color="#2B8C52", hover_color="#1E663B",
                    command=lambda pid=p.id: self.restore_project(pid)
                ).pack(pady=2)
            else:
                ctk.CTkButton(
                    btn_f, text="📦 Arquivar", width=82, height=24,
                    fg_color="#2b5c8c", hover_color="#1e4066",
                    command=lambda pid=p.id: self.archive_project(pid)
                ).pack(pady=2)

            ctk.CTkButton(
                btn_f, text="🗑 Excluir", width=82, height=24,
                fg_color="#8c2b2b", hover_color="#661e1e",
                command=lambda pid=p.id: self.delete_project(pid)
            ).pack(pady=2)

            # Hover sutil + click bindings — recursivo em todos os filhos não-botão
            def _bind_recursive(widget, proj=p):
                if isinstance(widget, ctk.CTkButton):
                    return
                widget.bind("<Enter>",    lambda e, c=card: c.configure(fg_color=card_hov))
                widget.bind("<Leave>",    lambda e, c=card: c.configure(fg_color=card_bg))
                widget.bind("<Button-1>", lambda e, proj=proj: self.open_360(proj))
                widget.bind("<Button-3>", lambda e, proj=proj: self._show_project_menu(e, proj))
                for child in widget.winfo_children():
                    _bind_recursive(child, proj)

            _bind_recursive(card, p)

        duration = time.time() - start_time
        widgets_after = count_widgets_recursive(self.scrollable_frame)
        log_perf_data("ProjectsView", "load_projects", duration, widgets_before, widgets_after,
                      loaded_items=len(visible_projects), trigger=trigger)

    def open_360(self, project):
        if self.open_360_callback:
            self.open_360_callback(project)

    def _show_project_menu(self, event, project):
        if getattr(project, 'is_archived', False):
            return
        from gui.components.context_menu import ContextMenu
        menu = ContextMenu(self)
        menu.add_command("✏️  Editar", command=lambda: self.open_edit_dialog(project))
        menu.add_separator()
        menu.add_command("🔔  Alertas...", command=lambda: self._open_alerts_manager(project))
        menu.add_separator()
        menu.add_header("Gerenciar")
        menu.add_command("📦  Arquivar", command=lambda: self.archive_project(project.id))
        menu.add_command("🗑️  Excluir",  command=lambda: self.delete_project(project.id), danger=True)
        menu.tk_popup(event.x_root, event.y_root)

    def _open_alerts_manager(self, project):
        from gui.views.alert_manager import AlertManagerDialog
        AlertManagerDialog.get_instance(self.winfo_toplevel(), "project", project.id, project.name)

    def _update_card_text_colors(self, card, bg_color):
        # Mantido por compatibilidade — novo estilo usa fundo neutro, não precisa de ajuste de cor
        pass

    def on_entity_updated(self):
        if not self.winfo_ismapped():
            self._is_dirty = True
            return
        self._is_dirty = False
        if not self.winfo_viewable():
            self.dirty = True
        else:
            if hasattr(self, '_refresh_after_id'):
                try: self.after_cancel(self._refresh_after_id)
                except Exception: pass
            self._refresh_after_id = self.after(60, lambda: self.load_projects(trigger="entity_updated"))

    def on_map(self, event=None):
        if event and event.widget != self and str(event.widget) != f"{self}.!ctkcanvas":
            return
        if self.dirty:
            self.dirty = False
            self.after(1, lambda: self.load_projects(trigger="<Map>"))

    def _check_scroll_loop(self):
        if not self.winfo_exists():
            return
        try:
            if self.winfo_viewable():
                scrollbar = getattr(self.scrollable_frame, "_scrollbar", None)
                if scrollbar:
                    low, high = scrollbar.get()
                    if high > 0.85:
                        self._load_more_if_needed()
        except Exception:
            pass
        self.after(500, self._check_scroll_loop)

    def _load_more_if_needed(self):
        """Usa contagem cacheada do último render — evita query ao banco no loop de 500ms."""
        if self._cached_projects_count > self.visible_projects_limit:
            self.visible_projects_limit += 15
            self.load_projects(trigger="lazy_load")
