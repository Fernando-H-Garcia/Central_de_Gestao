import sqlite3
import os

DB_PATH = "database/novo_cerebro.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if start_date exists
    cursor.execute("PRAGMA table_info(tasks)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "start_date" not in columns:
        print("Adding start_date column to tasks...")
        cursor.execute("ALTER TABLE tasks ADD COLUMN start_date DATETIME")
        conn.commit()
    
    print("Updating start_date to created_at for all tasks...")
    cursor.execute("UPDATE tasks SET start_date = created_at WHERE start_date IS NULL")
    
    print("Updating status 'A Fazer' to 'Pendente'...")
    cursor.execute("UPDATE tasks SET status = 'Pendente' WHERE status = 'A Fazer' OR status = 'A fazer'")
    
    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate()
