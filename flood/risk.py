"""
Flood risk assessment and scoring.
"""

from typing import List, Tuple
from models.flood import FloodSeverity, FloodRiskAssessment
from utils.constants import RISK_TIERS


def depth_to_severity(depth: float) -> Tuple[FloodSeverity, str]:
    """
    Classify flood depth into a severity tier.
    
    Args:
        depth: Water depth in metres
    
    Returns:
        (severity_enum, description_string)
    """
    for threshold, label, desc in RISK_TIERS:
        if depth <= threshold:
            return FloodSeverity(label.lower()), desc
    return FloodSeverity.CRITICAL, "Impassable - risk to life, do not attempt"


def compute_risk_score(
    max_depth: float,
    avg_depth: float,
    flooded_percentage: float,
) -> float:
    """
    Compute a normalized risk score (0.0 - 1.0) for a road segment.
    
    Formula:
        risk = (depth_factor * 0.5) + (coverage_factor * 0.3) + (avg_factor * 0.2)
    
    Args:
        max_depth: Maximum flood depth in metres
        avg_depth: Average flood depth in metres
        flooded_percentage: Percentage of road that is flooded (0-100)
    
    Returns:
        Risk score between 0.0 and 1.0
    """
    # Normalize depth (cap at 2m for scoring)
    depth_factor = min(max_depth / 2.0, 1.0)

    # Normalize coverage
    coverage_factor = min(flooded_percentage / 100.0, 1.0)

    # Normalize average depth
    avg_factor = min(avg_depth / 1.5, 1.0)

    risk = (depth_factor * 0.5) + (coverage_factor * 0.3) + (avg_factor * 0.2)
    return round(min(risk, 1.0), 3)


def assess_path_risk(
    checkpoints: List[Tuple[float, float, float]],
) -> FloodRiskAssessment:
    """
    Assess overall flood risk for a series of checkpoints along a path.
    
    Args:
        checkpoints: List of (lat, lon, depth) tuples
    
    Returns:
        FloodRiskAssessment with full breakdown
    """
    total = len(checkpoints)
    if total == 0:
        return FloodRiskAssessment(
            overall_risk=FloodSeverity.NONE,
            max_depth=0.0,
            avg_depth=0.0,
            flooded_percentage=0.0,
            checkpoints_total=0,
            checkpoints_flooded=0,
            recommendation="No data available.",
            tier_breakdown={},
        )

    flooded = [(lat, lon, d) for lat, lon, d in checkpoints if d > 0]
    max_depth = max((d for _, _, d in checkpoints), default=0.0)
    avg_depth = (sum(d for _, _, d in flooded) / len(flooded)) if flooded else 0.0
    flooded_pct = (len(flooded) / total) * 100

    # Overall severity based on max depth
    severity, _ = depth_to_severity(max_depth)

    # Tier breakdown
    tier_counts = {"none": 0, "low": 0, "moderate": 0, "high": 0, "critical": 0}
    for _, _, d in checkpoints:
        tier, _ = depth_to_severity(d)
        tier_counts[tier.value] += 1

    # Recommendations
    recommendations = {
        FloodSeverity.NONE: "Corridor appears clear. Proceed normally.",
        FloodSeverity.LOW: "Minor flood exposure. Most vehicles can pass.",
        FloodSeverity.MODERATE: "Car flood tolerance exceeded. Use SUV/truck or find alternative.",
        FloodSeverity.HIGH: "Specialist vehicles only. Strongly recommended to find alternative route.",
        FloodSeverity.CRITICAL: "DO NOT ATTEMPT. Immediately find a flood-avoiding route.",
    }

    return FloodRiskAssessment(
        overall_risk=severity,
        max_depth=max_depth,
        avg_depth=round(avg_depth, 3),
        flooded_percentage=round(flooded_pct, 1),
        checkpoints_total=total,
        checkpoints_flooded=len(flooded),
        recommendation=recommendations.get(severity, ""),
        tier_breakdown=tier_counts,
    )


def is_vehicle_passable(depth: float, vehicle_max_depth: float) -> bool:
    """Check if a vehicle can pass given the flood depth."""
    return depth <= vehicle_max_depth
