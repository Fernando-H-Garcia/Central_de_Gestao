import customtkinter as ctk
import tkinter as tk
import tkinter.messagebox as messagebox
import copy
from services.task_service import TaskService
from services.project_service import ProjectService
from models.entities import Task
from core.event_bus import event_bus
from gui.components.date_picker import DatePickerFrame

class TaskDialog(ctk.CTkToplevel):
    def __init__(self, master, task: Task = None, on_save=None):
        super().__init__(master)
        self.title("Nova Tarefa" if not task else "Editar Tarefa")
        self.geometry("500x620")
        self.task = task
        self.on_save = on_save
        self.project_service = ProjectService()
        self.projects = self.project_service.get_all_active()
        
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self.transient(master)
        self.grab_set()

        # Scrollable content frame to allow scrolling on lower resolution screens
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)

        self.lbl_title = ctk.CTkLabel(self.scroll, text="Título:")
        self.lbl_title.pack(pady=(15, 5), padx=20, anchor="w")
        self.ent_title = ctk.CTkEntry(self.scroll, width=420)
        self.ent_title.pack(pady=5, padx=20)
        
        self.lbl_context = ctk.CTkLabel(self.scroll, text="Descrição / Contexto:")
        self.lbl_context.pack(pady=(10, 5), padx=20, anchor="w")
        self.ent_context = ctk.CTkTextbox(self.scroll, width=420, height=80)
        self.ent_context.pack(pady=5, padx=20)
        
        self.lbl_status = ctk.CTkLabel(self.scroll, text="Status:")
        self.lbl_status.pack(pady=(10, 5), padx=20, anchor="w")
        self.opt_status = ctk.CTkOptionMenu(self.scroll, values=["Backlog", "A Fazer", "Em Andamento", "Pausado", "Aguardando", "Bloqueado", "Concluído"], width=420)
        self.opt_status.pack(pady=5, padx=20)

        self.lbl_energy = ctk.CTkLabel(self.scroll, text="Prioridade / Energia:")
        self.lbl_energy.pack(pady=(10, 5), padx=20, anchor="w")
        self.opt_energy = ctk.CTkOptionMenu(self.scroll, values=["Baixa", "Média", "Alta", "Máxima"], width=420)
        self.opt_energy.pack(pady=5, padx=20)
        
        self.lbl_proj = ctk.CTkLabel(self.scroll, text="Projeto Vinculado:")
        self.lbl_proj.pack(pady=(10, 5), padx=20, anchor="w")
        
        self.proj_dict = {"Nenhum": None}
        for p in self.projects:
            self.proj_dict[f"{p.id} - {p.name}"] = p.id
        self.opt_proj = ctk.CTkOptionMenu(self.scroll, values=list(self.proj_dict.keys()), width=420)
        self.opt_proj.pack(pady=5, padx=20)
        
        self.lbl_due = ctk.CTkLabel(self.scroll, text="Prazo:")
        self.lbl_due.pack(pady=(10, 5), padx=20, anchor="w")
        self.dp_due = DatePickerFrame(self.scroll)
        self.dp_due.pack(pady=5, padx=20, fill="x")
        
        self.lbl_estimated = ctk.CTkLabel(self.scroll, text="Esforço Estimado (Horas):")
        self.lbl_estimated.pack(pady=(10, 5), padx=20, anchor="w")
        self.ent_estimated_hours = ctk.CTkEntry(self.scroll, width=420)
        self.ent_estimated_hours.pack(pady=5, padx=20)
        self.ent_estimated_hours.insert(0, "0.0")

        self.chk_milestone = ctk.CTkCheckBox(self.scroll, text="É um Marco (Milestone - Sem duração/esforço)")
        self.chk_milestone.pack(pady=10, padx=20, anchor="w")

        if self.task:
            self.ent_title.insert(0, self.task.title)
            if self.task.context:
                self.ent_context.insert("0.0", self.task.context)
            self.opt_status.set(self.task.status)
            self.opt_energy.set(self.task.energy_level)
            
            if self.task.project_id:
                for k, v in self.proj_dict.items():
                    if v == self.task.project_id:
                        self.opt_proj.set(k)
                        break
                        
            if self.task.due_date:
                self.dp_due.set_date(self.task.due_date)

            self.ent_estimated_hours.delete(0, "end")
            self.ent_estimated_hours.insert(0, str(getattr(self.task, "estimated_hours", 0.0)))
            if getattr(self.task, "is_milestone", False):
                self.chk_milestone.select()
        else:
            self.opt_status.set("A Fazer")
            self.opt_energy.set("Média")
 
        self.btn_save = ctk.CTkButton(self, text="Salvar Tarefa", command=self.save)
        self.btn_save.pack(pady=(5, 15))

    def save(self):
        title = self.ent_title.get().strip()
        if not title:
            messagebox.showwarning("Aviso", "O título da tarefa é obrigatório.")
            return
            
        context = self.ent_context.get("0.0", "end").strip()
        status = self.opt_status.get()
        energy = self.opt_energy.get()
        proj_key = self.opt_proj.get()
        proj_id = self.proj_dict.get(proj_key)
        due_date = self.dp_due.get_date()
        alert_date = None
        alert_msg = None
        
        try:
            est_hours = float(self.ent_estimated_hours.get().strip() or 0.0)
        except ValueError:
            est_hours = 0.0

        is_ms = bool(self.chk_milestone.get())
        
        if self.task:
            self.task.title = title
            self.task.context = context
            self.task.status = status
            self.task.energy_level = energy
            self.task.project_id = proj_id
            self.task.due_date = due_date
            self.task.alert_date = alert_date
            self.task.alert_message = alert_msg
            self.task.estimated_hours = est_hours
            self.task.is_milestone = is_ms
            if self.on_save:
                self.on_save(self.task, is_new=False)
        else:
            new_task = Task(title=title, context=context, status=status, energy_level=energy, project_id=proj_id, due_date=due_date, alert_date=alert_date, alert_message=alert_msg, estimated_hours=est_hours, is_milestone=is_ms)
            if self.on_save:
                self.on_save(new_task, is_new=True)
                
        self.destroy()

class TasksView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.service = TaskService()
        self.project_service = ProjectService()
        self.show_archived = False
        self.columns = ["Backlog", "A Fazer", "Em Andamento", "Pausado", "Aguardando", "Bloqueado", "Concluído"]
        self.dirty = False
        event_bus.subscribe("snapshot_updated", lambda _: self.on_entity_updated())
        self.bind("<Map>", lambda e: self.on_map(e))
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(20, 10), padx=20)
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        self.header = ctk.CTkLabel(self.header_frame, text="Tarefas (Kanban)", font=ctk.CTkFont(size=28, weight="bold"))
        self.header.grid(row=0, column=0, sticky="w")
        
        self.btn_toggle_archived = ctk.CTkButton(self.header_frame, text="Arquivados", fg_color="transparent", border_width=1, text_color=("black", "white"), command=self.toggle_archived)
        self.btn_toggle_archived.grid(row=0, column=1, sticky="e", padx=10)

        self.btn_new = ctk.CTkButton(self.header_frame, text="+ Nova Tarefa", command=self.open_new_dialog)
        self.btn_new.grid(row=0, column=2, sticky="e")
        
        self.kanban_area = ctk.CTkScrollableFrame(self, fg_color="transparent", orientation="horizontal")
        self.kanban_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        self.col_frames = {}
        for idx, col_name in enumerate(self.columns):
            frame = ctk.CTkFrame(self.kanban_area, width=280)
            frame.grid(row=0, column=idx, sticky="nsew", padx=10, pady=5)
            frame.grid_propagate(False)
            
            lbl = ctk.CTkLabel(frame, text=col_name, font=ctk.CTkFont(weight="bold"))
            lbl.pack(pady=10)
            
            list_frame = ctk.CTkScrollableFrame(frame, fg_color="transparent")
            list_frame.pack(fill="both", expand=True, padx=5, pady=5)
            
            self.col_frames[col_name] = list_frame
            
        self.load_tasks()

    def toggle_archived(self):
        self.show_archived = not self.show_archived
        if self.show_archived:
            self.btn_toggle_archived.configure(fg_color="#1f538d", hover_color="#14375e")
        else:
            self.btn_toggle_archived.configure(fg_color="transparent")
        self.load_tasks()

    def open_new_dialog(self):
        TaskDialog(self.winfo_toplevel(), on_save=self.handle_save)

    def open_edit_dialog(self, task: Task):
        orig = copy.deepcopy(task)
        def save_edit(edited, is_new):
            self.service.update_task(edited, orig)
            event_bus.emit("entity_updated")
            self.load_tasks()
        TaskDialog(self.winfo_toplevel(), task=task, on_save=save_edit)

    def handle_save(self, task: Task, is_new: bool):
        if is_new:
            self.service.create_task(
                title=task.title, 
                context=task.context, 
                energy_level=task.energy_level, 
                status=task.status, 
                project_id=task.project_id, 
                due_date=task.due_date, 
                alert_date=task.alert_date, 
                alert_message=task.alert_message,
                estimated_hours=task.estimated_hours,
                is_milestone=task.is_milestone
            )
        event_bus.emit("entity_updated")
        self.load_tasks()

    def move_status(self, task: Task, direction: int):
        try:
            idx = self.columns.index(task.status)
            new_idx = idx + direction
            if 0 <= new_idx < len(self.columns):
                self.service.change_status(task, self.columns[new_idx])
                event_bus.emit("entity_updated")
                self.load_tasks()
        except ValueError:
            pass

    def move_to_status(self, task: Task, new_status: str):
        self.service.change_status(task, new_status)
        event_bus.emit("entity_updated")
        self.load_tasks()

    def archive_task(self, task_id: int):
        if messagebox.askyesno("Arquivar", "Arquivar esta tarefa?"):
            self.service.archive_task(task_id)
            event_bus.emit("entity_updated")
            self.load_tasks()

    def delete_task(self, task_id: int):
        if messagebox.askyesno("Excluir", "Enviar para a lixeira?"):
            self.service.soft_delete_task(task_id)
            event_bus.emit("entity_updated")
            self.load_tasks()

    def restore_task(self, task_id: int):
        if messagebox.askyesno("Restaurar", "Restaurar tarefa?"):
            self.service.restore_task(task_id)
            event_bus.emit("entity_updated")
            self.load_tasks()

    def _bind_all_children(self, widget, event, callback):
        """Recursively bind an event to a widget and ALL its children."""
        if isinstance(widget, ctk.CTkButton):
            return
        widget.bind(event, callback)
        for child in widget.winfo_children():
            self._bind_all_children(child, event, callback)

    def load_tasks(self, trigger="init"):
        import time
        from utils.instrumentation import log_perf_data, count_widgets_recursive
        start_time = time.time()
        widgets_before = sum(count_widgets_recursive(list_frame) for list_frame in self.col_frames.values())
        for list_frame in self.col_frames.values():
            for w in list_frame.winfo_children():
                w.destroy()
                
        tasks = self.service.get_all_archived() if self.show_archived else self.service.get_all_active()
        projects = {p.id: p.name for p in self.project_service.get_all_active()}
        
        for t in tasks:
            target_frame = self.col_frames.get(t.status, self.col_frames["Backlog"])
            
            # Determine background color based on theme
            bg_color = "#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#e0e0e0"
            card = ctk.CTkFrame(target_frame, fg_color=bg_color, cursor="hand2")
            card.pack(fill="x", pady=5)

            # Hover effect
            def _on_enter(e, c=card):
                c.configure(fg_color="#3a3a3a")
                self._update_card_text_colors(c, "#3a3a3a")
            def _on_leave(e, c=card, bg=bg_color):
                c.configure(fg_color=bg)
                self._update_card_text_colors(c, bg)

            ctk.CTkLabel(card, text=t.title, font=ctk.CTkFont(weight="bold"), wraplength=230, justify="left").pack(anchor="w", padx=10, pady=(10, 2))

            if t.project_id and t.project_id in projects:
                ctk.CTkLabel(card, text=f"📂 {projects[t.project_id]}", text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10)

            # Priority color mapping
            prio_colors = {
                "Máxima": "#E11D48",
                "Alta": "#F97316",
                "Média": "#EAB308",
                "Baixa": "#22C55E"
            }
            p_color = prio_colors.get(t.energy_level, "gray")
            prio_frame = ctk.CTkFrame(card, fg_color="transparent")
            prio_frame.pack(anchor="w", padx=10)
            ctk.CTkLabel(prio_frame, text="Prioridade: ", text_color="gray", font=ctk.CTkFont(size=11)).pack(side="left")
            lbl_p = ctk.CTkLabel(prio_frame, text=t.energy_level, text_color=p_color, font=ctk.CTkFont(size=11, weight="bold"))
            lbl_p.is_priority_colored = True
            lbl_p.pack(side="left")

            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.pack(fill="x", padx=5, pady=10)

            # Right‑click context menu
            from gui.components.context_menu import ContextMenu
            menu = ContextMenu(card)
            menu.add_command("✏️  Editar", command=lambda tk=t: self.open_edit_dialog(tk))
            menu.add_separator()
            menu.add_header("Alterar Status")
            menu.add_command("📥  Backlog",
                             command=lambda tk=t: self.move_to_status(tk, "Backlog"),
                             enabled=(t.status != "Backlog"))
            menu.add_command("📌  A Fazer",
                             command=lambda tk=t: self.move_to_status(tk, "A Fazer"),
                             enabled=(t.status != "A Fazer"))
            menu.add_command("▶️  Em Andamento",
                             command=lambda tk=t: self.move_to_status(tk, "Em Andamento"),
                             enabled=(t.status != "Em Andamento"))
            menu.add_command("⏸️  Pausado",
                             command=lambda tk=t: self.move_to_status(tk, "Pausado"),
                             enabled=(t.status != "Pausado"))
            menu.add_command("⏳  Aguardando",
                             command=lambda tk=t: self.move_to_status(tk, "Aguardando"),
                             enabled=(t.status != "Aguardando"))
            menu.add_command("🚫  Bloqueado",
                             command=lambda tk=t: self.move_to_status(tk, "Bloqueado"),
                             enabled=(t.status != "Bloqueado"))
            menu.add_command("✅  Concluir",
                             command=lambda tk=t: self.move_to_status(tk, "Concluído"),
                             enabled=(t.status != "Concluído"))
            menu.add_separator()
            menu.add_header("Gerenciar")
            if self.show_archived:
                menu.add_command("📦  Restaurar", command=lambda tid=t.id: self.restore_task(tid))
            else:
                menu.add_command("📦  Arquivar",  command=lambda tid=t.id: self.archive_task(tid))
            menu.add_command("🗑️  Excluir",   command=lambda tid=t.id: self.delete_task(tid), danger=True)

            # Bind click, context menu e hover recursivamente
            self._bind_all_children(card, "<Button-1>", lambda e, tk=t: self.open_edit_dialog(tk))
            self._bind_all_children(card, "<Button-3>", lambda e, m=menu: m.tk_popup(e.x_root, e.y_root))
            self._bind_all_children(card, "<Enter>", _on_enter)
            self._bind_all_children(card, "<Leave>", _on_leave)

            # Action buttons (still visible for quick actions)
            ctk.CTkButton(actions, text="✏️", width=30, command=lambda tk=t: self.open_edit_dialog(tk)).pack(side="left", padx=2)
            if self.show_archived:
                ctk.CTkButton(actions, text="Restaurar", width=70, fg_color="#2B8C52", hover_color="#1E663B", command=lambda tid=t.id: self.restore_task(tid)).pack(side="left", padx=2)
            else:
                ctk.CTkButton(actions, text="<", width=30, command=lambda tk=t: self.move_status(tk, -1)).pack(side="left", padx=2)
                ctk.CTkButton(actions, text=">", width=30, command=lambda tk=t: self.move_status(tk, 1)).pack(side="left", padx=2)
                ctk.CTkButton(actions, text="📦 Arquivar", width=70, height=20, fg_color="#2b5c8c", hover_color="#1e4066", command=lambda tid=t.id: self.archive_task(tid)).pack(side="left", padx=2)
            ctk.CTkButton(actions, text="🗑 Excluir", width=65, height=20, fg_color="#8c2b2b", hover_color="#661e1e", command=lambda tid=t.id: self.delete_task(tid)).pack(side="right", padx=2)
            
            # Initial text color setup
            self._update_card_text_colors(card, bg_color)
            
        duration = time.time() - start_time
        widgets_after = sum(count_widgets_recursive(list_frame) for list_frame in self.col_frames.values())
        log_perf_data("TasksView", "load_tasks", duration, widgets_before, widgets_after, loaded_items=len(tasks), trigger=trigger)

    def _update_card_text_colors(self, card, bg_color):
        is_dark = True
        hex_color = bg_color.lstrip('#')
        if len(hex_color) == 6:
            try:
                r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
                brightness = (r * 299 + g * 587 + b * 114) / 1000
                is_dark = brightness < 128
            except:
                pass
        
        text_color = "white" if is_dark else "black"
        meta_color = "#aaaaaa" if is_dark else "#555555"
        
        def _update(widget):
            if isinstance(widget, ctk.CTkLabel):
                if getattr(widget, "is_priority_colored", False):
                    return
                font_size = 12
                try:
                    font_size = widget.cget("font").cget("size")
                except:
                    pass
                if font_size <= 11 or widget.cget("text_color") in ("gray", "grey", "#aaaaaa", "#555555"):
                    widget.configure(text_color=meta_color)
                else:
                    widget.configure(text_color=text_color)
            for child in widget.winfo_children():
                if not isinstance(child, ctk.CTkButton):
                    _update(child)
        _update(card)

    def on_entity_updated(self):
        if not self.winfo_ismapped():
            self._is_dirty = True
            return
        self._is_dirty = False
        if not self.winfo_viewable():
            self.dirty = True
        else:
            self.load_tasks(trigger="entity_updated")

    def on_map(self, event=None):
        if event and event.widget != self and str(event.widget) != f"{self}.!ctkcanvas":
            return
        if self.dirty:
            self.dirty = False
            self.load_tasks(trigger="<Map>")
