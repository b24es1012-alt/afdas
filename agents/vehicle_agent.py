"""
Vehicle detection agent — determines the user's vehicle type from their query.
"""

import re
from typing import Optional

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from config.settings import settings
from models.vehicle import VehicleType, get_vehicle_profile, VehicleProfile
from utils.logger import agent_logger as logger


# Keyword-based vehicle detection
VEHICLE_KEYWORDS = {
    VehicleType.WALKING: ["walk", "walking", "on foot", "pedestrian"],
    VehicleType.MOTORCYCLE: ["motorcycle", "motorbike", "bike", "scooter"],
    VehicleType.CAR: ["car", "sedan", "driving", "drive"],
    VehicleType.SUV: ["suv", "4x4", "jeep", "off-road", "offroad"],
    VehicleType.AMBULANCE: ["ambulance", "emergency vehicle", "ems"],
    VehicleType.TRUCK: ["truck", "lorry", "heavy vehicle"],
    VehicleType.BOAT: ["boat", "rescue boat", "raft"],
}


def detect_vehicle_fast(query: str) -> Optional[VehicleType]:
    """
    Fast keyword-based vehicle detection.
    
    Args:
        query: User's query text
    
    Returns:
        VehicleType or None if not detectable
    """
    query_lower = query.lower()

    for vehicle_type, keywords in VEHICLE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in query_lower:
                return vehicle_type

    return None


async def detect_vehicle_llm(query: str) -> VehicleType:
    """
    LLM-based vehicle detection for ambiguous queries.
    
    Returns:
        Detected VehicleType (defaults to CAR)
    """
    llm = ChatGroq(
        model=settings.LLM_MODEL,
        temperature=0,
        api_key=settings.GROQ_API_KEY,
    )

    prompt = f"""From this flood navigation query, determine what vehicle the user has.
Options: walking, motorcycle, car, suv, ambulance, truck, boat

If unclear or not mentioned, respond with "car" (most common).

Query: "{query}"

Respond with ONLY the vehicle type (one word from the options)."""

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        vehicle_str = response.content.strip().lower()

        try:
            return VehicleType(vehicle_str)
        except ValueError:
            return VehicleType.CAR

    except Exception as e:
        logger.error(f"LLM vehicle detection error: {e}")
        return VehicleType.CAR


async def detect_vehicle(query: str, default: str = "car") -> VehicleProfile:
    """
    Main vehicle detection entry point.
    
    Args:
        query: User's query
        default: Default vehicle type if undetectable
    
    Returns:
        VehicleProfile for the detected vehicle
    """
    # Try fast detection first
    detected = detect_vehicle_fast(query)

    if detected:
        logger.info(f"Vehicle detected (fast): {detected.value}")
        return get_vehicle_profile(detected.value)

    # If query mentions specific passability questions, try LLM
    passability_words = ["can", "able", "reach", "passable", "pass through"]
    if any(w in query.lower() for w in passability_words):
        detected = await detect_vehicle_llm(query)
        logger.info(f"Vehicle detected (LLM): {detected.value}")
        return get_vehicle_profile(detected.value)

    # Default
    logger.info(f"Vehicle not detected, using default: {default}")
    return get_vehicle_profile(default)
