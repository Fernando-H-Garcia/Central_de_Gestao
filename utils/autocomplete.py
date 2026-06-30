import tkinter as tk
import customtkinter as ctk
from services.link_service import LinkService

class WikiAutocompleteHelper:
    def __init__(self, ctk_textbox: ctk.CTkTextbox, link_service=None):
        self.ctk_textbox = ctk_textbox
        self.text_widget = ctk_textbox._textbox
        self.link_service = link_service or LinkService()
        
        # State variables
        self.popup = None
        self.listbox = None
        self.cache = []       # Local entities cache loaded on popup open
        self.filtered = []    # Current filtered list
        self.trigger_index = None # The text index where '[[' started
        
        # Bind events to the text widget
        self.text_widget.bind("<KeyRelease>", self.on_key_release)
        self.text_widget.bind("<KeyPress>", self.on_key_press, add="+")
        self.text_widget.bind("<FocusOut>", self.on_focus_out)
        
        # Also close popup when user clicks somewhere else in the textbox
        self.text_widget.bind("<Button-1>", lambda e: self.close_popup(), add="+")

    def load_cache(self):
        """Loads all active entities from database once when popup triggers."""
        try:
            self.cache = self.link_service.get_all_linkable_entities()
        except Exception:
            self.cache = []

    def get_type_prefix(self, entity_type: str) -> str:
        prefixes = {
            "project": "📁 [Projeto] ",
            "task": "✅ [Tarefa] ",
            "idea": "💡 [Ideia] ",
            "wiki": "📖 [Wiki] "
        }
        return prefixes.get(entity_type.lower(), "🔗 ")

    def show_popup(self, x, y):
        if self.popup:
            return
            
        self.load_cache()
        if not self.cache:
            return

        # Create borderless floating window
        self.popup = tk.Toplevel(self.text_widget)
        self.popup.wm_overrideredirect(True)
        self.popup.wm_attributes("-topmost", True)
        
        # Colors to match UI theme
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg_color = "#2b2b2b" if is_dark else "#f0f0f0"
        fg_color = "#ffffff" if is_dark else "#000000"
        select_bg = "#2b8c52"
        select_fg = "#ffffff"
        
        frame = tk.Frame(self.popup, bg="#1a1a1a" if is_dark else "#d0d0d0", bd=1)
        frame.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(
            frame,
            bg=bg_color,
            fg=fg_color,
            selectbackground=select_bg,
            selectforeground=select_fg,
            font=self.text_widget.cget("font"),
            bd=0,
            highlightthickness=0,
            height=6,
            width=40
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)
        
        # Keep click focus on the main text widget
        self.listbox.bind("<ButtonRelease-1>", lambda e: self.insert_selection())
        
        self.update_filter()
        
        # Position popup with boundary checks
        self.popup.update_idletasks() # Ensure dimensions are calculated
        popup_width = self.popup.winfo_reqwidth()
        
        # Check window width boundary
        toplevel = self.text_widget.winfo_toplevel()
        toplevel_x = toplevel.winfo_rootx()
        toplevel_width = toplevel.winfo_width()
        max_right = toplevel_x + toplevel_width
        
        # If it overflows the main window's right edge, shift it left
        if x + popup_width > max_right:
            x = max_right - popup_width - 10
            # Ensure it does not go past the left edge
            x = max(toplevel_x, x)
            
        self.popup.geometry(f"+{x}+{y}")

    def close_popup(self):
        if self.popup:
            self.popup.destroy()
            self.popup = None
            self.listbox = None
            self.trigger_index = None

    def on_focus_out(self, event):
        # Delay closing slightly to allow listbox click events to process first
        self.text_widget.after(200, self.check_focus_and_close)

    def check_focus_and_close(self):
        if not self.popup:
            return
        try:
            focused = self.text_widget.focus_get()
            # If focus is still within popup or listbox, do not close
            if focused == self.listbox or focused == self.popup:
                return
        except Exception:
            pass
        self.close_popup()

    def insert_selection(self):
        if not self.listbox or not self.trigger_index:
            return
            
        selection_idx = self.listbox.curselection()
        if not selection_idx:
            return
            
        selected_item = self.filtered[selection_idx[0]]
        entity_type = selected_item["type"]
        entity_id = selected_item["id"]
        title = selected_item["title"]
        
        # Format: [[type:id|Title]]
        link_str = f"[[{entity_type}:{entity_id}|{title}]]"
        
        # Replace the prefix from trigger_index to current cursor position
        current_cursor = self.text_widget.index("insert")
        
        # Temporarily enable textbox if it was disabled (though it's in edit mode usually)
        self.text_widget.delete(self.trigger_index, current_cursor)
        self.text_widget.insert(self.trigger_index, link_str)
        
        self.close_popup()

    def on_key_press(self, event):
        # Intercept navigation keys when popup is open
        if self.popup and self.listbox:
            if event.keysym in ("Up", "Down"):
                current = self.listbox.curselection()
                size = self.listbox.size()
                if not current:
                    idx = 0
                else:
                    idx = current[0]
                    if event.keysym == "Up":
                        idx = max(0, idx - 1)
                    else:
                        idx = min(size - 1, idx + 1)
                
                self.listbox.selection_clear(0, "end")
                self.listbox.selection_set(idx)
                self.listbox.see(idx)
                self.listbox.activate(idx)
                return "break"
                
            elif event.keysym in ("Return", "Tab"):
                self.insert_selection()
                return "break"
                
            elif event.keysym == "Escape":
                self.close_popup()
                return "break"

    def on_key_release(self, event):
        # Avoid intercepting navigation/selection release events
        if event.keysym in ("Up", "Down", "Return", "Tab", "Escape"):
            return
            
        # Check Ctrl+Space trigger
        ctrl_space = (event.state & 0x0004) and event.keysym == "space"
        
        # Read text prior to cursor
        cursor_pos = self.text_widget.index("insert")
        line_start = self.text_widget.index("insert linestart")
        text_before = self.text_widget.get(line_start, cursor_pos)
        
        # Find last occurrences of '[['
        idx_in_line = text_before.rfind("[[")
        
        if idx_in_line != -1:
            # We have a current '[[', verify there isn't a closing ']]' after it
            query_text = text_before[idx_in_line + 2:]
            if "]]" in query_text:
                self.close_popup()
                return
                
            # Set the trigger index coordinates
            line_num = cursor_pos.split(".")[0]
            col_offset = idx_in_line
            self.trigger_index = f"{line_num}.{col_offset}"
            
            # Open or update popup
            if not self.popup:
                bbox = self.text_widget.bbox("insert")
                if bbox:
                    x, y, w, h = bbox
                    root_x = self.text_widget.winfo_rootx() + x
                    root_y = self.text_widget.winfo_rooty() + y + h
                    self.show_popup(root_x, root_y)
            else:
                self.update_filter()
        else:
            # Closing the popup if backspaced past the '[['
            self.close_popup()

    def update_filter(self):
        if not self.listbox or not self.trigger_index:
            return
            
        cursor_pos = self.text_widget.index("insert")
        query = self.text_widget.get(self.trigger_index + " + 2 chars", cursor_pos).lower().strip()
        
        # Filter cache
        self.filtered = []
        for item in self.cache:
            if not query or query in item["title"].lower():
                self.filtered.append(item)
                
        # Update listbox options
        self.listbox.delete(0, "end")
        for item in self.filtered:
            display_str = f"{self.get_type_prefix(item['type'])}{item['title']}"
            self.listbox.insert("end", display_str)
            
        if self.filtered:
            self.listbox.selection_set(0)
            self.listbox.activate(0)
        else:
            self.listbox.insert("end", "Nenhum candidato encontrado...")
