"""
WebSocket Notification Manager
────────────────────────────────
Broadcasts real-time events to all connected clients when:
  - A PO status changes
  - A new PO is created
  - An anomaly is detected on a PO

Usage in FastAPI:
    from websocket_manager import manager
    await manager.broadcast({"type": "po_created", "data": {...}})
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # Maps user_email → set of WebSocket connections (multi-tab support)
        self.active: Dict[str, Set[WebSocket]] = {}
        # Global listeners (receive all events)
        self.global_listeners: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, user_email: str = "anonymous"):
        await websocket.accept()
        if user_email not in self.active:
            self.active[user_email] = set()
        self.active[user_email].add(websocket)
        self.global_listeners.add(websocket)

    def disconnect(self, websocket: WebSocket, user_email: str = "anonymous"):
        if user_email in self.active:
            self.active[user_email].discard(websocket)
            if not self.active[user_email]:
                del self.active[user_email]
        self.global_listeners.discard(websocket)

    async def broadcast(self, event: dict):
        """Send event to all connected clients."""
        payload = json.dumps({**event, "timestamp": datetime.utcnow().isoformat()})
        dead = set()
        for ws in list(self.global_listeners):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        # Clean up dead connections
        for ws in dead:
            self.global_listeners.discard(ws)

    async def send_to_user(self, user_email: str, event: dict):
        """Send event to a specific user only."""
        if user_email not in self.active:
            return
        payload = json.dumps({**event, "timestamp": datetime.utcnow().isoformat()})
        dead = set()
        for ws in list(self.active[user_email]):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active[user_email].discard(ws)

    @property
    def connected_count(self):
        return len(self.global_listeners)


# Singleton — import this everywhere
manager = ConnectionManager()


# ─── Event helpers (call these from CRUD/routes) ──────────────────────────────

async def notify_po_created(po: dict):
    await manager.broadcast({
        "type": "PO_CREATED",
        "message": f"New PO {po['reference_no']} created for {po.get('vendor_name', 'vendor')}",
        "data": {
            "id": po["id"],
            "reference_no": po["reference_no"],
            "total_amount": po["total_amount"],
            "status": po["status"],
        }
    })

async def notify_status_changed(po_id: int, reference_no: str, old_status: str, new_status: str, changed_by: str = ""):
    await manager.broadcast({
        "type": "PO_STATUS_CHANGED",
        "message": f"PO {reference_no} status changed: {old_status} → {new_status}",
        "data": {
            "id": po_id,
            "reference_no": reference_no,
            "old_status": old_status,
            "new_status": new_status,
            "changed_by": changed_by,
        }
    })

async def notify_anomaly_detected(po_reference: str, risk_level: str, anomalies: list):
    if risk_level in ("MEDIUM", "HIGH"):
        await manager.broadcast({
            "type": "ANOMALY_DETECTED",
            "message": f"⚠️ {risk_level} risk anomaly on {po_reference}: {anomalies[0]['message'] if anomalies else 'Review required'}",
            "data": {
                "reference": po_reference,
                "risk_level": risk_level,
                "anomaly_count": len(anomalies),
            }
        })
