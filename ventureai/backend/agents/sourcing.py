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
            "You are a startup analyst. Extract structured information about a startup from the provided input.\n\n"
            "CRITICAL RULE: If the input is NOT about a real startup, company, product, or business — "
            "for example if it is random characters, gibberish, a single meaningless word, a test string, "
            "or completely off-topic — you MUST return ONLY this exact JSON and nothing else:\n"
            '{"company_name": "INVALID_INPUT", "founders": [], "funding_history": [], "score": 0, '
            '"summary": "Input does not describe a startup or company."}\n\n'
            "Only proceed with full extraction if the input clearly describes a real company or startup idea."
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
            await self.notify_band_platform(
                f"[Sourcing] {profile.company_name} identified | Stage: {profile.stage} | Score: {profile.score}/100\n{profile.summary}"
            )
            return profile

        except Exception as e:
            logger.exception("SourcingAgent failed to produce structured profile: %s", e)
            # Fallback: mark as INVALID_INPUT so the pipeline short-circuits cleanly
            fallback = StartupProfile(
                company_name="INVALID_INPUT",
                raw_description=raw_input,
                score=0,
                summary="Sourcing agent failed to process input.",
            )

            payload = fallback.dict()
            if session_id:
                payload["session_id"] = session_id

            try:
                await self.publish_to_band("startup_profile", payload)
            except Exception:
                logger.exception("Failed to publish fallback startup_profile")

            return fallback
