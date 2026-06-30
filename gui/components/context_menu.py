"""
context_menu.py — Menu de contexto moderno (substitui tk.Menu em todo o projeto).

API:
    m = ContextMenu(master)
    m.add_command("✏️ Editar", command=fn)
    m.add_header("Alterar Status")          # rótulo de seção (cinza, não clicável)
    m.add_command("▶ Em Andamento", ...)
    m.add_separator()
    m.add_command("🗑 Excluir", ..., danger=True)  # texto vermelho
    m.popup(x, y)   # ou m.tk_popup(x, y) — alias compatível
"""

import tkinter as tk
import customtkinter as ctk


class ContextMenu:
    """Popup moderno no estilo Linear/Notion — substitui tk.Menu em todo o projeto."""
    
    _active_menu = None

    def __init__(self, master):
        self._master = master
        self._items: list[dict] = []
        self._win: tk.Toplevel | None = None
        self._root_bind_id = None

    # ── Builder ────────────────────────────────────────────────────
    def add_command(self, label: str, command=None,
                    enabled: bool = True, danger: bool = False):
        """Adiciona um item clicável. danger=True → texto vermelho."""
        self._items.append(dict(type="command", label=label,
                                command=command, enabled=enabled, danger=danger))
        return self

    def add_separator(self):
        """Linha divisória entre grupos."""
        self._items.append(dict(type="separator"))
        return self

    def add_header(self, label: str):
        """Rótulo de seção em cinza pequeno — não é clicável."""
        self._items.append(dict(type="header", label=label))
        return self

    # ── Render ─────────────────────────────────────────────────────
    def popup(self, x: int, y: int):
        self._destroy()
        
        if ContextMenu._active_menu and ContextMenu._active_menu != self:
            ContextMenu._active_menu._destroy()
        ContextMenu._active_menu = self

        dark       = ctk.get_appearance_mode() == "Dark"
        bg         = "#1c1c2e" if dark else "#ffffff"
        hover_bg   = "#2a2a40" if dark else "#eef2ff"
        border_col = "#35354e" if dark else "#c8cce0"
        text_col   = "#e2e8f0" if dark else "#1e293b"
        text_dis   = "#55557a" if dark else "#94a3b8"
        text_hdr   = "#6366a0" if dark else "#94a3c8"   # seção — cinza azulado
        text_dng   = "#f87171" if dark else "#dc2626"   # perigo — vermelho
        sep_col    = "#3e3e60" if dark else "#b8c0d8"   # visível mas suave

        # ── Janela ────────────────────────────────────────────────
        self._win = tk.Toplevel(self._master)
        self._win.overrideredirect(True)
        self._win.wm_attributes("-topmost", True)

        # Borda fina (1 px) via Frame pai
        outer = tk.Frame(self._win, bg=border_col, padx=1, pady=1)
        outer.pack(fill="both", expand=True)

        inner = ctk.CTkFrame(outer, fg_color=bg, corner_radius=8)
        inner.pack(fill="both", expand=True, padx=0, pady=0)

        # ── Itens ─────────────────────────────────────────────────
        for item in self._items:
            t = item["type"]

            if t == "separator":
                sep_frame = tk.Frame(inner, height=2, bg=sep_col, bd=0, highlightthickness=0)
                sep_frame.pack(fill="x", padx=6, pady=5)
                sep_frame.pack_propagate(False)

            elif t == "header":
                ctk.CTkLabel(
                    inner,
                    text=item["label"].upper(),
                    font=ctk.CTkFont(size=9, weight="bold"),
                    text_color=text_hdr,
                    anchor="w",
                ).pack(fill="x", padx=16, pady=(6, 1))

            elif t == "command":
                enabled = item["enabled"]
                danger  = item["danger"]
                color   = text_dng if danger else (text_col if enabled else text_dis)
                hbg     = ("#3a1a1a" if dark else "#fff1f1") if danger else hover_bg

                btn = ctk.CTkButton(
                    inner,
                    text=item["label"],
                    anchor="w",
                    fg_color="transparent",
                    hover_color=hbg,
                    text_color=color,
                    font=ctk.CTkFont(size=12),
                    height=30,
                    corner_radius=6,
                    state="normal" if enabled else "disabled",
                    command=lambda cmd=item["command"]: self._execute(cmd),
                )
                btn.pack(fill="x", padx=4, pady=1)

        # ── Posicionamento ────────────────────────────────────────
        self._win.update_idletasks()
        w  = max(self._win.winfo_reqwidth(), 200)
        h  = self._win.winfo_reqheight()
        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        if x + w > sw:
            x = sw - w - 4
        if y + h > sh:
            y = sh - h - 4
        self._win.geometry(f"{w}x{h}+{x}+{y}")

        # ── Fechar ─────────────────────────────────────────────────────
        self._win.bind("<FocusOut>", self._on_focus_out)
        self._win.bind("<Escape>",   lambda e: self._destroy())
        self._win.after(50, self._win.focus_set)
        
        # Intercept clicks outside the menu
        root = self._master.winfo_toplevel()
        def close_if_outside(e):
            if self._win and e.widget != self._win and str(e.widget).find(str(self._win)) == -1:
                self._destroy()
        self._root_bind_id = root.bind("<Button-1>", close_if_outside, add="+")

    def _on_focus_out(self, event):
        try:
            focused = self._win.focus_get()
            if focused and str(focused).startswith(str(self._win)):
                return
        except Exception:
            pass
        self._destroy()

    def _execute(self, command):
        self._destroy()
        if command:
            try:
                command()
            except Exception:
                pass

    def _destroy(self):
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass
            self._win = None
            
        if self._root_bind_id:
            try:
                self._master.winfo_toplevel().unbind("<Button-1>", self._root_bind_id)
            except Exception:
                pass
            self._root_bind_id = None
            
        if ContextMenu._active_menu == self:
            ContextMenu._active_menu = None

    # Alias de compatibilidade
    def tk_popup(self, x: int, y: int):
        self.popup(x, y)
