import threading
import queue
import time
from core.data_context import DataSnapshot, data_context
from core.event_bus import event_bus
from PySide6.QtCore import QObject, Signal

class WorkerSignals(QObject):
    snapshot_ready = Signal(object)

class SnapshotLoaderWorker:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SnapshotLoaderWorker, cls).__new__(cls)
            cls._instance.queue = queue.Queue()
            cls._instance.thread = None
            cls._instance.running = False
            cls._instance.signals = WorkerSignals()
            cls._instance.signals.snapshot_ready.connect(cls._instance._apply_snapshot)
        return cls._instance
        
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.thread.start()
            
    def request_reload(self):
        print(f"[SNAPSHOT] request_reload() called")
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break
        self.queue.put("reload")
        
    def _worker_loop(self):
        from services.task_service import TaskService
        from services.project_service import ProjectService
        from services.agenda_service import AgendaService
        
        while self.running:
            try:
                msg = self.queue.get(timeout=1.0)
                if msg == "reload":
                    start_time = time.time()
                    print(f"[SNAPSHOT] Worker: building snapshot...")
                    
                    new_snapshot = DataSnapshot()
                    
                    task_service = TaskService()
                    project_service = ProjectService()
                    agenda_service = AgendaService()
                    
                    active_tasks = task_service.task_repo.get_all(include_archived=False, include_deleted=False)
                    print(f"[SNAPSHOT] Worker: loaded {len(active_tasks)} tasks")
                    for t in active_tasks:
                        new_snapshot.tasks_by_id[t.id] = t
                        
                    active_projects = project_service.project_repo.get_all(include_archived=False, include_deleted=False)
                    print(f"[SNAPSHOT] Worker: loaded {len(active_projects)} projects")
                    for p in active_projects:
                        new_snapshot.projects_by_id[p.id] = p
                        
                    agenda_items = agenda_service.agenda_repo.get_all()
                    print(f"[SNAPSHOT] Worker: loaded {len(agenda_items)} agenda items")
                    for a in agenda_items:
                        new_snapshot.agenda_items_by_id[a.id] = a
                        
                    new_snapshot.task_dependencies = agenda_service.dep_repo.get_all()
                    print(f"[SNAPSHOT] Worker: loaded {len(new_snapshot.task_dependencies)} dependencies")
                    
                    print(f"[SNAPSHOT] Worker: emitting snapshot_ready signal (took {time.time()-start_time:.2f}s)")
                    self.signals.snapshot_ready.emit(new_snapshot)
                        
            except queue.Empty:
                pass
            except Exception as e:
                import traceback
                print(f"[SNAPSHOT WORKER] Error: {e}")
                traceback.print_exc()

    def _apply_snapshot(self, new_snapshot):
        tasks_count = len(new_snapshot.tasks_by_id)
        print(f"[SNAPSHOT] _apply_snapshot: {tasks_count} tasks, emitting snapshot_updated")
        data_context.swap_snapshot(new_snapshot)
        print(f"[SNAPSHOT] _apply_snapshot: swapped, now emitting event")
        event_bus.emit("snapshot_updated")
        print(f"[SNAPSHOT] _apply_snapshot: done")

snapshot_worker = SnapshotLoaderWorker()
