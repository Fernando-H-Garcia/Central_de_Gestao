import customtkinter as ctk
from gui.views.workbench import WorkbenchView
from gui.views.projects import ProjectsView
# Deprecated imports removed: TasksView, NotesView, IdeasView
from gui.views.notes import NotesView
from gui.views.ideas import IdeasView
from gui.views.wiki import WikiView
from gui.views.project_360 import Project360View
from gui.views.task_detail import TaskDetailView
from gui.dialogs import GlobalSearchDialog, SmartCaptureDialog

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Central de Gestão")
        self.geometry("1200x800")
        self.after(100, lambda: self.state('zoomed'))
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        self.btn_workbench = ctk.CTkButton(self.sidebar, text="Meu Dia", command=lambda: self.show_view("workbench"))
        self.btn_workbench.pack(pady=(35, 10), padx=20)

        self.btn_agenda = ctk.CTkButton(self.sidebar, text="Agenda", command=lambda: self.show_view("agenda"))
        self.btn_agenda.pack(pady=10, padx=20)

        self.btn_projects = ctk.CTkButton(self.sidebar, text="Projetos", command=lambda: self.show_view("projects"))
        self.btn_projects.pack(pady=10, padx=20)

        self.btn_wiki = ctk.CTkButton(self.sidebar, text="Wiki", command=lambda: self.show_view("wiki"))
        self.btn_wiki.pack(pady=10, padx=20)
        
        # Main Content
        self.content_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew")
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)
        
        from gui.views.agenda import AgendaView
        
        self.views = {}
        self.views["workbench"] = WorkbenchView(self.content_area)
        self.views["wiki"] = WikiView(self.content_area)
        self.views["projects"] = ProjectsView(self.content_area, open_360_callback=self.open_project_360)
        self.views["project_360"] = Project360View(self.content_area, go_back_callback=lambda: self.show_view("projects"))
        self.views["agenda"] = AgendaView(self.content_area)
        self.show_view("workbench")
        
        # Subscribe to global navigation events
        from core.event_bus import event_bus
        event_bus.subscribe("navigate_to", self.handle_navigation)
        
        # Configure tracking
        self.configure_count = 0
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self._configure_after_id = None
        self.bind("<Configure>", self.on_window_configure)

    def on_closing(self):
        from utils.instrumentation import PerformanceReport
        PerformanceReport.generate(self)
        self.destroy()

    def on_window_configure(self, event):
        """Debounced handler — escreve no log apenas após 400ms sem redimensionamento.
        Evita centenas de operações de disco ao mover a janela entre monitores."""
        if event.widget != self:
            return
        self.configure_count += 1
        # Cancela o timer anterior e agenda um novo
        if self._configure_after_id:
            self.after_cancel(self._configure_after_id)
        w, h = event.width, event.height
        cnt = self.configure_count
        self._configure_after_id = self.after(400, lambda: self._log_configure(cnt, w, h))

    def _log_configure(self, count, w, h):
        """Grava no log de instrumentação após o redimensionamento estabilizar."""
        import os, time
        from utils.instrumentation import LOG_PATH
        t = time.strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{t}] EVENT | <Configure> count: {count} | size: {w}x{h}\n"
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(log_line)

    def open_search(self):
        GlobalSearchDialog(self)
        
    def open_capture(self):
        SmartCaptureDialog(self)

    def open_project_360(self, project):
        self.views["project_360"].load_project(project)
        self.show_view("project_360")

    def show_view(self, name):
        for view in self.views.values():
            view.grid_remove()
        if name in self.views:
            view = self.views[name]
            view.grid(row=0, column=0, sticky="nsew")
            if getattr(view, '_is_dirty', False):
                if hasattr(view, 'on_entity_updated'):
                    view._is_dirty = False
                    view.on_entity_updated()

    def handle_navigation(self, data):
        from core.event_bus import event_bus
        entity_type = data.get("type")
        entity_id = data.get("id")
        
        if entity_type == "project":
            from services.project_service import ProjectService
            p = ProjectService().project_repo.get_by_id(entity_id)
            if p:
                self.open_project_360(p)
                
        elif entity_type == "task":
            from services.task_service import TaskService
            t = TaskService().task_repo.get_by_id(entity_id)
            if t:
                if t.project_id:
                    from services.project_service import ProjectService
                    p = ProjectService().project_repo.get_by_id(t.project_id)
                    if p:
                        self.open_project_360(p)
                        self.views["project_360"]._open_task_detail(t)
                else:
                    win = ctk.CTkToplevel(self)
                    win.title(f"Detalhe da Tarefa: {t.title}")
                    win.geometry("800x600")
                    win.update_idletasks()
                    x = (win.winfo_screenwidth() - 800) // 2
                    y = (win.winfo_screenheight() - 600) // 2
                    win.geometry(f"+{x}+{y}")
                    win.transient(self)
                    win.grab_set()
                    
                    frame = TaskDetailView(win, t, go_back_callback=win.destroy)
                    frame.pack(fill="both", expand=True)
                    
        elif entity_type == "idea":
            from services.idea_service import IdeaService
            idea = IdeaService().idea_repo.get_by_id(entity_id)
            if idea:
                from gui.views.project_360 import QuickIdeaEditDialog
                def save_idea(edited):
                    from services.idea_service import IdeaService
                    IdeaService().update_idea(edited, idea)
                    event_bus.emit("entity_updated")
                QuickIdeaEditDialog(self, idea=idea, on_save=save_idea)
                
        elif entity_type == "note":
            from services.note_service import NoteService
            note = NoteService().note_repo.get_by_id(entity_id)
            if note:
                from gui.views.project_360 import QuickNoteEditDialog
                def save_note(edited):
                    from services.note_service import NoteService
                    NoteService().update(edited)
                    event_bus.emit("entity_updated")
                QuickNoteEditDialog(self, note=note, on_save=save_note)
                
        elif entity_type == "wiki" or entity_type == "knowledge_page":
            from services.knowledge_page_service import KnowledgePageService
            pg = KnowledgePageService().page_repo.get_by_id(entity_id)
            if pg:
                self.show_view("wiki")
                self.views["wiki"].select_page(pg)

    def on_unresolved_link_click(self, name):
        from gui.dialogs import UnresolvedLinkDialog
        UnresolvedLinkDialog(self, name, on_create=self.create_entity_from_link)

    def create_entity_from_link(self, name, entity_type):
        from core.event_bus import event_bus
        from services.link_service import LinkService
        link_service = LinkService()
        
        if entity_type == "Projeto":
            from services.project_service import ProjectService
            proj = ProjectService().create_project(name=name)
            event_bus.emit("entity_updated")
            link_service.navigate_to_entity("project", proj.id)
            
        elif entity_type == "Tarefa":
            from services.task_service import TaskService
            task = TaskService().create_task(title=name)
            event_bus.emit("entity_updated")
            link_service.navigate_to_entity("task", task.id)
            
        elif entity_type == "Ideia":
            from services.idea_service import IdeaService
            idea = IdeaService().create_idea(title=name)
            event_bus.emit("entity_updated")
            link_service.navigate_to_entity("idea", idea.id)
            
        elif entity_type == "Nota":
            from services.note_service import NoteService
            from models.entities import Note
            note = Note(content=name)
            created = NoteService().create(note)
            event_bus.emit("entity_updated")
            link_service.navigate_to_entity("note", created.id)
            
        elif entity_type == "Página Wiki":
            from services.knowledge_page_service import KnowledgePageService
            pg = KnowledgePageService().create_page(title=name)
            event_bus.emit("entity_updated")
            link_service.navigate_to_entity("wiki", pg.id)


