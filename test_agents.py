"""
Quick smoke test for all agents built so far.
Run from the project root:  python test_agents.py
"""
import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv(".env.local")

from ventureai.backend.band_client import InMemoryBandClient
from ventureai.backend.mock_data import MOCK_STARTUP_PROFILE
from ventureai.backend.agents.sourcing import SourcingAgent
from ventureai.backend.agents.market import MarketResearchAgent
from ventureai.backend.agents.founder import FounderResearchAgent
from ventureai.backend.agents.financial import FinancialAgent

AIML_KEY = os.environ.get("AIML_API_KEY", "")
BAND_KEY = os.environ.get("BAND_API_KEY", "")
SESSION_ID = "test-session-001"

AIRBNB_RAW = (
    "Airbnb is a peer-to-peer marketplace that lets homeowners rent out their spaces "
    "to travelers. Founded by Brian Chesky, Joe Gebbia, and Nathan Blecharczyk in 2008. "
    "Raised $600K seed from Y Combinator. Based in San Francisco."
)


async def run_test():
    band = InMemoryBandClient()
    await band.connect("test-room")

    received = []

    async def on_message(message_type, envelope):
        received.append((message_type, envelope.get("agent")))
        print(f"  ✓ [{envelope.get('agent')}] published '{message_type}'")

    await band.subscribe(["*"], on_message)

    print("\n=== Stage 1: Sourcing Agent ===")
    sourcing = SourcingAgent(name="sourcing", role="sourcing", api_key=AIML_KEY, band_api_key=BAND_KEY)
    await sourcing.connect_to_band(band)
    profile = await sourcing.process(AIRBNB_RAW, session_id=SESSION_ID)
    print(f"  company_name : {profile.company_name}")
    print(f"  stage        : {profile.stage}")
    print(f"  industry     : {profile.industry}")
    print(f"  score        : {profile.score}")
    print(f"  summary      : {profile.summary}")

    print("\n=== Stage 2: Research Agents (parallel) ===")
    market_agent   = MarketResearchAgent(name="market",   role="market_research",   api_key=AIML_KEY, band_api_key=BAND_KEY)
    founder_agent  = FounderResearchAgent(name="founder", role="founder_research",  api_key=AIML_KEY, band_api_key=BAND_KEY)
    financial_agent = FinancialAgent(name="financial",    role="financial_analysis", api_key=AIML_KEY, band_api_key=BAND_KEY)

    for agent in (market_agent, founder_agent, financial_agent):
        await agent.connect_to_band(band)

    market, founders, financial = await asyncio.gather(
        market_agent.process(profile, session_id=SESSION_ID),
        founder_agent.process(profile, session_id=SESSION_ID),
        financial_agent.process(profile, session_id=SESSION_ID),
    )

    print(f"\n  Market Analysis")
    print(f"    tam          : {market.tam}")
    print(f"    market_score : {market.market_score}")
    print(f"    summary      : {market.summary}")

    print(f"\n  Founder Analysis")
    print(f"    founders     : {[f.get('name') for f in founders.founders]}")
    print(f"    founder_score: {founders.founder_score}")
    print(f"    summary      : {founders.summary}")

    print(f"\n  Financial Analysis")
    print(f"    revenue_model    : {financial.revenue_model}")
    print(f"    financial_score  : {financial.financial_score}")
    print(f"    summary          : {financial.summary}")

    print(f"\n=== Band messages received: {len(received)} ===")
    for msg_type, agent_name in received:
        print(f"  {agent_name} → {msg_type}")

    await asyncio.gather(
        sourcing.close(),
        market_agent.close(),
        founder_agent.close(),
        financial_agent.close(),
    )
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(run_test())
