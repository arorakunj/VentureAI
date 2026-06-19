import asyncio
import json
import logging
import os
from typing import Optional

from ventureai.backend.agents.base_agent import BaseAgent
from ventureai.backend.models import FinancialAnalysis, StartupProfile
import ventureai.backend.mock_data as mock_data

logger = logging.getLogger("ventureai.financial")


class FinancialAgent(BaseAgent):

    def __init__(self, name, role, api_key, band_api_key, room_id=None):
        super().__init__(name, role, api_key, band_api_key, room_id)
        self._band_link = None
        self._runtime_task: Optional[asyncio.Task] = None

    async def connect_to_band_sdk(self):
        """Connect to the Band platform via the Band SDK and listen for startup_profile events."""
        from band import AgentRuntime, BandLink

        agent_key = os.environ.get("FINANCIAL_AGENT")
        if not agent_key:
            logger.warning("FINANCIAL_AGENT not set — skipping Band SDK connection")
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
        logger.info("FinancialAgent registered on Band as %s", agent_id)

    async def _on_band_event(self, ctx, event):
        """Triggered by Band when another agent sends a startup_profile event to this room."""
        from band import AgentTools
        from band.platform.event import MessageEvent
        if not isinstance(event, MessageEvent):
            return
        payload = event.payload
        if not payload or payload.message_type != "startup_profile":
            return

        logger.info("FinancialAgent: received startup_profile from Band")
        try:
            data = json.loads(payload.content)
            session_id = data.pop("session_id", None)
            profile = StartupProfile.parse_obj(data)
            analysis = await self.process(profile, session_id=session_id)

            tools = AgentTools.from_context(ctx)
            out = analysis.dict()
            if session_id:
                out["session_id"] = session_id
            await tools.send_event(content=json.dumps(out), message_type="financial_analysis")

        except Exception:
            logger.exception("FinancialAgent: failed handling Band event")

    async def process(self, profile: StartupProfile, session_id: Optional[str] = None) -> FinancialAnalysis:
        system_prompt = (
            "You are a VC financial analyst at a top-tier venture firm. "
            "Evaluate this startup's business model and financial prospects. "
            "Assess revenue model viability, unit economics, funding requirements, "
            "burn rate, and path to profitability. Identify any financial red flags. "
            "Return ONLY valid JSON. No markdown, no preamble, no explanation."
        )
        user_prompt = (
            f"Startup profile:\n{json.dumps(profile.dict(), indent=2)}\n\n"
            "Return ONLY valid JSON with these exact fields: "
            "revenue_model (string), unit_economics (object with string values), "
            "raise_amount (string), burn_assessment (string), "
            "path_to_profitability (string), financial_score (integer 0-100), "
            "red_flags (list of strings), summary (string)."
        )

        try:
            resp = await self.call_llm(system_prompt, user_prompt)

            candidate = resp
            if isinstance(resp, dict):
                if "result" in resp and isinstance(resp["result"], dict):
                    candidate = resp["result"]
                elif "data" in resp and isinstance(resp["data"], dict):
                    candidate = resp["data"]

            analysis = FinancialAnalysis.parse_obj(candidate)

            payload = analysis.dict()
            if session_id:
                payload["session_id"] = session_id
            await self.publish_to_band("financial_analysis", payload)
            logger.info("FinancialAgent published financial_analysis for %s", profile.company_name)
            await self.notify_band_platform(
                f"[Financial] {profile.company_name} | Revenue Model: {analysis.revenue_model} | Financial Score: {analysis.financial_score}/100\n{analysis.summary}"
            )
            return analysis

        except Exception as e:
            logger.exception("FinancialAgent LLM call failed: %s", e)
            fallback = mock_data.MOCK_FINANCIAL_ANALYSIS
            payload = fallback.dict()
            if session_id:
                payload["session_id"] = session_id
            try:
                await self.publish_to_band("financial_analysis", payload)
            except Exception:
                logger.exception("Failed to publish fallback financial_analysis")
            return fallback

    async def rebut(self, challenge: str, analysis: FinancialAnalysis, session_id: Optional[str] = None) -> str:
        system_prompt = (
            "You are the financial analyst in a VC investment committee debate. "
            "The Devil's Advocate has challenged your financial assessment. "
            "Defend your position with specific numbers and financial reasoning. "
            "Be precise and confident. Keep it to 2-3 sentences."
        )
        user_prompt = (
            f"Your original financial analysis: {json.dumps(analysis.dict(), indent=2)}\n\n"
            f"Devil's Advocate challenge: {challenge}\n\n"
            "Defend your analysis directly."
        )
        try:
            rebuttal = await self.call_llm_text(system_prompt, user_prompt)
        except Exception:
            logger.exception("FinancialAgent failed to generate rebuttal")
            rebuttal = "The unit economics and revenue model are sound — our financial projections are conservative and well-justified."

        await self.notify_band_platform(f"[Financial] Rebuttal: {rebuttal}")
        return rebuttal

    async def close(self):
        if self._runtime_task:
            self._runtime_task.cancel()
        if self._band_link:
            try:
                self._band_link.disconnect()
            except Exception:
                pass
        await super().close()
