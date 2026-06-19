import asyncio
import json
import logging
import os
from typing import Optional, Dict

from ventureai.backend.agents.base_agent import BaseAgent
from ventureai.backend.models import MarketAnalysis, FounderAnalysis, FinancialAnalysis, BearCase
import ventureai.backend.mock_data as mock_data

logger = logging.getLogger("ventureai.devil")


class DevilAgent(BaseAgent):
    def __init__(self, name, role, api_key, band_api_key, room_id=None):
        super().__init__(name, role, api_key, band_api_key, room_id)
        self._band_link = None
        self._runtime_task: Optional[asyncio.Task] = None
        
        # Dictionary to store intermediate results per session_id
        self._session_cache: Dict[str, dict] = {}

    async def connect_to_band_sdk(self):
        """Connect to the Band platform via the Band SDK and listen for analysis events."""
        from band import AgentRuntime, BandLink

        agent_key = os.environ.get("DEVIL_AGENT_API_KEY")
        if not agent_key:
            logger.warning("DEVIL_AGENT_API_KEY not set — skipping Band SDK connection")
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
        logger.info("DevilAgent registered on Band as %s", agent_id)

    async def _on_band_event(self, ctx, event):
        """Triggered when another agent sends an analysis event to this room."""
        from band import AgentTools
        from band.platform.event import MessageEvent
        if not isinstance(event, MessageEvent):
            return
        payload = event.payload
        if not payload or payload.message_type not in ["market_analysis", "founder_analysis", "financial_analysis"]:
            return

        try:
            data = json.loads(payload.content)
            session_id = data.get("session_id")
            if not session_id:
                return

            logger.info("DevilAgent: received %s from Band for session %s", payload.message_type, session_id)
            
            if session_id not in self._session_cache:
                self._session_cache[session_id] = {}
                
            # Store the specific analysis
            if payload.message_type == "market_analysis":
                data.pop("session_id", None)
                self._session_cache[session_id]["market"] = MarketAnalysis.parse_obj(data)
            elif payload.message_type == "founder_analysis":
                data.pop("session_id", None)
                self._session_cache[session_id]["founder"] = FounderAnalysis.parse_obj(data)
            elif payload.message_type == "financial_analysis":
                data.pop("session_id", None)
                self._session_cache[session_id]["financial"] = FinancialAnalysis.parse_obj(data)

            cache = self._session_cache[session_id]
            # Check if we have all 3 analyses
            if "market" in cache and "founder" in cache and "financial" in cache:
                logger.info("DevilAgent: all analyses received for session %s, processing...", session_id)
                
                analysis = await self.process(
                    cache["market"], 
                    cache["founder"], 
                    cache["financial"], 
                    session_id=session_id
                )

                # Publish result back to Band
                tools = AgentTools.from_context(ctx)
                out = analysis.dict()
                out["session_id"] = session_id
                await tools.send_event(content=json.dumps(out), message_type="bear_case")
                
                # Clean up cache
                del self._session_cache[session_id]

        except Exception:
            logger.exception("DevilAgent: failed handling Band event")

    async def process(
        self, 
        market: MarketAnalysis, 
        founder: FounderAnalysis, 
        financial: FinancialAnalysis, 
        session_id: Optional[str] = None
    ) -> BearCase:
        
        system_prompt = (
            "You are a highly skeptical VC partner acting as the 'Devil\'s Advocate'. "
            "Your job is to challenge every positive finding in the provided market, founder, and financial analyses. "
            "Identify weaknesses, steelman the bear case, and highlight failure modes. "
            "Return ONLY valid JSON. No markdown, no preamble, no explanation."
        )
        
        inputs = {
            "market_analysis": market.dict(),
            "founder_analysis": founder.dict(),
            "financial_analysis": financial.dict()
        }
        
        user_prompt = (
            f"Diligence inputs:\n{json.dumps(inputs, indent=2)}\n\n"
            "Return ONLY valid JSON with these exact fields: "
            "market_challenges (list of strings), founder_challenges (list of strings), "
            "financial_challenges (list of strings), failure_modes (list of strings), "
            "bear_case_score (integer 0-100 indicating severity of risks, 100=highest risk), summary (string)."
        )

        try:
            resp = await self.call_llm(system_prompt, user_prompt)

            candidate = resp
            if isinstance(resp, dict):
                if "result" in resp and isinstance(resp["result"], dict):
                    candidate = resp["result"]
                elif "data" in resp and isinstance(resp["data"], dict):
                    candidate = resp["data"]

            analysis = BearCase.parse_obj(candidate)

            payload = analysis.dict()
            if session_id:
                payload["session_id"] = session_id
            await self.publish_to_band("bear_case", payload)
            logger.info("DevilAgent published bear_case")
            await self.notify_band_platform(
                f"[Devil's Advocate] Bear Case | Risk Score: {analysis.bear_case_score}/100\n{analysis.summary}"
            )
            return analysis

        except Exception as e:
            logger.exception("DevilAgent LLM call failed: %s", e)
            fallback = mock_data.MOCK_BEAR_CASE
            payload = fallback.dict()
            if session_id:
                payload["session_id"] = session_id
            try:
                await self.publish_to_band("bear_case", payload)
            except Exception:
                logger.exception("Failed to publish fallback bear_case")
            await self.notify_band_platform(
                f"[Devil's Advocate] Bear Case | Risk Score: {fallback.bear_case_score}/100\n{fallback.summary}"
            )
            return fallback

    async def generate_challenges(
        self,
        market: MarketAnalysis,
        founder: FounderAnalysis,
        financial: FinancialAnalysis,
        bear: BearCase,
        session_id: Optional[str] = None,
    ) -> Dict[str, str]:
        system_prompt = (
            "You are the Devil's Advocate in a VC investment committee debate. "
            "You have already written a bear case. Now generate sharp, specific one-paragraph challenges "
            "aimed directly at each analyst to force them to defend their work. "
            "Be pointed and skeptical — name specific numbers, assumptions, or claims to attack. "
            "Return ONLY valid JSON. No markdown, no preamble."
        )
        user_prompt = (
            f"Market analysis: {json.dumps(market.dict(), indent=2)}\n\n"
            f"Founder analysis: {json.dumps(founder.dict(), indent=2)}\n\n"
            f"Financial analysis: {json.dumps(financial.dict(), indent=2)}\n\n"
            f"Your bear case: {json.dumps(bear.dict(), indent=2)}\n\n"
            "Return ONLY valid JSON with exactly these three fields: "
            "market_challenge (string), founder_challenge (string), financial_challenge (string)."
        )
        try:
            resp = await self.call_llm(system_prompt, user_prompt)
            challenges = {
                "market_challenge": resp.get("market_challenge", ""),
                "founder_challenge": resp.get("founder_challenge", ""),
                "financial_challenge": resp.get("financial_challenge", ""),
            }
        except Exception:
            logger.exception("DevilAgent failed to generate challenges, using bear case summary")
            challenges = {
                "market_challenge": bear.market_challenges[0] if bear.market_challenges else bear.summary,
                "founder_challenge": bear.founder_challenges[0] if bear.founder_challenges else bear.summary,
                "financial_challenge": bear.financial_challenges[0] if bear.financial_challenges else bear.summary,
            }

        await self.notify_band_platform(
            f"[Devil's Advocate] Challenging the analysts:\n\n"
            f"To Market: {challenges['market_challenge']}\n\n"
            f"To Founder: {challenges['founder_challenge']}\n\n"
            f"To Financial: {challenges['financial_challenge']}"
        )
        return challenges

    async def evaluate_round(
        self,
        challenges: Dict[str, str],
        market_rebuttal: str,
        founder_rebuttal: str,
        financial_rebuttal: str,
        round_num: int,
        session_id: Optional[str] = None,
    ) -> Dict:
        system_prompt = (
            "You are the Devil's Advocate in a VC investment committee debate. "
            "You challenged the analysts and they have responded. Evaluate their rebuttals critically.\n"
            "Decide whether to keep pressing or close the debate:\n"
            "- If the analysts have NOT adequately addressed your concerns, continue with sharper, more specific challenges.\n"
            "- If they have made genuinely compelling points that change your view, concede gracefully but note remaining concerns.\n"
            "- Be strategic — don't repeat yourself. Escalate or concede based on what was actually said.\n"
            "Return ONLY valid JSON. No markdown, no preamble."
        )
        user_prompt = (
            f"Round {round_num} — Your challenges:\n"
            f"  To Market: {challenges['market_challenge']}\n"
            f"  To Founder: {challenges['founder_challenge']}\n"
            f"  To Financial: {challenges['financial_challenge']}\n\n"
            f"Their rebuttals:\n"
            f"  Market: {market_rebuttal}\n"
            f"  Founder: {founder_rebuttal}\n"
            f"  Financial: {financial_rebuttal}\n\n"
            "Return ONLY valid JSON. If continuing, use this shape:\n"
            '{"continue": true, "response": "your 2-3 sentence reaction", '
            '"market_challenge": "new challenge", "founder_challenge": "new challenge", "financial_challenge": "new challenge"}\n'
            "If closing the debate, use this shape:\n"
            '{"continue": false, "response": "your closing statement — concede what was earned, hold what wasn\'t"}'
        )
        try:
            resp = await self.call_llm(system_prompt, user_prompt)
            should_continue = bool(resp.get("continue", False))
            result = {
                "continue": should_continue,
                "response": resp.get("response", ""),
            }
            if should_continue:
                result["market_challenge"] = resp.get("market_challenge", challenges["market_challenge"])
                result["founder_challenge"] = resp.get("founder_challenge", challenges["founder_challenge"])
                result["financial_challenge"] = resp.get("financial_challenge", challenges["financial_challenge"])
        except Exception:
            logger.exception("DevilAgent failed to evaluate round")
            result = {
                "continue": False,
                "response": "The analysts have made their case. I maintain my core concerns but acknowledge their points.",
            }

        label = "Pressing further" if result["continue"] else "Closing the debate"
        await self.notify_band_platform(f"[Devil's Advocate] {label}: {result['response']}")
        return result

    async def close(self):
        if self._runtime_task:
            self._runtime_task.cancel()
        if self._band_link:
            try:
                self._band_link.disconnect()
            except Exception:
                pass
        await super().close()
