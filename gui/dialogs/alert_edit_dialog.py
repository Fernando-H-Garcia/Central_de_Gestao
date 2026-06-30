import customtkinter as ctk
import tkinter.messagebox as messagebox
from gui.components.date_picker import DatePickerFrame
from models.alert import Alert

class AlertEditDialog(ctk.CTkToplevel):
    def __init__(self, master, entity_type: str, entity_id: int, alert: Alert = None, on_save=None):
        super().__init__(master)
        self.title("Novo Alerta" if not alert else "Editar Alerta")
        self.geometry("460x580")
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.alert = alert
        self.on_save = on_save

        self.resizable(False, False)
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 460) // 2
        y = (self.winfo_screenheight() - 580) // 2
        self.geometry(f"+{x}+{y}")
        self.transient(master)
        self.grab_set()

        # Layout configuration
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=15, pady=(10, 5))

        # Modern Card Container
        is_dark = ctk.get_appearance_mode() == "Dark"
        card_bg = "#1e1e2e" if is_dark else "#f8f9fc"
        self.card = ctk.CTkFrame(self.scroll, fg_color=card_bg, corner_radius=10)
        self.card.pack(fill="both", expand=True, padx=5, pady=5)

        lp = dict(padx=20, pady=(10, 2), anchor="w")
        wp = dict(padx=20, pady=(0, 8), fill="x")

        # Title Label in the form
        self.lbl_form_title = ctk.CTkLabel(
            self.card, 
            text="Novo Alerta" if not self.alert or not getattr(self.alert, 'id', None) else "Editar Alerta",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.lbl_form_title.pack(pady=(15, 15), padx=20, anchor="w")

        ctk.CTkLabel(self.card, text="Título do Alerta:", font=ctk.CTkFont(size=13, weight="bold"), text_color="gray").pack(**lp)
        self.ent_title = ctk.CTkEntry(self.card, width=380, placeholder_text="Ex: Verificar status...", height=35)
        self.ent_title.pack(**wp)

        ctk.CTkLabel(self.card, text="Descrição / Detalhes:", font=ctk.CTkFont(size=13, weight="bold"), text_color="gray").pack(**lp)
        self.txt_desc = ctk.CTkTextbox(self.card, height=80, width=380)
        self.txt_desc.pack(**wp)

        ctk.CTkLabel(self.card, text="Data:", font=ctk.CTkFont(size=13, weight="bold"), text_color="gray").pack(**lp)
        self.dp_date = DatePickerFrame(self.card)
        self.dp_date.pack(**wp)

        ctk.CTkLabel(self.card, text="Hora (Opcional, Ex: 14:30):", font=ctk.CTkFont(size=13, weight="bold"), text_color="gray").pack(**lp)
        self.ent_time = ctk.CTkEntry(self.card, width=380, placeholder_text="Ex: 14:00", height=35)
        self.ent_time.pack(**wp)

        ctk.CTkLabel(self.card, text="Prioridade:", font=ctk.CTkFont(size=13, weight="bold"), text_color="gray").pack(**lp)
        self.opt_priority = ctk.CTkOptionMenu(self.card, values=["Alta", "Média", "Baixa"], width=380, height=35)
        self.opt_priority.pack(**wp)
        self.opt_priority.set("Média")

        is_editing = self.alert and getattr(self.alert, 'id', None) is not None
        status_map_pt = {
            'pending': 'Pendente',
            'overdue': 'Atrasado',
            'completed': 'Concluído',
            'cancelled': 'Cancelado',
            'dismissed': 'Descartado'
        }
        if is_editing:
            ctk.CTkLabel(self.card, text="Status:", font=ctk.CTkFont(size=13, weight="bold"), text_color="gray").pack(**lp)
            self.opt_status = ctk.CTkOptionMenu(self.card, values=["Pendente", "Atrasado", "Concluído", "Cancelado"], width=380, height=35)
            self.opt_status.pack(**wp)
            self.opt_status.set("Pendente")
        else:
            self.opt_status = None


        # Load values if editing
        if self.alert:
            self.ent_title.insert(0, self.alert.title)
            if self.alert.description:
                self.txt_desc.insert("0.0", self.alert.description)
            if self.alert.alert_date:
                self.dp_date.set_date(self.alert.alert_date)
            if self.alert.alert_time:
                self.ent_time.insert(0, self.alert.alert_time)
            
            prio_map = {'high': 'Alta', 'medium': 'Média', 'low': 'Baixa'}
            self.opt_priority.set(prio_map.get(self.alert.priority, 'Média'))
            if is_editing and self.opt_status:
                self.opt_status.set(status_map_pt.get(self.alert.status, 'Pendente'))

        # Buttons
        self.btn_save = ctk.CTkButton(
            self, 
            text="Salvar Alerta", 
            height=36,
            fg_color="#2B8C52", 
            hover_color="#1E663B", 
            font=ctk.CTkFont(weight="bold"),
            command=self.save
        )
        self.btn_save.pack(pady=(10, 20), padx=30, fill="x")

    def save(self):
        title = self.ent_title.get().strip()
        if not title:
            messagebox.showwarning("Aviso", "O título do alerta é obrigatório.")
            return

        date_val = self.dp_date.get_date()
        if not date_val:
            messagebox.showwarning("Aviso", "A data do alerta é obrigatória.")
            return

        time_val = self.ent_time.get().strip() or None
        # Quick validation of format if supplied
        if time_val and ":" not in time_val:
            messagebox.showwarning("Aviso", "Formato de hora inválido. Use HH:MM")
            return

        prio_map_rev = {'Alta': 'high', 'Média': 'medium', 'Baixa': 'low'}
        priority = prio_map_rev.get(self.opt_priority.get(), 'medium')

        status_map_rev = {
            'Pendente': 'pending',
            'Atrasado': 'overdue',
            'Concluído': 'completed',
            'Cancelado': 'cancelled',
            'Descartado': 'dismissed'
        }
        status = status_map_rev.get(self.opt_status.get(), 'pending') if self.opt_status else "pending"

        desc = self.txt_desc.get("0.0", "end-1c").strip() or None

        if self.on_save:
            self.on_save(
                title=title,
                description=desc,
                alert_date=date_val,
                alert_time=time_val,
                priority=priority,
                status=status
            )
        self.destroy()

