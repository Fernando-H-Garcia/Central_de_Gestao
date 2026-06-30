import tkinter as tk
import customtkinter as ctk
import tkinter.messagebox as messagebox
import tkinter.simpledialog as simpledialog
import copy
from datetime import datetime

from services.project_service import ProjectService
from services.task_service import TaskService
from services.idea_service import IdeaService
from services.note_service import NoteService
from services.alert_service import AlertService
from gui.views.task_detail import TaskDetailView
from models.entities import Project, Task, Idea, Note
from core.event_bus import event_bus
from gui.components.date_picker import DatePickerFrame
from database.connection import get_db_cursor


# ─────────────────────────────────────────────
# Diálogo rápido para editar Tarefa inline
# ─────────────────────────────────────────────
class QuickTaskEditDialog(ctk.CTkToplevel):
    def __init__(self, master, task: Task, on_save=None):
        super().__init__(master)
        self.title("Editar Tarefa")
        self.geometry("480x520")
        self.task = copy.deepcopy(task)
        self.on_save = on_save
        self.resizable(False, False)

        self.update_idletasks()
        x = (self.winfo_screenwidth() - 480) // 2
        y = (self.winfo_screenheight() - 520) // 2
        self.geometry(f"+{x}+{y}")
        self.transient(master)
        self.grab_set()

        lp = dict(padx=20, pady=(0, 2), anchor="w")
        wp = dict(padx=20, pady=(0, 8), fill="x")

        ctk.CTkLabel(self, text="Título:").pack(**lp)
        self.ent_title = ctk.CTkEntry(self, width=440)
        self.ent_title.pack(**wp)
        self.ent_title.insert(0, task.title)

        ctk.CTkLabel(self, text="Contexto:").pack(**lp)
        self.txt_ctx = ctk.CTkTextbox(self, height=70, width=440)
        self.txt_ctx.pack(**wp)
        if task.context:
            self.txt_ctx.insert("0.0", task.context)

        ctk.CTkLabel(self, text="Status:").pack(**lp)
        self.opt_status = ctk.CTkOptionMenu(self, values=["Backlog", "A Fazer", "Em Andamento", "Pausado", "Aguardando", "Bloqueado", "Concluído"], width=440)
        self.opt_status.pack(**wp)
        self.opt_status.set(task.status)

        ctk.CTkLabel(self, text="Energia / Prioridade:").pack(**lp)
        self.opt_energy = ctk.CTkOptionMenu(self, values=["Baixa", "Média", "Alta", "Máxima"], width=440)
        self.opt_energy.pack(**wp)
        self.opt_energy.set(task.energy_level)

        ctk.CTkLabel(self, text="Prazo:").pack(**lp)
        self.dp_due = DatePickerFrame(self)
        self.dp_due.pack(**wp)
        self.dp_due.set_date(task.due_date)

        ctk.CTkButton(self, text="💾  Salvar", fg_color="#2B8C52", hover_color="#1E663B", command=self.save).pack(pady=16)

    def save(self):
        t = self.ent_title.get().strip()
        if not t:
            messagebox.showwarning("Aviso", "Título obrigatório.")
            return
        self.task.title = t
        self.task.context = self.txt_ctx.get("0.0", "end").strip()
        self.task.status = self.opt_status.get()
        self.task.energy_level = self.opt_energy.get()
        self.task.due_date = self.dp_due.get_date()
        self.task.alert_date = None
        self.task.alert_message = None
        if self.on_save:
            self.on_save(self.task)
        self.destroy()


# ─────────────────────────────────────────────
# Diálogo rápido para editar Ideia inline
# ─────────────────────────────────────────────
class QuickIdeaEditDialog(ctk.CTkToplevel):
    def __init__(self, master, idea: Idea, on_save=None):
        super().__init__(master)
        self.title("Editar Ideia")
        self.geometry("480x560")
        self.idea = copy.deepcopy(idea)
        self.on_save = on_save
        self.resizable(False, False)

        self.update_idletasks()
        x = (self.winfo_screenwidth() - 480) // 2
        y = (self.winfo_screenheight() - 560) // 2
        self.geometry(f"+{x}+{y}")
        self.transient(master)
        self.grab_set()

        # Scrollable content frame to prevent clipping on smaller resolutions
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)

        lp = dict(padx=20, pady=(0, 2), anchor="w")
        wp = dict(padx=20, pady=(0, 8), fill="x")

        ctk.CTkLabel(self.scroll, text="Título:").pack(**lp)
        self.ent_title = ctk.CTkEntry(self.scroll, width=400)
        self.ent_title.pack(**wp)
        self.ent_title.insert(0, idea.title)

        ctk.CTkLabel(self.scroll, text="Categoria:").pack(**lp)
        self.ent_cat = ctk.CTkEntry(self.scroll, width=400)
        self.ent_cat.pack(**wp)
        if idea.category:
            self.ent_cat.insert(0, idea.category)

        ctk.CTkLabel(self.scroll, text="Status:").pack(**lp)
        self.opt_status = ctk.CTkOptionMenu(self.scroll, values=["Nova", "Em Análise", "Aprovada", "Descartada"], width=400)
        self.opt_status.pack(**wp)
        self.opt_status.set(idea.status)

        ctk.CTkLabel(self.scroll, text="Prioridade:").pack(**lp)
        self.opt_prio = ctk.CTkOptionMenu(self.scroll, values=["Baixa", "Média", "Alta", "Crítica"], width=400)
        self.opt_prio.pack(**wp)
        self.opt_prio.set(idea.priority)

        ctk.CTkLabel(self.scroll, text="Próxima Revisão:").pack(**lp)
        self.dp_review = DatePickerFrame(self.scroll)
        self.dp_review.pack(**wp)
        self.dp_review.set_date(idea.next_review_date)

        ctk.CTkLabel(self.scroll, text="Descrição:").pack(**lp)
        self.txt_desc = ctk.CTkTextbox(self.scroll, height=70, width=400)
        self.txt_desc.pack(**wp)
        if idea.description:
            self.txt_desc.insert("0.0", idea.description)

        ctk.CTkButton(self, text="💾  Salvar", fg_color="#2B8C52", hover_color="#1E663B", command=self.save).pack(pady=10)

        # Categoria Autocomplete Dropdown
        from utils.dropdown_autocomplete import DropdownAutocompleteHelper, get_unique_categories
        self.cat_autocomplete = DropdownAutocompleteHelper(self.ent_cat, get_unique_categories)

    def save(self):
        t = self.ent_title.get().strip()
        if not t:
            messagebox.showwarning("Aviso", "Título obrigatório.")
            return
        self.idea.title = t
        self.idea.category = self.ent_cat.get().strip() or None
        self.idea.status = self.opt_status.get()
        self.idea.priority = self.opt_prio.get()
        self.idea.next_review_date = self.dp_review.get_date()
        self.idea.description = self.txt_desc.get("0.0", "end-1c").strip() or None
        if self.on_save:
            self.on_save(self.idea)
        self.destroy()


# ─────────────────────────────────────────────
# Diálogo rápido para editar Nota inline
# ─────────────────────────────────────────────
class QuickNoteEditDialog(ctk.CTkToplevel):
    def __init__(self, master, note: Note, on_save=None):
        super().__init__(master)
        self.title("Editar Nota")
        self.geometry("520x400")
        self.note = copy.deepcopy(note)
        self.on_save = on_save
        self.resizable(False, False)

        self.update_idletasks()
        x = (self.winfo_screenwidth() - 520) // 2
        y = (self.winfo_screenheight() - 400) // 2
        self.geometry(f"+{x}+{y}")
        self.transient(master)
        self.grab_set()

        ctk.CTkLabel(self, text="Conteúdo da Nota:", anchor="w").pack(padx=20, pady=(16, 4), anchor="w")
        self.txt = ctk.CTkTextbox(self, height=280)
        self.txt.pack(padx=20, pady=(0, 8), fill="both", expand=True)
        self.txt.insert("0.0", note.content or "")

        ctk.CTkButton(self, text="💾  Salvar", fg_color="#2B8C52", hover_color="#1E663B", command=self.save).pack(pady=12)

    def save(self):
        self.note.content = self.txt.get("0.0", "end-1c")
        if self.on_save:
            self.on_save(self.note)
        self.destroy()


# ─────────────────────────────────────────────
# Visão 360° principal
# ─────────────────────────────────────────────
class Project360View(ctk.CTkFrame):

    # Estado de grupos colapsáveis por projeto (persistente na sessão)
    _group_states: dict = {}

    def __init__(self, master, go_back_callback, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.go_back_callback = go_back_callback

        self.project_service = ProjectService()
        self.task_service = TaskService()
        self.idea_service = IdeaService()
        self.note_service = NoteService()
        self.alert_service = AlertService()

        self.current_project: Project | None = None
        self._group_limits = {}  # status_name -> int limit
        
        self.show_archived_tasks = False
        self.show_archived_ideas = False
        self.show_archived_notes = False
        self.dirty = False
        self.visible_tasks_limit = 15
        self.visible_ideas_limit = 15
        self.visible_notes_limit = 15
        self.task_sort_by = "Criação"
        self._active_filter = "Todas"  # Sprint 1: filtro ativo
        self._all_tasks_cache: list = []  # Sprint 1: lista completa para filtro client-side
        # Cached counts used by lazy-load scroll check (avoid DB queries in the 500ms loop)
        self._cached_tasks_count = 0
        self._cached_ideas_count = 0
        self._cached_notes_count = 0
        event_bus.subscribe("snapshot_updated", lambda _: self.on_entity_updated())
        self.bind("<Map>", lambda e: self.on_map(e))

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Top bar (Voltar + Nome + Editar) ─────────────────────────
        hf = ctk.CTkFrame(self, fg_color="transparent")
        hf.grid(row=0, column=0, sticky="ew", pady=(12, 0), padx=12)
        hf.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(hf, text="← Voltar", width=70, fg_color="transparent",
                      border_width=1, text_color=("black", "white"),
                      command=self.go_back_callback).grid(row=0, column=0, sticky="w", padx=(0, 12))

        self.lbl_nome = ctk.CTkLabel(hf, text="Visão 360°",
                                     font=ctk.CTkFont(size=22, weight="bold"))
        self.lbl_nome.grid(row=0, column=1, sticky="w")

        self.btn_edit_proj = ctk.CTkButton(hf, text="✏️  Editar Projeto", width=130,
                                           command=self.edit_project)
        self.btn_edit_proj.grid(row=0, column=2, sticky="e", padx=(12, 0))

        # ── Scrollable content ───────────────────────────────────────
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=6)
        self.scroll.grid_columnconfigure(0, weight=1)

        # ── Row 0: Overview card (objetivo + stats + prazo) ──────────
        self.ov = ctk.CTkFrame(self.scroll, corner_radius=10)
        self.ov.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 12))
        self.ov.grid_columnconfigure(0, weight=1)

        self.lbl_obj = ctk.CTkLabel(self.ov, text="Objetivo: —",
                                    font=ctk.CTkFont(size=13), anchor="w")
        self.lbl_obj.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 2))

        self.stats_frame = ctk.CTkFrame(self.ov, fg_color="transparent")
        self.stats_frame.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 6))

        # Sprint 1 — Barra de progresso (row 2 do overview card)
        self.progress_frame = ctk.CTkFrame(self.ov, fg_color="transparent")
        self.progress_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 4))
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=12,
                                               corner_radius=6, progress_color="#2563EB")
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.progress_bar.set(0)

        self.lbl_progress_text = ctk.CTkLabel(self.progress_frame, text="",
                                               font=ctk.CTkFont(size=12), anchor="center")
        self.lbl_progress_text.grid(row=1, column=0, sticky="ew")

        self.lbl_prazo_text = ctk.CTkLabel(self.progress_frame, text="",
                                            font=ctk.CTkFont(size=11), anchor="center",
                                            text_color="gray")
        self.lbl_prazo_text.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        # Origin area (hidden by default)
        self.origin_frame = ctk.CTkFrame(self.ov, fg_color="transparent")
        self.lbl_origin = ctk.CTkLabel(self.origin_frame, text="",
                                        font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_origin.pack(side="left")
        self.btn_open_origin = ctk.CTkButton(self.origin_frame, text="Abrir Ideia",
                                              width=80, height=22,
                                              command=self.open_originated_idea)
        self.btn_open_origin.pack(side="left", padx=10)

        # ── Row 1: Links panel ────────────────────────────────────────
        from gui.components.entity_links_panel import EntityLinksPanel
        self.links_panel = EntityLinksPanel(self.scroll, "project", 0)
        self.links_panel.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 12))

        # ── Row 2: Sprint 1 — KPI chips ───────────────────────────────
        self.kpi_frame = ctk.CTkFrame(self.scroll, corner_radius=10)
        self.kpi_frame.grid(row=2, column=0, sticky="ew", padx=4, pady=(0, 12))
        self.kpi_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)
        self._kpi_widgets = {}  # label refs por chave
        self._build_kpi_section()

        # ── Row 3: Sprint 1 — Filter chips ────────────────────────────
        self.filter_frame = ctk.CTkFrame(self.scroll, corner_radius=8,
                                          fg_color="transparent")
        self.filter_frame.grid(row=3, column=0, sticky="ew", padx=4, pady=(0, 6))
        self._filter_chip_btns = {}
        self._build_filter_chips()

        # ── Row 4: Tarefas (100% largura) ────────────────────────────
        self.task_outer = ctk.CTkFrame(self.scroll, corner_radius=10)
        self.task_outer.grid(row=4, column=0, sticky="ew", padx=4, pady=(0, 12))
        self.task_outer.grid_columnconfigure(0, weight=1)
        # Não usar grid_rowconfigure(1, weight=1) — deixa a altura ser natural

        # Header de tarefas
        task_hdr = ctk.CTkFrame(self.task_outer, fg_color="transparent")
        task_hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        task_hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(task_hdr, text="📋  Tarefas",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w")

        task_btn_frame = ctk.CTkFrame(task_hdr, fg_color="transparent")
        task_btn_frame.grid(row=0, column=1, sticky="e")

        self.btn_toggle_tasks = ctk.CTkButton(
            task_btn_frame, text="Arquivados", width=80, height=26,
            fg_color="transparent", border_width=1, text_color=("black", "white"),
            command=self.toggle_archived_tasks)
        self.btn_toggle_tasks.pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            task_btn_frame, text="+ Tarefa", width=75, height=26,
            fg_color="#2B8C52", hover_color="#1E663B",
            command=self.add_task).pack(side="left")

        # Body de tarefas — frame simples (sem scroll próprio, o scroll é o pai)
        self.task_col = ctk.CTkFrame(self.task_outer, fg_color="transparent")
        self.task_col.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.task_col.grid_columnconfigure(0, weight=1)

        # ── Row 6: Ideias + Notas lado a lado ────────────────────────
        bottom_row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        bottom_row.grid(row=5, column=0, sticky="ew", padx=4, pady=(0, 12))
        bottom_row.grid_columnconfigure((0, 1), weight=1)

        # Ideias
        self.idea_outer = ctk.CTkFrame(bottom_row, corner_radius=10)
        self.idea_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.idea_outer.grid_columnconfigure(0, weight=1)
        self._ideas_expanded = True
        self._build_ideas_section()

        # Notas
        self.note_outer = ctk.CTkFrame(bottom_row, corner_radius=10)
        self.note_outer.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.note_outer.grid_columnconfigure(0, weight=1)
        self._notes_expanded = False  # Notas iniciam recolhidas
        self._build_notes_section()

        self._check_scroll_loop()

    # ─────────────────────────────────────────────────────────────
    # Sprint 1: Construtores das seções novas
    # ─────────────────────────────────────────────────────────────

    _KPI_DEFS = [
        ("total",     "Tarefas",       "#374151"),
        ("done",      "Concluídas",    "#15803D"),
        ("active",    "Em andamento",  "#0369A1"),
        ("waiting",   "Aguardando",    "#6D28D9"),
        ("backlog",   "Backlog",        "#64748B"),
        ("blocked",   "Bloqueadas",    "#B91C1C"),
        ("overdue",   "Atrasadas",     "#D97706"),
    ]

    def _build_kpi_section(self):
        """Cria os 5 chips de KPI (criados uma vez, atualizados no refresh)."""
        for col_idx, (key, label, color) in enumerate(self._KPI_DEFS):
            chip = ctk.CTkFrame(self.kpi_frame, corner_radius=8,
                                fg_color=("#e8e8e8", "#2b2b2b"))
            chip.grid(row=0, column=col_idx, sticky="ew", padx=6, pady=10)

            lbl_num = ctk.CTkLabel(chip, text="0",
                                   font=ctk.CTkFont(size=22, weight="bold"),
                                   text_color=color)
            lbl_num.pack(pady=(8, 0))

            lbl_desc = ctk.CTkLabel(chip, text=label,
                                    font=ctk.CTkFont(size=11),
                                    text_color="gray")
            lbl_desc.pack(pady=(0, 8))

            self._kpi_widgets[key] = lbl_num

    def _build_filter_chips(self):
        """Cria os chips de filtro rápido."""
        filters = ["Todas", "Hoje", "Atrasadas", "Bloqueadas", "Alta Prioridade"]
        for f in filters:
            btn = ctk.CTkButton(
                self.filter_frame, text=f, width=90, height=28,
                corner_radius=14,
                fg_color="#1f538d" if f == "Todas" else ("#d0d0d0", "#3f3f3f"),
                hover_color="#2563EB",
                text_color="white" if f == "Todas" else ("black", "white"),
                font=ctk.CTkFont(size=12),
                command=lambda flt=f: self._apply_filter(flt))
            btn.pack(side="left", padx=4, pady=6)
            self._filter_chip_btns[f] = btn

    def _build_next_actions_section(self):
        """Constrói o cabeçalho e o container do painel Próximas Ações."""
        hdr = ctk.CTkFrame(self.next_actions_outer, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        hdr.grid_columnconfigure(0, weight=1)

        self.lbl_next_actions_title = ctk.CTkLabel(
            hdr, text="🎯  Próximas Ações  ▼",
            font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_next_actions_title.grid(row=0, column=0, sticky="w")
        self.lbl_next_actions_title.bind("<Button-1>", lambda e: self._toggle_next_actions())
        self.lbl_next_actions_title.configure(cursor="hand2")

        self.next_actions_body = ctk.CTkFrame(self.next_actions_outer, fg_color="transparent")
        self.next_actions_body.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.next_actions_body.grid_columnconfigure((0, 1, 2), weight=1)

    def _build_ideas_section(self):
        """Constrói o painel de Ideias (header + body colapsável)."""
        hdr = ctk.CTkFrame(self.idea_outer, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        hdr.grid_columnconfigure(0, weight=1)

        self.lbl_ideas_title = ctk.CTkLabel(
            hdr, text="💡  Ideias  ▼",
            font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_ideas_title.grid(row=0, column=0, sticky="w")
        self.lbl_ideas_title.bind("<Button-1>", lambda e: self._toggle_ideas())
        self.lbl_ideas_title.configure(cursor="hand2")

        idea_btn_f = ctk.CTkFrame(hdr, fg_color="transparent")
        idea_btn_f.grid(row=0, column=1, sticky="e")
        self.btn_toggle_ideas = ctk.CTkButton(
            idea_btn_f, text="Arquivados", width=75, height=24,
            fg_color="transparent", border_width=1, text_color=("black", "white"),
            command=self.toggle_archived_ideas)
        self.btn_toggle_ideas.pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            idea_btn_f, text="+ Ideia", width=65, height=24,
            fg_color="#2B8C52", hover_color="#1E663B",
            command=self.add_idea).pack(side="left")

        self.idea_col = ctk.CTkScrollableFrame(
            self.idea_outer, fg_color="transparent", height=180)
        self.idea_col.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 10))
        self.idea_col.grid_columnconfigure(0, weight=1)

    def _build_notes_section(self):
        """Constrói o painel de Notas (header + body colapsável; inicia recolhido)."""
        hdr = ctk.CTkFrame(self.note_outer, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        hdr.grid_columnconfigure(0, weight=1)

        self.lbl_notes_title = ctk.CTkLabel(
            hdr, text="📝  Notas  ▶",
            font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_notes_title.grid(row=0, column=0, sticky="w")
        self.lbl_notes_title.bind("<Button-1>", lambda e: self._toggle_notes())
        self.lbl_notes_title.configure(cursor="hand2")

        note_btn_f = ctk.CTkFrame(hdr, fg_color="transparent")
        note_btn_f.grid(row=0, column=1, sticky="e")
        self.btn_toggle_notes = ctk.CTkButton(
            note_btn_f, text="Arquivados", width=75, height=24,
            fg_color="transparent", border_width=1, text_color=("black", "white"),
            command=self.toggle_archived_notes)
        self.btn_toggle_notes.pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            note_btn_f, text="+ Nota", width=65, height=24,
            fg_color="#2B8C52", hover_color="#1E663B",
            command=self.add_note).pack(side="left")

        self.note_col = ctk.CTkScrollableFrame(
            self.note_outer, fg_color="transparent", height=180)
        self.note_col.grid_columnconfigure(0, weight=1)
        # Inicia recolhido: note_col NÃO é colocado no grid ainda
        if self._notes_expanded:
            self.note_col.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 10))

    # ── Toggle handlers para painéis recolhíveis ─────────────────────
    def _toggle_next_actions(self):
        self._next_actions_expanded = not self._next_actions_expanded
        arrow = "▼" if self._next_actions_expanded else "▶"
        self.lbl_next_actions_title.configure(text=f"🎯  Próximas Ações  {arrow}")
        if self._next_actions_expanded:
            self.next_actions_body.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        else:
            self.next_actions_body.grid_forget()

    def _toggle_ideas(self):
        self._ideas_expanded = not self._ideas_expanded
        arrow = "▼" if self._ideas_expanded else "▶"
        self.lbl_ideas_title.configure(text=f"💡  Ideias  {arrow}")
        if self._ideas_expanded:
            self.idea_col.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 10))
        else:
            self.idea_col.grid_forget()

    def _toggle_notes(self):
        self._notes_expanded = not self._notes_expanded
        arrow = "▼" if self._notes_expanded else "▶"
        self.lbl_notes_title.configure(text=f"📝  Notas  {arrow}")
        if self._notes_expanded:
            self.note_col.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 10))
        else:
            self.note_col.grid_forget()

    # ── Sprint 1: Filter chips ────────────────────────────────────────
    def _apply_filter(self, flt: str):
        self._active_filter = flt
        # Atualizar estilo dos chips
        for name, btn in self._filter_chip_btns.items():
            if name == flt:
                btn.configure(fg_color="#1f538d", text_color="white")
            else:
                btn.configure(fg_color=("#d0d0d0", "#3f3f3f"),
                               text_color=("black", "white"))
        # Re-renderizar tarefas com filtro
        self._render_tasks_filtered()

    def _filter_tasks(self, tasks: list) -> list:
        """Filtra a lista de tarefas conforme o chip ativo."""
        today = datetime.now().date()
        flt = self._active_filter
        if flt == "Todas":
            return tasks
        if flt == "Hoje":
            return [t for t in tasks if t.due_date and
                    str(t.due_date).split(" ")[0] == str(today)]
        if flt == "Atrasadas":
            return [t for t in tasks if t.due_date and t.status != "Concluído" and
                    str(t.due_date).split(" ")[0] < str(today)]
        if flt == "Bloqueadas":
            return [t for t in tasks if t.status == "Bloqueado" or
                    t.id in getattr(self, 'blocked_task_ids', set())]
        if flt == "Alta Prioridade":
            return [t for t in tasks if t.energy_level in ("Alta", "Máxima")]
        return tasks

    def _render_tasks_filtered(self):
        """Aplica o filtro ativo sobre o cache e re-renderiza sem ir ao banco."""
        filtered = self._filter_tasks(self._all_tasks_cache)
        self._render_tasks(filtered)

    # ── Load project ─────────────────────────
    def load_project(self, project: Project, trigger="init"):
        self._close_task_detail()  # Garante que detalhes anteriores sejam fechados
        self.current_project = project
        self.visible_tasks_limit = 15
        self.visible_ideas_limit = 15
        self.visible_notes_limit = 15
        self.refresh(trigger=trigger)

    def refresh_if_needed(self, trigger="init"):
        if not self.current_project:
            return
        updated = self.project_service.project_repo.get_by_id(self.current_project.id)
        if updated:
            self.current_project = updated
            self.refresh(trigger=trigger)

    def refresh(self, trigger="init"):
        if not self.current_project:
            return
        import time
        from utils.instrumentation import log_perf_data, count_widgets_recursive
        start_time = time.time()
        widgets_before = count_widgets_recursive(self.task_col) + count_widgets_recursive(self.idea_col) + count_widgets_recursive(self.note_col)
        widgets_before = count_widgets_recursive(self.task_col) + count_widgets_recursive(self.idea_col) + count_widgets_recursive(self.note_col)
        t_start = time.time()

        p = self.current_project

        # Configure overview card color
        dark = ctk.get_appearance_mode() == "Dark"
        status_colors = {
            "Concluído": "#15803D",
            "Em Andamento": "#0369A1",
            "Pausado": "#B45309",
            "Aguardando": "#6D28D9",
            "Bloqueado": "#B91C1C",
        }
        default_bg = "#2b2b2b" if dark else "#e8e8e8"
        bg = status_colors.get(p.status, default_bg)
        self.ov.configure(fg_color=bg)

        # Header title
        self.lbl_nome.configure(text=f"Visão 360°  —  {p.name}")

        # Objective
        self.lbl_obj.configure(text=f"Objetivo: {p.objective or '—'}")

        # Format display date as dd/mm/yyyy
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

        created_str = fmt_date(p.created_at) if hasattr(p, 'created_at') else "—"
        due_str = fmt_date(p.due_date)

        # Stats
        days_left = "—"
        if p.due_date:
            try:
                due = datetime.strptime(str(p.due_date).split(" ")[0], "%Y-%m-%d")
                delta = (due - datetime.now()).days
                days_left = f"{delta} dias" if delta >= 0 else f"⚠ Atrasado {-delta}d"
            except Exception:
                pass

        # Update stats frame in-place (create labels once, reconfigure on every refresh)
        prio_colors = {
            "Máxima": "#E11D48", "Alta": "#F97316", "Média": "#EAB308", "Baixa": "#22C55E"
        }
        p_color = prio_colors.get(p.priority, "gray")
        if not hasattr(self, "_stats_lbl_prefix"):
            self._stats_lbl_prefix = ctk.CTkLabel(self.stats_frame, text="Prioridade: ", text_color="gray")
            self._stats_lbl_prefix.pack(side="left")
            self._stats_lbl_prio = ctk.CTkLabel(self.stats_frame, text="", font=ctk.CTkFont(weight="bold"))
            self._stats_lbl_prio.pack(side="left")
            self._stats_lbl_dates = ctk.CTkLabel(self.stats_frame, text="", text_color="gray")
            self._stats_lbl_dates.pack(side="left")
        self._stats_lbl_prio.configure(text=p.priority, text_color=p_color)
        self._stats_lbl_dates.configure(text=f" | Criado em: {created_str} | Prazo: {due_str} ({days_left})")
        
        self._update_card_text_colors(self.ov, bg)

        from database.repositories.entity_link_repository import EntityLinkRepository
        links = EntityLinkRepository().get_links_by_type('project', p.id, 'originated_from')
        if links:
            orig_idea = self.idea_service.get_by_id(links[0]['target_id'])
            if orig_idea:
                if len(links) > 1:
                    self.lbl_origin.configure(text=f"Origem: 💡 {orig_idea.title} (+{len(links)-1} ideias)")
                else:
                    self.lbl_origin.configure(text=f"Origem: 💡 Ideia: {orig_idea.title}")
                self.origin_frame.grid(row=3, column=0, sticky="w", padx=12, pady=(0, 8))
                self._update_card_text_colors(self.origin_frame, bg)
            else:
                self.origin_frame.grid_forget()
        else:
            self.origin_frame.grid_forget()

        # Refresh links panel
        self.links_panel.update_entity("project", p.id)

        from utils.instrumentation import PerfContext

        with PerfContext("Buscar tarefas", module="Visão 360", category="Banco"):
            if self.show_archived_tasks:
                tasks = [t for t in self.task_service.get_all_archived() if t.project_id == p.id]
            else:
                tasks = self.task_service.get_tasks_by_project(p.id)

        # Sort tasks
        with PerfContext("Processar tarefas", module="Visão 360", category="Processamento"):
            if self.task_sort_by == "Prazo":
                tasks.sort(key=lambda t: (t.due_date is None, t.due_date or ""))
            elif self.task_sort_by == "Status":
                status_order = {"Bloqueado": 0, "Pausado": 1, "Aguardando": 2, "Em Andamento": 3, "A Fazer": 4, "Backlog": 5, "Concluído": 6}
                tasks.sort(key=lambda t: status_order.get(t.status, 99))
            elif self.task_sort_by == "Prioridade":
                priority_order = {"Máxima": 0, "Alta": 1, "Média": 2, "Baixa": 3}
                tasks.sort(key=lambda t: priority_order.get(t.energy_level, 99))
            elif self.task_sort_by == "Nome":
                tasks.sort(key=lambda t: t.title.lower())
            elif self.task_sort_by == "Criação":
                tasks.sort(key=lambda t: t.id)

        with PerfContext("Buscar ideias", module="Visão 360", category="Banco"):
            if self.show_archived_ideas:
                ideas = [i for i in self.idea_service.get_all_archived() if i.project_id == p.id]
            else:
                ideas = [i for i in self.idea_service.get_all_active() if i.project_id == p.id]

        with PerfContext("Buscar notas", module="Visão 360", category="Banco"):
            if self.show_archived_notes:
                notes = [n for n in self.note_service.get_all_archived() if n.project_id == p.id]
            else:
                notes = self.note_service.get_by_project_id(p.id)
            
        # Cache total counts for lazy-load scroll check
        self._cached_tasks_count = len(tasks)
        self._cached_ideas_count = len(ideas)
        self._cached_notes_count = len(notes)

        # Sprint 1: Update KPIs, progress bar, filter chips
        self._all_tasks_cache = list(tasks)
        
        with PerfContext("Calcular KPIs", module="Visão 360", category="Processamento"):
            self._update_kpis(tasks)
            self._update_progress(tasks, p)
            self._update_filter_chip_counts(tasks)

        visible_tasks = tasks[:self.visible_tasks_limit]
        visible_ideas = ideas[:self.visible_ideas_limit]
        visible_notes = notes[:self.visible_notes_limit]

        # Preload next pending alerts for visible tasks
        with PerfContext("Buscar alertas", module="Visão 360", category="Banco"):
            self.alert_service.mark_overdue_alerts()
            self.tasks_alerts_dict = self.alert_service.get_next_alerts_for_entities('task', [t.id for t in visible_tasks])


        # Pré-calcular quais tarefas visíveis estão bloqueadas por dependência obrigatória incompleta.
        # Usa o mesmo algoritmo da Agenda (batch SQL) para garantir consistência entre as telas.
        self.blocked_task_ids = set()
        try:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT id, status FROM tasks WHERE deleted_at IS NULL")
                all_statuses = {row['id']: row['status'] for row in cursor.fetchall()}

                # JOIN garante que apenas dependências entre tarefas ativas são consideradas
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
                        dep_status = all_statuses.get(dep['depends_on_task_id'])
                        if dep_status and dep_status not in ('Concluído', 'Concludo'):
                            self.blocked_task_ids.add(tid)
                            break
        except Exception as e:
            pass
            # print(f"[Project360] Erro ao calcular blocked_task_ids: {e}")

        # Preload promotion links and target titles for visible ideas
        self.ideas_links_dict = {}
        self.target_projects_dict = {}
        self.target_tasks_dict = {}
        
        if visible_ideas:
            idea_ids = [i.id for i in visible_ideas]
            placeholders = ",".join("?" for _ in idea_ids)
            
            # 1. Fetch links
            query_links = f"""
                SELECT source_id, target_type, target_id 
                FROM entity_links 
                WHERE source_type = 'idea' 
                  AND relationship_type = 'promoted_to' 
                  AND source_id IN ({placeholders})
            """
            target_proj_ids = []
            target_task_ids = []
            with get_db_cursor() as cursor:
                cursor.execute(query_links, idea_ids)
                for row in cursor.fetchall():
                    sid = row['source_id']
                    if sid not in self.ideas_links_dict:
                        self.ideas_links_dict[sid] = []
                    self.ideas_links_dict[sid].append(dict(row))
                    if row['target_type'] == 'project':
                        target_proj_ids.append(row['target_id'])
                    elif row['target_type'] == 'task':
                        target_task_ids.append(row['target_id'])
            
            # 2. Fetch project names in bulk
            if target_proj_ids:
                proj_placeholders = ",".join("?" for _ in target_proj_ids)
                with get_db_cursor() as cursor:
                    cursor.execute(f"SELECT id, name FROM projects WHERE id IN ({proj_placeholders})", target_proj_ids)
                    self.target_projects_dict = {row['id']: row['name'] for row in cursor.fetchall()}

            # 3. Fetch task titles in bulk
            if target_task_ids:
                task_placeholders = ",".join("?" for _ in target_task_ids)
                with get_db_cursor() as cursor:
                    cursor.execute(f"SELECT id, title FROM tasks WHERE id IN ({task_placeholders})", target_task_ids)
                    self.target_tasks_dict = {row['id']: row['title'] for row in cursor.fetchall()}

        with PerfContext("Renderizar tarefas", module="Visão 360", category="Renderização"):
            self._render_tasks(self._filter_tasks(tasks[:self.visible_tasks_limit]))
        with PerfContext("Renderizar ideias", module="Visão 360", category="Renderização"):
            self._render_ideas(visible_ideas)
        with PerfContext("Renderizar notas", module="Visão 360", category="Renderização"):
            self._render_notes(visible_notes)

        duration = time.time() - start_time
        widgets_after = count_widgets_recursive(self.task_col) + count_widgets_recursive(self.idea_col) + count_widgets_recursive(self.note_col)
        loaded_count = len(visible_tasks) + len(visible_ideas) + len(visible_notes)
        log_perf_data("Project360View", "refresh", duration, widgets_before, widgets_after, loaded_items=loaded_count, trigger=trigger)
        
        w_hdr = count_widgets_recursive(getattr(self, 'header', None))
        w_task = count_widgets_recursive(getattr(self, 'task_col', None))
        w_idea = count_widgets_recursive(getattr(self, 'idea_col', None))
        w_note = count_widgets_recursive(getattr(self, 'note_col', None))
        w_info = count_widgets_recursive(getattr(self, 'info_col', None))
        w_filters = count_widgets_recursive(getattr(self, 'filter_frame', None))
        w_scroll = count_widgets_recursive(getattr(self, 'scroll', None))
        w_total = count_widgets_recursive(self)
        w_other = w_total - (w_hdr + w_task + w_idea + w_note + w_info + w_filters)
        
        # print(f'\n=== [AUDITORIA PROJECT360 WIDGETS] ===')
        # print(f'Headers/KPIs.... {w_hdr}')
        # print(f'Filtros......... {w_filters}')
        # print(f'Task Column..... {w_task}')
        # print(f'Idea Column..... {w_idea}')
        # print(f'Note Column..... {w_note}')
        # print(f'Info Sidebar.... {w_info}')
        # print(f'Outros.......... {w_other}')
        # print(f'TOTAL........... {w_total}\n')

    # ────────────────────────────────────────────────────────────
    # Sprint 1: Helpers de atualização (KPIs, progress, filtros)
    # ────────────────────────────────────────────────────────────

    def _update_kpis(self, tasks: list):
        """Atualiza os números dos chips de KPI."""
        today = datetime.now().date()
        total   = len(tasks)
        done    = sum(1 for t in tasks if t.status == "Concluído")
        active  = sum(1 for t in tasks if t.status == "Em Andamento")
        waiting = sum(1 for t in tasks if t.status == "Aguardando")
        backlog = sum(1 for t in tasks if t.status == "Backlog")
        blocked = sum(1 for t in tasks if t.status == "Bloqueado" or
                      t.id in getattr(self, 'blocked_task_ids', set()))
        overdue = sum(1 for t in tasks if t.due_date and t.status != "Concluído" and
                      str(t.due_date).split(" ")[0] < str(today))

        vals = {"total": total, "done": done, "active": active,
                "waiting": waiting, "backlog": backlog,
                "blocked": blocked, "overdue": overdue}
        for key, lbl in self._kpi_widgets.items():
            lbl.configure(text=str(vals.get(key, 0)))

    def _update_progress(self, tasks: list, project):
        """Atualiza a barra de progresso com cor dinâmica e textos."""
        total = len(tasks)
        done  = sum(1 for t in tasks if t.status == "Concluído")
        pct   = done / total if total > 0 else 0.0

        # Cor dinâmica por percentual
        if pct <= 0.30:
            bar_color = "#DC2626"   # vermelho
        elif pct <= 0.70:
            bar_color = "#2563EB"   # azul
        else:
            bar_color = "#16A34A"   # verde

        self.progress_bar.configure(progress_color=bar_color)
        self.progress_bar.set(pct)

        pct_int = int(round(pct * 100))
        self.lbl_progress_text.configure(
            text=f"{pct_int}%  •  {done} de {total} tarefas concluídas")

        # Prazo
        if project.due_date:
            try:
                due = datetime.strptime(str(project.due_date).split(" ")[0], "%Y-%m-%d")
                delta = (due - datetime.now()).days
                due_str = due.strftime("%d/%m/%Y")
                if delta >= 0:
                    prazo_txt = f"Prazo: {due_str}  •  {delta} dias restantes"
                else:
                    prazo_txt = f"Prazo: {due_str}  •  ⚠ Atrasado {-delta} dias"
            except Exception:
                prazo_txt = ""
        else:
            prazo_txt = "Sem prazo definido"
        self.lbl_prazo_text.configure(text=prazo_txt)

    def _update_filter_chip_counts(self, tasks: list):
        """Atualiza os rótulos dos chips de filtro com contadores."""
        today = datetime.now().date()
        blocked_ids = getattr(self, 'blocked_task_ids', set())
        counts = {
            "Todas":          len(tasks),
            "Hoje":           sum(1 for t in tasks if t.due_date and
                                  str(t.due_date).split(" ")[0] == str(today)),
            "Atrasadas":      sum(1 for t in tasks if t.due_date and t.status != "Concluído" and
                                  str(t.due_date).split(" ")[0] < str(today)),
            "Bloqueadas":     sum(1 for t in tasks if t.status == "Bloqueado" or t.id in blocked_ids),
            "Alta Prioridade":sum(1 for t in tasks if t.energy_level in ("Alta", "Máxima")),
        }
        for name, btn in self._filter_chip_btns.items():
            btn.configure(text=f"{name} {counts.get(name, 0)}")

    # ────────────────────────────────────────────────────────────
    # Sprint 3: Próximas Ações por score composto
    # ────────────────────────────────────────────────────────────

    def _task_score(self, task) -> int:
        """Score composto para priorizar tarefas no painel Próximas Ações.
        +100 bloqueada | +50 atrasada | +25 vence em 7 dias | +10 alta prioridade
        """
        today = datetime.now().date()
        score = 0
        blocked_ids = getattr(self, 'blocked_task_ids', set())
        if task.status == "Bloqueado" or task.id in blocked_ids:
            score += 100
        if task.due_date and task.status != "Concluído":
            try:
                due = datetime.strptime(str(task.due_date).split(" ")[0], "%Y-%m-%d").date()
                delta = (due - today).days
                if delta < 0:
                    score += 50
                elif delta <= 7:
                    score += 25
            except Exception:
                pass
        if task.energy_level in ("Alta", "Máxima"):
            score += 10
        return score

    def _update_next_actions(self, tasks: list):
        """Renderiza até 3 cards de Próximas Ações por score composto."""
        # Limpar body
        for w in self.next_actions_body.winfo_children():
            w.destroy()

        active = [t for t in tasks if t.status != "Concluído"]
        top3 = sorted(active, key=self._task_score, reverse=True)[:3]

        if not top3:
            ctk.CTkLabel(self.next_actions_body, text="✅ Nenhuma ação pendente urgente.",
                         text_color="gray", font=ctk.CTkFont(size=12, slant="italic")
                         ).grid(row=0, column=0, columnspan=3, pady=8)
            return

        dark = ctk.get_appearance_mode() == "Dark"
        for col_idx, t in enumerate(top3):
            status_color = self._STATUS_COLORS.get(t.status, "#374151")
            card_bg = ("#eef2ff" if not dark else "#1e2030")

            card = ctk.CTkFrame(self.next_actions_body, corner_radius=8,
                                fg_color=card_bg)
            card.grid(row=0, column=col_idx, sticky="ew", padx=6, pady=4)
            card.grid_columnconfigure(1, weight=1)

            # Faixa lateral esquerda
            ctk.CTkFrame(card, width=4, corner_radius=2,
                         fg_color=status_color).grid(
                row=0, column=0, rowspan=3, sticky="ns", padx=(4, 0), pady=4)

            ctk.CTkLabel(card, text=t.title,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         wraplength=160, justify="left", anchor="w"
                         ).grid(row=0, column=1, sticky="w", padx=(8, 8), pady=(8, 2))

            score = self._task_score(t)
            score_tip = []
            if score >= 100:
                score_tip.append("🚨 Bloqueada")
            if score % 100 >= 50:
                score_tip.append("⏰ Atrasada")
            elif score % 100 >= 25:
                score_tip.append("📅 Vence em breve")
            if t.energy_level in ("Alta", "Máxima"):
                score_tip.append(f"⚡ {t.energy_level}")

            ctk.CTkLabel(card, text=" • ".join(score_tip) if score_tip else t.status,
                         font=ctk.CTkFont(size=11),
                         text_color="gray", anchor="w"
                         ).grid(row=1, column=1, sticky="w", padx=(8, 8))

            if t.due_date:
                ctk.CTkLabel(card, text=f"📅 {self._fmt(t.due_date)}",
                             font=ctk.CTkFont(size=11), text_color="gray", anchor="w"
                             ).grid(row=2, column=1, sticky="w", padx=(8, 8), pady=(0, 8))
            else:
                ctk.CTkLabel(card, text="Sem prazo",
                             font=ctk.CTkFont(size=11), text_color="gray", anchor="w"
                             ).grid(row=2, column=1, sticky="w", padx=(8, 8), pady=(0, 8))

            # Clique abre detalhe
            for child in card.winfo_children():
                if not isinstance(child, ctk.CTkButton):
                    child.bind("<Button-1>", lambda e, t=t: self._open_task_detail(t))
            card.bind("<Button-1>", lambda e, t=t: self._open_task_detail(t))

    def _card_enter(self, card):
        # Debounced Hover: Previne lag extremo ao scrollar e o mouse cruzar múltiplos widgets
        card._is_hovered = True
        if hasattr(card, '_leave_after_id'):
            card.after_cancel(card._leave_after_id)
            delattr(card, '_leave_after_id')
        
        if not hasattr(card, '_enter_after_id'):
            def apply_hover():
                if getattr(card, '_is_hovered', False):
                    try:
                        card.configure(fg_color=card.hover_bg)
                        # self._update_card_text_colors(card, card.hover_bg) # Omitindo cálculo caro de cor de texto para extrema performance
                    except: pass
                if hasattr(card, '_enter_after_id'):
                    delattr(card, '_enter_after_id')
            card._enter_after_id = card.after(25, apply_hover)

    def _card_leave(self, card):
        card._is_hovered = False
        if hasattr(card, '_enter_after_id'):
            card.after_cancel(card._enter_after_id)
            delattr(card, '_enter_after_id')
            
        def apply_leave():
            if not getattr(card, '_is_hovered', False):
                try:
                    card.configure(fg_color=card.bg)
                    # self._update_card_text_colors(card, card.bg)
                except: pass
            if hasattr(card, '_leave_after_id'):
                delattr(card, '_leave_after_id')
                
        if not hasattr(card, '_leave_after_id'):
            card._leave_after_id = card.after(25, apply_leave)

    def _show_task_menu(self, event, card):
        if getattr(card.item, 'is_archived', False):
            return
        from gui.components.context_menu import ContextMenu
        t = card.item
        menu = ContextMenu(card)
        menu.add_command("✏️  Editar",      command=lambda: self._edit_task(t))
        menu.add_separator()
        menu.add_header("Alterar Status")
        menu.add_command("📥  Backlog",       command=lambda: self._set_task_status(t, "Backlog"),
                         enabled=(t.status != "Backlog"))
        menu.add_command("📌  A Fazer",       command=lambda: self._set_task_status(t, "A Fazer"),
                         enabled=(t.status != "A Fazer"))
        menu.add_command("▶️  Em Andamento", command=lambda: self._set_task_status(t, "Em Andamento"),
                         enabled=(t.status != "Em Andamento"))
        menu.add_command("⏸️  Pausado",        command=lambda: self._set_task_status(t, "Pausado"),
                         enabled=(t.status != "Pausado"))
        menu.add_command("⏳  Aguardando",   command=lambda: self._set_task_status(t, "Aguardando"),
                         enabled=(t.status != "Aguardando"))
        menu.add_command("🚫  Bloqueado",    command=lambda: self._set_task_status(t, "Bloqueado"),
                         enabled=(t.status != "Bloqueado"))
        menu.add_command("✅  Concluir",     command=lambda: self._set_task_status(t, "Concluído"),
                         enabled=(t.status != "Concluído"))
        menu.add_separator()
        menu.add_command("🔔  Criar Alerta...", command=lambda: self._open_alerts_manager(t))
        menu.add_separator()
        menu.add_command("📦  Arquivar",      command=lambda: self._archive_task(t))
        menu.add_command("🗑️  Excluir",       command=lambda: self._delete_task(t), danger=True)
        menu.tk_popup(event.x_root, event.y_root)

    # Paletas constantes — definidas uma vez, reutilizadas em todos os cards
    _STATUS_COLORS = {
        "Backlog": "#374151", "A Fazer": "#1E40AF", "Em Andamento": "#0369A1",
        "Pausado": "#B45309", "Aguardando": "#6D28D9",
        "Bloqueado": "#B91C1C", "Concluído": "#15803D",
    }
    _STATUS_HOVER_COLORS = {
        "Backlog": "#4B5563", "A Fazer": "#2563EB", "Em Andamento": "#0284C7",
        "Pausado": "#D97706", "Aguardando": "#7C3AED",
        "Bloqueado": "#DC2626", "Concluído": "#16A34A",
    }
    _PRIO_COLORS = {
        "Máxima": "#E11D48", "Alta": "#F97316", "Média": "#EAB308", "Baixa": "#22C55E"
    }

    def _show_idea_menu(self, event, card):
        if getattr(card.item, 'is_archived', False):
            return
        from gui.components.context_menu import ContextMenu
        idea = card.item
        menu = ContextMenu(card)
        menu.add_command("✏️  Editar", command=lambda: self._edit_idea(idea))
        menu.add_separator()
        menu.add_header("Promover")
        menu.add_command("📁  Criar Projeto desta Ideia", command=lambda: self._promote_idea_to_project(idea))
        menu.add_command("📋  Criar Tarefa desta Ideia",  command=lambda: self._promote_idea_to_task(idea))
        menu.tk_popup(event.x_root, event.y_root)

    def _show_note_menu(self, event, card):
        if getattr(card.item, 'is_archived', False):
            return
        from gui.components.context_menu import ContextMenu
        n = card.item
        menu = ContextMenu(card)
        menu.add_command("✏️  Editar",    command=lambda: self._edit_note(n))
        menu.add_command("⭐  Favoritar",  command=lambda: self._toggle_fav_note(n))
        menu.add_separator()
        menu.add_header("Gerenciar")
        menu.add_command("📦  Arquivar",   command=lambda: self._archive_note(n))
        menu.add_command("🗑️  Excluir",    command=lambda: self._delete_note(n), danger=True)
        menu.tk_popup(event.x_root, event.y_root)

    # Ordem dos grupos: Bloqueado → Em Andamento → Aguardando → Pausado → A Fazer → Backlog → Concluído
    _GROUP_ORDER = ["Bloqueado", "Em Andamento", "Aguardando", "Pausado", "A Fazer", "Backlog", "Concluído"]

    # Cores dos badges de status
    _STATUS_BADGE_BG = {
        "Backlog":      "#374151", "A Fazer":      "#1E40AF",
        "Em Andamento": "#0369A1", "Pausado":      "#B45309",
        "Aguardando":   "#6D28D9", "Bloqueado":    "#B91C1C",
        "Concluído":    "#15803D",
    }

    def _render_tasks(self, tasks):
        pool_created = 0
        pool_reused = 0
        if not hasattr(self.task_col, "lbl_empty"):
            self.task_col.lbl_empty = ctk.CTkLabel(self.task_col, text="Nenhuma tarefa vinculada.", text_color="gray", font=ctk.CTkFont(size=12, slant="italic"))

        if not hasattr(self, '_task_groups_ui'):
            self._task_groups_ui = {}
            dark = ctk.get_appearance_mode() == "Dark"
            hdr_bg = ("#2b2b3b" if dark else "#ebebf5")
            
            for status_name in self._GROUP_ORDER:
                stripe_color = self._STATUS_COLORS.get(status_name, "#374151")
                grp_hdr = ctk.CTkFrame(self.task_col, fg_color=hdr_bg, corner_radius=6)
                
                faixa_hdr = ctk.CTkFrame(grp_hdr, width=4, height=22, corner_radius=2, fg_color=stripe_color)
                faixa_hdr.pack(side="left", padx=(6, 0), pady=5, fill="y")
                faixa_hdr.pack_propagate(False)

                lbl_grp = ctk.CTkLabel(grp_hdr, text="", font=ctk.CTkFont(size=12, weight="bold"), anchor="w")
                lbl_grp.pack(side="left", padx=8, pady=5)
                
                grp_body = ctk.CTkFrame(self.task_col, fg_color="transparent")
                grp_body.grid_columnconfigure((0, 1), weight=1, uniform="task_cols")
                
                self._task_groups_ui[status_name] = {
                    'hdr': grp_hdr,
                    'lbl': lbl_grp,
                    'body': grp_body,
                    'cards': [],
                    'seps': [],
                    'btn_more': None
                }
                
                # Setup binds with a default factory to capture current references
                def make_toggle(sn=status_name, hdr=grp_hdr, body=grp_body, lbl=lbl_grp):
                    def _toggle_group(e=None):
                        proj_key = str(getattr(self.current_project, 'id', 0))
                        sk = f"{proj_key}_{sn}"
                        cur = Project360View._group_states.get(sk, True)
                        nxt = not cur
                        Project360View._group_states[sk] = nxt
                        # arrow text update happens in refresh loop too, but we need it here
                        cur_text = lbl.cget("text")
                        arr = "▼" if nxt else "▶"
                        if len(cur_text) > 1:
                            lbl.configure(text=f"{arr}{cur_text[1:]}")
                        if nxt:
                            body.pack(fill="x", after=hdr)
                        else:
                            body.pack_forget()
                    return _toggle_group

                grp_hdr.bind("<Button-1>", make_toggle())
                lbl_grp.bind("<Button-1>", make_toggle())
                grp_hdr.configure(cursor="hand2")
                lbl_grp.configure(cursor="hand2")

        # Renderização Inteligente (Virtual DOM Diffing)
        self.task_col.lbl_empty.pack_forget()

        if not tasks:
            for ui in self._task_groups_ui.values():
                ui['hdr'].pack_forget()
                ui['body'].pack_forget()
            self.task_col.lbl_empty.pack(pady=14)
            return

        blocked_task_ids = getattr(self, 'blocked_task_ids', set())
        dark = ctk.get_appearance_mode() == "Dark"
        card_bg     = "#1e1e2e" if dark else "#f8f9fc"
        card_hov    = "#2a2a3e" if dark else "#eef0f8"
        sep_col     = "#2e2e48" if dark else "#dde1f0"

        # Agrupar por status
        groups = {s: [] for s in self._GROUP_ORDER}
        for t in tasks:
            grp = t.status if t.status in groups else "Backlog"
            groups[grp].append(t)

        proj_key = str(getattr(self.current_project, 'id', 0))

        for status_name in self._GROUP_ORDER:
            group_tasks_all = groups[status_name]
            ui = self._task_groups_ui[status_name]
            if not group_tasks_all:
                ui['hdr'].pack_forget()
                ui['body'].pack_forget()
                continue
            
            limit = self._group_limits.get(status_name, 10)
            group_tasks = group_tasks_all[:limit]
            has_more = len(group_tasks_all) > limit

            ui = self._task_groups_ui[status_name]
            state_key = f"{proj_key}_{status_name}"
            is_open = Project360View._group_states.get(state_key, True)
            arrow   = "▼" if is_open else "▶"
            
            ui['lbl'].configure(text=f"{arrow}  {status_name}  ({len(group_tasks)})")
            ui['hdr'].pack(fill="x", pady=(3, 0))
            if is_open:
                ui['body'].pack(fill="x", after=ui['hdr'])

            total_in_group = len(group_tasks)
            cards_pool = ui['cards']
            seps_pool = ui['seps']
            grp_body = ui['body']

            for idx, t in enumerate(group_tasks):
                row_i = idx // 2
                col_i = idx % 2
                is_last_odd = (idx == total_in_group - 1) and (total_in_group % 2 == 1)

                # --- Separadores ---
                if col_i == 0 and row_i > 0:
                    sep_idx = row_i - 1
                    if sep_idx >= len(seps_pool):
                        sep = ctk.CTkFrame(grp_body, height=1, fg_color=sep_col, corner_radius=0)
                        seps_pool.append(sep)
                    else:
                        sep = seps_pool[sep_idx]
                        sep.configure(fg_color=sep_col)
                    sep.grid(row=row_i * 2 - 1, column=0, columnspan=2, sticky="ew", padx=4, pady=0)

                # --- Card ---
                status_color = self._STATUS_COLORS.get(t.status, "#374151")
                prio_color   = self._PRIO_COLORS.get(t.energy_level, "gray")
                is_blocked   = (t.id in blocked_task_ids or t.status == "Bloqueado")

                if idx >= len(cards_pool):
                    card = ctk.CTkFrame(grp_body, fg_color=card_bg, corner_radius=6)
                    card.is_task_card = True
                    card.grid_columnconfigure(1, weight=1)
                    
                    faixa = ctk.CTkFrame(card, width=4, height=10, corner_radius=2)
                    faixa.grid(row=0, column=0, rowspan=3, sticky="ns", padx=(4, 0), pady=4)
                    card.faixa = faixa

                    card.lbl_title = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=13, weight="bold"), wraplength=260, justify="left", anchor="w")
                    card.lbl_title.grid(row=0, column=1, columnspan=2, sticky="w", padx=(8, 8), pady=(6, 1))

                    meta_f = ctk.CTkFrame(card, fg_color="transparent")
                    meta_f.grid(row=1, column=1, columnspan=2, sticky="w", padx=(8, 8), pady=(0, 1))
                    
                    card.lbl_status = ctk.CTkLabel(meta_f, font=ctk.CTkFont(size=10), text_color="white", corner_radius=6, height=16, padx=5, pady=1)
                    card.lbl_status.pack(side="left", padx=(0, 5))
                    
                    card.lbl_due = ctk.CTkLabel(meta_f, font=ctk.CTkFont(size=11), height=16, text_color="gray")
                    card.lbl_due.pack(side="left", padx=(0, 5))
                    
                    card.lbl_prio = ctk.CTkLabel(meta_f, font=ctk.CTkFont(size=11, weight="bold"), height=16)
                    card.lbl_prio.pack(side="left", padx=(0, 5))

                    card.lbl_alert = ctk.CTkLabel(card, text="", height=16)
                    card.lbl_alert.grid(row=0, column=2, sticky="ne", padx=(0, 8), pady=(6, 1))

                    btn_f = ctk.CTkFrame(card, fg_color="transparent")
                    btn_f.grid(row=2, column=1, columnspan=2, sticky="e", padx=(8, 8), pady=(1, 6))

                    card.btn_del = ctk.CTkButton(btn_f, text="🗑 Excluir", width=65, height=20, fg_color="#8c2b2b", hover_color="#661e1e")
                    card.btn_del.pack(side="right", padx=(3, 0))

                    card.btn_arq = ctk.CTkButton(btn_f, text="", width=75, height=20)
                    card.btn_arq.pack(side="right")
                    
                    pool_created += 1
                    cards_pool.append(card)

                if idx < len(cards_pool) - pool_created:
                    pool_reused += 1
                card = cards_pool[idx]
                col_span = 2 if is_last_odd else 1
                card.grid(row=row_i * 2, column=col_i, columnspan=col_span, sticky="nsew", padx=2, pady=2)
                card.item = t
                card.bg = card_bg
                card.hover_bg = card_hov
                card.configure(fg_color=card_bg)
                
                card.faixa.configure(fg_color=status_color)

                title_text = t.title
                if is_blocked: title_text = "⛔ " + title_text
                elif t.status == "Pausado": title_text = "⏸ " + title_text
                elif t.status == "Aguardando": title_text = "⏳ " + title_text
                card.lbl_title.configure(text=title_text)

                badge_bg = self._STATUS_BADGE_BG.get(t.status, "#374151")
                card.lbl_status.configure(text=t.status, fg_color=badge_bg)

                if t.due_date:
                    card.lbl_due.configure(text=f"📅 {self._fmt(t.due_date)}")
                    card.lbl_due.pack(side="left", padx=(0, 5))
                else:
                    card.lbl_due.pack_forget()

                if t.energy_level:
                    card.lbl_prio.configure(text=f"⚡ {t.energy_level}", text_color=prio_color)
                    card.lbl_prio.pack(side="left", padx=(0, 5))
                else:
                    card.lbl_prio.pack_forget()

                next_alert = getattr(self, 'tasks_alerts_dict', {}).get(t.id)
                if next_alert:
                    try:
                        is_overdue = next_alert.status == 'overdue'
                        is_today = next_alert.alert_date == datetime.now().strftime("%Y-%m-%d")
                        dt = datetime.strptime(next_alert.alert_date, "%Y-%m-%d")
                        date_str = dt.strftime('%d/%m')
                        
                        if is_overdue:
                            card.lbl_alert.configure(text="🔔 Atrasado", text_color="#ef4444", font=ctk.CTkFont(size=11, weight="bold"))
                        elif is_today:
                            card.lbl_alert.configure(text=f"🔔 {date_str}", text_color="#f97316", font=ctk.CTkFont(size=11, weight="bold"))
                        else:
                            card.lbl_alert.configure(text=f"🔔 {date_str}", text_color="gray", font=ctk.CTkFont(size=11, weight="normal"))
                        card.lbl_alert.grid(row=0, column=2, sticky="ne", padx=(0, 8), pady=(6, 1))
                    except Exception:
                        card.lbl_alert.grid_forget()
                else:
                    card.lbl_alert.grid_forget()

                card.btn_del.configure(command=lambda t=t: self._delete_task(t))
                if getattr(t, 'is_archived', False):
                    card.btn_arq.configure(text="Restaurar", fg_color="#2B8C52", hover_color="#1E663B", command=lambda t=t: self._restore_task(t))
                else:
                    card.btn_arq.configure(text="📦 Arquivar", fg_color="#2b5c8c", hover_color="#1e4066", command=lambda t=t: self._archive_task(t))

                # Redefine binds for current references
                self._bind_all_children(card, "<Button-1>", lambda e, c=card: self._open_task_detail(c.item))
                self._bind_all_children(card, "<Button-3>", lambda e, c=card: self._show_task_menu(e, c))
                self._bind_all_children(card, "<Enter>", lambda e, c=card: self._card_enter(c))
                self._bind_all_children(card, "<Leave>", lambda e, c=card: self._card_leave(c))

            # Hide excess cards for this group
            for c_idx in range(total_in_group, len(cards_pool)):
                cards_pool[c_idx].grid_forget()
            
            # Hide excess separators
            needed_seps = max(0, (total_in_group - 1) // 2) if total_in_group > 0 else 0
            for s_idx in range(needed_seps, len(seps_pool)):
                seps_pool[s_idx].grid_forget()


        pool_hidden = 0
        for ui in self._task_groups_ui.values():
            # SPRINT 2.1: Object Pool Cap (Max 30 cards per group)
            if len(ui['cards']) > 30:
                excess = ui['cards'][30:]
                for c in excess:
                    if not c.winfo_ismapped():
                        try: c.destroy()
                        except: pass
                ui['cards'] = ui['cards'][:30]

            for c in ui['cards']:
                if not c.winfo_ismapped():
                    pool_hidden += 1

            if has_more:
                if ui.get('btn_more') is None:
                    import customtkinter as ctk_temp
                    ui['btn_more'] = ctk_temp.CTkButton(
                        ui['body'], text="", width=200, fg_color="#374151", 
                        hover_color="#4b5563", command=lambda s=status_name: self._load_more_tasks(s)
                    )
                ui['btn_more'].configure(text=f"Mostrar mais ({len(group_tasks_all) - limit} ocultas)")
                ui['btn_more'].grid(row=(len(group_tasks) // 2) + 1, column=0, columnspan=2, pady=(10, 5))
            else:
                if ui.get('btn_more'):
                    ui['btn_more'].grid_forget()

        # print(f'[POOL] Project360 Refresh | Cards reutilizados: {pool_reused} | Cards criados: {pool_created} | Cards ocultados: {pool_hidden}')

    def _render_ideas(self, ideas):
        existing_cards = [w for w in self.idea_col.winfo_children() if isinstance(w, ctk.CTkFrame) and getattr(w, "is_idea_card", False)]
        for c in existing_cards:
            c.pack_forget()
            
        if hasattr(self.idea_col, "lbl_empty"):
            self.idea_col.lbl_empty.pack_forget()
            
        if not ideas:
            self.idea_col.configure(height=120)
            if not hasattr(self.idea_col, "lbl_empty"):
                self.idea_col.lbl_empty = ctk.CTkLabel(self.idea_col, text="Nenhuma ideia vinculada.", text_color="gray", font=ctk.CTkFont(size=12, slant="italic"))
            self.idea_col.lbl_empty.pack(pady=45)
            return

        for idx, idea in enumerate(ideas):
            dark = ctk.get_appearance_mode() == "Dark"
            bg = "#2b2b2b" if dark else "#e8e8e8"
            hover_bg = "#3f3f3f" if dark else "#d0d0d0"
            
            if idx < len(existing_cards):
                card = existing_cards[idx]
                card.pack(fill="x", pady=3)
            else:
                card = ctk.CTkFrame(self.idea_col, fg_color=bg, corner_radius=8)
                card.is_idea_card = True
                card.pack(fill="x", pady=3)
                card.grid_columnconfigure(0, weight=1)
                
                card.top = ctk.CTkFrame(card, fg_color="transparent")
                card.top.pack(fill="x", padx=10, pady=(8, 2))
                
                card.lbl_title = ctk.CTkLabel(card.top, text="", font=ctk.CTkFont(weight="bold"), wraplength=200, justify="left", anchor="w")
                card.lbl_title.pack(side="left", fill="x", expand=True)
                
                card.lbl_meta = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
                card.lbl_meta.pack(padx=10, pady=(0, 4), anchor="w")
                
                card.btn_frame = ctk.CTkFrame(card, fg_color="transparent")
                card.btn_frame.pack(fill="x", padx=10, pady=(0, 8))
                
                card.btn_del = ctk.CTkButton(card.btn_frame, text="🗑 Excluir", width=60, height=20, fg_color="#8c2b2b", hover_color="#661e1e")
                card.btn_del.pack(side="right", padx=(5, 0))
                card.btn_arq = ctk.CTkButton(card.btn_frame, text="📦 Arquivar", width=60, height=20, fg_color="#2b5c8c", hover_color="#1e4066")
                card.btn_arq.pack(side="right")
                
                self._bind_all_children(card, "<Button-1>", lambda e, c=card: self._edit_idea(c.item))
                self._bind_all_children(card, "<Button-3>", lambda e, c=card: self._show_idea_menu(e, c))
                self._bind_all_children(card, "<Enter>", lambda e, c=card: self._card_enter(c))
                self._bind_all_children(card, "<Leave>", lambda e, c=card: self._card_leave(c))

                
            card.item = idea
            card.bg = bg
            card.hover_bg = hover_bg
            card.configure(fg_color=bg)
            
            card.lbl_title.configure(text=idea.title)
            
            # Promotion badge from pre-calculated dictionaries
            links = getattr(self, 'ideas_links_dict', {}).get(idea.id, [])
            badge_text = None
            if links:
                badge_parts = []
                for link in links:
                    if link['target_type'] == 'project':
                        proj_name = getattr(self, 'target_projects_dict', {}).get(link['target_id'], "Projeto Inexistente")
                        badge_parts.append(f"📁 Virou Projeto: {proj_name}")
                    elif link['target_type'] == 'task':
                        tsk_title = getattr(self, 'target_tasks_dict', {}).get(link['target_id'], "Tarefa Inexistente")
                        badge_parts.append(f"✅ Virou Tarefa: {tsk_title}")
                if badge_parts:
                    badge_text = " | ".join(badge_parts)
 
            if badge_text:
                if not hasattr(card, "lbl_badge"):
                    card.lbl_badge = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=11, weight="bold"), text_color="#2B8C52", anchor="w")
                    card.lbl_badge.bind("<Button-1>", lambda e, c=card: self._edit_idea(c.item))
                    card.lbl_badge.bind("<Button-3>", lambda e, c=card: self._show_idea_menu(e, c))
                    card.lbl_badge.bind("<Enter>", lambda e, c=card: self._card_enter(c))
                    card.lbl_badge.bind("<Leave>", lambda e, c=card: self._card_leave(c))
                card.lbl_badge.configure(text=badge_text)
                card.lbl_badge.pack(padx=10, pady=(0, 4), anchor="w")
            else:
                if hasattr(card, "lbl_badge"):
                    card.lbl_badge.pack_forget()
            
            meta_parts = []
            if idea.category:
                meta_parts.append(f"📂 {idea.category}")
            if idea.priority:
                meta_parts.append(f"⚡{idea.priority}")
            card.lbl_meta.configure(text="  ".join(meta_parts))
            
            card.btn_del.configure(command=lambda: self._delete_idea(card.item))
            
            if getattr(idea, 'is_archived', False):
                card.btn_arq.configure(text="Restaurar", fg_color="#2B8C52", hover_color="#1E663B", command=lambda: self._restore_idea(card.item))
            else:
                card.btn_arq.configure(text="📦 Arquivar", fg_color="#2b5c8c", hover_color="#1e4066", command=lambda: self._archive_idea(card.item))
                
            self._update_card_text_colors(card, bg)

        # Dynamically adjust height up to 5 items before scrolling
        num_items = len(ideas)
        new_height = max(1, min(5, num_items)) * 105 + 15
        self.idea_col.configure(height=new_height)

    def _render_notes(self, notes):
        existing_cards = [w for w in self.note_col.winfo_children() if isinstance(w, ctk.CTkFrame) and getattr(w, "is_note_card", False)]
        for c in existing_cards:
            c.pack_forget()
            
        if hasattr(self.note_col, "lbl_empty"):
            self.note_col.lbl_empty.pack_forget()
            
        if not notes:
            self.note_col.configure(height=120)
            if not hasattr(self.note_col, "lbl_empty"):
                self.note_col.lbl_empty = ctk.CTkLabel(self.note_col, text="Nenhuma nota vinculada.", text_color="gray", font=ctk.CTkFont(size=12, slant="italic"))
            self.note_col.lbl_empty.pack(pady=45)
            return

        for idx, n in enumerate(notes):
            dark = ctk.get_appearance_mode() == "Dark"
            bg = "#2b2b2b" if dark else "#e8e8e8"
            hover_bg = "#3f3f3f" if dark else "#d0d0d0"
            
            if idx < len(existing_cards):
                card = existing_cards[idx]
                card.pack(fill="x", pady=3)
            else:
                card = ctk.CTkFrame(self.note_col, fg_color=bg, corner_radius=8)
                card.is_note_card = True
                card.pack(fill="x", pady=3)
                card.grid_columnconfigure(0, weight=1)
                
                card.top = ctk.CTkFrame(card, fg_color="transparent")
                card.top.pack(fill="x", padx=10, pady=(8, 2))
                
                card.lbl_title = ctk.CTkLabel(card.top, text="", font=ctk.CTkFont(weight="bold"), wraplength=200, justify="left", anchor="w")
                card.lbl_title.pack(side="left", fill="x", expand=True)
                
                card.lbl_meta = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=11), text_color="gray", anchor="w", wraplength=220)
                card.lbl_meta.pack(padx=10, pady=(0, 4), anchor="w")
                
                card.btn_frame = ctk.CTkFrame(card, fg_color="transparent")
                card.btn_frame.pack(fill="x", padx=10, pady=(0, 8))
                
                card.btn_del = ctk.CTkButton(card.btn_frame, text="🗑 Excluir", width=60, height=20, fg_color="#8c2b2b", hover_color="#661e1e")
                card.btn_del.pack(side="right", padx=(5, 0))
                card.btn_arq = ctk.CTkButton(card.btn_frame, text="📦 Arquivar", width=60, height=20, fg_color="#2b5c8c", hover_color="#1e4066")
                card.btn_arq.pack(side="right")
                
                self._bind_all_children(card, "<Button-1>", lambda e, c=card: self._edit_note(c.item))
                self._bind_all_children(card, "<Button-3>", lambda e, c=card: self._show_note_menu(e, c))
                self._bind_all_children(card, "<Enter>", lambda e, c=card: self._card_enter(c))
                self._bind_all_children(card, "<Leave>", lambda e, c=card: self._card_leave(c))

                
            card.item = n
            card.bg = bg
            card.hover_bg = hover_bg
            card.configure(fg_color=bg)
            
            preview = n.content.strip().split("\n")[0][:30] if n.content.strip() else "(Nota vazia)"
            if len(n.content) > 30:
                preview += "…"
            star = "⭐ " if n.is_favorite else ""
            card.lbl_title.configure(text=f"{star}{preview}")
            
            if n.content and len(n.content) > 50:
                snippet = n.content[50:100]
                if len(n.content) > 100:
                    snippet += "…"
                card.lbl_meta.configure(text=snippet)
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
        self.note_col.configure(height=new_height)

    def _bind_all_children(self, widget, event, callback):
        """Recursively bind an event to a widget and ALL its children."""
        if isinstance(widget, ctk.CTkButton):
            return
        widget.bind(event, callback)
        for child in widget.winfo_children():
            self._bind_all_children(child, event, callback)

    def _close_task_detail(self):
        """Destroi o TaskDetailView aberto (se houver) e restaura o scroll do projeto."""
        if hasattr(self, 'task_detail'):
            try:
                self.task_detail.destroy()
            except Exception:
                pass
            del self.task_detail
        # Sempre restaura o scroll, mesmo que não havia task_detail
        try:
            self.scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=6)
        except Exception:
            pass

    def _open_task_detail(self, task: Task):
        # Fecha qualquer detalhe anterior antes de abrir o novo
        self._close_task_detail()
        # Esconde o scroll e abre o TaskDetailView
        self.scroll.grid_forget()
        self.task_detail = TaskDetailView(self, task, go_back_callback=self._back_to_project)
        self.task_detail.grid(row=1, column=0, sticky="nsew", padx=10, pady=6)

    def _back_to_project(self):
        self._close_task_detail()
        self.refresh()


    def _edit_note(self, n: Note):
        def on_save(edited):
            self.note_service.update(edited)
            event_bus.emit("entity_updated")
        QuickNoteEditDialog(self.winfo_toplevel(), n, on_save=on_save)

    def _edit_task(self, task: Task):
        from gui.views.tasks import TaskDialog
        orig_task = copy.deepcopy(task)
        def on_save(edited_task, is_new):
            self.task_service.update_task(edited_task, orig_task)
            event_bus.emit("entity_updated")
        TaskDialog(self.winfo_toplevel(), task=task, on_save=on_save)

    def _set_task_status(self, task: Task, new_status: str):
        self.task_service.change_status(task, new_status)
        event_bus.emit("entity_updated")

    def _archive_task(self, task: Task):
        if messagebox.askyesno("Arquivar", "Deseja arquivar esta tarefa?"):
            self.task_service.archive_task(task.id)
            event_bus.emit("entity_updated")

    def _delete_task(self, task: Task):
        if messagebox.askyesno("Excluir", "Deseja enviar esta tarefa para a lixeira?"):
            self.task_service.soft_delete_task(task.id)
            event_bus.emit("entity_updated")

    def _restore_task(self, task: Task):
        if messagebox.askyesno("Restaurar", "Restaurar esta tarefa?"):
            self.task_service.restore_task(task.id)
            event_bus.emit("entity_updated")

    def _edit_idea(self, idea: Idea):
        """Open the quick‑edit dialog for an Idea and persist changes."""
        orig = copy.deepcopy(idea)
        def on_save(edited):
            self.idea_service.update_idea(edited, orig)
            event_bus.emit("entity_updated")
        QuickIdeaEditDialog(self.winfo_toplevel(), idea, on_save=on_save)

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

    def _toggle_fav_note(self, n: Note):
        n.is_favorite = not n.is_favorite
        self.note_service.update(n)
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
    def toggle_archived_tasks(self):
        self.show_archived_tasks = not self.show_archived_tasks
        if self.show_archived_tasks:
            self.btn_toggle_tasks.configure(fg_color="#1f538d", hover_color="#14375e")
        else:
            self.btn_toggle_tasks.configure(fg_color="transparent")
        self.refresh()
        
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

    # ── Edit project ─────────────────────────
    def edit_project(self):
        if not self.current_project:
            return
        from gui.views.projects import ProjectDialog
        orig = copy.deepcopy(self.current_project)
        def on_save(edited, is_new):
            self.project_service.update_project(edited, orig)
            event_bus.emit("entity_updated")
        ProjectDialog(self.winfo_toplevel(), project=self.current_project, on_save=on_save)

    # ── Add shortcuts ────────────────────────
    def add_task(self):
        if not self.current_project:
            return
        from gui.views.tasks import TaskDialog
        dummy = Task(title="", project_id=self.current_project.id)
        def on_save(task, is_new):
            self.task_service.create_task(
                title=task.title, context=task.context,
                energy_level=task.energy_level, status=task.status,
                project_id=task.project_id,
                due_date=task.due_date, alert_date=task.alert_date,
                alert_message=task.alert_message
            )
            event_bus.emit("entity_updated")
        TaskDialog(self.winfo_toplevel(), task=dummy, on_save=on_save)

    def add_idea(self):
        if not self.current_project:
            return
        dummy = Idea(title="", project_id=self.current_project.id)
        def on_save(i):
            self.idea_service.create_idea(
                title=i.title, description=i.description,
                project_id=i.project_id, task_id=i.task_id,
                category=i.category, interest_level=i.interest_level,
                status=i.status, priority=i.priority, next_review_date=i.next_review_date
            )
            event_bus.emit("entity_updated")
        QuickIdeaEditDialog(self.winfo_toplevel(), dummy, on_save=on_save)

    def add_note(self):
        """Abre o dialog e só persiste se o usuário confirmar. Expande a seção automaticamente."""
        if not self.current_project:
            return
        draft = Note(content="", project_id=self.current_project.id)
        def on_save(edited):
            if edited.id:
                self.note_service.update(edited)
            else:
                self.note_service.create(edited)
            # Garante que a seção de notas está visível após criação
            if not self._notes_expanded:
                self._toggle_notes()
            event_bus.emit("entity_updated")
        QuickNoteEditDialog(self.winfo_toplevel(), draft, on_save=on_save)

    # ── Helpers ──────────────────────────────
    def _clear(self, frame):
        for w in frame.winfo_children():
            w.destroy()

    def _empty_label(self, frame, text):
        ctk.CTkLabel(frame, text=text, text_color="gray",
                     font=ctk.CTkFont(size=12, slant="italic")).pack(pady=14)

    def _fmt(self, date_str) -> str:
        """Formats YYYY-MM-DD to DD/MM/YYYY."""
        try:
            parts = str(date_str).split(" ")[0].split("-")
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            pass
        return str(date_str)

    # Cache de brightness por cor de fundo (evita hex parsing repetido)
    _BRIGHTNESS_CACHE: dict = {}

    def _update_card_text_colors(self, card, bg_color):
        """Atualiza as cores de texto do card. Para task/idea/note cards usa atributos
        diretos (sem traversal recursivo). Para o overview card usa traversal completo."""
        # Compute text colors (cacheado por bg_color)
        if bg_color not in Project360View._BRIGHTNESS_CACHE:
            is_dark = True
            try:
                h = bg_color.lstrip('#')
                if len(h) == 6:
                    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                    is_dark = (r * 299 + g * 587 + b * 114) / 1000 < 128
            except Exception:
                pass
            Project360View._BRIGHTNESS_CACHE[bg_color] = is_dark
        is_dark = Project360View._BRIGHTNESS_CACHE[bg_color]
        text_color = "white" if is_dark else "black"
        meta_color = "#aaaaaa" if is_dark else "#555555"

        # Fast path: task/idea/note cards têm atributos conhecidos
        if getattr(card, 'is_task_card', False) or getattr(card, 'is_idea_card', False) or getattr(card, 'is_note_card', False):
            if hasattr(card, 'lbl_title'):
                card.lbl_title.configure(text_color=text_color)
            # lbl_meta, lbl_alert: meta_color (gray)
            for attr in ('lbl_meta', 'lbl_alert', 'lbl_meta'):
                lbl = getattr(card, attr, None)
                if lbl:
                    lbl.configure(text_color=meta_color)
            # lbl_prio: cor já definida por _PRIO_COLORS, não sobrescrever
            return

        # Slow path (overview card, origin_frame): traversal recursivo original
        def _update(widget):
            if isinstance(widget, ctk.CTkLabel):
                if getattr(widget, "is_priority_colored", False):
                    return
                font_size = 12
                try:
                    font_size = widget.cget("font").cget("size")
                except Exception:
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
            # Debounce: múltiplos eventos em rápida sucessão são colapsados em um só refresh
            if hasattr(self, '_refresh_after_id'):
                try:
                    self.after_cancel(self._refresh_after_id)
                except Exception:
                    pass
            self._refresh_after_id = self.after(60, lambda: self.refresh_if_needed(trigger="entity_updated"))

    def on_map(self, event=None):
        if event and event.widget != self and str(event.widget) != f"{self}.!ctkcanvas":
            return
        if self.dirty:
            self.dirty = False
            self.refresh_if_needed(trigger="<Map>")

    def _check_scroll_loop(self):
        if not self.winfo_exists():
            return
        try:
            if self.winfo_viewable() and self.current_project:
                scrollbar = getattr(self.scroll, "_scrollbar", None)
                if scrollbar:
                    pos = scrollbar.get()
                    if pos != getattr(self, "_last_scroll_pos", None):
                        self._last_scroll_pos = pos
                        low, high = pos
                        if high > 0.85:
                            self._load_more_if_needed()
        except Exception:
            pass
        self.after(500, self._check_scroll_loop)

    def _load_more_if_needed(self):
        p = self.current_project
        if not p:
            return
        
        if self.show_archived_tasks:
            tasks_count = len([t for t in self.task_service.get_all_archived() if t.project_id == p.id])
        else:
            tasks_count = len(self.task_service.get_tasks_by_project(p.id))

        if self.show_archived_ideas:
            ideas_count = len([i for i in self.idea_service.get_all_archived() if i.project_id == p.id])
        else:
            ideas_count = len([i for i in self.idea_service.get_all_active() if i.project_id == p.id])

        if self.show_archived_notes:
            notes_count = len([n for n in self.note_service.get_all_archived() if n.project_id == p.id])
        else:
            notes_count = len(self.note_service.get_by_project_id(p.id))
            
        needed = False
        if tasks_count > self.visible_tasks_limit:
            self.visible_tasks_limit += 15
            needed = True
        if ideas_count > self.visible_ideas_limit:
            self.visible_ideas_limit += 15
            needed = True
        if notes_count > self.visible_notes_limit:
            self.visible_notes_limit += 15
            needed = True
            
        if needed:
            self.refresh(trigger="lazy_load")

    def change_task_sorting(self, sort_val):
        self.task_sort_by = sort_val
        self.refresh(trigger="sort_tasks")

    def show_task_sort_menu(self):
        from gui.components.context_menu import ContextMenu
        menu = ContextMenu(self)
        options = ["Prazo", "Status", "Prioridade", "Nome", "Criação"]
        for opt in options:
            label_text = f"✓ {opt}" if self.task_sort_by == opt else f"  {opt}"
            menu.add_command(label_text, command=lambda o=opt: self.change_task_sorting(o))
        try:
            x = self.btn_sort_tasks.winfo_rootx()
            y = self.btn_sort_tasks.winfo_rooty() + self.btn_sort_tasks.winfo_height()
        except Exception:
            x, y = self.winfo_rootx(), self.winfo_rooty()
        menu.popup(x, y)

    def open_originated_idea(self):
         if self.current_project:
             from database.repositories.entity_link_repository import EntityLinkRepository
             links = EntityLinkRepository().get_links_by_type('project', self.current_project.id, 'originated_from')
             if links:
                 orig_idea = self.idea_service.get_by_id(links[0]['target_id'])
                 if orig_idea:
                     def on_save(edited):
                         self.idea_service.update_idea(edited, orig_idea)
                         event_bus.emit("entity_updated")
                     QuickIdeaEditDialog(self.winfo_toplevel(), orig_idea, on_save=on_save)

    def _promote_idea_to_project(self, idea):
         from gui.dialogs import PromoteIdeaToProjectDialog
         def handle_promote(idea_id, project_title, copy_desc, copy_tags, copy_attach, link_idea, **kwargs):
             self.idea_service.promote_to_project(idea_id, project_title, copy_desc, copy_tags, copy_attach, link_idea, **kwargs)
             event_bus.emit("entity_updated")
             messagebox.showinfo("Sucesso", "Projeto criado a partir da ideia com sucesso!")
         PromoteIdeaToProjectDialog(self.winfo_toplevel(), idea, on_promote=handle_promote)

    def _promote_idea_to_task(self, idea):
         from gui.dialogs import PromoteIdeaToTaskDialog
         def handle_promote(idea_id, task_title, copy_desc, copy_tags, copy_attach, link_idea, project_id, **kwargs):
             self.idea_service.promote_to_task(idea_id, task_title, copy_desc, copy_tags, copy_attach, link_idea, project_id, **kwargs)
             event_bus.emit("entity_updated")
             messagebox.showinfo("Sucesso", "Tarefa criada a partir da ideia com sucesso!")
         
         default_proj_id = self.current_project.id if self.current_project else None
         PromoteIdeaToTaskDialog(self.winfo_toplevel(), idea, default_project_id=default_proj_id, on_promote=handle_promote)

    def _open_alerts_manager(self, task):
        from gui.views.alert_manager import AlertManagerDialog
        AlertManagerDialog.get_instance(self.winfo_toplevel(), "task", task.id, task.title)

    def _load_more_tasks(self, status_name):
        current_limit = self._group_limits.get(status_name, 10)
        self._group_limits[status_name] = current_limit + 20
        self.refresh()
