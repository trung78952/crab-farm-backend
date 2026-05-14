from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.database import AsyncSessionLocal
from app.core.security import decode_access_token
from app.services.auth_service import get_user_by_id
from app.services.realtime_service import realtime_service

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None):
    if not token:
        await websocket.close(code=1008)
        return

    try:
        payload = decode_access_token(token)
        user_id = UUID(str(payload.get("sub")))
        async with AsyncSessionLocal() as db:
            user = await get_user_by_id(db, user_id)
        if user is None or not user.is_active:
            await websocket.close(code=1008)
            return
    except Exception:
        await websocket.close(code=1008)
        return

    await realtime_service.connect(websocket)
    try:
        await realtime_service.broadcast("connected", {"user_id": str(user_id)})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        realtime_service.disconnect(websocket)
