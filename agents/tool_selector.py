"""
Tool selector — determines which tools are needed for a given query.
Avoids executing unnecessary tools to reduce latency and cost.
"""

from typing import List, Set
from agents.classifier import QueryCategory
from utils.logger import agent_logger as logger


# Tool names available to the planner
ALL_TOOLS = [
    "get_coordinates_from_location",
    "search_amenity",
    "get_city_bbox",
    "check_flood_depth",
    "get_flooded_areas",
    "assess_path_flood_risk",
    "check_amenity_flood_status",
    "check_vehicle_passability",
    "calculate_route",
    "optimize_flood_safe_route",
]

# Tool sets per query category
CATEGORY_TOOLS = {
    QueryCategory.FLOOD_NAVIGATION: {
        "get_coordinates_from_location",
        "calculate_route",
        "check_flood_depth",
        "assess_path_flood_risk",
    },
    QueryCategory.FLOOD_INFO: {
        "check_flood_depth",
        "get_flooded_areas",
        "assess_path_flood_risk",
        "get_coordinates_from_location",
    },
    QueryCategory.EMERGENCY: {
        "get_coordinates_from_location",
        "search_amenity",
        "check_amenity_flood_status",
        "check_vehicle_passability",
        "calculate_route",
    },
    QueryCategory.AMENITY_SEARCH: {
        "get_coordinates_from_location",
        "search_amenity",
        "check_amenity_flood_status",
        "check_flood_depth",
    },
}


def select_tools(
    category: QueryCategory,
    query: str,
) -> List[str]:
    """
    Select the minimal set of tools needed for a query.
    
    Args:
        category: Classified query category
        query: Original user query (for keyword hints)
    
    Returns:
        List of tool names to make available to the planner
    """
    if category == QueryCategory.REJECTED:
        return []

    # Start with category-based tool set
    tools = set(CATEGORY_TOOLS.get(category, set()))

    # Enhance based on query keywords
    query_lower = query.lower()

    # Add location resolution if place names detected
    place_indicators = ["hospital", "station", "school", "shelter", "mosque"]
    if any(p in query_lower for p in place_indicators):
        tools.add("get_coordinates_from_location")
        tools.add("search_amenity")

    # Add routing if navigation intent
    route_indicators = ["route", "path", "navigate", "go to", "reach", "drive"]
    if any(r in query_lower for r in route_indicators):
        tools.add("calculate_route")

    # Add vehicle check if passability question
    vehicle_indicators = ["can", "passable", "ambulance", "truck", "car"]
    if any(v in query_lower for v in vehicle_indicators):
        tools.add("check_vehicle_passability")

    # Add multi-stop if multiple destinations
    multi_indicators = ["all", "multiple", "each", "every", "compare"]
    if any(m in query_lower for m in multi_indicators):
        tools.add("optimize_flood_safe_route")
        tools.add("check_amenity_flood_status")

    selected = sorted(tools)
    logger.info(f"Selected {len(selected)} tools for category '{category.value}': {selected}")
    return selected


def get_tool_descriptions() -> dict:
    """Get descriptions of all available tools for the planner prompt."""
    return {
        "get_coordinates_from_location": "Convert a place name to GPS coordinates",
        "search_amenity": "Find hospitals, shelters, police stations, etc.",
        "get_city_bbox": "Get bounding box coordinates for a city",
        "check_flood_depth": "Check real flood depth at specific coordinates",
        "get_flooded_areas": "List all active flood zones from data",
        "assess_path_flood_risk": "Assess flood risk along a straight-line corridor",
        "check_amenity_flood_status": "Check which facilities are in flood zones",
        "check_vehicle_passability": "Check if a vehicle can pass given flood depth",
        "calculate_route": "Compute K flood-aware shortest routes on road network",
        "optimize_flood_safe_route": "Find safest order for visiting multiple stops",
    }
