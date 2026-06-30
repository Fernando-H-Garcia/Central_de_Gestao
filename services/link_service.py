from database.repositories.entity_link_repository import EntityLinkRepository
from database.repositories.project_repository import ProjectRepository
from database.repositories.task_repository import TaskRepository
from database.repositories.idea_repository import IdeaRepository
from database.repositories.note_repository import NoteRepository
from database.repositories.knowledge_page_repository import KnowledgePageRepository
from core.event_bus import event_bus
from typing import List, Dict, Optional, Any

class LinkService:
    def __init__(self):
        self.link_repo = EntityLinkRepository()
        self.project_repo = ProjectRepository()
        self.task_repo = TaskRepository()
        self.idea_repo = IdeaRepository()
        self.note_repo = NoteRepository()
        self.wiki_repo = KnowledgePageRepository()

    def create_link(self, source_type: str, source_id: int, target_type: str, target_id: int, relationship_type: str):
        """Creates a bidirectional polymorphic link between source and target entities."""
        # Clean names
        s_type = source_type.lower().strip()
        t_type = target_type.lower().strip()
        r_type = relationship_type.lower().strip()

        # Add forward link
        self.link_repo.add_link(s_type, source_id, t_type, target_id, r_type)
        
        # Add reverse link to support bidirectional backlinks
        rev_relations = {
            "originated_from": "promoted_to",
            "promoted_to": "originated_from",
            "belongs_to": "contains",
            "contains": "belongs_to",
            "depends_on": "blocked_by",
            "blocked_by": "depends_on",
            "references": "referenced_by",
            "referenced_by": "references",
            "documents": "documented_by",
            "documented_by": "documents",
            "related": "related"
        }
        rev_type = rev_relations.get(r_type, "related")
        self.link_repo.add_link(t_type, target_id, s_type, source_id, rev_type)

    def delete_link(self, source_type: str, source_id: int, target_type: str, target_id: int, relationship_type: str):
        s_type = source_type.lower().strip()
        t_type = target_type.lower().strip()
        r_type = relationship_type.lower().strip()
        
        self.link_repo.remove_link(s_type, source_id, t_type, target_id, r_type)
        
        # Remove reverse link
        rev_relations = {
            "originated_from": "promoted_to",
            "promoted_to": "originated_from",
            "belongs_to": "contains",
            "contains": "belongs_to",
            "depends_on": "blocked_by",
            "blocked_by": "depends_on",
            "references": "referenced_by",
            "referenced_by": "references",
            "documents": "documented_by",
            "documented_by": "documents",
            "related": "related"
        }
        rev_type = rev_relations.get(r_type, "related")
        self.link_repo.remove_link(t_type, target_id, s_type, source_id, rev_type)

    def get_links_for_entity(self, entity_type: str, entity_id: int) -> List[Dict[str, Any]]:
        """Returns loaded target entities linked by the source entity."""
        links = self.link_repo.get_links_from(entity_type.lower().strip(), entity_id)
        resolved = []
        forward_types = {"references", "belongs_to", "depends_on", "documents", "promoted_to", "related"}
        for l in links:
            if l['relationship_type'] not in forward_types:
                continue
            obj = self._load_entity(l['target_type'], l['target_id'])
            if obj:
                resolved.append({
                    "relationship_type": l['relationship_type'],
                    "target_type": l['target_type'],
                    "target_id": l['target_id'],
                    "title": self._get_entity_title(l['target_type'], obj),
                    "obj": obj
                })
        return resolved

    def get_backlinks_for_entity(self, entity_type: str, entity_id: int) -> List[Dict[str, Any]]:
        """Returns loaded source entities pointing to the target entity (backlinks)."""
        links = self.link_repo.get_links_to(entity_type.lower().strip(), entity_id)
        resolved = []
        forward_types = {"references", "belongs_to", "depends_on", "documents", "promoted_to", "related"}
        for l in links:
            if l['relationship_type'] not in forward_types:
                continue
            # Exclude duplicate relationship definitions to prevent double list display
            obj = self._load_entity(l['source_type'], l['source_id'])
            if obj:
                resolved.append({
                    "relationship_type": l['relationship_type'],
                    "source_type": l['source_type'],
                    "source_id": l['source_id'],
                    "title": self._get_entity_title(l['source_type'], obj),
                    "obj": obj
                })
        return resolved

    def navigate_to_entity(self, entity_type: str, entity_id: int):
        """Emits global navigate_to event for GUI layers to switch screens."""
        event_bus.emit("navigate_to", {"type": entity_type.lower().strip(), "id": entity_id})

    def find_entity_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Searches all database entities by name (case-insensitive) to resolve wiki links."""
        search_name = name.strip().lower()
        if not search_name:
            return None

        # 1. Project
        for p in self.project_repo.get_all():
            if p.name.strip().lower() == search_name:
                return {"type": "project", "id": p.id, "title": p.name}

        # 2. Task
        for t in self.task_repo.get_all():
            if t.title.strip().lower() == search_name:
                return {"type": "task", "id": t.id, "title": t.title}

        # 3. Idea
        for idx in self.idea_repo.get_all():
            if idx.title.strip().lower() == search_name:
                return {"type": "idea", "id": idx.id, "title": idx.title}

        # 4. Wiki (Knowledge Page)
        for pg in self.wiki_repo.get_all():
            if pg.title.strip().lower() == search_name:
                return {"type": "wiki", "id": pg.id, "title": pg.title}

        # 5. Note (Match first line/content title snippet)
        for n in self.note_repo.get_all():
            content = n.content or ""
            first_line = content.strip().split("\n")[0].strip()
            if first_line.lower() == search_name or (len(first_line) > 30 and first_line[:30].lower() == search_name):
                return {"type": "note", "id": n.id, "title": first_line[:30]}

        return None

    def _load_entity(self, entity_type: str, entity_id: int) -> Optional[Any]:
        t = entity_type.lower().strip()
        try:
            if t == "project":
                return self.project_repo.get_by_id(entity_id)
            elif t == "task":
                return self.task_repo.get_by_id(entity_id)
            elif t == "idea":
                return self.idea_repo.get_by_id(entity_id)
            elif t == "note":
                return self.note_repo.get_by_id(entity_id)
            elif t == "wiki" or t == "knowledge_page":
                return self.wiki_repo.get_by_id(entity_id)
        except Exception:
            pass
        return None

    def _get_entity_title(self, entity_type: str, obj: Any) -> str:
        t = entity_type.lower().strip()
        if t == "project":
            return getattr(obj, "name", "Projeto sem nome")
        elif t == "task" or t == "idea" or t == "wiki" or t == "knowledge_page":
            return getattr(obj, "title", "Entidade sem título")
        elif t == "note":
            content = getattr(obj, "content", "") or ""
            first_line = content.strip().split("\n")[0]
            return first_line[:30] if first_line else "Nota vazia"
        return "Entidade desconhecida"

    ENTITY_TYPES = {"project", "task", "idea", "wiki"}

    def get_all_linkable_entities(self) -> List[Dict[str, Any]]:
        """Returns all linkable entities (projects, tasks, ideas, wiki pages) for autocomplete."""
        candidates = []
        
        # 1. Projects
        try:
            for p in self.project_repo.get_all():
                if not getattr(p, "is_archived", False) and getattr(p, "deleted_at", None) is None:
                    candidates.append({"type": "project", "id": p.id, "title": p.name})
        except Exception:
            pass

        # 2. Tasks
        try:
            for t in self.task_repo.get_all():
                if not getattr(t, "is_archived", False) and getattr(t, "deleted_at", None) is None:
                    candidates.append({"type": "task", "id": t.id, "title": t.title})
        except Exception:
            pass

        # 3. Ideas
        try:
            for idx in self.idea_repo.get_all():
                if not getattr(idx, "is_archived", False) and getattr(idx, "deleted_at", None) is None:
                    candidates.append({"type": "idea", "id": idx.id, "title": idx.title})
        except Exception:
            pass

        # 4. Wiki (Knowledge Pages)
        try:
            for pg in self.wiki_repo.get_all():
                if not getattr(pg, "is_archived", False) and getattr(pg, "deleted_at", None) is None:
                    candidates.append({"type": "wiki", "id": pg.id, "title": pg.title})
        except Exception:
            pass

        return candidates

    def find_references_to_entity(self, entity_type: str, entity_id: int) -> list:
        """Finds all references (backlinks) pointing to the given entity.
        Returns list of dicts with 'type_label' and 'title'."""
        references = []

        # 1. Entity links ([[type:id|Title]] in wiki pages)
        backlinks = self.get_backlinks_for_entity(entity_type, entity_id)
        for bl in backlinks:
            st = bl["source_type"]
            if st in ("wiki", "knowledge_page"):
                label = "Documento"
            elif st == "project":
                label = "Projeto"
            elif st == "task":
                label = "Tarefa"
            elif st == "idea":
                label = "Ideia"
            elif st == "note":
                label = "Nota"
            else:
                label = st.capitalize()
            references.append({"type_label": f"{label}:", "title": bl["title"]})

        # 2. File references ({{uuid|name}} in wiki page content)
        if entity_type in ("attachment", "file"):
            import re
            uuid_pattern = re.compile(r'\{\{([^|}]+)\|([^}]+)\}\}')
            try:
                from services.knowledge_page_service import KnowledgePageService
                from services.attachment_service import AttachmentService
                # Find the file UUID
                att_svc = AttachmentService()
                att = att_svc.repository.get_by_id(entity_id)
                if att:
                    target_uuid = att.uuid
                    kps = KnowledgePageService()
                    all_pages = kps.get_all_active()
                    for pg in all_pages:
                        content = pg.content or ""
                        for m in uuid_pattern.finditer(content):
                            if m.group(1) == target_uuid:
                                references.append({
                                    "type_label": "Arquivo:",
                                    "title": f"{m.group(2)} (citado em '{pg.title}')"
                                })
                                break
            except Exception:
                pass

        return references

    def _type_label(self, t: str) -> str:
        m = {"wiki": "documento", "project": "projeto", "task": "tarefa",
             "attachment": "arquivo", "file": "arquivo", "idea": "ideia",
             "note": "nota"}
        return m.get(t.lower().strip(), t)

    def delete_all_references_to(self, entity_type: str, entity_id: int):
        """Removes all references pointing to this entity from both entity_links and page content."""
        # 1. Delete entity_links rows
        links = self.link_repo.get_links_to(entity_type, entity_id)
        for l in links:
            self.delete_link(l["source_type"], l["source_id"],
                             l["target_type"], l["target_id"],
                             l["relationship_type"])

        # 2. Replace [[type:id|Title]] → "Title (type_label excluído)" in wiki page content
        import re
        from services.knowledge_page_service import KnowledgePageService
        kps = KnowledgePageService()

        normalized_type = entity_type.lower().strip()
        if normalized_type == "knowledge_page":
            normalized_type = "wiki"

        type_label = self._type_label(normalized_type)
        excl_label = f"{type_label} excluído"

        all_pages = kps.get_all_active()
        for pg in all_pages:
            content = pg.content or ""
            orig = content
            pattern = re.compile(
                r'\[' + re.escape(normalized_type) + r':' + str(entity_id) +
                r'\|([^\]]+)\]\]'
            )
            content = pattern.sub(rf'\1 ({excl_label})', content)
            if content != orig:
                pg.content = content
                kps.page_repo.update(pg)

        # 2b. Replace [[type:id|Title]] in activity logs (MANUAL/COMENTÁRIO actions)
        try:
            from database.connection import get_db_cursor
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT id, changed_fields_json FROM activity_logs
                    WHERE action IN ('MANUAL', 'MANUAL_NOTE', 'COMENTÁRIO')
                """)
                for row in cursor.fetchall():
                    log_id = row["id"]
                    text = row["changed_fields_json"] or ""
                    new_text = pattern.sub(rf'\1 ({excl_label})', text)
                    if new_text != text:
                        cursor.execute("UPDATE activity_logs SET changed_fields_json = ? WHERE id = ?",
                                       (new_text, log_id))
        except Exception:
            pass

        # 3. Replace {{uuid|name}} → "name (arquivo excluído)" in wiki page content
        if normalized_type in ("attachment", "file"):
            from services.attachment_service import AttachmentService
            att_svc = AttachmentService()
            att = att_svc.repository.get_by_id(entity_id)
            if att and att.uuid:
                for pg in all_pages:
                    content = pg.content or ""
                    orig = content
                    uuid_pat = re.compile(
                        r'\{\{' + re.escape(att.uuid) + r'\|([^}]+)\}\}'
                    )
                    content = uuid_pat.sub(r'\1 (arquivo excluído)', content)
                    if content != orig:
                        pg.content = content
                        kps.page_repo.update(pg)

            # 3b. Replace {{uuid|name}} in activity logs
            try:
                from database.connection import get_db_cursor
                with get_db_cursor() as cursor:
                    cursor.execute("""
                        SELECT id, changed_fields_json FROM activity_logs
                        WHERE action IN ('MANUAL', 'MANUAL_NOTE', 'COMENTÁRIO')
                    """)
                    for row in cursor.fetchall():
                        log_id = row["id"]
                        text = row["changed_fields_json"] or ""
                        new_text = uuid_pat.sub(r'\1 (arquivo excluído)', text)
                        if new_text != text:
                            cursor.execute("UPDATE activity_logs SET changed_fields_json = ? WHERE id = ?",
                                           (new_text, log_id))
            except Exception:
                pass

    def update_links_from_text(self, source_type: str, source_id: int, text: str):
        """
        Parses text for [[type:id|Title]] or [[Title]] patterns. Finds resolved entities,
        and performs an incremental update in the entity_links table.
        """
        s_type = source_type.lower().strip()
        
        if not text:
            # Delete all references links from this source
            for link in self.link_repo.get_links_from(s_type, source_id):
                if link['relationship_type'] == 'references':
                    self.delete_link(s_type, source_id, link['target_type'], link['target_id'], 'references')
            return

        import re
        # Match [[type:id|Title]] or [[Title]]
        pattern = re.compile(r'\[\[(?:([a-zA-Z0-9_]+):(\d+)\|)?(.*?)\]\]')
        matches = pattern.findall(text)
        
        current_resolved = set()  # Set of (target_type, target_id)
        
        for t_type, t_id, t_title in matches:
            t_title = t_title.strip()
            if t_type and t_id:
                # Direct type and id reference
                normalized_type = t_type.lower().strip()
                if normalized_type == "knowledge_page":
                    normalized_type = "wiki"
                current_resolved.add((normalized_type, int(t_id)))
            else:
                # Fallback to name resolution
                resolved = self.find_entity_by_name(t_title)
                if resolved:
                    current_resolved.add((resolved['type'], resolved['id']))

        # Prevent self-linking (an entity pointing to itself)
        current_resolved.discard((s_type, source_id))

        # Get existing links from this source
        existing = self.link_repo.get_links_from(s_type, source_id)
        existing_refs = {(l['target_type'], l['target_id']) for l in existing if l['relationship_type'] == 'references'}

        # Incremental addition of new links
        for target_type, target_id in current_resolved:
            if (target_type, target_id) not in existing_refs:
                self.create_link(s_type, source_id, target_type, target_id, 'references')

        # Incremental removal of old links that are no longer referenced
        for target_type, target_id in existing_refs:
            if (target_type, target_id) not in current_resolved:
                self.delete_link(s_type, source_id, target_type, target_id, 'references')

