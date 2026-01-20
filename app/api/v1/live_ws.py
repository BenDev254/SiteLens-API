import base64
import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import decode_access_token, get_session as get_db_session
from app.services import live_ws_service
from app.services.gemini_service import transcribe_audio
from app.services.auth_service import get_user_by_username
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


async def websocket_get_user(token: str, session: AsyncSession) -> Optional[User]:
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
        if not username:
            return None
        user = await get_user_by_username(session, username)
        return user
    except Exception:
        return None


@router.websocket("/ws/live/{project_id}")
async def live_ws(websocket: WebSocket, project_id: int, token: Optional[str] = None, session: AsyncSession = Depends(get_session)):
    # Expect token as query parameter `?token=...`
    await websocket.accept()
    try:
        # Parse token from query if not provided
        if not token:
            token = websocket.query_params.get("token")
        user = await websocket_get_user(token, session)
        if not user:
            await websocket.send_json({"type": "error", "message": "authentication required"})
            await websocket.close(code=1008)
            return

        await websocket.send_json({"type": "connected", "project_id": project_id, "user": user.username})

        audio_buffer = bytearray()
        while True:
            data = await websocket.receive()
            # data can be {'type': 'websocket.receive', 'text': '...'} or binary
            if "text" in data:
                try:
                    msg = json.loads(data["text"])
                except Exception:
                    await websocket.send_json({"type": "error", "message": "invalid json"})
                    continue
                mtype = msg.get("type")
                if mtype == "audio_chunk":
                    b64 = msg.get("data")
                    final = msg.get("final", False)
                    if not b64:
                        await websocket.send_json({"type": "error", "message": "missing data"})
                        continue
                    chunk = base64.b64decode(b64)
                    audio_buffer.extend(chunk)
                    await websocket.send_json({"type": "ack", "received_bytes": len(chunk)})
                    if final or len(audio_buffer) > 16000 * 5:  # flush every ~5s at 16kHz
                        # transcribe buffer
                        ab = bytes(audio_buffer)
                        audio_buffer = bytearray()
                        # Run transcription in background-ish manner
                        transcript_text = await transcribe_audio(ab)
                        t = await live_ws_service.persist_transcript(session, project_id, user.id, transcript_text)
                        await websocket.send_json({"type": "transcript", "id": t.id, "text": transcript_text})
                elif mtype == "image":
                    b64 = msg.get("data")
                    if not b64:
                        await websocket.send_json({"type": "error", "message": "missing image data"})
                        continue
                    # For now we don't forward images to external service, but we persist a short note
                    await live_ws_service.persist_transcript(session, project_id, user.id, "[image received: size=%d]" % len(b64), source="image")
                    await websocket.send_json({"type": "ack", "message": "image stored"})
                elif mtype == "close":
                    await websocket.send_json({"type": "closing"})
                    await websocket.close()
                    break
                else:
                    await websocket.send_json({"type": "error", "message": "unsupported message type"})
            elif "bytes" in data:
                # Binary frames: append raw bytes (treat as audio chunk)
                chunk = data["bytes"]
                audio_buffer.extend(chunk)
                await websocket.send_json({"type": "ack", "received_bytes": len(chunk)})
                if len(audio_buffer) > 16000 * 5:
                    ab = bytes(audio_buffer)
                    audio_buffer = bytearray()
                    transcript_text = await transcribe_audio(ab)
                    t = await live_ws_service.persist_transcript(session, project_id, user.id, transcript_text)
                    await websocket.send_json({"type": "transcript", "id": t.id, "text": transcript_text})
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: project_id=%s user=%s", project_id, getattr(user, "username", None))
    except Exception as exc:
        logger.exception("WebSocket error: %s", exc)
        try:
            await websocket.send_json({"type": "error", "message": "internal server error"})
            await websocket.close()
        except Exception:
            pass
