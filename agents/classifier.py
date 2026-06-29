"""
Query classifier — determines if a request is flood-related and actionable.
Rejects non-flood queries before they reach the expensive planner.
"""

import re
from typing import Tuple
from enum import Enum

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from config.settings import settings
from utils.logger import agent_logger as logger


class QueryCategory(str, Enum):
    FLOOD_NAVIGATION = "flood_navigation"
    FLOOD_INFO = "flood_info"
    EMERGENCY = "emergency"
    AMENITY_SEARCH = "amenity_search"
    GENERAL_QUESTION = "general_question"
    REJECTED = "rejected"


# Keywords that indicate flood-related queries
FLOOD_KEYWORDS = [
    "flood", "flooded", "water", "depth", "safe", "route", "navigate",
    "hospital", "shelter", "evacuate", "evacuation", "rescue", "stuck",
    "ambulance", "passable", "blocked", "road", "accessible", "nearest",
    "emergency", "help", "danger", "risk", "avoid", "alternative",
]

# Patterns that should be rejected (not flood-related)
REJECT_PATTERNS = [
    r"\b(joke|funny|humor)\b",
    r"\b(movie|film|show|series)\b",
    r"\b(recipe|cook|food)\b",
    r"\b(sport|game|match|score)\b",
    r"\b(celebrity|gossip)\b",
    r"\b(stock|crypto|bitcoin)\b",
]


def classify_query_fast(query: str) -> Tuple[QueryCategory, float]:
    """
    Fast rule-based classification (no LLM needed).
    Returns (category, confidence) tuple.
    
    Used as first-pass filter before LLM classification.
    """
    query_lower = query.lower().strip()

    # Check reject patterns first
    for pattern in REJECT_PATTERNS:
        if re.search(pattern, query_lower):
            return QueryCategory.REJECTED, 0.95

    # Count flood-relevant keywords
    keyword_hits = sum(1 for kw in FLOOD_KEYWORDS if kw in query_lower)
    total_words = len(query_lower.split())

    # Emergency detection
    emergency_words = {"emergency", "urgent", "help", "stuck", "rescue", "dying"}
    if emergency_words.intersection(query_lower.split()):
        return QueryCategory.EMERGENCY, 0.9

    # High confidence flood-related
    if keyword_hits >= 3:
        if any(w in query_lower for w in ["route", "path", "navigate", "direction", "go"]):
            return QueryCategory.FLOOD_NAVIGATION, 0.85
        return QueryCategory.FLOOD_INFO, 0.8

    # Medium confidence
    if keyword_hits >= 1:
        if any(w in query_lower for w in ["hospital", "shelter", "school", "pharmacy"]):
            return QueryCategory.AMENITY_SEARCH, 0.7
        return QueryCategory.FLOOD_INFO, 0.6

    # Low confidence — could be general
    if keyword_hits == 0 and total_words > 3:
        return QueryCategory.GENERAL_QUESTION, 0.5

    # Default to flood info with low confidence (let planner decide)
    return QueryCategory.FLOOD_INFO, 0.4


async def classify_query_llm(query: str) -> Tuple[QueryCategory, str]:
    """
    LLM-based classification for ambiguous queries.
    Only called when fast classification has low confidence.
    
    Returns:
        (category, explanation)
    """
    llm = ChatGroq(
        model=settings.LLM_MODEL,
        temperature=0,
        api_key=settings.GROQ_API_KEY,
    )

    prompt = f"""You are a query classifier for a Flood Disaster Assistance System.
Classify this user query into ONE of these categories:

- flood_navigation: User wants a safe route or directions during flooding
- flood_info: User asks about flood conditions, depth, affected areas
- emergency: User is in immediate danger or needs urgent help
- amenity_search: User looking for hospitals, shelters, facilities
- rejected: Query is NOT related to floods or navigation at all

Query: "{query}"

Respond with ONLY the category name (one word from the list above)."""

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        category_str = response.content.strip().lower().replace(" ", "_")

        # Map to enum
        try:
            category = QueryCategory(category_str)
        except ValueError:
            category = QueryCategory.FLOOD_INFO

        return category, f"LLM classified as: {category_str}"

    except Exception as e:
        logger.error(f"LLM classification error: {e}")
        return QueryCategory.FLOOD_INFO, f"Classification error, defaulting to flood_info"


async def classify_query(query: str) -> Tuple[QueryCategory, float, str]:
    """
    Main classification entry point.
    Uses fast rule-based first, falls back to LLM for ambiguous cases.
    
    Returns:
        (category, confidence, reason)
    """
    category, confidence = classify_query_fast(query)

    if confidence >= 0.7:
        logger.info(f"Query classified (fast): {category.value} (conf={confidence:.2f})")
        return category, confidence, "Rule-based classification"

    # Low confidence — use LLM
    logger.info(f"Fast classification uncertain (conf={confidence:.2f}), using LLM...")
    llm_category, reason = await classify_query_llm(query)
    logger.info(f"Query classified (LLM): {llm_category.value}")
    return llm_category, 0.8, reason
