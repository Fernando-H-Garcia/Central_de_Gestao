import sqlite3
import contextlib
import config

def get_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with optimized PRAGMAs for performance."""
    conn = sqlite3.connect(str(config.DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    # PRAGMAs required by the V1 implementation plan
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA cache_size = -10000;")
    return conn

@contextlib.contextmanager
def get_db_cursor():
    """Context manager for easy cursor usage with automatic commit/rollback."""
    class TimedCursor:
        def __init__(self, cursor):
            self._cursor = cursor
        def __getattr__(self, name):
            return getattr(self._cursor, name)
        def execute(self, sql, *args, **kwargs):
            import time
            import traceback
            import os
            from utils.instrumentation import log_db_query
            
            # Find the actual caller in the stack trace to detect redundant calls
            stack = traceback.extract_stack()
            caller_info = "unknown"
            for frame in reversed(stack[:-1]):
                filename = frame.filename
                if "connection.py" not in filename and "sqlite3" not in filename and "contextlib" not in filename:
                    caller_info = f"{os.path.basename(filename)}:{frame.lineno} in {frame.name}"
                    break
            
            start = time.perf_counter()
            try:
                return self._cursor.execute(sql, *args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                log_db_query(sql, duration)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        yield TimedCursor(cursor)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

