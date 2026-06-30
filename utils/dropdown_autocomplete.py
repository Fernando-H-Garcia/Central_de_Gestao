import tkinter as tk
import customtkinter as ctk
from database.connection import get_db_cursor

class DropdownAutocompleteHelper:
    def __init__(self, entry_widget: ctk.CTkEntry, values_callback, multiple=False):
        """
        Helper to show a dropdown autocomplete popup below an Entry widget.
        
        entry_widget: The CTkEntry widget to bind.
        values_callback: A zero-argument function returning a list of strings.
        multiple: If True, allows comma-separated list selection (like tags).
        """
        self.entry = entry_widget
        self.values_callback = values_callback
        self.multiple = multiple
        self.popup = None
        self.listbox = None
        
        # We need to bind to the inner entry component to capture focus and key events properly
        self.inner_entry = entry_widget._entry
        
        self.inner_entry.bind("<FocusIn>", self.on_focus_in)
        self.inner_entry.bind("<FocusOut>", self.on_focus_out)
        self.inner_entry.bind("<KeyRelease>", self.on_key_release)
        self.inner_entry.bind("<KeyPress>", self.on_key_press)
        
    def get_current_search_and_bounds(self):
        content = self.entry.get()
        cursor_pos = self.inner_entry.index("insert")
        
        if not self.multiple:
            return content.lower().strip(), 0, len(content)
            
        # For multiple items (like tags: tag1, tag2)
        # Find which item the cursor is currently in
        parts = content.split(",")
        char_count = 0
        for i, part in enumerate(parts):
            next_char_count = char_count + len(part) + (1 if i < len(parts) - 1 else 0)
            if char_count <= cursor_pos <= next_char_count:
                return part.lower().strip(), char_count, char_count + len(part)
            char_count = next_char_count
            
        return "", 0, len(content)

    def show_popup(self):
        if self.popup:
            return
            
        all_values = self.values_callback()
        if not all_values:
            return
            
        # Create borderless floating window
        self.popup = tk.Toplevel(self.entry)
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
            font=self.inner_entry.cget("font"),
            bd=0,
            highlightthickness=0,
            height=5,
            width=30
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)
        
        # Close on selection or click
        self.listbox.bind("<ButtonRelease-1>", lambda e: self.insert_selection())
        
        # Position popup below entry
        self.position_popup()
        self.update_filter()

    def position_popup(self):
        self.popup.update_idletasks()
        
        # Get coordinates of the entry widget relative to screen
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        width = self.entry.winfo_width()
        
        # Match entry width
        popup_height = self.popup.winfo_reqheight()
        
        toplevel = self.entry.winfo_toplevel()
        toplevel_x = toplevel.winfo_rootx()
        toplevel_width = toplevel.winfo_width()
        max_right = toplevel_x + toplevel_width
        
        if x + width > max_right:
            x = max_right - width - 10
            x = max(toplevel_x, x)
            
        self.popup.geometry(f"{width}x{popup_height}+{x}+{y}")

    def close_popup(self):
        if self.popup:
            self.popup.destroy()
            self.popup = None
            self.listbox = None

    def on_focus_in(self, event):
        # Open popup immediately on click/focus
        self.entry.after(100, self.show_popup)

    def on_focus_out(self, event):
        # Delay closing slightly to allow listbox click events to process
        self.entry.after(200, self.check_focus_and_close)

    def check_focus_and_close(self):
        if not self.popup:
            return
        try:
            focused = self.entry.focus_get()
            if focused == self.listbox or focused == self.popup or focused == self.inner_entry:
                return
        except Exception:
            pass
        self.close_popup()

    def insert_selection(self):
        if not self.listbox:
            return
            
        selection_idx = self.listbox.curselection()
        if not selection_idx:
            return
            
        selected_value = self.listbox.get(selection_idx[0])
        if selected_value == "Nenhum resultado encontrado...":
            return
            
        content = self.entry.get()
        
        if not self.multiple:
            self.entry.delete(0, "end")
            self.entry.insert(0, selected_value)
        else:
            # Comma-separated replacement
            search_str, start, end = self.get_current_search_and_bounds()
            
            # Reconstruct string
            before = content[:start]
            after = content[end:]
            
            # Clean up leading spaces or commas
            if before and not before.endswith(" ") and not before.endswith(","):
                before += ", "
            elif before.endswith(","):
                before += " "
                
            new_item = selected_value
            
            # Construct final content
            new_content = before + new_item + after
            
            self.entry.delete(0, "end")
            self.entry.insert(0, new_content)
            
            # Move cursor right after the added item
            new_cursor_pos = len(before + new_item)
            self.inner_entry.icursor(new_cursor_pos)
            
        self.close_popup()

    def on_key_press(self, event):
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
        if event.keysym in ("Up", "Down", "Return", "Tab", "Escape"):
            return
            
        if not self.popup:
            self.show_popup()
        else:
            self.update_filter()

    def update_filter(self):
        if not self.listbox:
            return
            
        all_values = self.values_callback()
        query, _, _ = self.get_current_search_and_bounds()
        
        filtered = [v for v in all_values if not query or query in v.lower()]
        
        self.listbox.delete(0, "end")
        for item in filtered:
            self.listbox.insert("end", item)
            
        if filtered:
            self.listbox.selection_set(0)
            self.listbox.activate(0)
        else:
            self.listbox.insert("end", "Nenhum resultado encontrado...")

# Helper database querying functions
def get_unique_categories() -> list:
    categories = set()
    try:
        with get_db_cursor() as cursor:
            # Fetch categories from ideas
            cursor.execute("SELECT DISTINCT category FROM ideas WHERE category IS NOT NULL AND category != ''")
            for row in cursor.fetchall():
                categories.add(row[0])
                
            # Fetch categories from knowledge_pages
            cursor.execute("SELECT DISTINCT category FROM knowledge_pages WHERE category IS NOT NULL AND category != ''")
            for row in cursor.fetchall():
                categories.add(row[0])
    except Exception:
        pass
    return sorted(list(categories))

def get_all_unique_tags() -> list:
    tags = []
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT name FROM tags ORDER BY name ASC")
            tags = [row[0] for row in cursor.fetchall()]
    except Exception:
        pass
    return tags
