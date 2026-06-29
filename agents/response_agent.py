"""
Response agent — formats final responses for the user.
Converts raw tool results into clear, safety-focused, actionable messages.
"""

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate

from config.settings import settings
from utils.logger import agent_logger as logger


RESPONDER_PROMPT = PromptTemplate(
    input_variables=["initial_query", "tool_results"],
    template="""You are a flood disaster response assistant for an AI-powered
navigation system. All flood data comes from real Copernicus Emergency Management
Service data and OpenStreetMap infrastructure.

The user asked: {initial_query}

Collected tool results:
{tool_results}

Using ONLY the information above, write a clear, helpful, safety-focused response:

Guidelines:
- Start with the most critical safety information
- Highlight flooded areas and unsafe routes clearly
- Recommend only verified-safe facilities
- Include specific coordinates when relevant
- Mention flood depths and vehicle limitations
- If a route was calculated, mention distance, time, and risk
- If a map was generated, tell the user it's available for viewing
- Use clear formatting (bullet points, sections)
- End with a safety recommendation

Do NOT:
- Make up information not in the tool results
- Recommend routes through dangerous flood zones
- Downplay flood risks
""",
)


async def generate_response(initial_query: str, tool_results: str) -> str:
    """
    Generate a final user-facing response from tool results.
    
    Args:
        initial_query: Original user question
        tool_results: Concatenated tool execution results
    
    Returns:
        Formatted response string
    """
    llm = ChatGroq(
        model=settings.LLM_MODEL,
        temperature=0.1,  # Slight creativity for natural language
        api_key=settings.GROQ_API_KEY,
    )

    prompt_text = RESPONDER_PROMPT.format(
        initial_query=initial_query,
        tool_results=tool_results,
    )

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt_text)])
        return response.content
    except Exception as e:
        logger.error(f"Response generation error: {e}")
        return _fallback_response(initial_query, tool_results)


def _fallback_response(query: str, results: str) -> str:
    """Generate a simple fallback response if LLM fails."""
    return (
        f"I processed your request about: {query}\n\n"
        f"Here are the results:\n{results[:2000]}\n\n"
        "Please exercise caution in flood-affected areas. "
        "If in immediate danger, call emergency services."
    )


def format_route_response(route_results: list) -> str:
    """Format route results into a readable summary."""
    if not route_results:
        return "No routes could be found between the given locations."

    lines = [f"Found {len(route_results)} route(s):\n"]

    for route in route_results:
        risk_label = "LOW"
        if route.risk_score > 0.6:
            risk_label = "HIGH"
        elif route.risk_score > 0.3:
            risk_label = "MODERATE"

        lines.append(
            f"Route {route.route_index + 1}:\n"
            f"  Distance: {route.total_distance_m:.0f} m\n"
            f"  Est. Time: {route.estimated_time_s / 60:.1f} min\n"
            f"  Risk: {risk_label} ({route.risk_score:.2f})\n"
            f"  Flooded Segments: {route.flooded_segments}/{route.total_segments}\n"
            f"  Max Flood Depth: {route.max_flood_depth:.2f} m\n"
        )

    return "\n".join(lines)
