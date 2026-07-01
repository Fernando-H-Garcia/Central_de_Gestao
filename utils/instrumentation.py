import os
import time
from collections import defaultdict
PERFORMANCE_DEBUG = True

from config import LOGS_DIR
LOG_PATH = os.path.join(LOGS_DIR, "instrumentation_log.txt")

class PerfTracker:
    timings = defaultdict(list)          # category -> [duration_sec, ...]
    queries = defaultdict(int)           # sql -> count
    query_times = defaultdict(float)     # sql -> total_time_sec
    total_db_time_sec = 0.0
    total_render_time_sec = 0.0
    total_process_time_sec = 0.0
    widgets_created = 0

    @classmethod
    def reset(cls):
        cls.timings.clear()
        cls.queries.clear()
        cls.query_times.clear()
        cls.total_db_time_sec = 0.0
        cls.total_render_time_sec = 0.0
        cls.total_process_time_sec = 0.0
        cls.widgets_created = 0

class PerfContext:
    def __init__(self, name: str, module: str = None, category: str = "Processamento"):
        """
        name: Name of the step (e.g. 'Buscar projeto')
        module: The main view/module grouping (e.g. 'Visão 360', 'Agenda')
        category: 'Processamento', 'Renderização', 'Banco'
        """
        self.name = name
        self.module = module
        self.category = category
        self.start_time = 0

    def __enter__(self):
        if not PERFORMANCE_DEBUG: return self
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not PERFORMANCE_DEBUG: return
        duration = time.perf_counter() - self.start_time
        
        if self.category == "Renderização":
            PerfTracker.total_render_time_sec += duration
        elif self.category == "Processamento":
            PerfTracker.total_process_time_sec += duration
        elif self.category == "Banco":
            PerfTracker.total_db_time_sec += duration
            
        if self.module:
            PerfTracker.timings[self.module].append(duration)

        # print(f"[PERF] {self.name.ljust(35, '.')} {duration:.3f}s")

class PerformanceReport:
    @staticmethod
    def generate(app=None):
        if not PERFORMANCE_DEBUG:
            # print("Performance monitoring is disabled (PERFORMANCE_DEBUG = False).")
            return
            
        # print("\n==============================")
        # print("CONTAGEM DE WIDGETS POR TELA (Sprint 1.1)")
        # print("==============================")
        if app and hasattr(app, "views"):
            for name, view in app.views.items():
                c = count_widgets_recursive(view)
                # print(f"{name.capitalize()}\nWidgets ativos: {c}\n")
                pass
        else:
            pass
            # print("Instância do app não fornecida para contagem.")

        # print("\n==============================")
        # print("PERFORMANCE REPORT")
        # print("==============================")
        
        for category, times in PerfTracker.timings.items():
            if times:
                avg = sum(times) / len(times)
                # print(f"\n{category}")
                # print(f"Tempo Médio: {avg:.2f}s (Amostras: {len(times)})")
            
        # print(f"\nConsultas Executadas\n{sum(PerfTracker.queries.values())}")
        # print(f"\nTempo Total Banco\n{PerfTracker.total_db_time_sec:.2f}s")
        # print(f"\nTempo Total Renderização\n{PerfTracker.total_render_time_sec:.2f}s")
        # print(f"\nTempo Total Processamento\n{PerfTracker.total_process_time_sec:.2f}s")
        # print(f"\nWidgets Criados\n{PerfTracker.widgets_created}")
        
        times = [
            ("Banco", PerfTracker.total_db_time_sec),
            ("Renderização de Widgets", PerfTracker.total_render_time_sec),
            ("Processamento", PerfTracker.total_process_time_sec)
        ]
        times.sort(key=lambda x: x[1], reverse=True)
        if times[0][1] > 0:
            pass
            # print(f"\nMaior Gargalo\n{times[0][0]} ({times[0][1]:.2f}s)")

        # print("==============================")

        repetitive = [(sql, count, PerfTracker.query_times[sql]) for sql, count in PerfTracker.queries.items() if count > 1]
        if repetitive:
            repetitive.sort(key=lambda x: x[1], reverse=True)
            # print("\n*** AVISO: Consultas Repetidas (Possível N+1) ***")
            for sql, count, t_time in repetitive[:10]: # top 10
                pass
                # print(f"[DB] {sql[:80]}...\nExecutada: {count} vezes\nTempo total: {t_time:.3f}s\n")



def count_widgets_recursive(widget):
    if not widget or not hasattr(widget, "winfo_children"):
        return 0
    try:
        children = widget.winfo_children()
        total = len(children) + sum(count_widgets_recursive(child) for child in children)
        if PERFORMANCE_DEBUG:
            # We don't want to increment global counter on every single query of it unless it's a true creation.
            # But the user asked to track total created widgets. We can log it per view.
            pass
        return total
    except Exception:
        return 0

def log_perf_data(view_name: str, method_name: str, duration: float, widgets_destroyed: int, widgets_created: int, loaded_items: int = 0, trigger: str = "init"):
    if not PERFORMANCE_DEBUG: return
    PerfTracker.widgets_created += widgets_created
    
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    t = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{t}] [UI] Refresh completo da {view_name}.{method_name} | trigger: {trigger} | Tempo: {duration:.2f}s | created: {widgets_created}\n"
    # print(log_line.strip())
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(log_line)

def log_db_query(sql: str, duration: float):
    if not PERFORMANCE_DEBUG: return
    PerfTracker.total_db_time_sec += duration
    clean_sql = " ".join(sql.strip().split())
    PerfTracker.queries[clean_sql] += 1
    PerfTracker.query_times[clean_sql] += duration
    
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    t = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{t}] DB   | query time: {duration:.3f}s | SQL: {clean_sql[:100]}...\n"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(log_line)
