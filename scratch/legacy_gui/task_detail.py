import tkinter as tk
import tkinter.messagebox as messagebox
import customtkinter as ctk
from services.idea_service import IdeaService
from services.note_service import NoteService
from services.task_service import TaskService
from services.alert_service import AlertService
from gui.dialogs.task_alert_popup import TaskAlertPopup
from models.entities import Task, Idea, Note
from core.event_bus import event_bus
import copy
from datetime import datetime
import json


class QuickActivityDialog(ctk.CTkToplevel):
    def __init__(self, master, initial_text="", on_save=None):
        super().__init__(master)
        self.title("Adicionar Atividade" if not initial_text else "Editar Atividade")
        self.geometry("400x250")
        self.on_save = on_save
        self.resizable(False, False)

        self.update_idletasks()
        x = (self.winfo_screenwidth() - 400) // 2
        y = (self.winfo_screenheight() - 250) // 2
        self.geometry(f"+{x}+{y}")
        self.transient(master)
        self.grab_set()

        ctk.CTkLabel(self, text="Descreva a atividade:", anchor="w").pack(padx=20, pady=(16, 4), anchor="w")
        self.txt = ctk.CTkTextbox(self, height=120)
        self.txt.pack(padx=20, pady=(0, 8), fill="both", expand=True)
        if initial_text:
            self.txt.insert("0.0", initial_text)

        ctk.CTkButton(self, text="💾  Salvar", fg_color="#2B8C52", hover_color="#1E663B", command=self.save).pack(pady=12)

    def save(self):
        val = self.txt.get("0.0", "end-1c").strip()
        if not val:
            return
        if self.on_save:
            self.on_save(val)
        self.destroy()

class TaskDetailView(ctk.CTkFrame):
    def __init__(self, master, task: Task, go_back_callback, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.task = task
        self.go_back_callback = go_back_callback
        self.idea_service = IdeaService()
        self.note_service = NoteService()
        self.task_service = TaskService()
        self.alert_service = AlertService()


        # IMPORTANT: allow this frame to expand properly
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.show_archived_ideas = False
        self.show_archived_notes = False

        # Subscribe to updates
        self.dirty = False
        self._entity_updated_cb = lambda _: self.on_entity_updated()
        event_bus.subscribe("snapshot_updated", self._entity_updated_cb)
        self.bind("<Map>", lambda e: self.on_map(e))

        # Header with back button and title
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(10, 6), padx=20)
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            header, text="← Voltar", width=70, fg_color="transparent",
            border_width=1, text_color=("black", "white"), command=self.go_back_callback,
        ).grid(row=0, column=0, sticky="w", padx=(0, 12))

        ctk.CTkLabel(
            header, text=f"Tarefa – {self.task.title}", font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=1, sticky="w")
        
        ctk.CTkButton(
            header, text="✏️ Editar Tarefa", width=120, command=self.edit_task
        ).grid(row=0, column=2, sticky="e", padx=(12, 0))

        # Content area – two columns
        cols_frame = ctk.CTkFrame(self, fg_color="transparent")
        cols_frame.grid(row=1, column=0, sticky="nsew", padx=4)
        cols_frame.grid_columnconfigure((0, 1), weight=1)
        cols_frame.grid_rowconfigure(0, weight=1)

        # ── LEFT COLUMN ──
        left_col = ctk.CTkFrame(cols_frame, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=5)
        left_col.grid_columnconfigure(0, weight=1)
        left_col.grid_rowconfigure(1, weight=1) # Subtasks will expand

        # Task Details (Top)
        detail_outer = ctk.CTkFrame(left_col, corner_radius=10)
        detail_outer.grid(row=0, column=0, sticky="nsew", pady=5)
        detail_outer.grid_columnconfigure(0, weight=1)
        
        hdr1 = ctk.CTkFrame(detail_outer, fg_color="transparent")
        hdr1.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(hdr1, text="📋 Detalhes da Tarefa", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        
        self._detail_body = ctk.CTkFrame(detail_outer, fg_color="transparent")
        self._detail_body.pack(fill="both", expand=True, padx=6, pady=(0, 10))

        # Activity Log (Bottom, Scrollable)
        log_outer = ctk.CTkFrame(left_col, corner_radius=10)
        log_outer.grid(row=1, column=0, sticky="nsew", pady=5)
        log_outer.grid_columnconfigure(0, weight=1)
        log_outer.grid_rowconfigure(1, weight=1)

        hdr2 = ctk.CTkFrame(log_outer, fg_color="transparent")
        hdr2.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        hdr2.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr2, text="🕒 Registro de Atividades", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(hdr2, text="+ Atividade", width=80, fg_color="#1f538d", command=self.add_activity).grid(row=0, column=1, sticky="e")

        self._log_scroll = ctk.CTkScrollableFrame(log_outer, fg_color="transparent")
        self._log_scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 10))

        # ── RIGHT COLUMN ──
        right_col = ctk.CTkFrame(cols_frame, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=5)
        right_col.grid_columnconfigure(0, weight=1)
        right_col.grid_rowconfigure((0, 1), weight=0)

        # Ideas (Top, Scrollable)
        idea_outer = ctk.CTkFrame(right_col, corner_radius=10)
        idea_outer.grid(row=0, column=0, sticky="ew", pady=5)
        idea_outer.grid_columnconfigure(0, weight=1)
        idea_outer.grid_rowconfigure(1, weight=0)
 
        hdr3 = ctk.CTkFrame(idea_outer, fg_color="transparent")
        hdr3.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        hdr3.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr3, text="💡 Ideias da Tarefa", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w")
        
        btn_frame3 = ctk.CTkFrame(hdr3, fg_color="transparent")
        btn_frame3.grid(row=0, column=1, sticky="e")
        self.btn_toggle_ideas = ctk.CTkButton(btn_frame3, text="Arquivados", width=75, height=26, fg_color="transparent", border_width=1, text_color=("black", "white"), command=self.toggle_archived_ideas)
        self.btn_toggle_ideas.pack(side="left", padx=(0, 5))
        ctk.CTkButton(btn_frame3, text="+ Ideia", width=80, height=26, fg_color="#1f538d", command=self.add_idea).pack(side="left")
 
        self._idea_scroll = ctk.CTkScrollableFrame(idea_outer, fg_color="transparent", height=120)
        self._idea_scroll.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 10))
 
        # Notes (Bottom, Scrollable)
        note_outer = ctk.CTkFrame(right_col, corner_radius=10)
        note_outer.grid(row=1, column=0, sticky="ew", pady=5)
        note_outer.grid_columnconfigure(0, weight=1)
        note_outer.grid_rowconfigure(1, weight=0)

        hdr4 = ctk.CTkFrame(note_outer, fg_color="transparent")
        hdr4.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        hdr4.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr4, text="📝 Notas da Tarefa", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w")

        btn_frame4 = ctk.CTkFrame(hdr4, fg_color="transparent")
        btn_frame4.grid(row=0, column=1, sticky="e")
        self.btn_toggle_notes = ctk.CTkButton(btn_frame4, text="Arquivados", width=75, height=26, fg_color="transparent", border_width=1, text_color=("black", "white"), command=self.toggle_archived_notes)
        self.btn_toggle_notes.pack(side="left", padx=(0, 5))
        ctk.CTkButton(btn_frame4, text="+ Nota", width=80, height=26, fg_color="#1f538d", command=self.add_note).pack(side="left")

        self._note_scroll = ctk.CTkScrollableFrame(note_outer, fg_color="transparent", height=120)
        self._note_scroll.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 10))

        # ── Links and Backlinks Panel ──────
        from gui.components.entity_links_panel import EntityLinksPanel
        self.links_panel = EntityLinksPanel(self, "task", self.task.id)
        self.links_panel.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 5))

        self.refresh()
        self.check_and_show_alerts()

    def check_and_show_alerts(self):
        self.alert_service.mark_overdue_alerts()
        active_alerts = self.alert_service.get_active_alerts_for_task(self.task.id)
        if active_alerts:
            self.after(200, lambda: TaskAlertPopup(self.winfo_toplevel(), self.task.id, self.task.title, active_alerts, self.alert_service))


    def refresh_if_needed(self, trigger="init"):
        if self.winfo_exists():
            self.refresh(trigger=trigger)

    def refresh(self, trigger="init"):
        import time
        from utils.instrumentation import log_perf_data, count_widgets_recursive
        start_time = time.time()
        widgets_before = count_widgets_recursive(self._detail_body) + count_widgets_recursive(self._log_scroll) + count_widgets_recursive(self._idea_scroll) + count_widgets_recursive(self._note_scroll)

        self._render_task()
        self._render_activity_log()
        self._render_ideas()
        self._render_notes()
        self.links_panel.update_entity("task", self.task.id)

        duration = time.time() - start_time
        widgets_after = count_widgets_recursive(self._detail_body) + count_widgets_recursive(self._log_scroll) + count_widgets_recursive(self._idea_scroll) + count_widgets_recursive(self._note_scroll)
        
        # Count the number of actual cards/items created in sub-scrolls
        loaded_count = len(self._detail_body.winfo_children() + self._log_scroll.winfo_children() + self._idea_scroll.winfo_children() + self._note_scroll.winfo_children())
        log_perf_data("TaskDetailView", "refresh", duration, widgets_before, widgets_after, loaded_items=loaded_count, trigger=trigger)

    def _clear(self, frame):
        for w in frame.winfo_children():
            w.destroy()

    def _bind_all_children(self, widget, event, callback):
        """Recursively bind an event to a widget and ALL its children."""
        if isinstance(widget, ctk.CTkButton):
            return
        widget.bind(event, callback)
        for child in widget.winfo_children():
            self._bind_all_children(child, event, callback)

    def _render_task(self):
        self._clear(self._detail_body)
        dark = ctk.get_appearance_mode() == "Dark"

        status_colors = {
            "Backlog": "#374151", "A Fazer": "#1E40AF", "Em Andamento": "#0369A1",
            "Pausado": "#B45309", "Aguardando": "#6D28D9",
            "Bloqueado": "#B91C1C", "Concluído": "#15803D",
        }
        prio_colors = {
            "Máxima": "#E11D48", "Alta": "#F97316", "Média": "#EAB308", "Baixa": "#22C55E"
        }

        stripe_color = status_colors.get(self.task.status, "#374151")
        card_bg  = "#1e1e2e" if dark else "#f8f9fc"

        # Card principal
        card = ctk.CTkFrame(self._detail_body, fg_color=card_bg, corner_radius=8)
        card.pack(fill="x", pady=(0, 4))
        card.grid_columnconfigure(1, weight=1)

        # Faixa lateral colorida (4px)
        ctk.CTkFrame(card, width=4, height=10, corner_radius=2,
                     fg_color=stripe_color).grid(
            row=0, column=0, rowspan=4, sticky="ns", padx=(4, 0), pady=6)

        # Título
        ctk.CTkLabel(
            card, text=self.task.title,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=340, justify="left", anchor="w",
            text_color=("black" if not dark else "white")
        ).grid(row=0, column=1, sticky="w", padx=(10, 8), pady=(10, 2))

        # Contexto (se houver)
        if self.task.context and self.task.context.strip():
            ctk.CTkLabel(
                card, text=self.task.context.strip(),
                font=ctk.CTkFont(size=12),
                wraplength=360, justify="left", anchor="w",
                text_color="gray"
            ).grid(row=1, column=1, sticky="w", padx=(10, 8), pady=(0, 4))

        # Badge de status + prazo + prioridade
        meta_f = ctk.CTkFrame(card, fg_color="transparent")
        meta_f.grid(row=2, column=1, sticky="w", padx=(10, 8), pady=(0, 4))

        ctk.CTkLabel(
            meta_f, text=self.task.status,
            font=ctk.CTkFont(size=10),
            fg_color=stripe_color, text_color="white",
            corner_radius=6, padx=5, pady=1
        ).pack(side="left", padx=(0, 6))

        if self.task.due_date:
            ctk.CTkLabel(
                meta_f, text=f"📅 {self._fmt(self.task.due_date)}",
                font=ctk.CTkFont(size=11), text_color="gray"
            ).pack(side="left", padx=(0, 6))

        if self.task.energy_level:
            p_color = prio_colors.get(self.task.energy_level, "gray")
            ctk.CTkLabel(
                meta_f, text=f"⚡ {self.task.energy_level}",
                font=ctk.CTkFont(size=11, weight="bold"), text_color=p_color
            ).pack(side="left")

        # Origem (ideia)
        from database.repositories.entity_link_repository import EntityLinkRepository
        links = EntityLinkRepository().get_links_by_type('task', self.task.id, 'originated_from')
        if links:
            idea_origin = self.idea_service.get_by_id(links[0]['target_id'])
            if idea_origin:
                origin_f = ctk.CTkFrame(card, fg_color="transparent")
                origin_f.grid(row=3, column=1, sticky="w", padx=(10, 8), pady=(0, 10))

                label_text = (
                    f"💡 Origem: {idea_origin.title} (+{len(links)-1} ideias)"
                    if len(links) > 1
                    else f"💡 Origem: {idea_origin.title}"
                )
                ctk.CTkLabel(
                    origin_f, text=label_text,
                    font=ctk.CTkFont(size=11, slant="italic"), text_color="gray"
                ).pack(side="left")

                def open_origin_idea(idea_item=idea_origin):
                    from gui.views.project_360 import QuickIdeaEditDialog
                    def save_edit(edited):
                        self.idea_service.update_idea(edited, copy.deepcopy(idea_item))
                        event_bus.emit("entity_updated")
                    QuickIdeaEditDialog(self.winfo_toplevel(), idea=idea_item, on_save=save_edit)

                ctk.CTkButton(
                    origin_f, text="Abrir", width=55, height=20,
                    font=ctk.CTkFont(size=10), fg_color="#1f538d",
                    command=open_origin_idea
                ).pack(side="left", padx=(8, 0))
        else:
            # Adiciona pady bottom quando não há origem
            card.grid_rowconfigure(2, pad=6)


    def _render_activity_log(self):
        self._clear(self._log_scroll)
        logs = self.task_service.log_repo.get_by_entity("task", self.task.id)
        
        if not logs:
            ctk.CTkLabel(self._log_scroll, text="Nenhuma atividade registrada.", text_color="gray", font=ctk.CTkFont(size=12, slant="italic")).pack(pady=14)
            return
            
        for log in logs:
            self._activity_card(log, self._log_scroll)

    def _activity_card(self, log, parent):
        dark = ctk.get_appearance_mode() == "Dark"
        bg = "#2b2b2b" if dark else "#e8e8e8"
        card = ctk.CTkFrame(parent, fg_color=bg, corner_radius=8)
        card.pack(fill="x", pady=3)
        
        dt_str = "—"
        if log.created_at:
            try:
                dt_obj = datetime.strptime(str(log.created_at), "%Y-%m-%d %H:%M:%S")
                dt_str = dt_obj.strftime("%d/%m/%Y %H:%M")
            except Exception:
                dt_str = str(log.created_at)[:16]
                
        changes = {}
        if log.changed_fields_json:
            try:
                changes = json.loads(log.changed_fields_json)
            except Exception:
                pass
                
        if log.action == "CREATED":
            title = changes.get("title", {}).get("to", self.task.title)
            prazo = changes.get("due_date", {}).get("to", "")
            prio = changes.get("energy_level", {}).get("to", "Média")
            status = changes.get("status", {}).get("to", "Backlog")
            
            if prazo and prazo != "None":
                try:
                    p = str(prazo).split(" ")[0].split("-")
                    prazo = f"{p[2]}/{p[1]}/{p[0]}"
                except:
                    pass
            else:
                prazo = "Sem prazo"

            text = f"Criação da tarefa '{title}' com prazo {prazo} prioridade {prio} Status {status}"
            
        elif log.action == "UPDATED":
            parts = []
            field_names = {
                "title": "título", "context": "contexto", "energy_level": "prioridade",
                "status": "status", "due_date": "prazo",
                "alert_date": "data do alerta", "alert_message": "mensagem do alerta"
            }
            for k, v in changes.items():
                v_from = v.get("from") or "vazio"
                v_to = v.get("to") or "vazio"
                name = field_names.get(k, k)
                parts.append(f"{name} de '{v_from}' para '{v_to}'")
            if not parts:
                text = f"Alteração da tarefa '{self.task.title}'"
            else:
                text = f"Alteração da tarefa '{self.task.title}' - " + ", ".join(parts)
                
        elif log.action == "MANUAL_NOTE":
            text = changes.get("note", "Nota vazia")
        elif log.action == "DEPENDENCY_ADDED":
            blocker = changes.get("depends_on_title", f"Tarefa #{changes.get('depends_on_task_id', '?')}")
            strength = changes.get("dependency_strength", "obrigatória")
            text = f"Dependência adicionada: aguarda conclusão de '{blocker}' ({strength})"

        elif log.action == "DEPENDENCY_REMOVED":
            blocker = changes.get("depends_on_title", f"Tarefa #{changes.get('depends_on_task_id', '?')}")
            text = f"Dependência removida: '{blocker}' não é mais pré-requisito desta tarefa"

        elif log.action == "STATUS_AUTO_CHANGED":
            from_s = changes.get("status", {}).get("from", "?")
            to_s   = changes.get("status", {}).get("to", "?")
            reason = changes.get("reason", "")
            blockers = changes.get("blocking_tasks", [])
            blocker_str = f" (aguardando: {', '.join(blockers)})" if blockers else ""
            text = f"🤖 Status alterado automaticamente de '{from_s}' para '{to_s}' — {reason}{blocker_str}"

        else:
            text = f"Ação: {log.action}"

            
        full_text = f"{dt_str} - {text}"
        # Texto puro sem data/hora para pré-preencher alertas
        activity_text_only = text
        
        if log.action == "MANUAL_NOTE":
            color = ("black", "white")
            font_weight = "bold"
        else:
            color = ("gray", "#cccccc")
            font_weight = "normal"
            
        if log.action == "MANUAL_NOTE":
            lbl_frame = ctk.CTkFrame(card, fg_color="transparent")
            lbl_frame.pack(fill="x", padx=10, pady=8, expand=True)
            ctk.CTkLabel(lbl_frame, text=full_text, font=ctk.CTkFont(size=12, weight=font_weight), text_color=color, wraplength=520, justify="left", anchor="w").pack(side="left", fill="x", expand=True)
            
            btn_del = ctk.CTkButton(lbl_frame, text="🗑️", width=35, height=25, font=ctk.CTkFont(size=14), fg_color="transparent", text_color="#8c2b2b", hover_color=("#d0d0d0", "#3f3f3f"), command=lambda l=log: self.confirm_delete_activity(l))
            btn_del.pack(side="right", padx=(5, 0))
            
            btn_edit = ctk.CTkButton(lbl_frame, text="✏️", width=35, height=25, font=ctk.CTkFont(size=14), fg_color="transparent", text_color=("black", "white"), hover_color=("#d0d0d0", "#3f3f3f"), command=lambda l=log: self.edit_activity(l))
            btn_edit.pack(side="right", padx=(5, 0))

            btn_del.bind("<Enter>", lambda e, b=btn_del: b.configure(text="🗑️ Excluir"))
            btn_del.bind("<Leave>", lambda e, b=btn_del: b.configure(text="🗑️"))
            btn_edit.bind("<Enter>", lambda e, b=btn_edit: b.configure(text="✏️ Editar"))
            btn_edit.bind("<Leave>", lambda e, b=btn_edit: b.configure(text="✏️"))
            
            # Bind right-click context menu for MANUAL_NOTE (all children)
            self._bind_activity_menu(card, log, activity_text_only, is_manual=True)
            self._bind_activity_menu(lbl_frame, log, activity_text_only, is_manual=True)
        else:
            lbl = ctk.CTkLabel(card, text=full_text, font=ctk.CTkFont(size=12, weight=font_weight), text_color=color, wraplength=620, justify="left", anchor="w")
            lbl.pack(fill="x", padx=10, pady=8)
            # Bind right-click context menu for automatic entries
            self._bind_activity_menu(card, log, activity_text_only, is_manual=False)
            self._bind_activity_menu(lbl, log, activity_text_only, is_manual=False)

    def _bind_activity_menu(self, widget, log, activity_text_only, is_manual: bool):
        """Bind right-click context menu on a widget for an activity card."""
        widget.bind("<Button-3>", lambda e: self._show_activity_menu(e, log, activity_text_only, is_manual))
        for child in widget.winfo_children():
            if not isinstance(child, ctk.CTkButton):
                self._bind_activity_menu(child, log, activity_text_only, is_manual)

    def _show_activity_menu(self, event, log, activity_text_only: str, is_manual: bool):
        """Show right-click context menu for an activity log card."""
        from gui.components.context_menu import ContextMenu
        menu = ContextMenu(self)
        if is_manual:
            menu.add_command("✏️  Editar",   command=lambda: self.edit_activity(log))
            menu.add_separator()
            menu.add_header("Gerenciar")
            menu.add_command("🗑️  Excluir",  command=lambda: self.confirm_delete_activity(log), danger=True)
            menu.add_separator()
        menu.add_header("Ações")
        menu.add_command("🔔  Criar Alerta desta Atividade",
                         command=lambda: self._open_alerts_from_activity(activity_text_only))
        menu.tk_popup(event.x_root, event.y_root)

    def _open_alerts_from_activity(self, activity_text: str):
        """Opens AlertManagerDialog and then immediately opens a new AlertEditDialog pre-filled with the activity text."""
        from gui.views.alert_manager import AlertManagerDialog
        from gui.dialogs.alert_edit_dialog import AlertEditDialog
        from services.alert_service import AlertService
        from models.alert import Alert
        from datetime import datetime

        # Open the AlertManagerDialog for this task
        manager = AlertManagerDialog.get_instance(
            self.winfo_toplevel(),
            entity_type="task",
            entity_id=self.task.id,
            entity_title=self.task.title
        )

        # Get today's date as default in the dialog
        today_str = datetime.now().strftime("%Y-%m-%d")

        # Prepare a dummy Alert with the activity text pre-filled as description
        prefilled_alert = Alert(
            entity_type="task",
            entity_id=self.task.id,
            title="",
            description=activity_text,
            alert_date=today_str
        )

        def on_save(title, description, alert_date, alert_time, priority, status):
            AlertService().create_alert(
                entity_type="task",
                entity_id=self.task.id,
                title=title,
                description=description,
                alert_date=alert_date,
                alert_time=alert_time,
                priority=priority,
                status=status
            )
            event_bus.emit("entity_updated")
            # Refresh the manager if still open
            try:
                manager.refresh()
            except Exception:
                pass

        # Open AlertEditDialog after manager is fully rendered
        manager.after(150, lambda: AlertEditDialog(
            manager,
            entity_type="task",
            entity_id=self.task.id,
            alert=prefilled_alert,
            on_save=on_save
        ))

    def _card_enter(self, card):
        card.configure(fg_color=card.hover_bg)
        self._update_card_text_colors(card, card.hover_bg)

    def _card_leave(self, card):
        card.configure(fg_color=card.bg)
        self._update_card_text_colors(card, card.bg)

    def _show_idea_menu(self, event, card):
        if getattr(card.item, 'is_archived', False):
            return
        from gui.components.context_menu import ContextMenu
        idea = card.item
        menu = ContextMenu(card)
        menu.add_command("✏️  Editar", command=lambda: self._edit_idea_from_detail(idea))
        menu.add_separator()
        menu.add_header("Gerenciar")
        menu.add_command("📦  Arquivar", command=lambda: self._archive_idea_from_detail(idea))
        menu.add_command("🗑️  Excluir", command=lambda: self._delete_idea_from_detail(idea), danger=True)
        menu.tk_popup(event.x_root, event.y_root)

    def _edit_idea_from_detail(self, idea):
        from gui.views.project_360 import QuickIdeaEditDialog
        def save_edit(edited):
            self.idea_service.update_idea(edited, copy.deepcopy(idea))
            event_bus.emit("entity_updated")
        QuickIdeaEditDialog(self.winfo_toplevel(), idea=idea, on_save=save_edit)

    def _archive_idea_from_detail(self, idea):
        import tkinter.messagebox as messagebox
        if messagebox.askyesno("Arquivar", "Arquivar esta ideia?"):
            self.idea_service.archive_idea(idea.id)
            event_bus.emit("entity_updated")

    def _delete_idea_from_detail(self, idea):
        import tkinter.messagebox as messagebox
        if messagebox.askyesno("Excluir", "Excluir esta ideia?"):
            self.idea_service.soft_delete_idea(idea.id)
            event_bus.emit("entity_updated")

    def _show_note_menu(self, event, card):
        if getattr(card.item, 'is_archived', False):
            return
        from gui.components.context_menu import ContextMenu
        n = card.item
        menu = ContextMenu(card)
        menu.add_command("✏️  Editar", command=lambda: self._edit_note_from_detail(n))
        menu.add_separator()
        menu.add_header("Gerenciar")
        menu.add_command("📦  Arquivar", command=lambda: self._archive_note_from_detail(n))
        menu.add_command("🗑️  Excluir", command=lambda: self._delete_note_from_detail(n), danger=True)
        menu.tk_popup(event.x_root, event.y_root)

    def _edit_note_from_detail(self, n):
        from gui.views.project_360 import QuickNoteEditDialog
        def save_edit(edited):
            self.note_service.update(edited)
            event_bus.emit("entity_updated")
        QuickNoteEditDialog(self.winfo_toplevel(), note=n, on_save=save_edit)

    def _archive_note_from_detail(self, n):
        import tkinter.messagebox as messagebox
        if messagebox.askyesno("Arquivar", "Arquivar esta nota?"):
            self.note_service.archive(n.id)
            event_bus.emit("entity_updated")

    def _delete_note_from_detail(self, n):
        import tkinter.messagebox as messagebox
        if messagebox.askyesno("Excluir", "Excluir esta nota?"):
            self.note_service.soft_delete(n.id)
            event_bus.emit("entity_updated")

    def _render_ideas(self):
        existing_cards = [w for w in self._idea_scroll.winfo_children() if isinstance(w, ctk.CTkFrame) and getattr(w, "is_idea_card", False)]
        for c in existing_cards:
            c.pack_forget()
            
        if hasattr(self._idea_scroll, "lbl_empty"):
            self._idea_scroll.lbl_empty.pack_forget()
            
        if self.show_archived_ideas:
            ideas = [i for i in self.idea_service.get_all_archived() if i.task_id == self.task.id]
        else:
            ideas = self.idea_service.get_ideas_by_task(self.task.id)
            
        if not ideas:
            self._idea_scroll.configure(height=120)
            if not hasattr(self._idea_scroll, "lbl_empty"):
                self._idea_scroll.lbl_empty = ctk.CTkLabel(self._idea_scroll, text="Nenhuma ideia vinculada.", text_color="gray", font=ctk.CTkFont(size=12, slant="italic"))
            self._idea_scroll.lbl_empty.pack(pady=45)
            return

        for idx, idea in enumerate(ideas):
            dark = ctk.get_appearance_mode() == "Dark"
            bg = "#2b2b2b" if dark else "#e8e8e8"
            hover_bg = "#3f3f3f" if dark else "#d0d0d0"
            
            if idx < len(existing_cards):
                card = existing_cards[idx]
                card.pack(fill="x", pady=3)
            else:
                card = ctk.CTkFrame(self._idea_scroll, fg_color=bg, corner_radius=8)
                card.is_idea_card = True
                card.pack(fill="x", pady=3)
                
                card.top = ctk.CTkFrame(card, fg_color="transparent")
                card.top.pack(fill="x", padx=10, pady=(8, 2))
                
                card.lbl_title = ctk.CTkLabel(card.top, text="", font=ctk.CTkFont(weight="bold"), wraplength=300, anchor="w")
                card.lbl_title.pack(side="left", fill="x", expand=True)
                
                card.lbl_meta = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
                card.lbl_meta.pack(padx=10, pady=(0, 4), anchor="w")
                
                card.btn_frame = ctk.CTkFrame(card, fg_color="transparent")
                card.btn_frame.pack(fill="x", padx=10, pady=(0, 8))
                
                card.btn_del = ctk.CTkButton(card.btn_frame, text="🗑 Excluir", width=60, height=20, fg_color="#8c2b2b", hover_color="#661e1e")
                card.btn_del.pack(side="right", padx=(5, 0))
                card.btn_arq = ctk.CTkButton(card.btn_frame, text="📦 Arquivar", width=60, height=20, fg_color="#2b5c8c", hover_color="#1e4066")
                card.btn_arq.pack(side="right")
                
                self._bind_all_children(card, "<Button-1>", lambda e, c=card: self._edit_idea_from_detail(c.item))
                self._bind_all_children(card, "<Button-3>", lambda e, c=card: self._show_idea_menu(e, c))
                self._bind_all_children(card, "<Enter>", lambda e, c=card: self._card_enter(c))
                self._bind_all_children(card, "<Leave>", lambda e, c=card: self._card_leave(c))
                
            card.item = idea
            card.bg = bg
            card.hover_bg = hover_bg
            card.configure(fg_color=bg)
            
            star = "⭐ " if idea.is_favorite else ""
            card.lbl_title.configure(text=f"{star}{idea.title}")
            
            meta = [f"[{idea.status}]", idea.priority]
            if idea.next_review_date:
                meta.append(f"🔄 {self._fmt(idea.next_review_date)}")
            card.lbl_meta.configure(text="  ".join(meta))
            
            card.btn_del.configure(command=lambda: self._delete_idea(card.item))
            if getattr(idea, 'is_archived', False):
                card.btn_arq.configure(text="Restaurar", fg_color="#2B8C52", hover_color="#1E663B", command=lambda: self._restore_idea(card.item))
            else:
                card.btn_arq.configure(text="📦 Arquivar", fg_color="#2b5c8c", hover_color="#1e4066", command=lambda: self._archive_idea(card.item))
                
            self._update_card_text_colors(card, bg)

        # Dynamically adjust height up to 5 items before scrolling
        num_items = len(ideas)
        new_height = max(1, min(5, num_items)) * 105 + 15
        self._idea_scroll.configure(height=new_height)

    def _render_notes(self):
        existing_cards = [w for w in self._note_scroll.winfo_children() if isinstance(w, ctk.CTkFrame) and getattr(w, "is_note_card", False)]
        for c in existing_cards:
            c.pack_forget()
            
        if hasattr(self._note_scroll, "lbl_empty"):
            self._note_scroll.lbl_empty.pack_forget()
            
        if self.show_archived_notes:
            notes = [n for n in self.note_service.get_all_archived() if n.task_id == self.task.id]
        else:
            notes = self.note_service.get_notes_by_task(self.task.id)
            
        if not notes:
            self._note_scroll.configure(height=120)
            if not hasattr(self._note_scroll, "lbl_empty"):
                self._note_scroll.lbl_empty = ctk.CTkLabel(self._note_scroll, text="Nenhuma nota vinculada.", text_color="gray", font=ctk.CTkFont(size=12, slant="italic"))
            self._note_scroll.lbl_empty.pack(pady=45)
            return

        for idx, n in enumerate(notes):
            dark = ctk.get_appearance_mode() == "Dark"
            bg = "#2b2b2b" if dark else "#e8e8e8"
            hover_bg = "#3f3f3f" if dark else "#d0d0d0"
            
            if idx < len(existing_cards):
                card = existing_cards[idx]
                card.pack(fill="x", pady=3)
            else:
                card = ctk.CTkFrame(self._note_scroll, fg_color=bg, corner_radius=8)
                card.is_note_card = True
                card.pack(fill="x", pady=3)
                
                card.top = ctk.CTkFrame(card, fg_color="transparent")
                card.top.pack(fill="x", padx=10, pady=(8, 2))
                
                card.lbl_title = ctk.CTkLabel(card.top, text="", font=ctk.CTkFont(weight="bold"), wraplength=300, anchor="w")
                card.lbl_title.pack(side="left", fill="x", expand=True)
                
                card.lbl_meta = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=11), text_color="gray", anchor="w", wraplength=300)
                card.lbl_meta.pack(padx=10, pady=(0, 4), anchor="w")
                
                card.btn_frame = ctk.CTkFrame(card, fg_color="transparent")
                card.btn_frame.pack(fill="x", padx=10, pady=(0, 8))
                
                card.btn_del = ctk.CTkButton(card.btn_frame, text="🗑 Excluir", width=60, height=20, fg_color="#8c2b2b", hover_color="#661e1e")
                card.btn_del.pack(side="right", padx=(5, 0))
                card.btn_arq = ctk.CTkButton(card.btn_frame, text="📦 Arquivar", width=60, height=20, fg_color="#2b5c8c", hover_color="#1e4066")
                card.btn_arq.pack(side="right")
                
                self._bind_all_children(card, "<Button-1>", lambda e, c=card: self._edit_note_from_detail(c.item))
                self._bind_all_children(card, "<Button-3>", lambda e, c=card: self._show_note_menu(e, c))
                self._bind_all_children(card, "<Enter>", lambda e, c=card: self._card_enter(c))
                self._bind_all_children(card, "<Leave>", lambda e, c=card: self._card_leave(c))
                
            card.item = n
            card.bg = bg
            card.hover_bg = hover_bg
            card.configure(fg_color=bg)
            
            preview = (n.content or "").split("\n")[0][:50] or "(Nota vazia)"
            star = "⭐ " if n.is_favorite else ""
            card.lbl_title.configure(text=f"{star}{preview}")
            
            if n.content and len(n.content) > 50:
                card.lbl_meta.configure(text=n.content[50:100] + ("…" if len(n.content) > 100 else ""))
                card.lbl_meta.pack(padx=10, pady=(0, 4), anchor="w")
            else:
                card.lbl_meta.configure(text="")
                card.lbl_meta.pack_forget()
                
            card.btn_del.configure(command=lambda: self._delete_note(card.item))
            if getattr(n, 'is_archived', False):
                card.btn_arq.configure(text="Restaurar", fg_color="#2B8C52", hover_color="#1E663B", command=lambda: self._restore_note(card.item))
            else:
                card.btn_arq.configure(text="📦 Arquivar", fg_color="#2b5c8c", hover_color="#1e4066", command=lambda: self._archive_note(card.item))
                
            self._update_card_text_colors(card, bg)

        # Dynamically adjust height up to 5 items before scrolling
        num_items = len(notes)
        new_height = max(1, min(5, num_items)) * 105 + 15
        self._note_scroll.configure(height=new_height)

    def _archive_idea(self, i: Idea):
        if messagebox.askyesno("Arquivar", "Arquivar esta ideia?"):
            self.idea_service.archive_idea(i.id)
            event_bus.emit("entity_updated")

    def _delete_idea(self, i: Idea):
        if messagebox.askyesno("Excluir", "Excluir esta ideia?"):
            self.idea_service.soft_delete_idea(i.id)
            event_bus.emit("entity_updated")
            
    def _restore_idea(self, i: Idea):
        if messagebox.askyesno("Restaurar", "Restaurar esta ideia?"):
            self.idea_service.restore_idea(i.id)
            event_bus.emit("entity_updated")

    def _archive_note(self, n: Note):
        if messagebox.askyesno("Arquivar", "Arquivar esta nota?"):
            self.note_service.archive(n.id)
            event_bus.emit("entity_updated")

    def _delete_note(self, n: Note):
        if messagebox.askyesno("Excluir", "Excluir esta nota?"):
            self.note_service.soft_delete(n.id)
            event_bus.emit("entity_updated")

    def _restore_note(self, n: Note):
        if messagebox.askyesno("Restaurar", "Restaurar esta nota?"):
            self.note_service.restore(n.id)
            event_bus.emit("entity_updated")

    # ── Toggles ──────────────────────────────
    def toggle_archived_ideas(self):
        self.show_archived_ideas = not self.show_archived_ideas
        if self.show_archived_ideas:
            self.btn_toggle_ideas.configure(fg_color="#1f538d", hover_color="#14375e")
        else:
            self.btn_toggle_ideas.configure(fg_color="transparent")
        self.refresh()
        
    def toggle_archived_notes(self):
        self.show_archived_notes = not self.show_archived_notes
        if self.show_archived_notes:
            self.btn_toggle_notes.configure(fg_color="#1f538d", hover_color="#14375e")
        else:
            self.btn_toggle_notes.configure(fg_color="transparent")
        self.refresh()

    def _fmt(self, date_str) -> str:
        try:
            parts = str(date_str).split(" ")[0].split("-")
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            pass
        return str(date_str)

    def edit_task(self):
        from gui.views.tasks import TaskDialog
        orig_task = copy.deepcopy(self.task)
        def on_save(edited_task, is_new):
            self.task_service.update_task(edited_task, orig_task)
            self.task = edited_task
            event_bus.emit("entity_updated")
        TaskDialog(self.winfo_toplevel(), task=self.task, on_save=on_save)

    def add_activity(self):
        def on_save(note):
            self.task_service.add_manual_activity(self.task.id, note)
            event_bus.emit("entity_updated")
        QuickActivityDialog(self.winfo_toplevel(), on_save=on_save)

    def edit_activity(self, log):
        changes = {}
        if log.changed_fields_json:
            try:
                changes = json.loads(log.changed_fields_json)
            except Exception:
                pass
        current_text = changes.get("note", "")
        
        def on_save(new_text):
            self.task_service.update_manual_activity(log.id, new_text)
            event_bus.emit("entity_updated")
            
        QuickActivityDialog(self.winfo_toplevel(), initial_text=current_text, on_save=on_save)

    def confirm_delete_activity(self, log):
        if messagebox.askyesno("Excluir Atividade", "Deseja realmente excluir esta atividade?"):
            self.task_service.delete_activity(log.id)
            event_bus.emit("entity_updated")

    def add_idea(self):
        from gui.views.project_360 import QuickIdeaEditDialog
        dummy = Idea(title="", project_id=self.task.project_id, task_id=self.task.id)
        def on_save(i):
            self.idea_service.create_idea(
                title=i.title, description=i.description,
                project_id=i.project_id, task_id=i.task_id,
                category=i.category, interest_level=i.interest_level,
                status=i.status, priority=i.priority, next_review_date=i.next_review_date
            )
            event_bus.emit("entity_updated")
        QuickIdeaEditDialog(self.winfo_toplevel(), idea=dummy, on_save=on_save)

    def add_note(self):
        from gui.views.project_360 import QuickNoteEditDialog
        dummy = Note(content="", project_id=self.task.project_id, task_id=self.task.id)
        def on_save(edited):
            created = self.note_service.create(edited)
            event_bus.emit("entity_updated")
        QuickNoteEditDialog(self.winfo_toplevel(), note=dummy, on_save=on_save)

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

    def destroy(self):
        if hasattr(self, "_entity_updated_cb"):
            event_bus.unsubscribe("entity_updated", self._entity_updated_cb)
        super().destroy()

    def on_entity_updated(self):
        if not self.winfo_exists():
            return
        if not self.winfo_ismapped():
            self._is_dirty = True
            return
        self._is_dirty = False
        if not self.winfo_viewable():
            self.dirty = True
        else:
            self.refresh_if_needed(trigger="entity_updated")

    def on_map(self, event=None):
        if event and event.widget != self and str(event.widget) != f"{self}.!ctkcanvas":
            return
        if self.dirty:
            self.dirty = False
            self.refresh_if_needed(trigger="<Map>")
