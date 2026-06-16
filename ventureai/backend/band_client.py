import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

import aiohttp

logger = logging.getLogger("ventureai.band_client")


class BandClient:
    async def connect(self, room_id: str):
        raise NotImplementedError()

    async def publish(self, agent_name: str, message_type: str, data: Dict[str, Any]):
        raise NotImplementedError()

    async def subscribe(self, message_types: List[str], callback: Callable[[str, Dict[str, Any]], Any]):
        raise NotImplementedError()

    async def close(self):
        pass


class InMemoryBandClient(BandClient):
    """A simple in-process pub/sub Band client used for local development and tests.

    Subscribers register callbacks for message types. When publish() is called, callbacks are
    scheduled as tasks so they don't block the publisher.
    """

    def __init__(self):
        self._subs: Dict[str, List[Callable[[str, Dict[str, Any]], Any]]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, room_id: str):
        # noop for in-memory client
        logger.info("InMemoryBandClient connected to room %s", room_id)

    async def publish(self, agent_name: str, message_type: str, data: Dict[str, Any]):
        # Envelope message
        envelope = {
            "agent": agent_name,
            "type": message_type,
            "data": data,
        }

        # deliver to exact-type subscribers
        async with self._lock:
            callbacks = list(self._subs.get(message_type, []))
            # wildcard subscribers registered under '*'
            callbacks += list(self._subs.get("*", []))

        for cb in callbacks:
            try:
                # schedule callbacks so publish is non-blocking
                if asyncio.iscoroutinefunction(cb):
                    asyncio.create_task(cb(message_type, envelope))
                else:
                    # run sync callbacks in threadpool
                    loop = asyncio.get_running_loop()
                    loop.run_in_executor(None, cb, message_type, envelope)
            except Exception:
                logger.exception("Error scheduling subscriber callback for %s", message_type)

    async def subscribe(self, message_types: List[str], callback: Callable[[str, Dict[str, Any]], Any]):
        async with self._lock:
            for m in message_types:
                self._subs.setdefault(m, []).append(callback)
        logger.info("Subscriber registered for %s", message_types)


class HttpPollingBandClient(BandClient):
    """A thin HTTP polling adapter skeleton. Configure with BAND_BASE_URL and BAND_API_KEY.

    This is a best-effort adapter; adapt paths to your Band installation. It polls for new messages
    and calls subscribers callbacks.
    """

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None
        self._subs: Dict[str, List[Callable[[str, Dict[str, Any]], Any]]] = {}
        self._poll_task: Optional[asyncio.Task] = None
        self._running = False

    async def connect(self, room_id: str):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        self._session = aiohttp.ClientSession(headers=headers)
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop(room_id))

    async def _poll_loop(self, room_id: str):
        # Polling loop; adjust endpoint and response parsing to your Band API
        url = f"{self.base_url}/rooms/{room_id}/messages"
        while self._running:
            try:
                async with self._session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        body = await resp.json()
                        # Expect body to be a list of messages
                        for msg in body or []:
                            mtype = msg.get("type")
                            callbacks = self._subs.get(mtype, []) + self._subs.get("*", [])
                            for cb in callbacks:
                                if asyncio.iscoroutinefunction(cb):
                                    asyncio.create_task(cb(mtype, msg))
                                else:
                                    loop = asyncio.get_running_loop()
                                    loop.run_in_executor(None, cb, mtype, msg)
                    else:
                        logger.debug("Band polling returned status %s", resp.status)
            except Exception:
                logger.exception("Error polling Band messages")

            await asyncio.sleep(1.0)

    async def publish(self, agent_name: str, message_type: str, data: Dict[str, Any]):
        if not self._session:
            raise RuntimeError("HttpPollingBandClient not connected")
        url = f"{self.base_url}/rooms/publish"
        payload = {"agent": agent_name, "type": message_type, "data": data}
        try:
            async with self._session.post(url, json=payload, timeout=10) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    logger.error("Failed to publish to Band: %s %s", resp.status, text)
        except Exception:
            logger.exception("Failed to publish to Band")

    async def subscribe(self, message_types: List[str], callback: Callable[[str, Dict[str, Any]], Any]):
        for m in message_types:
            self._subs.setdefault(m, []).append(callback)

    async def close(self):
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
        if self._session:
            await self._session.close()
