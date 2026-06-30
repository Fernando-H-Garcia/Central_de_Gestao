from database.connection import get_db_cursor

class SearchService:
    def search(self, query: str):
        if not query.strip():
            return []
        
        safe_query = query.replace('"', '').replace("'", '').strip() + "*"
        
        sql = """
            SELECT entity_type, entity_id, title, snippet(global_search, 3, '[', ']', '...', 15) as preview 
            FROM global_search 
            WHERE global_search MATCH ? 
            ORDER BY rank 
            LIMIT 50
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute(sql, (safe_query,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            return []
