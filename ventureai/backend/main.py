import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from dotenv import load_dotenv
load_dotenv(".env.local")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .band_client import InMemoryBandClient
from .models import InvestmentMemo
from .agents.sourcing import SourcingAgent
from .agents.market import MarketResearchAgent
from .agents.founder import FounderResearchAgent
from .agents.financial import FinancialAgent
from .agents.devil import DevilAgent
from .agents.committee import CommitteeAgent

logger = logging.getLogger("ventureai.main")

# In-memory session storage
SESSIONS: Dict[str, List[Dict[str, Any]]] = {}
MEMOS: Dict[str, Dict[str, Any]] = {}
WS_CONNECTIONS: Dict[str, List[WebSocket]] = {}
WAITERS: Dict[str, asyncio.Event] = {}

band_client = InMemoryBandClient()

# Global agent instances — initialised in lifespan, reused across requests
sourcing_agent: SourcingAgent = None
market_agent: MarketResearchAgent = None
founder_agent: FounderResearchAgent = None
financial_agent: FinancialAgent = None
devil_agent: DevilAgent = None
committee_agent: CommitteeAgent = None


async def _on_band_message(message_type: str, envelope: Dict[str, Any]):
    data = envelope.get("data", {})
    session_id = data.get("session_id")
    entry = {"agent": envelope.get("agent"), "type": message_type, "data": data}
    if session_id:
        SESSIONS.setdefault(session_id, []).append(entry)
        waiter = WAITERS.get(session_id)
        if waiter and not waiter.is_set():
            waiter.set()
        if message_type == "investment_memo":
            MEMOS[session_id] = data
        for ws in list(WS_CONNECTIONS.get(session_id, [])):
            try:
                asyncio.create_task(ws.send_text(json.dumps(entry)))
            except Exception:
                logger.exception("Failed to send WS message")


@asynccontextmanager
async def lifespan(_: FastAPI):
    global sourcing_agent, market_agent, founder_agent, financial_agent, devil_agent, committee_agent

    await band_client.connect(os.environ.get("ROOM_ID", "default"))
    await band_client.subscribe(["*"], _on_band_message)

    api_key = os.environ.get("AIML_API_KEY", "")
    room_id = os.environ.get("ROOM_ID", "default")

    sourcing_agent = SourcingAgent("sourcing", "sourcing", api_key, os.environ.get("SOURCING_AGENT_API_KEY", ""), room_id)
    market_agent = MarketResearchAgent("market", "market", api_key, os.environ.get("MARKET_RESEARCH_AGENT", ""), room_id)
    founder_agent = FounderResearchAgent("founder", "founder", api_key, os.environ.get("FOUNDER_RESEARCH_AGENT", ""), room_id)
    financial_agent = FinancialAgent("financial", "financial", api_key, os.environ.get("FINANCIAL_AGENT", ""), room_id)
    devil_agent = DevilAgent("devil", "devil", api_key, os.environ.get("DEVIL_AGENT_API_KEY", ""), room_id)
    committee_agent = CommitteeAgent("committee", "committee", api_key, os.environ.get("COMMITTEE_AGENT_API_KEY", ""), room_id)

    for agent in [sourcing_agent, market_agent, founder_agent, financial_agent, devil_agent, committee_agent]:
        await agent.connect_to_band(band_client)

    logger.info("All 6 agents connected to band")
    logger.info("Using LLM model: %s", os.environ.get("AIML_MODEL", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"))

    yield

    for agent in [sourcing_agent, market_agent, founder_agent, financial_agent, devil_agent, committee_agent]:
        if agent:
            await agent.close()


app = FastAPI(lifespan=lifespan)

# Enable CORS for dev/local access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _publish_debate_msg(session_id: str, speaker: str, content: str, round_num: int, phase: str):
    await band_client.publish("debate", "debate_message", {
        "session_id": session_id,
        "speaker": speaker,
        "content": content,
        "round": round_num,
        "phase": phase,
    })


async def run_pipeline(raw_input: str, session_id: str):
    try:
        await asyncio.wait_for(_run_pipeline(raw_input, session_id), timeout=180)
    except asyncio.TimeoutError:
        logger.error("Pipeline timed out for session %s", session_id)
        rejection = InvestmentMemo(
            verdict="PASS", confidence_score=0,
            executive_summary="Pipeline timed out — the analysis took too long to complete.",
            market_score=0, founder_score=0, financial_score=0, bear_case_score=0, overall_score=0,
            recommendation="Try again with a clearer company description.",
            due_diligence_questions=[], suggested_valuation_range="N/A", summary="Timed out.",
        )
        payload = rejection.dict()
        payload["session_id"] = session_id
        await band_client.publish("committee", "investment_memo", payload)
    except Exception:
        logger.exception("Pipeline failed for session %s", session_id)


async def _run_pipeline(raw_input: str, session_id: str):
    try:
        # Stage 1: extract startup profile
        profile = await sourcing_agent.process(raw_input, session_id=session_id)

        # Gate: reject nonsensical / non-startup input immediately
        if profile.company_name.upper().replace(" ", "_") == "INVALID_INPUT":
            rejection = InvestmentMemo(
                verdict="PASS",
                confidence_score=0,
                executive_summary="Input rejected — the provided text does not describe a startup or company.",
                market_score=0,
                founder_score=0,
                financial_score=0,
                bear_case_score=0,
                overall_score=0,
                recommendation="Provide a startup name, website URL, or a description of the company to run analysis.",
                due_diligence_questions=[],
                suggested_valuation_range="N/A",
                summary="Invalid or insufficient input.",
            )
            payload = rejection.dict()
            payload["session_id"] = session_id
            await band_client.publish("committee", "investment_memo", payload)
            return

        # Stage 2: parallel analysis
        market, founder, financial = await asyncio.gather(
            market_agent.process(profile, session_id=session_id),
            founder_agent.process(profile, session_id=session_id),
            financial_agent.process(profile, session_id=session_id),
        )

        # Stage 3: devil's advocate bear case
        bear = await devil_agent.process(market, founder, financial, session_id=session_id)

        # Stage 4: dynamic debate — devil challenges until analysts satisfy the concerns or max rounds hit
        MAX_ROUNDS = 3
        challenges = await devil_agent.generate_challenges(market, founder, financial, bear, session_id=session_id)
        debate_log: List[str] = []

        def _fmt_challenges(c: Dict[str, str]) -> str:
            return (
                f"[To Market] {c['market_challenge']}\n\n"
                f"[To Founder] {c['founder_challenge']}\n\n"
                f"[To Financial] {c['financial_challenge']}"
            )

        await _publish_debate_msg(session_id, "Devil's Advocate", _fmt_challenges(challenges), 1, "challenge")

        for round_num in range(1, MAX_ROUNDS + 1):
            market_rb, founder_rb, financial_rb = await asyncio.gather(
                market_agent.rebut(challenges["market_challenge"], market, session_id=session_id),
                founder_agent.rebut(challenges["founder_challenge"], founder, session_id=session_id),
                financial_agent.rebut(challenges["financial_challenge"], financial, session_id=session_id),
            )

            await _publish_debate_msg(session_id, "Market Research", market_rb, round_num, "rebuttal")
            await _publish_debate_msg(session_id, "Founder Diligence", founder_rb, round_num, "rebuttal")
            await _publish_debate_msg(session_id, "Financial Analysis", financial_rb, round_num, "rebuttal")

            debate_log.append(
                f"--- Round {round_num} ---\n"
                f"Devil → Market: {challenges['market_challenge']}\n"
                f"Market: {market_rb}\n\n"
                f"Devil → Founder: {challenges['founder_challenge']}\n"
                f"Founder: {founder_rb}\n\n"
                f"Devil → Financial: {challenges['financial_challenge']}\n"
                f"Financial: {financial_rb}"
            )

            decision = await devil_agent.evaluate_round(
                challenges, market_rb, founder_rb, financial_rb, round_num, session_id=session_id
            )
            await _publish_debate_msg(session_id, "Devil's Advocate", decision["response"], round_num, "evaluation")
            debate_log.append(f"Devil's verdict on round {round_num}: {decision['response']}")

            if not decision["continue"] or round_num == MAX_ROUNDS:
                break

            challenges = {
                "market_challenge": decision["market_challenge"],
                "founder_challenge": decision["founder_challenge"],
                "financial_challenge": decision["financial_challenge"],
            }
            await _publish_debate_msg(
                session_id, "Devil's Advocate", _fmt_challenges(challenges), round_num + 1, "challenge"
            )

        debate_summary = "\n\n".join(debate_log)

        # Stage 5: committee synthesizes everything including the debate
        await committee_agent.process(
            profile, market, founder, financial, bear,
            session_id=session_id,
            debate_summary=debate_summary,
        )

    except Exception:
        logger.exception("Pipeline failed for session %s", session_id)


@app.post("/evaluate")
async def evaluate(payload: Dict[str, Any]):
    raw_input = payload.get("input")
    if not raw_input:
        raise HTTPException(status_code=400, detail="missing 'input' in body")

    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = []
    WAITERS[session_id] = asyncio.Event()

    asyncio.create_task(run_pipeline(raw_input, session_id))

    try:
        await asyncio.wait_for(WAITERS[session_id].wait(), timeout=5.0)
    except asyncio.TimeoutError:
        logger.info("/evaluate timeout waiting for first message for session %s", session_id)
    finally:
        WAITERS.pop(session_id, None)

    return JSONResponse({"session_id": session_id})


@app.get("/status/{session_id}")
async def status(session_id: str):
    return JSONResponse({"messages": SESSIONS.get(session_id, [])})


@app.get("/memo/{session_id}")
async def memo(session_id: str):
    result = MEMOS.get(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="memo not ready")
    return JSONResponse(result)


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    WS_CONNECTIONS.setdefault(session_id, []).append(websocket)
    # Replay messages that arrived before the WebSocket connected
    for entry in list(SESSIONS.get(session_id, [])):
        try:
            await websocket.send_text(json.dumps(entry))
        except Exception:
            break
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        WS_CONNECTIONS[session_id].remove(websocket)
