from database.repositories.base_repository import BaseRepository
from models.agenda_item import AgendaItem
from models.user_capacity import UserCapacity
from database.connection import get_db_cursor
from typing import List, Optional

class AgendaRepository(BaseRepository[AgendaItem]):
    def __init__(self):
        super().__init__('agenda_items', AgendaItem)

    def create(self, item: AgendaItem) -> AgendaItem:
        with get_db_cursor() as cursor:
            cursor.execute('''
                INSERT INTO agenda_items (entity_type, entity_id, start_date, end_date, effort_hours, schedule_status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (item.entity_type, item.entity_id, item.start_date, item.end_date, item.effort_hours, item.schedule_status))
            item.id = cursor.lastrowid
            return item

    def update(self, item: AgendaItem) -> AgendaItem:
        with get_db_cursor() as cursor:
            cursor.execute('''
                UPDATE agenda_items
                SET start_date = ?, end_date = ?, effort_hours = ?, schedule_status = ?
                WHERE id = ?
            ''', (item.start_date, item.end_date, item.effort_hours, item.schedule_status, item.id))
            return item

    def get_all(self, include_archived=False, include_deleted=False) -> List[AgendaItem]:
        # agenda_items doesn't have is_archived or deleted_at, override get_all
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM agenda_items")
            return [self._row_to_model(row) for row in cursor.fetchall()]

    def get_by_entity(self, entity_type: str, entity_id: int) -> List[AgendaItem]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM agenda_items WHERE entity_type = ? AND entity_id = ?", (entity_type, entity_id))
            return [self._row_to_model(row) for row in cursor.fetchall()]

    # --- User Capacity Helpers ---
    def get_capacity(self, date_str: str) -> Optional[UserCapacity]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM user_capacity WHERE date = ?", (date_str,))
            row = cursor.fetchone()
            if row:
                return UserCapacity(**dict(row))
            return None

    def get_all_capacities(self) -> List[UserCapacity]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM user_capacity")
            return [UserCapacity(**dict(row)) for row in cursor.fetchall()]

    def set_capacity(self, date_str: str, available_hours: float) -> UserCapacity:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT id FROM user_capacity WHERE date = ?", (date_str,))
            row = cursor.fetchone()
            if row:
                cursor.execute("UPDATE user_capacity SET available_hours = ? WHERE date = ?", (available_hours, date_str))
                cap_id = row['id']
            else:
                cursor.execute("INSERT INTO user_capacity (date, available_hours) VALUES (?, ?)", (date_str, available_hours))
                cap_id = cursor.lastrowid
            
            return UserCapacity(id=cap_id, date=date_str, available_hours=available_hours)
