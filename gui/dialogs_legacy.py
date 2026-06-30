import customtkinter as ctk
import tkinter.messagebox as messagebox
from services.search_service import SearchService
from services.smart_capture_service import SmartCaptureService
from gui.components.date_picker import DatePickerFrame

class GlobalSearchDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Pesquisa Global (FTS5)")
        self.geometry("650x450")
        self.search_service = SearchService()
        
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self.transient(master)
        
        self.ent_search = ctk.CTkEntry(self, width=610, placeholder_text="Digite para pesquisar em todos os módulos...", font=ctk.CTkFont(size=16))
        self.ent_search.pack(pady=20, padx=20)
        self.ent_search.bind("<KeyRelease>", self.do_search)
        self.ent_search.focus()
        
        self.results_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.results_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def do_search(self, event=None):
        query = self.ent_search.get()
        for w in self.results_frame.winfo_children():
            w.destroy()
            
        if len(query) < 2:
            return
            
        results = self.search_service.search(query)
        if not results:
             ctk.CTkLabel(self.results_frame, text="Nenhum resultado encontrado.", text_color="gray").pack(pady=20)
             return
             
        for r in results:
            card = ctk.CTkFrame(self.results_frame, fg_color="#2b2b2b" if ctk.get_appearance_mode()=="Dark" else "#e0e0e0")
            card.pack(fill="x", pady=5)
            
            type_str = str(r.get('entity_type', '')).upper()
            title_str = str(r.get('title', ''))
            preview_str = str(r.get('preview', ''))
            
            header = f"[{type_str}] {title_str}"
            ctk.CTkLabel(card, text=header, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)
            ctk.CTkLabel(card, text=preview_str, text_color="gray", wraplength=550, justify="left").pack(anchor="w", padx=10, pady=(0, 10))

class SmartCaptureDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Captura Inteligente V1")
        self.geometry("550x380")
        self.capture_service = SmartCaptureService()
        
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self.transient(master)
        self.grab_set()

        self.lbl = ctk.CTkLabel(self, text="O que está na sua mente?", font=ctk.CTkFont(size=18, weight="bold"))
        self.lbl.pack(pady=(20, 5), padx=20, anchor="w")
        
        self.ent_input = ctk.CTkEntry(self, width=510, font=ctk.CTkFont(size=14))
        self.ent_input.pack(pady=5, padx=20)
        self.ent_input.bind("<KeyRelease>", self.preview)
        self.ent_input.focus()
        
        self.preview_frame = ctk.CTkFrame(self, width=510, height=140)
        self.preview_frame.pack(pady=15, padx=20, fill="both", expand=True)
        self.preview_frame.pack_propagate(False)
        
        self.lbl_prev_type = ctk.CTkLabel(self.preview_frame, text="Tipo: -", font=ctk.CTkFont(weight="bold", size=14))
        self.lbl_prev_type.pack(anchor="w", padx=15, pady=(15, 5))
        self.lbl_prev_title = ctk.CTkLabel(self.preview_frame, text="Título: -")
        self.lbl_prev_title.pack(anchor="w", padx=15, pady=2)
        self.lbl_prev_date = ctk.CTkLabel(self.preview_frame, text="Data/Hora: -")
        self.lbl_prev_date.pack(anchor="w", padx=15, pady=2)
        
        self.parsed_data = None
        
        self.btn_save = ctk.CTkButton(self, text="Salvar Captura", command=self.save, height=40)
        self.btn_save.pack(pady=10)

    def preview(self, event=None):
        text = self.ent_input.get()
        if not text.strip():
            self.lbl_prev_type.configure(text="Tipo: -")
            self.lbl_prev_title.configure(text="Título: -")
            self.lbl_prev_date.configure(text="Data/Hora: -")
            self.parsed_data = None
            return
            
        self.parsed_data = self.capture_service.parse_input(text)
        
        type_str = self.parsed_data.get('type', 'task').upper()
        conf_str = self.parsed_data.get('confidence', 0)
        self.lbl_prev_type.configure(text=f"Tipo: {type_str} (Confiança: {conf_str}%)")
        self.lbl_prev_title.configure(text=f"Título: {self.parsed_data.get('title', '')}")
        dh = f"{self.parsed_data.get('due_date') or ''} {self.parsed_data.get('time') or ''}".strip()
        self.lbl_prev_date.configure(text=f"Data/Hora: {dh if dh else 'N/A'}")

    def save(self):
        if not self.parsed_data or not self.parsed_data.get("title"):
            messagebox.showwarning("Aviso", "Digite algo válido para capturar.")
            return
        
        tipo = self.parsed_data.get("type", "task")
        title = self.parsed_data.get("title", "")
        due_date = self.parsed_data.get("due_date")
        
        if tipo == "task":
            from services.task_service import TaskService
            TaskService().create_task(title=title, due_date=due_date)
        else:
            from services.task_service import TaskService
            TaskService().create_task(title=title, due_date=due_date, context=f"Intenção capturada: {tipo.upper()}")
            
        if hasattr(self.master, 'views') and 'workbench' in self.master.views:
            self.master.views['workbench'].refresh()
        self.destroy()

class PromoteIdeaToProjectDialog(ctk.CTkToplevel):
    def __init__(self, master, idea, on_promote=None):
        super().__init__(master)
        self.title("Criar Projeto a partir da Ideia")
        self.geometry("520x680")
        self.idea = idea
        self.on_promote = on_promote
        self.resizable(False, False)

        self.update_idletasks()
        x = (self.winfo_screenwidth() - 520) // 2
        y = (self.winfo_screenheight() - 680) // 2
        self.geometry(f"+{x}+{y}")
        self.transient(master)
        self.grab_set()

        # Scrollable content frame
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        lp = dict(padx=15, pady=(10, 2), anchor="w")
        wp = dict(padx=15, pady=(0, 8), fill="x")

        ctk.CTkLabel(scroll, text="Título do Projeto:", font=ctk.CTkFont(weight="bold")).pack(**lp)
        self.ent_title = ctk.CTkEntry(scroll)
        self.ent_title.pack(**wp)
        self.ent_title.insert(0, idea.title)

        ctk.CTkLabel(scroll, text="Descrição do Projeto:", font=ctk.CTkFont(weight="bold")).pack(**lp)
        self.txt_desc = ctk.CTkTextbox(scroll, height=80)
        self.txt_desc.pack(**wp)
        if idea.description:
            self.txt_desc.insert("0.0", idea.description)

        ctk.CTkLabel(scroll, text="Prioridade:", font=ctk.CTkFont(weight="bold")).pack(**lp)
        self.opt_prio = ctk.CTkOptionMenu(scroll, values=["Baixa", "Média", "Alta", "Crítica"])
        self.opt_prio.pack(**wp)
        self.opt_prio.set(idea.priority or "Média")

        ctk.CTkLabel(scroll, text="Prazo:", font=ctk.CTkFont(weight="bold")).pack(**lp)
        self.ent_due = DatePickerFrame(scroll)
        self.ent_due.pack(**wp)

        ctk.CTkLabel(scroll, text="Data de Alerta:", font=ctk.CTkFont(weight="bold")).pack(**lp)
        self.ent_alert = DatePickerFrame(scroll)
        self.ent_alert.pack(**wp)

        ctk.CTkLabel(scroll, text="Mensagem do Alerta:", font=ctk.CTkFont(weight="bold")).pack(**lp)
        self.ent_alert_msg = ctk.CTkEntry(scroll, placeholder_text="Ex: O prazo está acabando!")
        self.ent_alert_msg.pack(**wp)

        # Checkboxes
        self.cb_desc = ctk.CTkCheckBox(scroll, text="Copiar descrição da ideia")
        self.cb_desc.pack(padx=15, pady=4, anchor="w")
        self.cb_desc.select()

        self.cb_tags = ctk.CTkCheckBox(scroll, text="Copiar tags da ideia")
        self.cb_tags.pack(padx=15, pady=4, anchor="w")
        self.cb_tags.select()

        self.cb_attach = ctk.CTkCheckBox(scroll, text="Copiar anexos da ideia")
        self.cb_attach.pack(padx=15, pady=4, anchor="w")
        self.cb_attach.select()

        self.cb_link = ctk.CTkCheckBox(scroll, text="Criar vínculo entre ideia e projeto")
        self.cb_link.pack(padx=15, pady=4, anchor="w")
        self.cb_link.select()

        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(5, 15))

        self.btn_create = ctk.CTkButton(btn_frame, text="📁 Criar Projeto", fg_color="#2B8C52", hover_color="#1E663B", command=self.create)
        self.btn_create.pack(side="left", padx=10)

        self.btn_cancel = ctk.CTkButton(btn_frame, text="Cancelar", fg_color="transparent", border_width=1, text_color=("black", "white"), command=self.destroy)
        self.btn_cancel.pack(side="left", padx=10)

    def create(self):
        title = self.ent_title.get().strip()
        if not title:
            messagebox.showwarning("Aviso", "O título do projeto é obrigatório.")
            return
        
        desc = self.txt_desc.get("0.0", "end-1c").strip() if self.cb_desc.get() == 1 else None
        if self.on_promote:
            self.on_promote(
                self.idea.id,
                title,
                desc,
                self.cb_tags.get() == 1,
                self.cb_attach.get() == 1,
                self.cb_link.get() == 1,
                priority=self.opt_prio.get(),
                due_date=self.ent_due.get_date(),
                alert_date=self.ent_alert.get_date(),
                alert_message=self.ent_alert_msg.get().strip() or None
            )
        self.destroy()


class PromoteIdeaToTaskDialog(ctk.CTkToplevel):
    def __init__(self, master, idea, default_project_id=None, on_promote=None):
        super().__init__(master)
        self.title("Criar Tarefa a partir da Ideia")
        self.geometry("520x680")
        self.idea = idea
        self.on_promote = on_promote
        self.resizable(False, False)

        self.update_idletasks()
        x = (self.winfo_screenwidth() - 520) // 2
        y = (self.winfo_screenheight() - 680) // 2
        self.geometry(f"+{x}+{y}")
        self.transient(master)
        self.grab_set()

        # Scrollable content frame
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        lp = dict(padx=15, pady=(10, 2), anchor="w")
        wp = dict(padx=15, pady=(0, 8), fill="x")

        ctk.CTkLabel(scroll, text="Título da Tarefa:", font=ctk.CTkFont(weight="bold")).pack(**lp)
        self.ent_title = ctk.CTkEntry(scroll)
        self.ent_title.pack(**wp)
        self.ent_title.insert(0, idea.title)

        ctk.CTkLabel(scroll, text="Descrição da Tarefa:", font=ctk.CTkFont(weight="bold")).pack(**lp)
        self.txt_desc = ctk.CTkTextbox(scroll, height=80)
        self.txt_desc.pack(**wp)
        if idea.description:
            self.txt_desc.insert("0.0", idea.description)

        # Project Selection
        ctk.CTkLabel(scroll, text="Projeto Destino (Opcional):", font=ctk.CTkFont(weight="bold")).pack(**lp)
        from services.project_service import ProjectService
        self.projects = ProjectService().get_all_active()
        self.project_dict = {"Nenhum": None}
        for p in self.projects:
            self.project_dict[f"{p.id} - {p.name}"] = p.id
        
        self.opt_project = ctk.CTkOptionMenu(scroll, values=list(self.project_dict.keys()))
        self.opt_project.pack(**wp)
        
        default_val = "Nenhum"
        if default_project_id:
            for k, v in self.project_dict.items():
                if v == default_project_id:
                    default_val = k
                    break
        self.opt_project.set(default_val)

        ctk.CTkLabel(scroll, text="Prioridade / Energia:", font=ctk.CTkFont(weight="bold")).pack(**lp)
        self.opt_prio = ctk.CTkOptionMenu(scroll, values=["Baixa", "Média", "Alta", "Crítica"])
        self.opt_prio.pack(**wp)
        self.opt_prio.set(idea.priority or "Média")

        ctk.CTkLabel(scroll, text="Status:", font=ctk.CTkFont(weight="bold")).pack(**lp)
        self.opt_status = ctk.CTkOptionMenu(scroll, values=["Backlog", "A Fazer", "Em Andamento", "Pausado", "Aguardando", "Bloqueado", "Concluído"])
        self.opt_status.pack(**wp)
        self.opt_status.set("Backlog")

        ctk.CTkLabel(scroll, text="Prazo:", font=ctk.CTkFont(weight="bold")).pack(**lp)
        self.ent_due = DatePickerFrame(scroll)
        self.ent_due.pack(**wp)

        ctk.CTkLabel(scroll, text="Data de Alerta:", font=ctk.CTkFont(weight="bold")).pack(**lp)
        self.ent_alert = DatePickerFrame(scroll)
        self.ent_alert.pack(**wp)

        ctk.CTkLabel(scroll, text="Mensagem do Alerta:", font=ctk.CTkFont(weight="bold")).pack(**lp)
        self.ent_alert_msg = ctk.CTkEntry(scroll, placeholder_text="Ex: O prazo está acabando!")
        self.ent_alert_msg.pack(**wp)

        # Checkboxes
        self.cb_desc = ctk.CTkCheckBox(scroll, text="Copiar descrição da ideia")
        self.cb_desc.pack(padx=15, pady=4, anchor="w")
        self.cb_desc.select()

        self.cb_tags = ctk.CTkCheckBox(scroll, text="Copiar tags da ideia")
        self.cb_tags.pack(padx=15, pady=4, anchor="w")
        self.cb_tags.select()

        self.cb_attach = ctk.CTkCheckBox(scroll, text="Copiar anexos da ideia")
        self.cb_attach.pack(padx=15, pady=4, anchor="w")
        self.cb_attach.select()

        self.cb_link = ctk.CTkCheckBox(scroll, text="Criar vínculo entre ideia e tarefa")
        self.cb_link.pack(padx=15, pady=4, anchor="w")
        self.cb_link.select()

        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(5, 15))

        self.btn_create = ctk.CTkButton(btn_frame, text="📋 Criar Tarefa", fg_color="#2B8C52", hover_color="#1E663B", command=self.create)
        self.btn_create.pack(side="left", padx=10)

        self.btn_cancel = ctk.CTkButton(btn_frame, text="Cancelar", fg_color="transparent", border_width=1, text_color=("black", "white"), command=self.destroy)
        self.btn_cancel.pack(side="left", padx=10)

    def create(self):
        title = self.ent_title.get().strip()
        if not title:
            messagebox.showwarning("Aviso", "O título da tarefa é obrigatório.")
            return
        
        proj_key = self.opt_project.get()
        proj_id = self.project_dict.get(proj_key)

        desc = self.txt_desc.get("0.0", "end-1c").strip() if self.cb_desc.get() == 1 else None
        if self.on_promote:
            self.on_promote(
                self.idea.id,
                title,
                desc,
                self.cb_tags.get() == 1,
                self.cb_attach.get() == 1,
                self.cb_link.get() == 1,
                proj_id,
                priority=self.opt_prio.get(),
                status=self.opt_status.get(),
                due_date=self.ent_due.get_date(),
                alert_date=self.ent_alert.get_date(),
                alert_message=self.ent_alert_msg.get().strip() or None
            )
        self.destroy()


class UnresolvedLinkDialog(ctk.CTkToplevel):
    def __init__(self, master, entity_name, on_create=None):
        super().__init__(master)
        self.title("Entidade não encontrada")
        self.geometry("380x280")
        self.entity_name = entity_name
        self.on_create = on_create
        self.resizable(False, False)
        
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 380) // 2
        y = (self.winfo_screenheight() - 280) // 2
        self.geometry(f"+{x}+{y}")
        self.transient(master)
        self.grab_set()
        
        ctk.CTkLabel(self, text=f"A entidade '{entity_name}' não foi encontrada.", font=ctk.CTkFont(weight="bold")).pack(pady=(20, 5))
        ctk.CTkLabel(self, text="Deseja criar uma nova entidade com este nome?").pack(pady=(0, 15))
        
        self.opt_type = ctk.CTkOptionMenu(self, values=["Projeto", "Tarefa", "Ideia", "Nota", "Página Wiki"], width=200)
        self.opt_type.pack(pady=10)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        ctk.CTkButton(btn_frame, text="Criar", fg_color="#2B8C52", hover_color="#1E663B", command=self.confirm, width=100).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancelar", fg_color="transparent", border_width=1, text_color=("black", "white"), command=self.destroy, width=100).pack(side="left", padx=10)
        
    def confirm(self):
        t = self.opt_type.get()
        if self.on_create:
            self.on_create(self.entity_name, t)
        self.destroy()

