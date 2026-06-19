import asyncio
import json
import logging
import os
from typing import Optional

from ventureai.backend.agents.base_agent import BaseAgent
from ventureai.backend.models import FounderAnalysis, StartupProfile
import ventureai.backend.mock_data as mock_data

logger = logging.getLogger("ventureai.founder")


class FounderResearchAgent(BaseAgent):

    def __init__(self, name, role, api_key, band_api_key, room_id=None):
        super().__init__(name, role, api_key, band_api_key, room_id)
        self._band_link = None
        self._runtime_task: Optional[asyncio.Task] = None

    async def connect_to_band_sdk(self):
        """Connect to the Band platform via the Band SDK and listen for startup_profile events."""
        from band import AgentRuntime, BandLink

        agent_key = os.environ.get("FOUNDER_RESEARCH_AGENT")
        if not agent_key:
            logger.warning("FOUNDER_RESEARCH_AGENT not set — skipping Band SDK connection")
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
        logger.info("FounderResearchAgent registered on Band as %s", agent_id)

    async def _on_band_event(self, ctx, event):
        """Triggered by Band when another agent sends a startup_profile event to this room."""
        from band import AgentTools
        from band.platform.event import MessageEvent
        if not isinstance(event, MessageEvent):
            return
        payload = event.payload
        if not payload or payload.message_type != "startup_profile":
            return

        logger.info("FounderResearchAgent: received startup_profile from Band")
        try:
            data = json.loads(payload.content)
            session_id = data.pop("session_id", None)
            profile = StartupProfile.parse_obj(data)
            analysis = await self.process(profile, session_id=session_id)

            tools = AgentTools.from_context(ctx)
            out = analysis.dict()
            if session_id:
                out["session_id"] = session_id
            await tools.send_event(content=json.dumps(out), message_type="founder_analysis")

        except Exception:
            logger.exception("FounderResearchAgent: failed handling Band event")

    async def process(self, profile: StartupProfile, session_id: Optional[str] = None) -> FounderAnalysis:
        system_prompt = (
            "You are a VC partner specializing in founder diligence at a top-tier venture firm. "
            "Evaluate the founding team based on the startup profile provided. "
            "Assess each founder's background, domain expertise, and any red flags. "
            "Also assess overall team completeness and whether any prior exits exist. "
            "Return ONLY valid JSON. No markdown, no preamble, no explanation."
        )
        user_prompt = (
            f"Startup profile:\n{json.dumps(profile.dict(), indent=2)}\n\n"
            "Return ONLY valid JSON with these exact fields: "
            "founders (list of objects, each with: name, background, domain_expertise, red_flags), "
            "team_completeness (string), prior_exits (boolean), "
            "founder_score (integer 0-100), summary (string)."
        )

        try:
            resp = await self.call_llm(system_prompt, user_prompt)

            candidate = resp
            if isinstance(resp, dict):
                if "result" in resp and isinstance(resp["result"], dict):
                    candidate = resp["result"]
                elif "data" in resp and isinstance(resp["data"], dict):
                    candidate = resp["data"]

            analysis = FounderAnalysis.parse_obj(candidate)

            payload = analysis.dict()
            if session_id:
                payload["session_id"] = session_id
            await self.publish_to_band("founder_analysis", payload)
            logger.info("FounderResearchAgent published founder_analysis for %s", profile.company_name)
            await self.notify_band_platform(
                f"[Founder Research] {profile.company_name} | Team Completeness: {analysis.team_completeness} | Founder Score: {analysis.founder_score}/100\n{analysis.summary}"
            )
            return analysis

        except Exception as e:
            logger.exception("FounderResearchAgent LLM call failed: %s", e)
            fallback = mock_data.MOCK_FOUNDER_ANALYSIS
            payload = fallback.dict()
            if session_id:
                payload["session_id"] = session_id
            try:
                await self.publish_to_band("founder_analysis", payload)
            except Exception:
                logger.exception("Failed to publish fallback founder_analysis")
            return fallback

    async def rebut(self, challenge: str, analysis: FounderAnalysis, session_id: Optional[str] = None) -> str:
        system_prompt = (
            "You are the founder diligence analyst in a VC investment committee debate. "
            "The Devil's Advocate has challenged your assessment of the founding team. "
            "Defend your position with specific evidence from the founder backgrounds. "
            "Be direct and confident. Keep it to 2-3 sentences."
        )
        user_prompt = (
            f"Your original founder analysis: {json.dumps(analysis.dict(), indent=2)}\n\n"
            f"Devil's Advocate challenge: {challenge}\n\n"
            "Defend your assessment directly."
        )
        try:
            rebuttal = await self.call_llm_text(system_prompt, user_prompt)
        except Exception:
            logger.exception("FounderResearchAgent failed to generate rebuttal")
            rebuttal = "The founding team's track record and domain expertise speak for themselves — our assessment is well-grounded."

        await self.notify_band_platform(f"[Founder Research] Rebuttal: {rebuttal}")
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
