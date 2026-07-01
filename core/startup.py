"""First Run Hardening — auto-configuração, auto-repair e self-test."""

import json
import logging
import sqlite3
import shutil
import sys
from datetime import datetime
from pathlib import Path

import config
from config import (
    _is_bundled, DATA_DIR, DB_DIR, DB_PATH, MIGRATIONS_DIR,
    CONFIG_DIR, LOGS_DIR, BACKUPS_DIR, ATTACHMENTS_STORAGE_DIR,
    INSTALL_DB_PATH, INSTALL_MIGRATIONS_DIR, INSTALL_CONFIG_DIR,
)

DEFAULT_CONFIG_TEMPLATE = {
    "theme": "dark",
    "auto_backup": True,
    "backup_interval_days": 7,
    "max_logs_days": 30,
}

_logger = None


def _get_logger():
    global _logger
    if _logger is None:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        _logger = logging.getLogger("startup")
        handler = logging.FileHandler(str(LOGS_DIR / "startup.log"), encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        _logger.addHandler(handler)
        _logger.setLevel(logging.INFO)
        _logger.info("=" * 60)
        _logger.info("STARTUP INICIADO")
    return _logger


def log(msg, level="info"):
    getattr(_get_logger(), level, _get_logger().info)(msg)


# ----------------------------------------------------------------------
# 1. Diretórios de dados
# ----------------------------------------------------------------------

def ensure_data_dirs():
    """Garante que todos os diretórios de dados existem (fail-safe)."""
    dirs = [
        DATA_DIR, DB_DIR, MIGRATIONS_DIR, CONFIG_DIR,
        LOGS_DIR, BACKUPS_DIR, ATTACHMENTS_STORAGE_DIR,
    ]
    for d in dirs:
        try:
            d.mkdir(parents=True, exist_ok=True)
            log(f"Diretorio OK: {d}")
        except Exception as e:
            log(f"Falha ao criar diretorio {d}: {e}", "error")
            raise
    return True


# ----------------------------------------------------------------------
# 2. Configuração padrão
# ----------------------------------------------------------------------

def ensure_default_config():
    """Cria config padrão se não existir (fallback de config)."""
    config_file = CONFIG_DIR / "default_config.json"
    if config_file.exists():
        log("Config ja existe")
        return True

    try:
        if _is_bundled and INSTALL_CONFIG_DIR.exists():
            src = INSTALL_CONFIG_DIR / "default_config.json"
            if src.exists():
                shutil.copy2(str(src), str(config_file))
                log("Config copiada do instalador")
                return True

        with open(str(config_file), "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG_TEMPLATE, f, indent=2)
        log("Config padrao criada do template")
        return True
    except Exception as e:
        log(f"Falha ao criar config: {e}", "error")
        return False


# ----------------------------------------------------------------------
# 3. Migrations
# ----------------------------------------------------------------------

def ensure_migration_files():
    """Garante migrations disponíveis em DATA_DIR."""
    if _is_bundled and INSTALL_MIGRATIONS_DIR.exists():
        for f in INSTALL_MIGRATIONS_DIR.glob("*.sql"):
            dst = MIGRATIONS_DIR / f.name
            if not dst.exists():
                try:
                    shutil.copy2(str(f), str(dst))
                    log(f"Migration copiada: {f.name}")
                except Exception as e:
                    log(f"Falha ao copiar migration {f.name}: {e}", "error")
                    raise
    count = len(list(MIGRATIONS_DIR.glob("*.sql")))
    log(f"Migrations: {count} arquivo(s)")
    return count > 0


# ----------------------------------------------------------------------
# 4. Banco de dados
# ----------------------------------------------------------------------

def ensure_seed_db():
    """Copia seed DB se não existir ainda."""
    if DB_PATH.exists():
        log("Banco ja existe")
        return True
    if _is_bundled and INSTALL_DB_PATH.exists():
        try:
            shutil.copy2(str(INSTALL_DB_PATH), str(DB_PATH))
            log("Seed DB copiada")
            return True
        except Exception as e:
            log(f"Falha ao copiar seed DB: {e}", "error")
    else:
        log("Sem seed DB — migrations criarao o schema")
    return False


def _backup_and_remove_corrupted():
    """Faz backup de DB corrompido, depois remove."""
    if not DB_PATH.exists():
        return False
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUPS_DIR / f"novo_cerebro_corrompido_{timestamp}.db"
    try:
        shutil.copy2(str(DB_PATH), str(backup))
        log(f"DB corrompido salvo em: {backup}", "warning")
        DB_PATH.unlink(missing_ok=True)
        for ext in ["-wal", "-shm"]:
            p = DB_PATH.with_name(DB_PATH.name + ext)
            if p.exists():
                p.unlink()
        log("DB corrompido removido")
        return True
    except Exception as e:
        log(f"Falha ao manipular DB corrompido: {e}", "error")
        return False


def check_db_integrity():
    """Executa PRAGMA integrity_check."""
    try:
        import database.connection as db_conn
        conn = db_conn.get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            row = cursor.fetchone()
        ok = row and row[0] == "ok"
        log(f"Integridade do banco: {'OK' if ok else 'FALHA'}")
        return ok
    except Exception:
        log("Nao foi possivel verificar integridade", "error")
        return False


def _get_current_schema_version():
    """Lê a versão atual do schema. Retorna 0 se não existir."""
    import database.connection as db_conn
    try:
        with db_conn.get_db_cursor() as cursor:
            cursor.execute("SELECT MAX(version) FROM schema_version")
            row = cursor.fetchone()
            return row[0] if row and row[0] is not None else 0
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        return 0


def _apply_single_migration(cursor, file_path, version):
    """Aplica uma migration. Ignora erros de 'duplicate column'/'already exists'."""
    sql = file_path.read_text(encoding="utf-8")
    try:
        cursor.executescript(sql)
        log(f"Migration {file_path.name} aplicada")
    except sqlite3.OperationalError as e:
        msg = str(e).lower()
        if "duplicate column" in msg or "already exists" in msg:
            log(f"Migration {file_path.name}: ignorado ({e})", "warning")
        else:
            raise
    cursor.execute(
        "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
        (version,)
    )


def run_migrations():
    """Executa migrations pendentes."""
    current = _get_current_schema_version()
    log(f"Versao atual do schema: {current}")

    files = sorted(
        p for p in MIGRATIONS_DIR.glob("*.sql")
        if p.stem.split("_")[0].isdigit()
    )

    import database.connection as db_conn
    with db_conn.get_db_cursor() as cursor:
        for f in files:
            version = int(f.stem.split("_")[0])
            if version > current:
                _apply_single_migration(cursor, f, version)


def _run_all_migrations_from_scratch():
    """Executa TODAS as migrations do zero (pós-recovery)."""
    import database.connection as db_conn

    with db_conn.get_db_cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """)

    files = sorted(
        p for p in MIGRATIONS_DIR.glob("*.sql")
        if p.stem.split("_")[0].isdigit()
    )

    with db_conn.get_db_cursor() as cursor:
        for f in files:
            version = int(f.stem.split("_")[0])
            _apply_single_migration(cursor, f, version)

    log(f"Todas as {len(files)} migrations reaplicadas (recovery)")


# ----------------------------------------------------------------------
# 5. Startup completo com auto-repair
# ----------------------------------------------------------------------

def run_migrations_with_recovery():
    """Executa migrations com recovery automático em caso de falha."""
    try:
        run_migrations()
    except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
        msg = str(e).lower()
        if "database disk image is malformed" in msg or "corrupt" in msg:
            log(f"DB corrompido detectado: {e}", "error")
            _backup_and_remove_corrupted()
            log("Recriando banco a partir do zero...", "warning")
            _run_all_migrations_from_scratch()
            log("Banco recriado com sucesso!", "warning")
        elif "no such table" in msg:
            log(f"Schema incompleto: {e}", "error")
            _run_all_migrations_from_scratch()
            log("Migrations reaplicadas do zero!", "warning")
        else:
            log(f"Erro nas migrations: {e}", "error")
            raise


# ----------------------------------------------------------------------
# 6. Self-test pós-startup
# ----------------------------------------------------------------------

def run_self_test():
    """Verifica se tudo está funcional após o startup."""
    results = {}

    data_dirs_ok = all([
        DATA_DIR.exists(),
        DB_DIR.exists(),
        MIGRATIONS_DIR.exists(),
        CONFIG_DIR.exists(),
        LOGS_DIR.exists(),
        BACKUPS_DIR.exists(),
    ])
    results["data_dirs"] = data_dirs_ok
    log(f"Self-test data_dirs: {'OK' if data_dirs_ok else 'FALHA'}")

    config_ok = (CONFIG_DIR / "default_config.json").exists()
    results["config"] = config_ok
    log(f"Self-test config: {'OK' if config_ok else 'FALHA'}")

    db_exists_ok = DB_PATH.exists()
    results["db_exists"] = db_exists_ok
    log(f"Self-test db_exists: {'OK' if db_exists_ok else 'FALHA'}")

    db_integrity = False
    if db_exists_ok:
        db_integrity = check_db_integrity()
    results["db_integrity"] = db_integrity
    log(f"Self-test db_integrity: {'OK' if db_integrity else 'FALHA'}")

    all_ok = all(results.values())
    if all_ok:
        log("Self-test: TODOS OS CHECKS OK")
    else:
        log(f"Self-test: FALHAS DETECTADAS - {results}", "warning")

    return results


# ----------------------------------------------------------------------
# 7. Pipeline completo de startup
# ----------------------------------------------------------------------

def run_startup_pipeline():
    """Pipeline completo de inicialização com auto-repair."""
    log("=" * 60)
    log("INICIANDO STARTUP PIPELINE")

    steps = []

    try:
        ensure_data_dirs()
        steps.append(("data_dirs", True))
    except Exception as e:
        steps.append(("data_dirs", False, str(e)))
        log(f"FATAL: data_dirs falhou - {e}", "error")
        return False

    try:
        ensure_default_config()
        steps.append(("config", True))
    except Exception as e:
        steps.append(("config", False, str(e)))
        log(f"FATAL: config falhou - {e}", "error")
        return False

    try:
        ensure_migration_files()
        steps.append(("migration_files", True))
    except Exception as e:
        steps.append(("migration_files", False, str(e)))
        log(f"FATAL: migration_files falhou - {e}", "error")
        return False

    try:
        ensure_seed_db()
        steps.append(("seed_db", True))
    except Exception as e:
        steps.append(("seed_db", False, str(e)))

    try:
        run_migrations_with_recovery()
        steps.append(("migrations", True))
    except Exception as e:
        steps.append(("migrations", False, str(e)))
        log(f"FATAL: migrations falhou - {e}", "error")
        return False

    self_test = run_self_test()
    steps.append(("self_test", self_test.get("db_integrity", False)))

    any_fail = any(not ok for _, ok in steps)
    if any_fail:
        log("Startup pipeline concluido COM FALHAS", "warning")
    else:
        log("Startup pipeline concluido COM SUCESSO")

    log("=" * 60)
    return not any_fail


def startup_init():
    """Chamado no início de main() — setup de logging + pipeline."""
    log_msg = _get_logger()
    config_repaired = run_startup_pipeline()
    return config_repaired
