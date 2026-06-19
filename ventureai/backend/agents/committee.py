import asyncio
import json
import logging
import os
from typing import Optional, Dict

from ventureai.backend.agents.base_agent import BaseAgent
from ventureai.backend.models import StartupProfile, MarketAnalysis, FounderAnalysis, FinancialAnalysis, BearCase, InvestmentMemo
import ventureai.backend.mock_data as mock_data

logger = logging.getLogger("ventureai.committee")


class CommitteeAgent(BaseAgent):
    def __init__(self, name, role, api_key, band_api_key, room_id=None):
        super().__init__(name, role, api_key, band_api_key, room_id)
        self._band_link = None
        self._runtime_task: Optional[asyncio.Task] = None
        
        # Dictionary to store intermediate results per session_id
        self._session_cache: Dict[str, dict] = {}

    async def connect_to_band_sdk(self):
        """Connect to the Band platform via the Band SDK and listen for analysis events."""
        from band import AgentRuntime, BandLink

        agent_key = os.environ.get("COMMITTEE_AGENT_API_KEY")
        if not agent_key:
            logger.warning("COMMITTEE_AGENT_API_KEY not set — skipping Band SDK connection")
            return
        parts = agent_key.split("_")
        agent_id = parts[2] if len(parts) >= 4 else agent_key

        self._band_link = BandLink(agent_id=agent_id, api_key=agent_key)
        runtime = AgentRuntime(
            self._band_link,
            agent_id=agent_id,
            on_execute=self._on_band_event,
        )
        self._runtime_task = asyncio.create_task(runtime.run())
        logger.info("CommitteeAgent registered on Band as %s", agent_id)

    async def _on_band_event(self, ctx, event):
        """Triggered when another agent sends an analysis event to this room."""
        from band import AgentTools
        from band.platform.event import MessageEvent
        if not isinstance(event, MessageEvent):
            return
        payload = event.payload
        if not payload or payload.message_type not in ["startup_profile", "market_analysis", "founder_analysis", "financial_analysis", "bear_case"]:
            return

        try:
            data = json.loads(payload.content)
            session_id = data.get("session_id")
            if not session_id:
                return

            logger.info("CommitteeAgent: received %s from Band for session %s", payload.message_type, session_id)
            
            if session_id not in self._session_cache:
                self._session_cache[session_id] = {}
                
            # Store the specific analysis
            if payload.message_type == "startup_profile":
                data.pop("session_id", None)
                self._session_cache[session_id]["startup"] = StartupProfile.parse_obj(data)
            elif payload.message_type == "market_analysis":
                data.pop("session_id", None)
                self._session_cache[session_id]["market"] = MarketAnalysis.parse_obj(data)
            elif payload.message_type == "founder_analysis":
                data.pop("session_id", None)
                self._session_cache[session_id]["founder"] = FounderAnalysis.parse_obj(data)
            elif payload.message_type == "financial_analysis":
                data.pop("session_id", None)
                self._session_cache[session_id]["financial"] = FinancialAnalysis.parse_obj(data)
            elif payload.message_type == "bear_case":
                data.pop("session_id", None)
                self._session_cache[session_id]["bear"] = BearCase.parse_obj(data)

            cache = self._session_cache[session_id]
            # Check if we have all 5 pieces of information
            if all(k in cache for k in ["startup", "market", "founder", "financial", "bear"]):
                logger.info("CommitteeAgent: all inputs received for session %s, processing...", session_id)
                
                investment_memo = await self.process(
                    cache["startup"],
                    cache["market"], 
                    cache["founder"], 
                    cache["financial"], 
                    cache["bear"],
                    session_id=session_id
                )

                # Publish result back to Band
                tools = AgentTools.from_context(ctx)
                out = investment_memo.dict()
                out["session_id"] = session_id
                await tools.send_event(content=json.dumps(out), message_type="investment_memo")
                
                # Clean up cache
                del self._session_cache[session_id]

        except Exception:
            logger.exception("CommitteeAgent: failed handling Band event")

    async def process(
        self,
        startup: StartupProfile,
        market: MarketAnalysis,
        founder: FounderAnalysis,
        financial: FinancialAnalysis,
        bear: BearCase,
        session_id: Optional[str] = None,
        debate_summary: str = "",
    ) -> InvestmentMemo:

        system_prompt = (
            "You are the Lead Partner of VentureAI Investment Committee. "
            "Your job is to synthesize all diligence reports and the debate that followed between "
            "the Devil's Advocate and the analysts. Weigh the upside against the risks. "
            "Let the debate inform your confidence level and recommendation. "
            "Make a definitive investment decision. "
            "Return ONLY valid JSON. No markdown, no preamble, no explanation."
        )

        inputs = {
            "startup_profile": startup.dict(),
            "market_analysis": market.dict(),
            "founder_analysis": founder.dict(),
            "financial_analysis": financial.dict(),
            "bear_case": bear.dict(),
        }

        debate_section = f"\n\nDEBATE TRANSCRIPT:\n{debate_summary}" if debate_summary else ""

        user_prompt = (
            f"Diligence inputs:\n{json.dumps(inputs, indent=2)}{debate_section}\n\n"
            "Return ONLY valid JSON with these exact fields: "
            "verdict (string: exactly 'INVEST', 'PASS', or 'WATCH'), "
            "confidence_score (integer 0-100), "
            "executive_summary (string), "
            "market_score (integer 0-100, taken from the market analysis), "
            "founder_score (integer 0-100, taken from the founder analysis), "
            "financial_score (integer 0-100, taken from the financial analysis), "
            "bear_case_score (integer 0-100, taken from the bear case), "
            "overall_score (integer 0-100, your weighted synthesis), "
            "recommendation (string, 1-2 sentences on what to do next), "
            "due_diligence_questions (list of strings, top questions before closing), "
            "suggested_valuation_range (string), "
            "summary (string)."
        )

        try:
            resp = await self.call_llm(system_prompt, user_prompt)

            candidate = resp
            if isinstance(resp, dict):
                if "result" in resp and isinstance(resp["result"], dict):
                    candidate = resp["result"]
                elif "data" in resp and isinstance(resp["data"], dict):
                    candidate = resp["data"]

            memo = InvestmentMemo.parse_obj(candidate)

            payload = memo.dict()
            if session_id:
                payload["session_id"] = session_id
            await self.publish_to_band("investment_memo", payload)
            logger.info("CommitteeAgent published investment_memo")
            await self.notify_band_platform(
                f"[Investment Committee] Verdict: {memo.verdict} | Confidence: {memo.confidence_score}/100\n{memo.executive_summary}",
                event_type="task",
            )
            return memo

        except Exception as e:
            logger.exception("CommitteeAgent LLM call failed: %s", e)
            fallback = mock_data.MOCK_INVESTMENT_MEMO
            payload = fallback.dict()
            if session_id:
                payload["session_id"] = session_id
            try:
                await self.publish_to_band("investment_memo", payload)
            except Exception:
                logger.exception("Failed to publish fallback investment_memo")
            return fallback

    async def close(self):
        if self._runtime_task:
            self._runtime_task.cancel()
        if self._band_link:
            try:
                self._band_link.disconnect()
            except Exception:
                pass
        await super().close()
