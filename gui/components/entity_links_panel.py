import tkinter as tk
import customtkinter as ctk
from services.link_service import LinkService

class EntityLinksPanel(ctk.CTkFrame):
    def __init__(self, master, entity_type: str, entity_id: int, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.link_service = LinkService()
        
        # State variables for hover/popup tracking
        self.popup = None
        self.listbox = None
        self.mouse_in_trigger = False
        self.mouse_in_popup = False
        self.current_links = []
        
        # Style tokens
        self.is_dark = ctk.get_appearance_mode() == "Dark"
        
        # Layout: Compact horizontal frame
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="x", anchor="w")
        
        self.btn_out = ctk.CTkButton(
            self.container, 
            text="🔗 Referências (0)", 
            width=140, 
            height=28,
            fg_color=("#e0e0e0", "#2b2b2b"),
            hover_color=("#d0d0d0", "#3f3f3f"),
            text_color=("black", "white")
        )
        self.btn_out.pack(side="left", padx=(0, 10))
        
        self.btn_in = ctk.CTkButton(
            self.container, 
            text="↩️ Referenciado por (0)", 
            width=170, 
            height=28,
            fg_color=("#e0e0e0", "#2b2b2b"),
            hover_color=("#d0d0d0", "#3f3f3f"),
            text_color=("black", "white")
        )
        self.btn_in.pack(side="left")
        
        # Bind hover events
        self.btn_out.bind("<Enter>", lambda e: self.on_trigger_enter(e, is_backlink=False))
        self.btn_out.bind("<Leave>", self.on_trigger_leave)
        self.btn_in.bind("<Enter>", lambda e: self.on_trigger_enter(e, is_backlink=True))
        self.btn_in.bind("<Leave>", self.on_trigger_leave)
        
        self.refresh()
        
    def update_entity(self, entity_type: str, entity_id: int):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.refresh()
        
    def refresh(self):
        if not self.entity_id:
            self.btn_out.configure(text="🔗 Referências (0)")
            self.btn_in.configure(text="↩️ Referenciado por (0)")
            return
            
        try:
            self.out_links = self.link_service.get_links_for_entity(self.entity_type, self.entity_id)
            self.in_links = self.link_service.get_backlinks_for_entity(self.entity_type, self.entity_id)
        except Exception:
            self.out_links = []
            self.in_links = []
            
        self.btn_out.configure(text=f"🔗 Referências ({len(self.out_links)})")
        self.btn_in.configure(text=f"↩️ Referenciado por ({len(self.in_links)})")
        
    def on_trigger_enter(self, event, is_backlink: bool):
        self.mouse_in_trigger = True
        
        # Close any existing popup
        self.close_popup()
        
        # Determine links to display
        links = self.in_links if is_backlink else self.out_links
        self.current_links = links
        
        # Pass the trigger button so show_popup can compute available space
        trigger_btn = event.widget
        x = trigger_btn.winfo_rootx()
        y_below = trigger_btn.winfo_rooty() + trigger_btn.winfo_height()
        y_top   = trigger_btn.winfo_rooty()
        
        self.show_popup(x, y_below, y_top, is_backlink)

    def on_trigger_leave(self, event):
        self.mouse_in_trigger = False
        self.after(200, self.check_close_popup)

    def on_popup_enter(self, event):
        self.mouse_in_popup = True

    def on_popup_leave(self, event):
        self.mouse_in_popup = False
        self.after(200, self.check_close_popup)

    def check_close_popup(self):
        if not self.mouse_in_trigger and not self.mouse_in_popup:
            self.close_popup()

    def show_popup(self, x: int, y_below: int, y_top: int, is_backlink: bool):
        """Exibe o popup de links com posicionamento inteligente:
        - Se não couber abaixo, abre acima do botão.
        - Nunca ultrapassa a borda direita ou esquerda da tela.
        - Adiciona scrollbar quando há muitos itens.
        """
        self.popup = tk.Toplevel(self)
        self.popup.wm_overrideredirect(True)
        self.popup.wm_attributes("-topmost", True)
        
        bg_color  = "#2b2b2b" if self.is_dark else "#f0f0f0"
        fg_color  = "#ffffff" if self.is_dark else "#000000"
        select_bg = "#2b8c52"
        select_fg = "#ffffff"
        border_color = "#1a1a1a" if self.is_dark else "#d0d0d0"

        frame = tk.Frame(self.popup, bg=border_color, bd=1)
        frame.pack(fill="both", expand=True)

        # Limita altura visível a 8 itens, mas adiciona scrollbar se precisar
        n_items   = max(1, len(self.current_links)) if self.current_links else 1
        list_h    = min(8, n_items)
        need_scroll = n_items > 8

        self.listbox = tk.Listbox(
            frame,
            bg=bg_color,
            fg=fg_color,
            selectbackground=select_bg,
            selectforeground=select_fg,
            bd=0,
            highlightthickness=0,
            height=list_h,
            width=42
        )

        if need_scroll:
            sb = tk.Scrollbar(frame, orient="vertical", command=self.listbox.yview)
            self.listbox.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")

        self.listbox.pack(side="left", fill="both", expand=True)
        
        # Preenche a lista
        icons = {
            "project": "📁", "task": "📋", "idea": "💡",
            "note": "📝", "wiki": "📖", "knowledge_page": "📖"
        }
        
        if not self.current_links:
            self.listbox.insert("end", " Nenhuma ligação encontrada.")
            self.listbox.configure(state="disabled")
        else:
            for lnk in self.current_links:
                t_key = lnk.get('target_type') if 'target_type' in lnk else lnk.get('source_type')
                icon = icons.get(t_key, "🔗")
                display_str = f" {icon} {lnk['title']} ({lnk['relationship_type']})"
                self.listbox.insert("end", display_str)
            
            self.listbox.selection_set(0)
            self.listbox.activate(0)
            self.listbox.bind("<ButtonRelease-1>", lambda e: self.navigate_selection())
            self.listbox.bind("<KeyPress-Return>",  lambda e: self.navigate_selection())
            self.listbox.bind("<KeyPress-Tab>",     lambda e: self.navigate_selection())
            self.listbox.bind("<KeyPress-Escape>",  lambda e: self.close_popup())

        self.popup.bind("<Enter>", self.on_popup_enter)
        self.popup.bind("<Leave>", self.on_popup_leave)
        self.listbox.focus_set()

        # ── Posicionamento inteligente ───────────────────────────────
        # Primeiro posiciona fora da área visível para medir tamanho real
        self.popup.geometry("+0+0")
        self.popup.update_idletasks()

        pw = self.popup.winfo_reqwidth()
        ph = self.popup.winfo_reqheight()
        sw = self.popup.winfo_screenwidth()
        sh = self.popup.winfo_screenheight()
        margin = 10

        # Horizontal: garante que não ultrapasse a borda direita nem esquerda
        final_x = x
        if final_x + pw + margin > sw:
            final_x = sw - pw - margin
        final_x = max(margin, final_x)

        # Vertical: prefere abrir abaixo; se não couber, abre acima
        if y_below + ph + margin <= sh:
            final_y = y_below           # Abaixo do botão (posicionamento padrão)
        else:
            final_y = y_top - ph        # Acima do botão
            if final_y < margin:
                # Nem acima cabe: centraliza na tela e limpa o que sobrar
                final_y = max(margin, sh - ph - margin)

        self.popup.geometry(f"+{final_x}+{final_y}")

    def close_popup(self):
        if self.popup:
            self.popup.destroy()
            self.popup = None
            self.listbox = None

    def navigate_selection(self):
        if not self.listbox or not self.current_links:
            return
            
        selection = self.listbox.curselection()
        if not selection:
            return
            
        item = self.current_links[selection[0]]
        self.close_popup()
        
        # Navigate to target or source depending on the layout structure
        t_type = item.get('target_type') if 'target_type' in item else item.get('source_type')
        t_id = item.get('target_id') if 'target_id' in item else item.get('source_id')
        self.link_service.navigate_to_entity(t_type, t_id)
