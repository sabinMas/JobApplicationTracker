"""
WebSocket connection manager for broadcasting automation events to the frontend.
"""
from fastapi import WebSocket
from typing import Dict, List
import json
from datetime import datetime, timezone


class ConnectionManager:
    def __init__(self):
        # session_id -> list of connected WebSocket clients
        self._connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self._connections:
            self._connections[session_id] = []
        self._connections[session_id].append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self._connections:
            self._connections[session_id].discard(websocket) if hasattr(
                self._connections[session_id], "discard"
            ) else None
            try:
                self._connections[session_id].remove(websocket)
            except ValueError:
                pass
            if not self._connections[session_id]:
                del self._connections[session_id]

    async def broadcast(self, session_id: str, event: dict):
        """Send event dict to all clients watching this session."""
        event.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        message = json.dumps(event)
        dead = []
        for ws in self._connections.get(session_id, []):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(session_id, ws)

    def has_listeners(self, session_id: str) -> bool:
        return bool(self._connections.get(session_id))


# Singleton used across routers
ws_manager = ConnectionManager()
