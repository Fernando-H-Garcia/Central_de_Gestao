import customtkinter as ctk
import tkinter as tk
import tkinter.messagebox as messagebox

# Monkeypatch wm_overrideredirect to handle Tcl/Tk returning None or empty string on Windows under CustomTkinter
orig_overrideredirect = tk.Toplevel.wm_overrideredirect
def patched_overrideredirect(self, boolean=None):
    try:
        if boolean is None:
            val = orig_overrideredirect(self)
            return val if val is not None else False
        else:
            self.tk.call('wm', 'overrideredirect', self._w, boolean)
    except Exception:
        pass

tk.Toplevel.wm_overrideredirect = patched_overrideredirect
tk.Toplevel.overrideredirect = patched_overrideredirect

from gui.components.ctk_calendar import CTkCalendar
from gui.components.context_menu import ContextMenu
from datetime import datetime
from services.alert_service import AlertService
from gui.dialogs.alert_edit_dialog import AlertEditDialog
from models.alert import Alert
import copy

class AlertManagerDialog(ctk.CTkToplevel):
    # Static dictionary to manage singleton instances by (entity_type, entity_id)
    _instances = {}

    @classmethod
    def get_instance(cls, master, entity_type: str, entity_id: int, entity_title: str):
        key = (entity_type, entity_id)
        if key in cls._instances:
            try:
                # If window is open, bring it to front
                inst = cls._instances[key]
                inst.deiconify()
                inst.focus_force()
                return inst
            except Exception:
                # In case reference is dead but key exists
                pass

        # Create new instance and track it
        inst = cls(master, entity_type, entity_id, entity_title)
        cls._instances[key] = inst
        return inst

    def __init__(self, master, entity_type: str, entity_id: int, entity_title: str):
        super().__init__(master)
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.entity_title = entity_title
        self.alert_service = AlertService()

        self.title(f"Alertas - {entity_title}")
        self.geometry("820x500")
        self.resizable(False, False)

        # Set position center
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 820) // 2
        y = (self.winfo_screenheight() - 500) // 2
        self.geometry(f"+{x}+{y}")
        self.transient(master)

        # Clean key from singleton tracker on destroy
        self.bind("<Destroy>", self.on_destroy)

        # UI Layout (Split View)
        # Left Panel (Calendar) & Right Panel (Alert List)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1, minsize=400) # Left
        self.grid_columnconfigure(1, weight=1, minsize=400) # Right

        # ==========================================
        # LEFT PANEL: Calendar
        # ==========================================
        self.left_panel = ctk.CTkFrame(self, corner_radius=0)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Header
        self.lbl_cal_header = ctk.CTkLabel(self.left_panel, text="Calendário de Alertas", font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_cal_header.pack(pady=10)

        self.calendar = CTkCalendar(self.left_panel, on_date_select=self.on_date_selected)
        self.calendar.pack(fill="both", expand=True, padx=15, pady=15)

        # ==========================================
        # RIGHT PANEL: Alerts List
        # ==========================================
        self.right_panel = ctk.CTkFrame(self, corner_radius=0)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.right_panel.grid_rowconfigure(1, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

        # List Header
        self.lbl_list_header = ctk.CTkLabel(self.right_panel, text="Alertas da Data Selecionada", font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_list_header.grid(row=0, column=0, pady=10, sticky="ew")

        # Scrollable list container
        self.scroll_list = ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent")
        self.scroll_list.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        # Bottom section: New Alert Button
        self.btn_new = ctk.CTkButton(
            self.right_panel, 
            text="+ Novo Alerta", 
            fg_color="#2B8C52", 
            hover_color="#1E663B", 
            command=self.open_new_alert_dialog
        )
        self.btn_new.grid(row=2, column=0, pady=15, padx=20, sticky="ew")

        # Initial loading
        self.refresh()

    def on_destroy(self, event):
        key = (self.entity_type, self.entity_id)
        if key in AlertManagerDialog._instances:
            del AlertManagerDialog._instances[key]

    def on_date_selected(self, event=None):
        self.refresh_alerts_list()

    def refresh(self):
        self.refresh_calendar_indicators()
        self.refresh_alerts_list()

    def refresh_calendar_indicators(self):
        """Places color and count markers on calendar days containing alerts."""
        alerts = self.alert_service.get_alerts_for_entity(self.entity_type, self.entity_id)
        
        # Group alerts by date to count quantities and determine color priority
        from collections import defaultdict
        grouped = defaultdict(list)
        for a in alerts:
            if a.status in ('pending', 'overdue'):
                grouped[a.alert_date].append(a)

        # Setup events dict for CTkCalendar
        events_dict = {}
        for date_str, date_alerts in grouped.items():
            priorities = [a.priority for a in date_alerts]
            if 'high' in priorities:
                events_dict[date_str] = 'high'
            elif 'medium' in priorities:
                events_dict[date_str] = 'medium'
            else:
                events_dict[date_str] = 'low'
                
        self.calendar.set_events(events_dict)


    def refresh_alerts_list(self):
        # Clear existing cards
        for w in self.scroll_list.winfo_children():
            w.destroy()

        selected_date_str = self.calendar.get_date() # Format: YYYY-MM-DD
        
        # Load all alerts for this entity
        all_entity_alerts = self.alert_service.get_alerts_for_entity(self.entity_type, self.entity_id)
        
        # Filter by selected date
        day_alerts = [a for a in all_entity_alerts if a.alert_date == selected_date_str]

        if not day_alerts:
            ctk.CTkLabel(
                self.scroll_list, 
                text="Nenhum alerta para esta data.", 
                text_color="gray",
                font=ctk.CTkFont(slant="italic")
            ).pack(pady=40)
            return

        # Render list of alerts for the day
        for alert in day_alerts:
            prio_color = "#C23616" if alert.priority == 'high' else ("#B8860B" if alert.priority == 'medium' else "#1a5c9e")
            prio_text = "Alta" if alert.priority == 'high' else ("Média" if alert.priority == 'medium' else "Baixa")
            is_dark = ctk.get_appearance_mode() == "Dark"
            if alert.status == 'overdue':
                card_bg = "#3b1d1d" if is_dark else "#fde8e8"
            else:
                card_bg = "#2b2b2b" if is_dark else "#e0e0e0"
            card = ctk.CTkFrame(self.scroll_list, fg_color=card_bg, corner_radius=6)
            card.pack(fill="x", pady=3, padx=2)

            # Color Bar indicator
            left_bar = ctk.CTkFrame(card, width=4, corner_radius=2, fg_color=prio_color)
            left_bar.pack(side="left", fill="y", padx=(2, 0), pady=4)

            content_frame = ctk.CTkFrame(card, fg_color="transparent")
            content_frame.pack(side="left", fill="x", expand=True, padx=8, pady=2)

            title_str = f"[{prio_text}] {alert.title}"
            if alert.alert_time:
                title_str = f"⏰ {alert.alert_time} | {title_str}"
            
            lbl_title = ctk.CTkLabel(content_frame, text=title_str, font=ctk.CTkFont(size=12, weight="bold"), anchor="w")
            lbl_title.pack(anchor="w")

            if alert.description:
                # Truncate description if too long
                desc_text = alert.description.replace('\n', ' ')
                if len(desc_text) > 60:
                    desc_text = desc_text[:57] + "..."
                lbl_desc = ctk.CTkLabel(content_frame, text=desc_text, font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
                lbl_desc.pack(anchor="w")

            status_map_pt = {
                'pending': 'Pendente',
                'overdue': 'Atrasado',
                'completed': 'Concluído',
                'cancelled': 'Cancelado',
                'dismissed': 'Descartado'
            }
            status_str = f"Status: {status_map_pt.get(alert.status, alert.status)}"
            if alert.status == 'completed':
                status_color = "#2B8C52"
            elif alert.status == 'overdue':
                status_color = "#ef4444"
            elif alert.status == 'cancelled':
                status_color = "gray"
            else:
                status_color = "#3b82f6"

            lbl_status = ctk.CTkLabel(content_frame, text=status_str, font=ctk.CTkFont(size=11, slant="italic"), text_color=status_color, anchor="w", height=16)
            lbl_status.pack(anchor="w", pady=(2, 0))

            # Recursive bindings helper for double click and right click
            def bind_events_recursive(w, a=alert):
                if isinstance(w, ctk.CTkButton):
                    return
                # Double click left button to edit
                w.bind("<Double-Button-1>", lambda e, al=a: self.open_edit_alert_dialog(al))
                # Right click (Button-3) for context menu
                w.bind("<Button-3>", lambda e, al=a: self.show_context_menu(e, al))
                for child in w.winfo_children():
                    bind_events_recursive(child, a)
                if hasattr(w, "_canvas"):
                    w._canvas.bind("<Double-Button-1>", lambda e, al=a: self.open_edit_alert_dialog(al))
                    w._canvas.bind("<Button-3>", lambda e, al=a: self.show_context_menu(e, al))
                if hasattr(w, "_text_label"):
                    w._text_label.bind("<Double-Button-1>", lambda e, al=a: self.open_edit_alert_dialog(al))
                    w._text_label.bind("<Button-3>", lambda e, al=a: self.show_context_menu(e, al))

            bind_events_recursive(card)


    def show_context_menu(self, event, alert):
        menu = ContextMenu(self)
        menu.add_command("✏️ Editar", command=lambda: self.open_edit_alert_dialog(alert))
        if self.entity_type == 'task':
            menu.add_command("👁 Abrir Tarefa", command=lambda: self.open_entity(alert))
        if alert.status in ('pending', 'overdue'):
            menu.add_command("✅ Concluir", command=lambda: self.complete_alert_quick(alert.id))
        menu.add_separator()
        menu.add_command("🗑 Excluir", command=lambda: self.delete_alert(alert.id), danger=True)
        menu.popup(event.x_root, event.y_root)


    def open_entity(self, alert):
        """Bridges directly to open the task details page."""
        self.destroy()
        from services.link_service import LinkService
        LinkService().navigate_to_entity(self.entity_type, self.entity_id)

    def open_new_alert_dialog(self):
        selected_date_str = self.calendar.get_date()
        
        # Prepare dummy alert object for default date
        default_alert = Alert(
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            title="",
            alert_date=selected_date_str
        )

        def on_save(title, description, alert_date, alert_time, priority, status):
            self.alert_service.create_alert(
                entity_type=self.entity_type,
                entity_id=self.entity_id,
                title=title,
                description=description,
                alert_date=alert_date,
                alert_time=alert_time,
                priority=priority,
                status=status
            )
            # Trigger updates
            from core.event_bus import event_bus
            event_bus.emit("entity_updated")
            self.refresh()

        AlertEditDialog(self, self.entity_type, self.entity_id, alert=default_alert, on_save=on_save)

    def open_edit_alert_dialog(self, alert: Alert):
        orig = copy.deepcopy(alert)

        def on_save(title, description, alert_date, alert_time, priority, status):
            alert.title = title
            alert.description = description
            alert.alert_date = alert_date
            alert.alert_time = alert_time
            alert.priority = priority
            alert.status = status
            self.alert_service.update_alert(alert, orig)
            
            from core.event_bus import event_bus
            event_bus.emit("entity_updated")
            self.refresh()

        AlertEditDialog(self, self.entity_type, self.entity_id, alert=alert, on_save=on_save)

    def delete_alert(self, alert_id: int):
        if messagebox.askyesno("Excluir", "Deseja excluir este alerta de forma definitiva?"):
            self.alert_service.delete_alert(alert_id)
            from core.event_bus import event_bus
            event_bus.emit("entity_updated")
            self.refresh()

    def complete_alert_quick(self, alert_id: int):
        self.alert_service.complete_alert(alert_id)
        from core.event_bus import event_bus
        event_bus.emit("entity_updated")
        self.refresh()

