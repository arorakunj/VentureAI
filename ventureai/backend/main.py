import asyncio
import json
import logging
import os
import uuid
from typing import Any, Dict, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse

from .band_client import InMemoryBandClient
from .agents.sourcing import SourcingAgent

app = FastAPI()
logger = logging.getLogger("ventureai.main")

# Simple in-memory storage for session messages and memos
SESSIONS: Dict[str, List[Dict[str, Any]]] = {}
MEMOS: Dict[str, Dict[str, Any]] = {}
WS_CONNECTIONS: Dict[str, List[WebSocket]] = {}
# per-session waiters to allow /evaluate to wait for first message delivery
WAITERS: Dict[str, asyncio.Event] = {}

# Create a global in-memory band client for dev
band_client = InMemoryBandClient()


async def _on_band_message(message_type: str, envelope: Dict[str, Any]):
    # Store message by session_id if present
    data = envelope.get("data", {})
    session_id = data.get("session_id")
    entry = {
        "agent": envelope.get("agent"),
        "type": message_type,
        "data": data,
    }
    if session_id:
        SESSIONS.setdefault(session_id, []).append(entry)
        # notify any waiter waiting for the first message for this session
        waiter = WAITERS.get(session_id)
        if waiter and not waiter.is_set():
            waiter.set()
        # if it's an investment_memo, store separately
        if message_type == "investment_memo":
            MEMOS[session_id] = data

        # broadcast to any websocket clients
        conns = WS_CONNECTIONS.get(session_id, [])
        for ws in list(conns):
            try:
                asyncio.create_task(ws.send_text(json.dumps(entry)))
            except Exception:
                logger.exception("Failed to send WS message")


@app.on_event("startup")
async def startup_event():
    await band_client.connect(os.environ.get("ROOM_ID", "default"))
    # subscribe to all messages
    await band_client.subscribe(["*"], _on_band_message)


@app.post("/evaluate")
async def evaluate(payload: Dict[str, Any]):
    raw_input = payload.get("input")
    if not raw_input:
        raise HTTPException(status_code=400, detail="missing 'input' in body")

    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = []
    # create a waiter event so we can optionally wait for the first publish
    WAITERS[session_id] = asyncio.Event()

    # instantiate a sourcing agent per request
    agent = SourcingAgent(
        name="sourcing",
        role="sourcing",
        api_key=os.environ.get("AIML_API_KEY", ""),
        band_api_key=os.environ.get("BAND_API_KEY", ""),
    )
    await agent.connect_to_band(band_client)

    # run sourcing in background and return session id immediately
    asyncio.create_task(agent.process(raw_input, session_id=session_id))

    # Wait briefly for the first message to be delivered so clients won't see an empty status.
    try:
        await asyncio.wait_for(WAITERS[session_id].wait(), timeout=5.0)
    except asyncio.TimeoutError:
        # It's okay — return session id even if no message yet.
        logger.info("/evaluate timeout waiting for first message for session %s", session_id)
    finally:
        # cleanup waiter to avoid leaks
        WAITERS.pop(session_id, None)

    return JSONResponse({"session_id": session_id})


@app.get("/status/{session_id}")
async def status(session_id: str):
    return JSONResponse({"messages": SESSIONS.get(session_id, [])})


@app.get("/memo/{session_id}")
async def memo(session_id: str):
    memo = MEMOS.get(session_id)
    if not memo:
        raise HTTPException(status_code=404, detail="memo not ready")
    return JSONResponse(memo)


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    WS_CONNECTIONS.setdefault(session_id, []).append(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive, no inbound handling
    except WebSocketDisconnect:
        WS_CONNECTIONS[session_id].remove(websocket)
