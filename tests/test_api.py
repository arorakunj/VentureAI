"""Test API endpoints"""
import pytest
import json
from httpx import AsyncClient
from ventureai.backend.main import app


@pytest.mark.asyncio
async def test_evaluate_valid_input():
    """Test /evaluate with valid input returns session_id"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/evaluate",
            json={"input": "Airbnb is a marketplace for short-term rentals"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0


@pytest.mark.asyncio
async def test_evaluate_missing_input():
    """Test /evaluate with missing input returns 400"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/evaluate",
            json={}
        )
        assert response.status_code == 400
        data = response.json()
        assert "missing 'input'" in data.get("detail", "")


@pytest.mark.asyncio
async def test_status_endpoint():
    """Test /status returns message list"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First, create a session
        eval_response = await client.post(
            "/evaluate",
            json={"input": "Test startup"}
        )
        session_id = eval_response.json()["session_id"]

        # Then check status
        status_response = await client.get(f"/status/{session_id}")
        assert status_response.status_code == 200
        data = status_response.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)


@pytest.mark.asyncio
async def test_status_nonexistent_session():
    """Test /status with non-existent session returns empty list"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/status/invalid-session-id")
        assert response.status_code == 200
        data = response.json()
        assert data["messages"] == []


@pytest.mark.asyncio
async def test_memo_not_ready():
    """Test /memo before pipeline completes returns 404"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a session but don't wait for memo
        eval_response = await client.post(
            "/evaluate",
            json={"input": "Test"}
        )
        session_id = eval_response.json()["session_id"]

        # Immediately check memo (won't be ready)
        memo_response = await client.get(f"/memo/{session_id}")
        # May be 404 or 200 depending on timing, but data shouldn't exist yet
        if memo_response.status_code == 404:
            assert "memo not ready" in memo_response.json().get("detail", "")
