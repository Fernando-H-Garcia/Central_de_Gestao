import logging
import sys
import traceback
from config import LOGS_DIR

log_file = LOGS_DIR / "app_errors.log"
logging.basicConfig(
    filename=str(log_file),
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    print(f"Um erro inesperado ocorreu. Detalhes salvos em {log_file}")

def setup_global_error_handler():
    sys.excepthook = handle_exception
