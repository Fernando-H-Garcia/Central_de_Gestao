import customtkinter as ctk
from typing import List
from models.alert import Alert
from services.alert_service import AlertService

class TaskAlertPopup(ctk.CTkToplevel):
    def __init__(self, master, task_id: int, task_title: str, alerts: List[Alert], alert_service: AlertService):
        super().__init__(master)
        self.task_id = task_id
        self.task_title = task_title
        self.alerts = alerts
        self.alert_service = alert_service
        self.resolved_ids = set()

        self.title("Alertas da Tarefa")
        self.geometry("500x450")
        self.resizable(False, False)
        
        # Center popup
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 500) // 2
        y = (self.winfo_screenheight() - 450) // 2
        self.geometry(f"+{x}+{y}")
        self.transient(master)
        self.grab_set()

        # Protocol for closing window
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Title/Header
        self.lbl_title = ctk.CTkLabel(
            self, 
            text=f"🔔 Alertas Ativos - {self.task_title}", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.lbl_title.pack(pady=(15, 10), padx=20, anchor="w")

        # Scrollable container for alerts
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        self.render_alerts()

        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", side="bottom", padx=15, pady=15)
        
        self.btn_close = ctk.CTkButton(
            footer, 
            text="Fechar", 
            fg_color="#4b5563", 
            hover_color="#374151", 
            command=self.on_close
        )
        self.btn_close.pack(side="right")

    def render_alerts(self):
        # Clear existing children
        for child in self.scroll.winfo_children():
            child.destroy()

        active_list = [a for a in self.alerts if a.id not in self.resolved_ids]
        if not active_list:
            # All resolved! Auto-close
            self.destroy()
            return

        for alert in active_list:
            is_dark = ctk.get_appearance_mode() == "Dark"
            card_bg = "#1e1e2e" if is_dark else "#f8f9fc"
            card = ctk.CTkFrame(self.scroll, fg_color=card_bg, corner_radius=8)
            card.pack(fill="x", pady=6, padx=5)

            is_overdue = alert.status == 'overdue'
            if is_overdue:
                status_text = "ATRASADO"
                status_color = "#ef4444"
            else:
                status_text = "PENDENTE"
                status_color = "#3b82f6"

            # 4px Left colored stripe
            stripe = ctk.CTkFrame(card, width=4, corner_radius=2, fg_color=status_color)
            stripe.pack(side="left", fill="y", padx=(4, 0), pady=6)
            stripe.pack_propagate(False)

            # Content container
            content_frame = ctk.CTkFrame(card, fg_color="transparent")
            content_frame.pack(side="left", fill="both", expand=True, padx=12, pady=10)

            # Badge & Title row
            badge_title_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            badge_title_frame.pack(fill="x", anchor="w")

            lbl_badge = ctk.CTkLabel(
                badge_title_frame, 
                text=f" {status_text} ", 
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="white",
                fg_color=status_color,
                corner_radius=4
            )
            lbl_badge.pack(side="left", padx=(0, 8))

            lbl_title = ctk.CTkLabel(
                badge_title_frame, 
                text=alert.title, 
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w"
            )
            lbl_title.pack(side="left", fill="x", expand=True)

            # Description
            if alert.description:
                lbl_desc = ctk.CTkLabel(
                    content_frame, 
                    text=alert.description, 
                    font=ctk.CTkFont(size=12),
                    text_color="#94a3b8",
                    wraplength=420,
                    justify="left",
                    anchor="w"
                )
                lbl_desc.pack(fill="x", pady=(4, 2), anchor="w")

            # Date/Time
            time_str = f" às {alert.alert_time}" if alert.alert_time else ""
            date_formatted = alert.alert_date
            try:
                from datetime import datetime
                dt = datetime.strptime(alert.alert_date, "%Y-%m-%d")
                date_formatted = dt.strftime("%d/%m/%Y")
            except:
                pass
            lbl_date = ctk.CTkLabel(
                content_frame, 
                text=f"Agendado para: {date_formatted}{time_str}", 
                font=ctk.CTkFont(size=11),
                text_color="#cbd5e1",
                anchor="w"
            )
            lbl_date.pack(fill="x", pady=(2, 6), anchor="w")

            # Action Buttons Frame
            actions_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            actions_frame.pack(fill="x", pady=(4, 0))

            # "Concluir Alerta" button
            btn_complete = ctk.CTkButton(
                actions_frame,
                text="✅ Concluir Alerta",
                width=130,
                height=28,
                fg_color="#059669",
                hover_color="#047857",
                command=lambda a_id=alert.id: self.action_complete(a_id)
            )
            btn_complete.pack(side="left", padx=(0, 10))

            # "Adiar Alerta" option dropdown menu
            lbl_adiar = ctk.CTkLabel(actions_frame, text="Adiar:", font=ctk.CTkFont(size=12))
            lbl_adiar.pack(side="left", padx=(0, 5))

            opt_adiar = ctk.CTkOptionMenu(
                actions_frame,
                values=["10 min", "30 min", "1 hora", "1 dia"],
                width=100,
                height=28,
                command=lambda val, a_id=alert.id: self.action_snooze(a_id, val)
            )
            opt_adiar.set("Adiar Alerta")
            opt_adiar.pack(side="left")

    def action_complete(self, alert_id: int):
        self.alert_service.complete_alert(alert_id)
        self.resolved_ids.add(alert_id)
        self.render_alerts()

    def action_snooze(self, alert_id: int, option_str: str):
        # option_str can be: "10 min", "30 min", "1 hora", "1 dia"
        mapping = {
            "10 min": "10min",
            "30 min": "30min",
            "1 hora": "1h",
            "1 dia": "1dia"
        }
        snooze_val = mapping.get(option_str, "10min")
        self.alert_service.snooze_alert(alert_id, snooze_val)
        self.resolved_ids.add(alert_id)
        self.render_alerts()

    def on_close(self):
        # Mark all unresolved alerts in this popup as overdue
        active_list = [a for a in self.alerts if a.id not in self.resolved_ids]
        for alert in active_list:
            self.alert_service.mark_alert_overdue(alert.id)
        self.destroy()
