import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from config import DB_PATH
import sqlite3
from models.entities import Project, Task, Idea, Note, KnowledgePage

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

entities = {
    "projects": Project,
    "tasks": Task,
    "ideas": Idea,
    "notes": Note,
    "knowledge_pages": KnowledgePage
}

for table, cls in entities.items():
    print(f"Checking {table}...")
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]

    from dataclasses import fields
    dc_fields = [f.name for f in fields(cls)]

    missing_in_db = set(dc_fields) - set(columns)
    missing_in_dc = set(columns) - set(dc_fields)

    if missing_in_db:
        print(f"  Missing in DB: {missing_in_db}")
    if missing_in_dc:
        print(f"  Missing in Dataclass: {missing_in_dc}")

print("Done.")
