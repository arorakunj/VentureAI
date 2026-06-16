import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import aiohttp
import ssl
try:
    import certifi
except Exception:
    certifi = None

from ventureai.backend.models import StartupProfile


logger = logging.getLogger("ventureai.base_agent")
logging.basicConfig(level=logging.INFO)


class BaseAgent(ABC):
    def __init__(self, name: str, role: str, api_key: str, band_api_key: str, room_id: Optional[str] = None):
        self.name = name
        self.role = role
        self.api_key = api_key
        self.band_api_key = band_api_key
        self.room_id = room_id or "default"
        self.band_client = None
        # Create aiohttp session with a certifi-backed SSL context when available
        ssl_context = None
        if certifi is not None:
            try:
                ssl_context = ssl.create_default_context(cafile=certifi.where())
            except Exception:
                ssl_context = None

        connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context is not None else None
        self._session = aiohttp.ClientSession(connector=connector)

    async def connect_to_band(self, band_client):
        """Attach a BandClient instance (injected) and register the agent."""
        self.band_client = band_client
        try:
            await self.band_client.connect(self.room_id)
            logger.info(f"Agent {self.name} connected to Band room {self.room_id}")
        except Exception as e:
            logger.error("Failed to connect to Band: %s", e)

    async def publish_to_band(self, message_type: str, data: Dict[str, Any]):
        if not self.band_client:
            logger.warning("No band client configured, skipping publish")
            return
        try:
            await self.band_client.publish(self.name, message_type, data)
            logger.info(f"{self.name} published {message_type}")
        except Exception as e:
            logger.exception("Failed publishing to Band: %s", e)

    async def subscribe_to_band(self, message_types: List[str], callback):
        if not self.band_client:
            logger.warning("No band client configured, cannot subscribe")
            return
        await self.band_client.subscribe(message_types, callback)

    async def call_llm(self, system_prompt: str, user_prompt: str, timeout: int = 30) -> Dict[str, Any]:
        """Call the AI/ML API and expect pure JSON in response body. Returns parsed JSON or raises."""
        url = os.environ.get("AIML_API_URL", "https://api.aimlapi.com/v1/chat/completions")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        payload = {
            "model": os.environ.get("AIML_MODEL", "meta-llama/Meta-Llama-3.1-13B-Instruct"),
            "messages": [
                {"role": "user", "content": combined_prompt},
            ],
            "max_tokens": 1500,
            "temperature": 0.0,
        }

        try:
            async with self._session.post(url, headers=headers, json=payload, timeout=timeout) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    logger.error("LLM API error %s: %s", resp.status, text)
                    raise RuntimeError(f"LLM API error: {resp.status}")

                # The model is instructed to return only JSON. Try to parse.
                try:
                    parsed = json.loads(text)
                    return parsed
                except json.JSONDecodeError:
                    # Attempt to extract JSON substring
                    start = text.find("{")
                    end = text.rfind("}")
                    if start != -1 and end != -1 and end > start:
                        try:
                            parsed = json.loads(text[start:end+1])
                            return parsed
                        except json.JSONDecodeError:
                            logger.exception("Failed to parse JSON from LLM response")
                    raise
        except asyncio.TimeoutError:
            logger.exception("LLM call timed out")
            raise

    @abstractmethod
    async def process(self, *args, **kwargs):
        """Implement agent-specific logic. Must publish results to Band."""
        raise NotImplementedError()

    async def close(self):
        try:
            await self._session.close()
        except Exception:
            pass
