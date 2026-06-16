import logging
from typing import Optional, Dict, Any

from ventureai.backend.agents.base_agent import BaseAgent
from ventureai.backend.models import StartupProfile


logger = logging.getLogger("ventureai.sourcing")


class SourcingAgent(BaseAgent):
    """Sourcing Agent: extracts a structured StartupProfile from free text/URL/name.

    Usage: agent.process(raw_input, session_id=...) -> StartupProfile
    Publishes to Band with message_type='startup_profile' and payload=data
    """

    async def process(self, raw_input: str, session_id: Optional[str] = None) -> StartupProfile:
        system_prompt = (
            "You are a startup analyst. Extract structured information about this startup from the provided input. "
            "Return a JSON object matching the StartupProfile schema exactly."
        )

        user_prompt = (
            "Input:\n" + raw_input + "\n\n"
            "Return ONLY valid JSON matching the StartupProfile fields: company_name, one_liner, stage, industry, founders (list), "
            "funding_history (list), location, website, raw_description, score (0-100), summary. No text outside JSON."
        )

        try:
            resp = await self.call_llm(system_prompt, user_prompt)

            # Normalize the LLM response to a candidate dict.
            candidate: Dict[str, Any]
            if isinstance(resp, dict):
                # Common wrappers: {'result': {...}} or direct object
                if "result" in resp and isinstance(resp["result"], dict):
                    candidate = resp["result"]
                elif "data" in resp and isinstance(resp["data"], dict):
                    candidate = resp["data"]
                else:
                    candidate = resp
            else:
                raise ValueError("LLM returned non-dict response")

            profile = StartupProfile.parse_obj(candidate)

            payload = profile.dict()
            if session_id:
                payload["session_id"] = session_id

            await self.publish_to_band("startup_profile", payload)
            logger.info("SourcingAgent published startup_profile for %s", profile.company_name)
            return profile

        except Exception as e:
            logger.exception("SourcingAgent failed to produce structured profile: %s", e)
            # Fallback: produce a minimal StartupProfile using the raw input
            try:
                company_name = (raw_input.strip().splitlines()[0]) if raw_input else "unknown"
            except Exception:
                company_name = "unknown"

            fallback = StartupProfile(
                company_name=company_name[:200],
                raw_description=raw_input,
                score=0,
                summary=f"Fallback profile generated after LLM/parse error: {str(e)}",
            )

            payload = fallback.dict()
            if session_id:
                payload["session_id"] = session_id

            try:
                await self.publish_to_band("startup_profile", payload)
            except Exception:
                logger.exception("Failed to publish fallback startup_profile")

            return fallback
