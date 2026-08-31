"""
Central Refresh Manager for coordinating UI updates across all Qt views.
Listens to event_bus entity_updated and snapshot_updated events and dispatches
refresh signals to registered views.
"""
from typing import Callable, Dict, List, Optional, Set
from core.event_bus import event_bus


def notify_entity_updated(entity_type: str, entity_id: Optional[int] = None, action: str = "update"):
    """
    Emit a unified entity_updated event to event_bus.
    """
    data = {
        "entity_type": entity_type,
        "action": action
    }
    if entity_id is not None:
        data["entity_id"] = entity_id
        data["id"] = entity_id
    event_bus.emit("entity_updated", data)


class RefreshManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RefreshManager, cls).__new__(cls)
            cls._instance._subscribers: Dict[str, Set[Callable]] = {}
            cls._instance._global_subscribers: Set[Callable] = set()
            cls._instance._is_connected = False
            cls._instance._init_bus()
        return cls._instance

    def _init_bus(self):
        if not self._is_connected:
            event_bus.subscribe("entity_updated", self._on_entity_updated)
            event_bus.subscribe("snapshot_updated", self._on_snapshot_updated)
            self._is_connected = True

    def register(self, entity_types: List[str], callback: Callable[[dict], None]):
        """Register a callback for specific entity types (e.g. ['task', 'project'])."""
        for et in entity_types:
            if et not in self._subscribers:
                self._subscribers[et] = set()
            self._subscribers[et].add(callback)

    def register_global(self, callback: Callable[[dict], None]):
        """Register a callback that fires on ANY entity update."""
        self._global_subscribers.add(callback)

    def unregister(self, callback: Callable):
        """Unregister callback from all entity types and global list."""
        for et_set in self._subscribers.values():
            et_set.discard(callback)
        self._global_subscribers.discard(callback)

    def _on_entity_updated(self, data=None):
        import time
        t0 = time.perf_counter()
        payload = data if isinstance(data, dict) else {}
        entity_type = payload.get("entity_type")
        print(f"[PERF REFRESH_MGR] _on_entity_updated START entity_type={entity_type} data={payload}")

        # Notify specific subscribers
        if entity_type and entity_type in self._subscribers:
            for cb in list(self._subscribers[entity_type]):
                try:
                    cb(payload)
                except Exception as e:
                    import logging
                    logging.exception(f"Error in refresh callback for {entity_type}: {e}")

        # Notify global subscribers
        for cb in list(self._global_subscribers):
            try:
                cb(payload)
            except Exception as e:
                import logging
                logging.exception(f"Error in global refresh callback: {e}")
        print(f"[PERF REFRESH_MGR] _on_entity_updated FINISHED in {(time.perf_counter()-t0)*1000:.2f}ms")

    def _on_snapshot_updated(self, data=None):
        # Refresh all on snapshot restore/update
        payload = {"entity_type": "all", "action": "snapshot"}
        for et_set in self._subscribers.values():
            for cb in list(et_set):
                try:
                    cb(payload)
                except Exception:
                    pass
        for cb in list(self._global_subscribers):
            try:
                cb(payload)
            except Exception:
                pass


refresh_manager = RefreshManager()
