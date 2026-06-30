import customtkinter as ctk
from gui.views.tasks import TasksView

class TaskPanel(ctk.CTkFrame):
    """Reusable panel that embeds the existing TasksView.
    It will be displayed inside Project360View.
    """
    def __init__(self, master, project_id=None, **kwargs):
        super().__init__(master, **kwargs)
        self.project_id = project_id
        # Initialize the original TasksView but hide its navigation controls
        self.tasks_view = TasksView(self)
        self.tasks_view.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        # Load tasks for the given project if provided
        if self.project_id is not None:
            self.load_project_tasks()

    def load_project_tasks(self):
        """Placeholder: actual implementation will query tasks for self.project_id.
        """
        # TODO: integrate with task_service to fetch tasks belonging to the project
        pass
