import threading
import queue
import logging

class TaskQueue:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TaskQueue, cls).__new__(cls)
                cls._instance._init_queue()
            return cls._instance

    def _init_queue(self):
        self.q = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker, daemon=True, name="TaskQueueWorker")
        self.worker_thread.start()

    def _worker(self):
        while True:
            func, args, kwargs = self.q.get()
            try:
                func(*args, **kwargs)
            except Exception as e:
                logging.error(f"Error in TaskQueue background task {func.__name__}: {e}", exc_info=True)
            finally:
                self.q.task_done()

    def submit(self, func, *args, **kwargs):
        """Submit a task to run in the background."""
        self.q.put((func, args, kwargs))

# Global instance for easy imports
task_queue = TaskQueue()
