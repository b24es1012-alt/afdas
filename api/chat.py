"""
Chat API endpoint — AI-powered flood assistance chat.
Now with Redis-based session memory for multi-turn conversations.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from auth.middleware import get_current_user, CurrentUser
from agents.planner import run_agent
from agents.classifier import classify_query, QueryCategory
from cache.session_memory import SessionMemory
from utils.logger import api_logger as logger

router = APIRouter(prefix="/chat", tags=["Chat"])

# Shared session memory instance
_session_memory = SessionMemory()


# ── Request/Response Models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Chat message from the user."""
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = Field(default=None, description="Session ID for conversation memory. Auto-generated if not provided.")
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
    session_id: str  # Return session_id so frontend can send it back
    routes: Optional[list] = None  # Structured route data for map display


class SessionInfoResponse(BaseModel):
    """Session metadata."""
    session_id: str
    exists: bool
    message_count: int = 0
    ttl_remaining: int = 0
    session_started: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: Optional[CurrentUser] = Depends(get_current_user),
):
    """
    Send a message to the AI flood assistance agent.
    
    The agent will:
    1. Load conversation history from Redis (session memory)
    2. Classify the query (flood-related check)
    3. Detect vehicle type from context
    4. Plan execution steps
    5. Execute tools (routing, flood check, amenity search, etc.)
    6. Generate a helpful, safety-focused response
    7. Save both user message and response to session memory
    
    Pass `session_id` to maintain conversation context across messages.
    If omitted, a new session is created automatically.
    """
    # Generate or use provided session_id
    session_id = request.session_id or str(uuid.uuid4())

    logger.info(f"Chat request [session={session_id[:8]}...]: '{request.message[:80]}...'")

    # Store user message in session memory
    try:
        await _session_memory.add_message(
            session_id=session_id,
            role="user",
            content=request.message,
            metadata={
                "lat": request.lat,
                "lon": request.lon,
                "event_id": request.event_id,
            },
        )
    except Exception as e:
        logger.warning(f"Failed to store user message in session: {e}")

    # Quick reject for obviously non-flood queries
    category, confidence, _ = await classify_query(request.message)

    if category == QueryCategory.REJECTED:
        reject_response = (
            "I can only help with flood-related navigation and emergency assistance. "
            "Please ask about safe routes, flood conditions, nearby hospitals, "
            "evacuation shelters, or other flood-related topics."
        )
        # Store rejection in session too
        try:
            await _session_memory.add_message(
                session_id=session_id,
                role="assistant",
                content=reject_response,
                metadata={"category": "rejected"},
            )
        except Exception:
            pass

        return ChatResponse(
            success=False,
            response=reject_response,
            category="rejected",
            vehicle_type="none",
            steps_executed=0,
            session_id=session_id,
        )

    try:
        # Import tools map here to avoid circular imports
        from agents.tools import get_tools_map, get_last_route_results, clear_last_route_results

        tools_map = get_tools_map()
        
        # Clear any previous route results before running agent
        clear_last_route_results()
        
        # Build query with GPS context and conversation history
        query = request.message

        # Add location context if GPS provided
        if request.lat and request.lon:
            from agents.tools import _reverse_geocode_city
            city, state, country = await _reverse_geocode_city(request.lat, request.lon)
            query = f"{query}\n[User GPS: lat={request.lat}, lon={request.lon}, city={city}, state={state}, country={country}]"

        # Add conversation history from session memory
        try:
            history_context = await _session_memory.get_context_string(
                session_id=session_id,
                last_n=8,  # Include last 8 messages for context
                max_chars=2500,
            )
            if history_context:
                query = f"{query}\n\n{history_context}"
        except Exception as e:
            logger.warning(f"Failed to load session history: {e}")

        # Run the AI agent
        result = await run_agent(query, tools_map)

        # Extract final response
        final_message = ""
        if result["messages"]:
            final_message = result["messages"][-1].content

        # Get structured route data if calculate_route was called
        routes_data = get_last_route_results()
        clear_last_route_results()

        # Store assistant response in session memory
        try:
            await _session_memory.add_message(
                session_id=session_id,
                role="assistant",
                content=final_message,
                metadata={
                    "category": result.get("category", "unknown"),
                    "vehicle_type": result.get("vehicle_type", "car"),
                    "has_routes": routes_data is not None,
                    "steps_executed": len(result.get("plan", [])),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to store assistant response in session: {e}")

        return ChatResponse(
            success=True,
            response=final_message,
            category=result.get("category", "unknown"),
            vehicle_type=result.get("vehicle_type", "car"),
            steps_executed=len(result.get("plan", [])),
            session_id=session_id,
            routes=routes_data,
        )

    except Exception as e:
        logger.error(f"Chat agent error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent error: {str(e)}",
        )


@router.get("/session/{session_id}", response_model=SessionInfoResponse)
async def get_session_info(session_id: str):
    """Get metadata about a chat session (message count, TTL, etc.)."""
    info = await _session_memory.get_session_info(session_id)
    return SessionInfoResponse(
        session_id=session_id,
        exists=info.get("exists", False),
        message_count=info.get("message_count", 0),
        ttl_remaining=info.get("ttl_remaining", 0),
        session_started=info.get("session_started"),
    )


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear all messages for a session (reset conversation)."""
    await _session_memory.clear_session(session_id)
    return {"success": True, "message": f"Session {session_id} cleared"}


@router.get("/session/{session_id}/history")
async def get_session_history(
    session_id: str,
    last_n: int = 20,
):
    """Retrieve conversation history for a session."""
    messages = await _session_memory.get_history(session_id, last_n=last_n)
    return {
        "session_id": session_id,
        "messages": [msg.to_dict() for msg in messages],
        "count": len(messages),
    }
