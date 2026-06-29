"""
Centralized logging configuration for AFDAS.
"""

import logging
import sys
from config.settings import settings


def setup_logger(name: str = "afdas") -> logging.Logger:
    """
    Create and configure a logger instance.
    
    Args:
        name: Logger name (default: 'afdas')
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    level = logging.DEBUG if settings.DEBUG else logging.INFO
    logger.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Format
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


# Module-level loggers
logger = setup_logger("afdas")
api_logger = setup_logger("afdas.api")
agent_logger = setup_logger("afdas.agent")
flood_logger = setup_logger("afdas.flood")
graph_logger = setup_logger("afdas.graph")
routing_logger = setup_logger("afdas.routing")
cache_logger = setup_logger("afdas.cache")
scheduler_logger = setup_logger("afdas.scheduler")
