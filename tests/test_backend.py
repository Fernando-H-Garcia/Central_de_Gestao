import os
import sys
import unittest
from pathlib import Path

# Add parent directory to path to allow importing modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Dynamic override of DB_PATH before other modules load it
import config
TEST_DB_PATH = config.DB_DIR / "segundo_cerebro_test.db"
config.DB_PATH = TEST_DB_PATH

from main import run_migrations
from models.entities import Note, Event, Idea, KnowledgePage
from services.note_service import NoteService
from services.event_service import EventService
from services.idea_service import IdeaService
from services.knowledge_page_service import KnowledgePageService
from database.connection import get_db_cursor

class TestBackendEntities(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure any leftover test db is deleted
        if TEST_DB_PATH.exists():
            try:
                TEST_DB_PATH.unlink()
            except OSError:
                pass
        # Run migrations to build schema
        run_migrations()

    @classmethod
    def tearDownClass(cls):
        # Close connection and cleanup test db files
        import gc
        gc.collect() # close any unclosed SQLite connections
        
        # Cleanup WAL files too
        for file in [TEST_DB_PATH, TEST_DB_PATH.with_suffix('.db-wal'), TEST_DB_PATH.with_suffix('.db-shm')]:
            if file.exists():
                try:
                    file.unlink()
                except OSError:
                    pass

    def setUp(self):
        # Clean tables before each test to guarantee isolation
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM notes")
            cursor.execute("DELETE FROM events")
            cursor.execute("DELETE FROM ideas")
            cursor.execute("DELETE FROM knowledge_pages")
            cursor.execute("DELETE FROM activity_logs")
            cursor.execute("DELETE FROM entity_links")
            cursor.execute("DELETE FROM projects")
            cursor.execute("DELETE FROM tasks")
            cursor.execute("DELETE FROM agenda_items")
            cursor.execute("DELETE FROM task_dependencies")
            cursor.execute("DELETE FROM user_capacity")

    def test_note_service(self):
        service = NoteService()
        
        # 1. Create
        note = Note(content="Minha nota de teste")
        created = service.create(note)
        self.assertIsNotNone(created.id)
        self.assertEqual(created.content, "Minha nota de teste")
        
        # 2. Get
        retrieved = service.get(created.id)
        self.assertEqual(retrieved.content, "Minha nota de teste")
        
        # 3. Update
        retrieved.content = "Nota atualizada"
        updated = service.update(retrieved)
        self.assertEqual(service.get(created.id).content, "Nota atualizada")
        
        # 4. List (get_all)
        notes = service.list()
        self.assertEqual(len(notes), 1)
        
        # 5. Archive
        service.archive(created.id)
        self.assertEqual(len(service.list(include_archived=False)), 0)
        self.assertEqual(len(service.list(include_archived=True)), 1)
        
        # 6. Restore
        service.restore(created.id)
        self.assertEqual(len(service.list(include_archived=False)), 1)
        
        # 7. Soft Delete
        service.soft_delete(created.id)
        self.assertEqual(len(service.list(include_deleted=False)), 0)
        
        # 8. Check activity logs
        with get_db_cursor() as cursor:
            cursor.execute("SELECT action FROM activity_logs WHERE entity_type = 'note'")
            actions = [row[0] for row in cursor.fetchall()]
            self.assertIn("CREATED", actions)
            self.assertIn("UPDATED", actions)
            self.assertIn("ARCHIVED", actions)
            self.assertIn("RESTORED", actions)
            self.assertIn("DELETED", actions)

    def test_event_service(self):
        service = EventService()
        
        # 1. Create
        event = service.create(title="Reunião Importante", description="Discussão de metas", start="2026-06-03 16:00:00", location="Sala 1")
        self.assertIsNotNone(event.id)
        
        # 2. List Active
        active = service.list_active()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].title, "Reunião Importante")
        
        # 3. Update
        import copy
        orig = copy.deepcopy(event)
        event.title = "Reunião Cancelada"
        service.update(event, orig)
        self.assertEqual(service.list_active()[0].title, "Reunião Cancelada")
        
        # 4. Archive
        service.archive(event.id)
        self.assertEqual(len(service.list_active()), 0)
        self.assertEqual(len(service.list_archived()), 1)
        
        # 5. Restore
        service.restore(event.id)
        self.assertEqual(len(service.list_active()), 1)
        
        # 6. Delete
        service.delete(event.id)
        self.assertEqual(len(service.list_active()), 0)
        
        # 7. Verify Logs
        with get_db_cursor() as cursor:
            cursor.execute("SELECT action FROM activity_logs WHERE entity_type = 'event'")
            actions = [row[0] for row in cursor.fetchall()]
            self.assertIn("CREATED", actions)
            self.assertIn("UPDATED", actions)
            self.assertIn("ARCHIVED", actions)
            self.assertIn("RESTORED", actions)
            self.assertIn("DELETED", actions)

    def test_idea_service(self):
        service = IdeaService()
        
        # 1. Create
        idea = service.create_idea(title="Nova Ideia", description="Detalhes da ideia", interest_level=4, status="Nova", priority="Alta")
        self.assertIsNotNone(idea.id)
        self.assertEqual(idea.title, "Nova Ideia")
        self.assertEqual(idea.priority, "Alta")
        
        # 2. Get by ID
        retrieved = service.get_by_id(idea.id)
        self.assertEqual(retrieved.title, "Nova Ideia")
        
        # 3. Update
        import copy
        orig = copy.deepcopy(retrieved)
        retrieved.title = "Ideia Brilhante"
        retrieved.interest_level = 5
        service.update_idea(retrieved, orig)
        self.assertEqual(service.get_by_id(idea.id).title, "Ideia Brilhante")
        self.assertEqual(service.get_by_id(idea.id).interest_level, 5)
        
        # 4. Get All Active
        active = service.get_all_active()
        self.assertEqual(len(active), 1)
        
        # 5. Archive
        service.archive_idea(idea.id)
        self.assertEqual(len(service.get_all_active()), 0)
        self.assertEqual(len(service.get_all_archived()), 1)
        
        # 6. Restore
        service.restore_idea(idea.id)
        self.assertEqual(len(service.get_all_active()), 1)
        
        # 7. Soft Delete
        service.soft_delete_idea(idea.id)
        self.assertEqual(len(service.get_all_active()), 0)
        
        # 8. Check Logs
        with get_db_cursor() as cursor:
            cursor.execute("SELECT action FROM activity_logs WHERE entity_type = 'idea'")
            actions = [row[0] for row in cursor.fetchall()]
            self.assertIn("CREATED", actions)
            self.assertIn("UPDATED", actions)
            self.assertIn("ARCHIVED", actions)
            self.assertIn("RESTORED", actions)
            self.assertIn("DELETED", actions)

    def test_knowledge_page_service(self):
        service = KnowledgePageService()
        
        # 1. Create
        page = service.create_page(title="Wiki Python", content="Dicas de Python", category="Programação", review_interval_days=7)
        self.assertIsNotNone(page.id)
        self.assertEqual(page.title, "Wiki Python")
        
        # 2. Get by ID
        retrieved = service.get_by_id(page.id)
        self.assertEqual(retrieved.content, "Dicas de Python")
        
        # 3. Update
        import copy
        orig = copy.deepcopy(retrieved)
        retrieved.title = "Wiki Python 3"
        retrieved.content = "Dicas avançadas de Python"
        service.update_page(retrieved, orig)
        self.assertEqual(service.get_by_id(page.id).title, "Wiki Python 3")
        
        # 4. Get All Active
        active = service.get_all_active()
        self.assertEqual(len(active), 1)
        
        # 5. Archive
        service.archive_page(page.id)
        self.assertEqual(len(service.get_all_active()), 0)
        self.assertEqual(len(service.get_all_archived()), 1)
        
        # 6. Restore
        service.restore_page(page.id)
        self.assertEqual(len(service.get_all_active()), 1)
        
        # 7. Soft Delete
        service.soft_delete_page(page.id)
        self.assertEqual(len(service.get_all_active()), 0)
        
        # 8. Check Logs
        with get_db_cursor() as cursor:
            cursor.execute("SELECT action FROM activity_logs WHERE entity_type = 'knowledge_page'")
            actions = [row[0] for row in cursor.fetchall()]
            self.assertIn("CREATED", actions)
            self.assertIn("UPDATED", actions)
            self.assertIn("ARCHIVED", actions)
            self.assertIn("RESTORED", actions)
            self.assertIn("DELETED", actions)

    def test_idea_promotion(self):
        service = IdeaService()
        idea = service.create_idea(title="Minha Ideia Temática", description="Detalhes cruciais da ideia", priority="Alta")
        service.idea_repo.set_tags(idea.id, ["Python", "SQLite"])
        
        # Test promote to project
        proj_id = service.promote_to_project(
            idea_id=idea.id,
            project_title="Projeto Promovido",
            description_text=idea.description,
            copy_tags=True,
            copy_attachments=False,
            link_idea=True
        )
        
        from services.project_service import ProjectService
        proj_service = ProjectService()
        proj = proj_service.project_repo.get_by_id(proj_id)
        self.assertIsNotNone(proj)
        self.assertEqual(proj.name, "Projeto Promovido")
        self.assertEqual(proj.objective, "Detalhes cruciais da ideia")
        self.assertEqual(proj.originated_from_idea_id, idea.id)
        
        # Verify tag copy
        proj_tags = proj_service.project_repo.get_tags(proj_id)
        self.assertIn("Python", proj_tags)
        self.assertIn("SQLite", proj_tags)
        
        # Verify original idea is linked
        updated_idea = service.get_by_id(idea.id)
        self.assertEqual(updated_idea.linked_project_id, proj_id)
        self.assertEqual(updated_idea.promoted_type, "project")
        self.assertIsNotNone(updated_idea.promoted_at)
        
        # Test promote to task
        task_id = service.promote_to_task(
            idea_id=idea.id,
            task_title="Tarefa Promovida",
            description_text=idea.description,
            copy_tags=True,
            copy_attachments=False,
            link_idea=True,
            project_id=proj_id
        )
        
        from services.task_service import TaskService
        task_service = TaskService()
        task = task_service.task_repo.get_by_id(task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task.title, "Tarefa Promovida")
        self.assertEqual(task.context, "Detalhes cruciais da ideia")
        self.assertEqual(task.project_id, proj_id)
        self.assertEqual(task.originated_from_idea_id, idea.id)
        
        # Verify tag copy on task
        task_tags = task_service.task_repo.get_tags(task_id)
        self.assertIn("Python", task_tags)
        self.assertIn("SQLite", task_tags)

        # Verify dynamic entity links
        from database.repositories.entity_link_repository import EntityLinkRepository
        el_repo = EntityLinkRepository()
        
        idea_links = el_repo.get_links_by_type('idea', idea.id, 'promoted_to')
        self.assertEqual(len(idea_links), 2)
        
        project_links = el_repo.get_links_by_type('project', proj_id, 'originated_from')
        self.assertEqual(len(project_links), 1)
        self.assertEqual(project_links[0]['target_id'], idea.id)
        
        task_links = el_repo.get_links_by_type('task', task_id, 'originated_from')
        self.assertEqual(len(task_links), 1)
        self.assertEqual(task_links[0]['target_id'], idea.id)

    def test_id_based_and_incremental_linking(self):
        from services.link_service import LinkService
        from services.project_service import ProjectService
        from services.knowledge_page_service import KnowledgePageService
        
        link_service = LinkService()
        proj_service = ProjectService()
        wiki_service = KnowledgePageService()
        
        # 1. Create entities
        proj = proj_service.create_project("Projeto Teste Auto", "Algum objetivo")
        wiki_page = wiki_service.create_page("Wiki Auxiliar")
        
        # 2. Test get_all_linkable_entities includes them
        linkables = link_service.get_all_linkable_entities()
        linkable_ids = [(item['type'], item['id']) for item in linkables]
        self.assertIn(("project", proj.id), linkable_ids)
        self.assertIn(("wiki", wiki_page.id), linkable_ids)
        
        # 3. Test parsing and auto-linking from text (wiki page linking to project)
        # Using format: [[project:ID|Title]]
        wiki_text_with_id_link = f"Abaixo estão os detalhes do [[project:{proj.id}|Projeto Teste Auto]]"
        link_service.update_links_from_text("wiki", wiki_page.id, wiki_text_with_id_link)
        
        # Check link exists
        links = link_service.get_links_for_entity("wiki", wiki_page.id)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]['target_type'], "project")
        self.assertEqual(links[0]['target_id'], proj.id)
        self.assertEqual(links[0]['relationship_type'], "references")
        
        # Check backlink
        backlinks = link_service.get_backlinks_for_entity("project", proj.id)
        self.assertEqual(len(backlinks), 1)
        self.assertEqual(backlinks[0]['source_type'], "wiki")
        self.assertEqual(backlinks[0]['source_id'], wiki_page.id)
        
        # 4. Test parsing and fallback name resolution linking
        wiki_text_with_name_link = "Temos o link [[Projeto Teste Auto]] aqui."
        # Reset references links and test again
        link_service.update_links_from_text("wiki", wiki_page.id, wiki_text_with_name_link)
        
        links = link_service.get_links_for_entity("wiki", wiki_page.id)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]['target_type'], "project")
        self.assertEqual(links[0]['target_id'], proj.id)
        
        # 5. Test incremental sync (add and remove links)
        # Target wiki refers to both project and itself (self reference discarded), plus a non-existent name
        wiki_text_multiple = f"Referencia [[project:{proj.id}|Projeto]] e [[Wiki Auxiliar]] (self) e [[NaoExistente]]"
        link_service.update_links_from_text("wiki", wiki_page.id, wiki_text_multiple)
        
        # Should only have project (self discarded, non-existent not linked)
        links = link_service.get_links_for_entity("wiki", wiki_page.id)
        self.assertEqual(len(links), 1)
        
        # 6. Test completely clearing references when text is empty
        link_service.update_links_from_text("wiki", wiki_page.id, "")
        links = link_service.get_links_for_entity("wiki", wiki_page.id)
        self.assertEqual(len(links), 0)

    def test_agenda_service(self):
        from services.agenda_service import AgendaService
        from services.task_service import TaskService
        
        agenda_service = AgendaService()
        task_service = TaskService()
        
        # 1. Create a task to schedule
        task = task_service.create_task(title="Tarefa Exemplo", context="Contexto da tarefa")
        task_id = task.id
        
        # 2. Schedule multiple periods
        period1 = agenda_service.create_schedule("task", task_id, "2026-07-01", "2026-07-03", 6.0, "planejado")
        period2 = agenda_service.create_schedule("task", task_id, "2026-07-10", "2026-07-12", 9.0, "em_andamento")
        
        self.assertIsNotNone(period1.id)
        self.assertIsNotNone(period2.id)
        
        # 3. Retrieve and check
        schedules = agenda_service.get_schedules_for_entity("task", task_id)
        self.assertEqual(len(schedules), 2)
        
        # 4. Check planned hours distribution
        # "2026-07-01", "2026-07-02", "2026-07-03" -> 3 days. 6.0 effort / 3 = 2.0 hours per day
        hours_on_01 = agenda_service.get_total_planned_hours_for_date("2026-07-01")
        self.assertEqual(hours_on_01, 2.0)
        
        # 5. User Capacity
        cap = agenda_service.set_user_capacity("2026-07-01", 4.0)
        self.assertEqual(agenda_service.get_user_capacity("2026-07-01"), 4.0)
        # Check default capacity on weekday
        self.assertEqual(agenda_service.get_user_capacity("2026-07-06"), 8.0) # Monday
        
        # 6. Task Dependencies
        task_dep = task_service.create_task(title="Tarefa Dependente", context="Depende da primeira")
        task_dep_id = task_dep.id
        dep = agenda_service.add_dependency(task_dep_id, task_id, "finish_to_start", "obrigatória")
        self.assertEqual(dep.task_id, task_dep_id)
        self.assertEqual(dep.depends_on_task_id, task_id)
        self.assertEqual(dep.dependency_strength, "obrigatória")
        
        # Check blocked state
        self.assertTrue(agenda_service.is_task_blocked(task_dep_id))
        self.assertTrue(agenda_service.is_task_blocking(task_id))

        # Check non-blocking dependency strength
        task_dep2 = task_service.create_task(title="Tarefa Dependente Recomendada", context="Depende de forma recomendada")
        dep2 = agenda_service.add_dependency(task_dep2.id, task_id, "finish_to_start", "recomendada")
        self.assertEqual(dep2.dependency_strength, "recomendada")
        self.assertFalse(agenda_service.is_task_blocked(task_dep2.id)) # Should not be blocked because it's only 'recomendada'
        
        # Dependency Tree
        tree = agenda_service.get_dependency_tree(task_dep_id)
        self.assertEqual(tree['task_id'], task_dep_id)
        self.assertEqual(len(tree['dependencies']), 1)
        self.assertEqual(tree['dependencies'][0]['tree']['task_id'], task_id)

        # 7. Check estimated_hours and is_milestone properties on task
        task.estimated_hours = 5.5
        task.is_milestone = True
        updated_task = task_service.task_repo.update(task)
        self.assertEqual(updated_task.estimated_hours, 5.5)
        self.assertTrue(updated_task.is_milestone)


if __name__ == "__main__":
    unittest.main()
