"""
Chat API endpoint — AI-powered flood assistance chat.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from auth.middleware import get_current_user, CurrentUser
from agents.planner import run_agent
from agents.classifier import classify_query, QueryCategory
from utils.logger import api_logger as logger

router = APIRouter(prefix="/chat", tags=["Chat"])


# ── Request/Response Models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Chat message from the user."""
    message: str = Field(..., min_length=1, max_length=1000)
    event_id: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class ChatResponse(BaseModel):
    """Chat response from the AI agent."""
    success: bool
    response: str
    category: str
    vehicle_type: str
    steps_executed: int


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: Optional[CurrentUser] = Depends(get_current_user),
):
    """
    Send a message to the AI flood assistance agent.
    
    The agent will:
    1. Classify the query (flood-related check)
    2. Detect vehicle type from context
    3. Plan execution steps
    4. Execute tools (routing, flood check, amenity search, etc.)
    5. Generate a helpful, safety-focused response
    """
    logger.info(f"Chat request: '{request.message[:80]}...'")

    # Quick reject for obviously non-flood queries
    category, confidence, _ = await classify_query(request.message)

    if category == QueryCategory.REJECTED:
        return ChatResponse(
            success=False,
            response=(
                "I can only help with flood-related navigation and emergency assistance. "
                "Please ask about safe routes, flood conditions, nearby hospitals, "
                "evacuation shelters, or other flood-related topics."
            ),
            category="rejected",
            vehicle_type="none",
            steps_executed=0,
        )

    try:
        # Import tools map here to avoid circular imports
        from agents.tools import get_tools_map

        tools_map = get_tools_map()
        result = await run_agent(request.message, tools_map)

        # Extract final response
        final_message = ""
        if result["messages"]:
            final_message = result["messages"][-1].content

        return ChatResponse(
            success=True,
            response=final_message,
            category=result.get("category", "unknown"),
            vehicle_type=result.get("vehicle_type", "car"),
            steps_executed=len(result.get("plan", [])),
        )

    except Exception as e:
        logger.error(f"Chat agent error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent error: {str(e)}",
        )
