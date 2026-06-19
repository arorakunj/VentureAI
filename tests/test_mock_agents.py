"""Test agents with mocked LLM responses (no API required)"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from ventureai.backend.models import StartupProfile
from ventureai.backend.agents.sourcing import SourcingAgent
from ventureai.backend.band_client import InMemoryBandClient


@pytest.fixture
async def mock_band():
    """Create a mock band client"""
    band = InMemoryBandClient()
    await band.connect("test-room")
    return band


@pytest.mark.asyncio
async def test_sourcing_agent_with_mock_llm(mock_band):
    """Test SourcingAgent with mocked LLM response"""
    agent = SourcingAgent("sourcing", "sourcing", api_key="test-key", band_api_key="", room_id="test-room")
    await agent.connect_to_band(mock_band)

    # Mock LLM response
    mock_response = {
        "company_name": "Airbnb",
        "one_liner": "Peer-to-peer marketplace for rentals",
        "stage": "Series A",
        "industry": "Travel Tech",
        "founders": ["Brian Chesky", "Joe Gebbia"],
        "location": "San Francisco",
        "website": "airbnb.com",
        "score": 85
    }

    with patch.object(agent, 'call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response

        profile = await agent.process("Test startup description", session_id="test-session")

        assert profile.company_name == "Airbnb"
        assert profile.stage == "Series A"
        assert profile.score == 85
        assert "Brian Chesky" in profile.founders

    await agent.close()


@pytest.mark.asyncio
async def test_sourcing_agent_minimal_response(mock_band):
    """Test SourcingAgent with minimal LLM response"""
    agent = SourcingAgent("sourcing", "sourcing", api_key="test-key", band_api_key="", room_id="test-room")
    await agent.connect_to_band(mock_band)

    mock_response = {
        "company_name": "TestCo",
        "score": 0
    }

    with patch.object(agent, 'call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response

        profile = await agent.process("TestCo is a startup", session_id="test-session")

        assert profile.company_name == "TestCo"
        assert profile.score == 0
        assert profile.founders == []

    await agent.close()


@pytest.mark.asyncio
async def test_sourcing_agent_llm_error_handling(mock_band):
    """Test SourcingAgent handles LLM errors gracefully"""
    agent = SourcingAgent("sourcing", "sourcing", api_key="test-key", band_api_key="", room_id="test-room")
    await agent.connect_to_band(mock_band)

    with patch.object(agent, 'call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = RuntimeError("LLM API error: 404")

        # Should not raise, but return empty/default profile
        profile = await agent.process("Test input", session_id="test-session")

        assert profile is not None
        assert isinstance(profile, StartupProfile)

    await agent.close()


@pytest.mark.asyncio
async def test_market_agent_with_mock_llm(mock_band):
    """Test MarketResearchAgent with mocked LLM response"""
    from ventureai.backend.agents.market import MarketResearchAgent

    agent = MarketResearchAgent("market", "market", api_key="test-key", band_api_key="", room_id="test-room")
    await agent.connect_to_band(mock_band)

    mock_response = {
        "tam": "$50B",
        "market_growth": "30% CAGR",
        "timing_verdict": "Perfect timing, strong tailwinds",
        "competitors": ["Vrbo", "HomeAway", "Booking.com"],
        "differentiation": "Unique trust model",
        "market_score": 85,
        "key_risks": ["Regulatory pressure", "Competitive response"],
        "summary": "Massive market with strong growth"
    }

    with patch.object(agent, 'call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response

        profile = StartupProfile(company_name="Airbnb")
        market = await agent.process(profile, session_id="test-session")

        assert market.tam == "$50B"
        assert market.market_score == 85
        assert len(market.competitors) == 3

    await agent.close()


@pytest.mark.asyncio
async def test_financial_agent_with_mock_llm(mock_band):
    """Test FinancialAgent with mocked LLM response"""
    from ventureai.backend.agents.financial import FinancialAgent

    agent = FinancialAgent("financial", "financial", api_key="test-key", band_api_key="", room_id="test-room")
    await agent.connect_to_band(mock_band)

    mock_response = {
        "revenue_model": "Marketplace take rate (3-10%)",
        "unit_economics": {
            "cac": "$50",
            "ltv": "$2000",
            "payback_months": 2
        },
        "raise_amount": "$25M Series B",
        "burn_assessment": "Moderate burn, $2M/month",
        "path_to_profitability": "24 months at current trajectory",
        "financial_score": 75,
        "red_flags": [],
        "summary": "Strong unit economics"
    }

    with patch.object(agent, 'call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response

        profile = StartupProfile(company_name="Airbnb")
        financial = await agent.process(profile, session_id="test-session")

        assert financial.financial_score == 75
        assert financial.unit_economics["ltv"] == "$2000"
        assert len(financial.red_flags) == 0

    await agent.close()
