from typing import Callable, Dict, List

class EventBus:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._subscribers = {}
            cls._instance._pending_events = {}
            cls._instance._flush_timer = None
        return cls._instance

    def _init_timer(self):
        """Create a persistent QTimer once (lazy init)."""
        if self._flush_timer is None:
            from PySide6.QtCore import QTimer
            self._flush_timer = QTimer()
            self._flush_timer.setSingleShot(True)
            self._flush_timer.timeout.connect(self._flush)
            self._flush_timer.setObjectName("event_bus_flush_timer")

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
            
    def unsubscribe(self, event_type: str, callback: Callable):
        if event_type in self._subscribers and callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)
            
    def _flush(self):
        pending = self._pending_events
        self._pending_events = {}
        
        for event_type, events_by_key in pending.items():
            if event_type in self._subscribers:
                for key, data in events_by_key.items():
                    for callback in self._subscribers[event_type]:
                        callback(data)

    def _schedule_flush(self):
        self._init_timer()
        if not self._flush_timer.isActive():
            self._flush_timer.start(16)

    def _cancel_flush(self):
        if self._flush_timer is not None:
            try:
                self._flush_timer.stop()
            except RuntimeError:
                pass

    def emit(self, event_type: str, data=None):
        key = None
        action = 'update'
        if isinstance(data, dict):
            key = data.get('id')
            action = data.get('action', 'update')
            
        if event_type not in self._pending_events:
            self._pending_events[event_type] = {}
            
        existing_data = self._pending_events[event_type].get(key)
        should_update = True
        if isinstance(existing_data, dict) and isinstance(data, dict):
            existing_action = existing_data.get('action')
            if existing_action == 'delete' and action != 'delete':
                should_update = False
                
        if should_update:
            self._pending_events[event_type][key] = data
            
        total_pending = sum(len(d) for d in self._pending_events.values())
        
        if total_pending > 20:
            self._cancel_flush()
            self._flush()
        elif not self._flush_timer or not self._flush_timer.isActive():
            self._schedule_flush()

event_bus = EventBus()
