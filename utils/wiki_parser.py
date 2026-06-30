import re
import tkinter as tk
import customtkinter as ctk
from services.link_service import LinkService

WIKI_LINK_RE = re.compile(r'\[\[(?:([a-zA-Z0-9_]+):(\d+)\|)?(.*?)\]\]')

def render_wiki_text(ctk_textbox: ctk.CTkTextbox, raw_text: str, on_create_callback=None):
    """
    Parses raw_text for [[type:id|Display Name]] or [[Entity Name]] patterns and renders them inside the ctk_textbox.
    Resolved links are styled in green and navigate on click.
    Unresolved links are styled in red and trigger the creation popup.
    """
    # Access the underlying tk.Text widget
    text_widget = ctk_textbox._textbox
    
    # Enable editing to update content
    ctk_textbox.configure(state="normal")
    text_widget.delete("0.0", "end")
    
    if not raw_text:
        ctk_textbox.configure(state="disabled")
        return
 
    link_service = LinkService()
    last_idx = 0
    
    # Configure default text layout tags
    text_widget.tag_config("default", spacing2=3, spacing3=3)
    
    # Regex search for links
    for match in WIKI_LINK_RE.finditer(raw_text):
        start, end = match.span()
        t_type = match.group(1)
        t_id = match.group(2)
        display_name = match.group(3).strip()
        
        # Insert text before the link pattern
        if start > last_idx:
            text_widget.insert("end", raw_text[last_idx:start], "default")
            
        resolved = None
        if t_type and t_id:
            # Query by explicit type and ID
            normalized_type = t_type.lower().strip()
            if normalized_type == "knowledge_page":
                normalized_type = "wiki"
            try:
                entity_obj = link_service._load_entity(normalized_type, int(t_id))
                if entity_obj:
                    actual_title = link_service._get_entity_title(normalized_type, entity_obj)
                    resolved = {
                        "type": normalized_type,
                        "id": int(t_id),
                        "title": actual_title
                    }
            except Exception:
                pass
        else:
            # Fallback to name resolution
            resolved = link_service.find_entity_by_name(display_name)
            
        tag_name = f"link_{start}_{end}"
        if resolved:
            # Render resolved link showing the actual title in the DB
            link_text = f"[[{resolved['title']}]]"
            text_widget.insert("end", link_text, (tag_name, "default"))
            
            # Style as green/blue hyperlink
            text_widget.tag_config(tag_name, foreground="#2B8C52", underline=True)
            
            # Bind navigation
            target_type = resolved["type"]
            target_id = resolved["id"]
            text_widget.tag_bind(tag_name, "<Button-1>", lambda e, t=target_type, idx=target_id: link_service.navigate_to_entity(t, idx))
        else:
            # Render unresolved link
            link_text = f"🔴 [[{display_name}]]"
            text_widget.insert("end", link_text, (tag_name, "default"))
            
            # Style as red broken link
            text_widget.tag_config(tag_name, foreground="#C23616", underline=True)
            
            # Bind creation dialog
            if on_create_callback:
                text_widget.tag_bind(tag_name, "<Button-1>", lambda e, name=display_name: on_create_callback(name))
                
        # Hover cursor effects
        text_widget.tag_bind(tag_name, "<Enter>", lambda e: ctk_textbox.configure(cursor="hand2"))
        text_widget.tag_bind(tag_name, "<Leave>", lambda e: ctk_textbox.configure(cursor="arrow"))
        
        last_idx = end
        
    # Insert remaining text after last match
    if last_idx < len(raw_text):
        text_widget.insert("end", raw_text[last_idx:], "default")
        
    # Disable textbox for read-only navigation experience
    ctk_textbox.configure(state="disabled")

import os

