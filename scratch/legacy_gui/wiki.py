import customtkinter as ctk
import tkinter as tk
import tkinter.messagebox as messagebox
import copy
from collections import defaultdict
from services.knowledge_page_service import KnowledgePageService
from services.link_service import LinkService
from services.attachment_service import AttachmentService
from core.event_bus import event_bus

from models.entities import KnowledgePage


# ─── colour tokens ────────────────────────────────────────────────────────────
def _is_dark() -> bool:
    return ctk.get_appearance_mode() == "Dark"

SIDEBAR_BG_DARK  = "#13131f"
SIDEBAR_BG_LIGHT = "#f0f2f8"
CARD_BG_DARK     = "#1c1c2e"
CARD_BG_LIGHT    = "#ffffff"
CARD_HOV_DARK    = "#262640"
CARD_HOV_LIGHT   = "#e8eaf8"
CARD_SEL_DARK    = "#2d2d55"
CARD_SEL_LIGHT   = "#dde1f8"
ACCENT           = "#6366f1"       # indigo
ACCENT_HOV       = "#4f52d4"
GREEN            = "#22c55e"
GREEN_HOV        = "#16a34a"
RED              = "#ef4444"
RED_HOV          = "#dc2626"
AMBER            = "#f59e0b"
BORDER_DARK      = "#2a2a48"
BORDER_LIGHT     = "#d1d5eb"
TEXT_MUTED_DARK  = "#94a3b8"
TEXT_MUTED_LIGHT = "#64748b"


class WikiView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.page_service  = KnowledgePageService()
        self.link_service  = LinkService()
        self.attachment_service = AttachmentService()
        self.current_page  = None
        self.show_archived = False
        self.is_preview_mode = True
        self._search_after_id    = None
        self._selection_in_progress = False   # impede deselect logo após seleção

        # ── layout: sidebar (col 0) | editor (col 1) ──────────────────
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=280)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_editor()

        self.set_form_state(False)
        self.load_pages_list()
        # Bind global click AFTER widgets exist so winfo_toplevel() works
        self.after(200, self._bind_global_deselect)

    # ═══════════════════════════════════════════════════════════════════
    # SIDEBAR
    # ═══════════════════════════════════════════════════════════════════
    def _build_sidebar(self):
        dark = _is_dark()
        sb_bg = SIDEBAR_BG_DARK if dark else SIDEBAR_BG_LIGHT

        self.sidebar = ctk.CTkFrame(self, fg_color=sb_bg, corner_radius=12)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(10, 4), pady=10)
        self.sidebar.grid_rowconfigure(2, weight=1)
        self.sidebar.grid_columnconfigure(0, weight=1)

        # ── header ────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(14, 8))
        hdr.grid_columnconfigure(0, weight=1)

        title_f = ctk.CTkFrame(hdr, fg_color="transparent")
        title_f.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            title_f, text="📚  Wiki",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w"
        ).pack(side="left")

        # New page button — full width
        self.btn_new = ctk.CTkButton(
            hdr, text="＋  Nova Página",
            fg_color=ACCENT, hover_color=ACCENT_HOV,
            height=34, corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.create_new_page
        )
        self.btn_new.pack(fill="x", pady=(0, 8))

        # Search bar
        search_f = ctk.CTkFrame(hdr, fg_color=CARD_BG_DARK if dark else CARD_BG_LIGHT,
                                corner_radius=8)
        search_f.pack(fill="x")
        ctk.CTkLabel(search_f, text="🔍", font=ctk.CTkFont(size=14)).pack(
            side="left", padx=(8, 4), pady=6)
        self.ent_search = ctk.CTkEntry(
            search_f, placeholder_text="Buscar páginas ou tags…",
            border_width=0, fg_color="transparent", height=32
        )
        self.ent_search.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=4)
        self.ent_search.bind("<KeyRelease>", self._on_search_key)

        # ── divider ────────────────────────────────────────────────────
        div = tk.Frame(self.sidebar, height=1,
                       bg=BORDER_DARK if dark else BORDER_LIGHT,
                       bd=0, highlightthickness=0)
        div.grid(row=1, column=0, sticky="ew", padx=12, pady=0)
        div.pack_propagate(False)

        # ── pages tree ────────────────────────────────────────────────
        self.pages_scroll = ctk.CTkScrollableFrame(
            self.sidebar, fg_color="transparent"
        )
        self.pages_scroll.grid(row=2, column=0, sticky="nsew", padx=8, pady=6)

        # ── footer ────────────────────────────────────────────────────
        ftr = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        ftr.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 12))

        self.btn_toggle_archived = ctk.CTkButton(
            ftr, text="🗂  Ver Arquivadas",
            fg_color="transparent", border_width=1,
            border_color=BORDER_DARK if dark else BORDER_LIGHT,
            text_color=TEXT_MUTED_DARK if dark else TEXT_MUTED_LIGHT,
            hover_color=CARD_HOV_DARK if dark else CARD_HOV_LIGHT,
            height=30, corner_radius=8,
            font=ctk.CTkFont(size=12),
            command=self.toggle_archived
        )
        self.btn_toggle_archived.pack(fill="x")

    # ═══════════════════════════════════════════════════════════════════
    # EDITOR PANEL
    # ═══════════════════════════════════════════════════════════════════
    def _build_editor(self):
        dark = _is_dark()

        self.editor_panel = ctk.CTkFrame(self, corner_radius=12,
                                          fg_color=CARD_BG_DARK if dark else CARD_BG_LIGHT)
        self.editor_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 10), pady=10)
        self.editor_panel.grid_rowconfigure(3, weight=1)
        self.editor_panel.grid_columnconfigure(0, weight=1)
        self.editor_panel.grid_columnconfigure(1, weight=0, minsize=250)

        # ── top bar: breadcrumb + actions ─────────────────────────────
        self.topbar = ctk.CTkFrame(self.editor_panel, fg_color="transparent", height=54)
        self.topbar.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 0))
        self.topbar.grid_propagate(False)
        self.topbar.grid_columnconfigure(0, weight=1)

        self.lbl_breadcrumb = ctk.CTkLabel(
            self.topbar, text="Nenhuma página selecionada",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED_DARK if dark else TEXT_MUTED_LIGHT,
            anchor="w"
        )
        self.lbl_breadcrumb.grid(row=0, column=0, sticky="w")

        self.lbl_page_title = ctk.CTkLabel(
            self.topbar, text="",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w"
        )
        self.lbl_page_title.grid(row=1, column=0, sticky="w")

        # action buttons (right side of topbar)
        action_f = ctk.CTkFrame(self.topbar, fg_color="transparent")
        action_f.grid(row=0, column=1, rowspan=2, sticky="e")

        self.btn_favorite = ctk.CTkButton(
            action_f, text="⭐", width=36, height=30,
            fg_color="transparent", hover_color=CARD_HOV_DARK if dark else CARD_HOV_LIGHT,
            border_width=1, border_color=BORDER_DARK if dark else BORDER_LIGHT,
            corner_radius=8, command=self.toggle_favorite
        )

        self.btn_archive = ctk.CTkButton(
            action_f, text="📦 Arquivar", width=90, height=30,
            fg_color="transparent", hover_color=CARD_HOV_DARK if dark else CARD_HOV_LIGHT,
            border_width=1, border_color=BORDER_DARK if dark else BORDER_LIGHT,
            corner_radius=8, font=ctk.CTkFont(size=12),
            command=self.archive_page
        )

        self.btn_delete = ctk.CTkButton(
            action_f, text="🗑 Excluir", width=85, height=30,
            fg_color=RED, hover_color=RED_HOV,
            corner_radius=8, font=ctk.CTkFont(size=12),
            command=self.delete_page
        )

        # ── mode toggle tabs (Read | Edit) ────────────────────────────
        tabs_outer = ctk.CTkFrame(self.editor_panel, fg_color="transparent")
        tabs_outer.grid(row=1, column=0, sticky="ew", padx=18, pady=(12, 0))

        tab_bg = "#1a1a2e" if dark else "#e8eaf8"
        self.tabs_frame = ctk.CTkFrame(tabs_outer, fg_color=tab_bg, corner_radius=8)
        self.tabs_frame.pack(side="left")

        self.btn_read = ctk.CTkButton(
            self.tabs_frame, text="👁  Leitura", width=100, height=28,
            corner_radius=6, font=ctk.CTkFont(size=12),
            command=lambda: self._set_mode(True)
        )
        self.btn_read.pack(side="left", padx=3, pady=3)

        self.btn_edit = ctk.CTkButton(
            self.tabs_frame, text="✏️  Editar", width=100, height=28,
            corner_radius=6, font=ctk.CTkFont(size=12),
            command=lambda: self._set_mode(False)
        )
        self.btn_edit.pack(side="left", padx=(0, 3), pady=3)

        # ── metadata strip ────────────────────────────────────────────
        meta_bg = "#16162a" if dark else "#f4f5fc"
        self.meta_strip = ctk.CTkFrame(self.editor_panel, fg_color=meta_bg, corner_radius=8)
        self.meta_strip.grid(row=2, column=0, sticky="ew", padx=18, pady=(10, 0))
        self.meta_strip.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Category
        cat_f = ctk.CTkFrame(self.meta_strip, fg_color="transparent")
        cat_f.grid(row=0, column=0, padx=10, pady=8, sticky="ew")
        ctk.CTkLabel(cat_f, text="CATEGORIA",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=TEXT_MUTED_DARK if dark else TEXT_MUTED_LIGHT
                     ).pack(anchor="w")
        self.ent_category = ctk.CTkEntry(cat_f, height=28, corner_radius=6,
                                          border_color=BORDER_DARK if dark else BORDER_LIGHT)
        self.ent_category.pack(fill="x", pady=(2, 0))

        # Parent
        par_f = ctk.CTkFrame(self.meta_strip, fg_color="transparent")
        par_f.grid(row=0, column=1, padx=10, pady=8, sticky="ew")
        ctk.CTkLabel(par_f, text="PÁGINA PAI",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=TEXT_MUTED_DARK if dark else TEXT_MUTED_LIGHT
                     ).pack(anchor="w")
        self.opt_parent = ctk.CTkOptionMenu(par_f, values=["Nenhuma"],
                                             height=28, corner_radius=6)
        self.opt_parent.pack(fill="x", pady=(2, 0))

        # Review interval
        rev_f = ctk.CTkFrame(self.meta_strip, fg_color="transparent")
        rev_f.grid(row=0, column=2, padx=10, pady=8, sticky="ew")
        ctk.CTkLabel(rev_f, text="REVISÃO (DIAS)",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=TEXT_MUTED_DARK if dark else TEXT_MUTED_LIGHT
                     ).pack(anchor="w")
        self.ent_review = ctk.CTkEntry(rev_f, placeholder_text="Ex: 7, 30…",
                                        height=28, corner_radius=6,
                                        border_color=BORDER_DARK if dark else BORDER_LIGHT)
        self.ent_review.pack(fill="x", pady=(2, 0))

        # Tags
        tags_f = ctk.CTkFrame(self.meta_strip, fg_color="transparent")
        tags_f.grid(row=0, column=3, padx=10, pady=8, sticky="ew")
        ctk.CTkLabel(tags_f, text="TAGS",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=TEXT_MUTED_DARK if dark else TEXT_MUTED_LIGHT
                     ).pack(anchor="w")
        self.ent_tags = ctk.CTkEntry(tags_f, placeholder_text="python, estudos…",
                                      height=28, corner_radius=6,
                                      border_color=BORDER_DARK if dark else BORDER_LIGHT)
        self.ent_tags.pack(fill="x", pady=(2, 0))

        # Title entry (only visible in edit mode)
        title_wrap = ctk.CTkFrame(self.meta_strip, fg_color="transparent")
        title_wrap.grid(row=1, column=0, columnspan=4, padx=10, pady=(0, 8), sticky="ew")
        ctk.CTkLabel(title_wrap, text="TÍTULO",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=TEXT_MUTED_DARK if dark else TEXT_MUTED_LIGHT
                     ).pack(anchor="w")
        self.ent_title = ctk.CTkEntry(title_wrap, height=30, corner_radius=6,
                                       border_color=BORDER_DARK if dark else BORDER_LIGHT,
                                       font=ctk.CTkFont(size=14))
        self.ent_title.pack(fill="x", pady=(2, 0))

        # ── content area ──────────────────────────────────────────────
        self.txt_content = ctk.CTkTextbox(
            self.editor_panel,
            font=ctk.CTkFont(size=14, family="Consolas"),
            corner_radius=0,
            border_width=0,
            wrap="word"
        )
        self.txt_content.grid(row=3, column=0, sticky="nsew", padx=0, pady=(8, 0))

        # ── bottom action bar ─────────────────────────────────────────
        self.action_bar = ctk.CTkFrame(
            self.editor_panel,
            fg_color="#16162a" if dark else "#f4f5fc",
            height=52, corner_radius=0
        )
        self.action_bar.grid(row=4, column=0, sticky="ew")
        self.action_bar.grid_propagate(False)
        self.action_bar.grid_columnconfigure(0, weight=1)

        # --- ATTACHMENTS PANEL ---
        self._build_attachments_panel()


        self.lbl_status = ctk.CTkLabel(
            self.action_bar, text="",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED_DARK if dark else TEXT_MUTED_LIGHT
        )
        self.lbl_status.grid(row=0, column=0, sticky="w", padx=18)

        self.btn_save = ctk.CTkButton(
            self.action_bar, text="💾  Salvar Alterações",
            fg_color=GREEN, hover_color=GREEN_HOV,
            height=34, width=160, corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.save_changes
        )
        self.btn_save.grid(row=0, column=1, sticky="e", padx=18, pady=9)

        # ── Entity links panel ────────────────────────────────────────
        from gui.components.entity_links_panel import EntityLinksPanel
        self.links_panel = EntityLinksPanel(self.editor_panel, "wiki", 0)
        self.links_panel.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 8))

        # ── Autocomplete helpers ──────────────────────────────────────
        from utils.autocomplete import WikiAutocompleteHelper
        self.autocomplete = WikiAutocompleteHelper(self.txt_content, self.link_service)

        from utils.dropdown_autocomplete import (
            DropdownAutocompleteHelper, get_unique_categories, get_all_unique_tags
        )
        self.category_autocomplete = DropdownAutocompleteHelper(
            self.ent_category, get_unique_categories)
        self.tags_autocomplete = DropdownAutocompleteHelper(
            self.ent_tags, get_all_unique_tags, multiple=True)

        # ── initial tab appearance ────────────────────────────────────
        self._refresh_tab_style()

    # ═══════════════════════════════════════════════════════════════════
    # TAB STYLE
    # ═══════════════════════════════════════════════════════════════════
    def _refresh_tab_style(self):
        dark = _is_dark()
        inactive_bg  = "transparent"
        active_bg    = ACCENT
        inactive_txt = TEXT_MUTED_DARK if dark else TEXT_MUTED_LIGHT
        active_txt   = "#ffffff"

        if self.is_preview_mode:
            self.btn_read.configure(fg_color=active_bg, text_color=active_txt)
            self.btn_edit.configure(fg_color=inactive_bg, text_color=inactive_txt)
        else:
            self.btn_read.configure(fg_color=inactive_bg, text_color=inactive_txt)
            self.btn_edit.configure(fg_color=active_bg, text_color=active_txt)

    def _set_mode(self, preview: bool):
        self.is_preview_mode = preview
        self._refresh_tab_style()
        self.refresh_editor_content()

    # ═══════════════════════════════════════════════════════════════════
    # FORM STATE
    # ═══════════════════════════════════════════════════════════════════
    def set_form_state(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        for w in [self.ent_title, self.ent_category, self.opt_parent,
                  self.ent_review, self.ent_tags]:
            w.configure(state=state)

        if not enabled:
            for entry in [self.ent_title, self.ent_category, self.ent_review, self.ent_tags]:
                entry.configure(state="normal")
                entry.delete(0, "end")
                entry.configure(state="disabled")

            self.txt_content.configure(state="normal")
            self.txt_content.delete("0.0", "end")
            self.txt_content.configure(state="disabled")

            self.btn_save.configure(state="disabled")
            self.lbl_breadcrumb.configure(text="Nenhuma página selecionada")
            self.lbl_page_title.configure(text="")
            self.lbl_status.configure(text="")
            self.links_panel.update_entity("wiki", 0)

            # hide action buttons
            for b in [self.btn_favorite, self.btn_archive, self.btn_delete]:
                b.pack_forget()
        else:
            # show action buttons
            for b in [self.btn_delete, self.btn_archive, self.btn_favorite]:
                b.pack(side="right", padx=4)

    # ═══════════════════════════════════════════════════════════════════
    # TREE LIST
    # ═══════════════════════════════════════════════════════════════════
    def _on_search_key(self, event=None):
        if self._search_after_id:
            try:
                self.after_cancel(self._search_after_id)
            except Exception:
                pass
        self._search_after_id = self.after(250, self.load_pages_list)

    def load_pages_list(self):
        from utils.instrumentation import PerfContext, count_widgets_recursive, log_perf_data
        import time
        start_time = time.time()
        widgets_before = count_widgets_recursive(self.pages_scroll)

        for w in self.pages_scroll.winfo_children():
            w.destroy()

        dark = _is_dark()
        query = self.ent_search.get().lower().strip()
        
        with PerfContext("Buscar páginas", module="Wiki", category="Banco"):
            all_pages = (self.page_service.get_all_archived()
                         if self.show_archived
                         else self.page_service.get_all_active())

            if query:
                filtered = []
                for p in all_pages:
                    tags = self.page_service.get_tags(p.id)
                    tags_str = " ".join(tags).lower()
                    if (query in p.title.lower()
                            or (p.content and query in p.content.lower())
                            or (p.category and query in p.category.lower())
                            or query in tags_str):
                        filtered.append(p)
                all_pages = filtered

        with PerfContext("Montar árvore", module="Wiki", category="Processamento"):
            active_ids = {p.id for p in all_pages}
            pages_by_parent: dict = defaultdict(list)
            roots = []
            for p in all_pages:
                if p.parent_id is None or p.parent_id not in active_ids:
                    roots.append(p)
                else:
                    pages_by_parent[p.parent_id].append(p)

            roots.sort(key=lambda x: x.title)

        if not roots:
            ctk.CTkLabel(
                self.pages_scroll,
                text="Nenhuma página encontrada.",
                text_color=TEXT_MUTED_DARK if dark else TEXT_MUTED_LIGHT,
                font=ctk.CTkFont(size=12, slant="italic")
            ).pack(pady=24)
            return

        def render_tree(pages, depth=0):
            for p in pages:
                is_cur = self.current_page and self.current_page.id == p.id
                bg = (CARD_SEL_DARK if dark else CARD_SEL_LIGHT) if is_cur else \
                     (CARD_BG_DARK  if dark else CARD_BG_LIGHT)
                hov = CARD_HOV_DARK if dark else CARD_HOV_LIGHT

                card = ctk.CTkFrame(
                    self.pages_scroll,
                    fg_color=bg, corner_radius=8, cursor="hand2"
                )
                card._is_wiki_page_card = True
                card.pack(fill="x", pady=2, padx=(4 + depth * 16, 4))

                # linha principal com tk.Frame (sem altura m\u00ednima do CTk)
                row = tk.Frame(card, bg=bg, bd=0, highlightthickness=0)
                row.pack(fill="x")

                if is_cur:
                    acc = tk.Frame(row, width=3, bg=ACCENT, bd=0, highlightthickness=0)
                    acc.pack(side="left", fill="y", pady=3, padx=(4, 0))

                font_w     = "bold" if is_cur else "normal"
                title_pady = (5, 2) if (is_cur and p.category) else 5
                lbl = ctk.CTkLabel(
                    row,
                    text=p.title,
                    font=ctk.CTkFont(size=13, weight=font_w),
                    anchor="w"
                )
                lbl.pack(side="left", fill="x", expand=True,
                         padx=(6, 4), pady=title_pady)

                if p.is_favorite:
                    ctk.CTkLabel(row, text="\u2605", text_color=AMBER,
                                 font=ctk.CTkFont(size=11)
                                 ).pack(side="right", padx=(0, 8))

                # categoria: s\u00f3 quando selecionado, abaixo do t\u00edtulo
                if is_cur and p.category:
                    cat_row = tk.Frame(card, bg=bg, bd=0, highlightthickness=0)
                    cat_row.pack(fill="x", padx=12, pady=(0, 5))
                    ctk.CTkLabel(
                        cat_row, text=p.category,
                        font=ctk.CTkFont(size=10),
                        fg_color=ACCENT, text_color="white",
                        corner_radius=4, padx=6, pady=1
                    ).pack(side="left")

                # bindings
                def _on_card_click(e, pg=p):
                    self._selection_in_progress = True
                    self.select_page(pg)

                for widget in [card, row, lbl]:
                    widget.bind("<Button-1>", _on_card_click)
                    widget.bind("<Enter>",
                                lambda e, c=card, h=hov: c.configure(fg_color=h))
                    widget.bind("<Leave>",
                                lambda e, c=card, b=bg: c.configure(fg_color=b))

                if p.id in pages_by_parent:
                    children = sorted(pages_by_parent[p.id], key=lambda x: x.title)
                    render_tree(children, depth + 1)

        with PerfContext("Renderizar interface", module="Wiki", category="Renderização"):
            render_tree(roots)
            
        duration = time.time() - start_time
        widgets_after = count_widgets_recursive(self.pages_scroll)
        log_perf_data("WikiView", "load_pages_list", duration, widgets_before, widgets_after, loaded_items=len(all_pages))

    # ═══════════════════════════════════════════════════════════════════
    # PAGE SELECTION
    # ═══════════════════════════════════════════════════════════════════
    def load_parents_menu(self):
        all_pages = self.page_service.get_all_active()
        self.parent_dict = {"Nenhuma": None}
        for p in all_pages:
            if self.current_page and p.id == self.current_page.id:
                continue
            self.parent_dict[f"{p.id} – {p.title}"] = p.id
        self.opt_parent.configure(values=list(self.parent_dict.keys()))

    def select_page(self, page: KnowledgePage):
        # ── guarda modo edi\u00e7\u00e3o ───────────────────────────────────────────
        if not self.is_preview_mode and self.current_page:
            if self.current_page.id == page.id:
                return   # mesma p\u00e1gina em edi\u00e7\u00e3o \u2014 n\u00e3o muda nada
            resp = messagebox.askyesnocancel(
                "Salvar altera\u00e7\u00f5es",
                f"Deseja salvar as altera\u00e7\u00f5es em \u2018{self.current_page.title}\u2019 antes de continuar?"
            )
            if resp is None:
                return          # Cancelar \u2014 permanece na p\u00e1gina atual
            if resp is True:
                self.save_changes()   # Sim \u2014 salva (j\u00e1 muda para preview internamente)
            # resp is False \u2014 descarta e continua para nova p\u00e1gina
        # ─────────────────────────────────────────────────────────────────

        self.current_page = page
        self.load_parents_menu()
        self.set_form_state(True)

        # breadcrumb
        if page.parent_id:
            parent = self.page_service.get_by_id(page.parent_id)
            crumb = f"{parent.title}  ›  {page.title}" if parent else page.title
        else:
            crumb = "Raiz"
        self.lbl_breadcrumb.configure(text=crumb)
        self.lbl_page_title.configure(text=page.title)

        # fields
        self.ent_title.configure(state="normal")
        self.ent_title.delete(0, "end")
        self.ent_title.insert(0, page.title)

        self.ent_category.configure(state="normal")
        self.ent_category.delete(0, "end")
        if page.category:
            self.ent_category.insert(0, page.category)

        self.ent_review.configure(state="normal")
        self.ent_review.delete(0, "end")
        if page.review_interval_days:
            self.ent_review.insert(0, str(page.review_interval_days))

        tags = self.page_service.get_tags(page.id)
        self.ent_tags.configure(state="normal")
        self.ent_tags.delete(0, "end")
        self.ent_tags.insert(0, ", ".join(tags))

        # parent
        self.opt_parent.set("Nenhuma")
        if page.parent_id:
            for k, v in self.parent_dict.items():
                if v == page.parent_id:
                    self.opt_parent.set(k)
                    break

        # favourite & archive buttons
        self.btn_favorite.configure(text="★" if page.is_favorite else "☆")
        self.btn_archive.configure(
            text="↩ Restaurar" if page.is_archived else "📦 Arquivar"
        )

        # content
        self.is_preview_mode = True
        self._refresh_tab_style()
        self.refresh_editor_content()

        # links
        self.links_panel.update_entity("wiki", page.id)
        self.lbl_status.configure(text=f"ID {page.id}")

        self.load_pages_list()
        self._render_attachments()

    # ═══════════════════════════════════════════════════════════════════
    # EDITOR CONTENT
    # ═══════════════════════════════════════════════════════════════════
    def refresh_editor_content(self):
        if not self.current_page:
            return
        page = self.current_page
        self.txt_content.configure(state="normal")
        self.txt_content.delete("0.0", "end")

        if self.is_preview_mode:
            from utils.wiki_parser import render_wiki_text
            render_wiki_text(
                self.txt_content,
                page.content or "",
                on_create_callback=self.winfo_toplevel().on_unresolved_link_click
            )
            self.txt_content.configure(state="disabled")
            self.btn_save.configure(state="disabled")
            # hide title edit in read mode
            self.ent_title.configure(state="disabled")
        else:
            if page.content:
                self.txt_content.insert("0.0", page.content)
            self.txt_content.configure(state="normal")
            self.btn_save.configure(state="normal")
            self.ent_title.configure(state="normal")

    def toggle_mode(self):
        self._set_mode(not self.is_preview_mode)

    # ═══════════════════════════════════════════════════════════════════
    # ACTIONS
    # ═══════════════════════════════════════════════════════════════════
    def create_new_page(self):
        self._selection_in_progress = True   # impede deselect pelo handler global
        new_page = self.page_service.create_page(title="Nova Página Wiki")
        self.select_page(new_page)
        self._set_mode(False)

    def save_changes(self):
        if not self.current_page:
            return

        title = self.ent_title.get().strip()
        if not title:
            messagebox.showwarning("Aviso", "O título da página é obrigatório.")
            return

        original = copy.deepcopy(self.current_page)
        self.current_page.title    = title
        self.current_page.category = self.ent_category.get().strip() or None

        review_days = self.ent_review.get().strip()
        try:
            self.current_page.review_interval_days = int(review_days) if review_days else None
        except ValueError:
            messagebox.showwarning("Aviso", "Intervalo de revisão deve ser um número inteiro.")
            return

        parent_key = self.opt_parent.get()
        self.current_page.parent_id = self.parent_dict.get(parent_key)
        self.current_page.content   = self.txt_content.get("0.0", "end-1c").strip() or None

        self.page_service.update_page(self.current_page, original)

        try:
            self.link_service.update_links_from_text(
                "wiki", self.current_page.id, self.current_page.content or ""
            )
        except Exception:
            pass

        raw_tags = self.ent_tags.get().split(",")
        cleaned_tags = [t.strip() for t in raw_tags if t.strip()]
        self.page_service.set_tags(self.current_page.id, cleaned_tags)

        self.lbl_status.configure(text="✅  Alterações salvas!")
        self.lbl_page_title.configure(text=title)
        self._set_mode(True)
        self.links_panel.refresh()
        self.load_pages_list()

    def toggle_favorite(self):
        if not self.current_page:
            return
        original = copy.deepcopy(self.current_page)
        self.current_page.is_favorite = not self.current_page.is_favorite
        self.page_service.update_page(self.current_page, original)
        self.select_page(self.current_page)

    def archive_page(self):
        if not self.current_page:
            return
        if self.current_page.is_archived:
            self.page_service.restore_page(self.current_page.id)
            self.current_page.is_archived = False
            self.select_page(self.current_page)
        else:
            self.page_service.archive_page(self.current_page.id)
            self.current_page = None
            self.set_form_state(False)
            self.load_pages_list()

    def delete_page(self):
        if not self.current_page:
            return
        if messagebox.askyesno("Excluir", "Deseja enviar esta página para a lixeira?"):
            self.page_service.soft_delete_page(self.current_page.id)
            self.current_page = None
            self.set_form_state(False)
            self.load_pages_list()

    def toggle_archived(self):
        self.show_archived = not self.show_archived
        self.btn_toggle_archived.configure(
            text="🗂  Ocultar Arquivadas" if self.show_archived else "🗂  Ver Arquivadas"
        )
        self.load_pages_list()

    def _deselect(self):
        """Limpa a seleção da página atual."""
        if self.current_page is None:
            return
        self.current_page = None
        self.set_form_state(False)
        self.load_pages_list()

    def _bind_global_deselect(self):
        """Registra handler global no root para deselecionar ao clicar fora."""
        try:
            root = self.winfo_toplevel()
            root.bind("<Button-1>", self._on_global_click, add="+")
        except Exception:
            pass

    def _on_global_click(self, event):
        """Deseleciona se o clique não foi dentro do editor nem em um card de página."""
        if self.current_page is None:
            return
        # Só age se esta view estiver visível
        try:
            if not self.winfo_ismapped():
                return
        except Exception:
            return

        # Se um card acabou de ser clicado, ignora este ciclo
        if self._selection_in_progress:
            self._selection_in_progress = False
            return

        # Sobe a hierarquia de widgets a partir do alvo do clique
        w = event.widget
        while w is not None:
            if w is self.editor_panel:
                return  # dentro do editor — mantém seleção
            if getattr(w, '_is_wiki_page_card', False):
                return  # dentro de um card de página — mantém
            try:
                w = w.master
            except AttributeError:
                break

        # Clicou fora de tudo relevante — deseleciona
        self._deselect()


    # ── ATTACHMENTS LOGIC ──────────────────────────────────────────────
    def _build_attachments_panel(self):
        dark = _is_dark()
        self.attachments_panel = ctk.CTkFrame(self.editor_panel, fg_color="#1a1a2e" if dark else "#e8eaf8", corner_radius=8)
        # Put it on column 1, spanning from row 1 to row 4
        self.attachments_panel.grid(row=1, column=1, rowspan=4, sticky="nsew", padx=(0, 18), pady=(12, 0))
        
        # Header
        hdr_f = ctk.CTkFrame(self.attachments_panel, fg_color="transparent")
        hdr_f.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(hdr_f, text="📎 Anexos", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        
        self.btn_add_attachment = ctk.CTkButton(
            hdr_f, text="+", width=28, height=28, corner_radius=6,
            command=self._cmd_add_attachment
        )
        self.btn_add_attachment.pack(side="right")
        
        # List of attachments
        self.attachments_scroll = ctk.CTkScrollableFrame(self.attachments_panel, fg_color="transparent")
        self.attachments_scroll.pack(fill="both", expand=True, padx=5, pady=5)

    def _cmd_add_attachment(self):
        if not self.current_page:
            messagebox.showwarning("Aviso", "Selecione ou salve a página primeiro.")
            return
            
        import tkinter.filedialog as fd
        filepath = fd.askopenfilename(title="Selecionar Anexo")
        if not filepath:
            return
            
        try:
            self.attachment_service.add_attachment(filepath, "knowledge_pages", self.current_page.id)
            self._render_attachments()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao anexar arquivo: {e}")

    def _render_attachments(self):
        # Clear existing
        for widget in self.attachments_scroll.winfo_children():
            widget.destroy()
            
        if not self.current_page:
            return
            
        attachments = self.attachment_service.get_attachments_for_entity("knowledge_pages", self.current_page.id)
        
        if not attachments:
            ctk.CTkLabel(self.attachments_scroll, text="Nenhum anexo", text_color="gray").pack(pady=20)
            return
            
        dark = _is_dark()
        card_bg = CARD_BG_DARK if dark else CARD_BG_LIGHT
        
        for att in attachments:
            self._build_attachment_card(att, card_bg)

    def _build_attachment_card(self, att, bg_color):
        card = ctk.CTkFrame(self.attachments_scroll, fg_color=bg_color, corner_radius=6)
        card.pack(fill="x", pady=2, padx=2)
        
        # Info
        info_f = ctk.CTkFrame(card, fg_color="transparent")
        info_f.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # Name
        lbl_name = ctk.CTkLabel(info_f, text=att.file_name, anchor="w", justify="left", wraplength=140, font=ctk.CTkFont(size=12, weight="bold"))
        lbl_name.pack(fill="x")
        
        # Size
        kb = att.file_size / 1024 if att.file_size else 0
        lbl_size = ctk.CTkLabel(info_f, text=f"{kb:.1f} KB", anchor="w", font=ctk.CTkFont(size=10), text_color="gray")
        lbl_size.pack(fill="x")
        
        # Removed buttons, only relying on double-click and right-click

        for w in (card, info_f, lbl_name, lbl_size):
            w.bind("<Double-Button-1>", lambda e, a=att: self._open_attachment(a))
            w.bind("<Button-3>", lambda e, a=att: self._show_attachment_context_menu(e, a))

    def _show_attachment_context_menu(self, event, att):
        from gui.components.context_menu import ContextMenu
        menu = ContextMenu(self)
        menu.add_command("Abrir", command=lambda: self._open_attachment(att))
        menu.add_command("Abrir Pasta", command=lambda: self._open_attachment_folder(att))
        menu.add_separator()
        menu.add_command("Excluir", command=lambda: self._delete_attachment(att), danger=True)
        
        menu.tk_popup(event.x_root, event.y_root)

    def _open_attachment_folder(self, att):
        import os, subprocess
        path = att.file_path
        if os.path.exists(path):
            subprocess.run(['explorer', '/select,', os.path.normpath(path)])
        else:
            messagebox.showerror("Erro", "Arquivo não encontrado no disco!")

    def _open_attachment(self, att):
        import os
        path = att.file_path
        if os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showerror("Erro", "Arquivo não encontrado no disco!")

    def _delete_attachment(self, att):
        if messagebox.askyesno("Confirmar", f"Excluir anexo '{att.file_name}'?"):
            self.attachment_service.delete_attachment(att.id)
            self._render_attachments()

