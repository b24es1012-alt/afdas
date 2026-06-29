"""
Environment-specific configuration overrides.
"""

import os
from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


def get_environment() -> Environment:
    """Determine current environment from ENV variable."""
    env = os.getenv("AFDAS_ENV", "development").lower()
    try:
        return Environment(env)
    except ValueError:
        return Environment.DEVELOPMENT


def is_production() -> bool:
    return get_environment() == Environment.PRODUCTION


def is_development() -> bool:
    return get_environment() == Environment.DEVELOPMENT


def is_testing() -> bool:
    return get_environment() == Environment.TESTING


# CORS origins per environment
CORS_ORIGINS = {
    Environment.DEVELOPMENT: ["http://localhost:3000", "http://localhost:5173"],
    Environment.STAGING: ["https://staging.afdas.app"],
    Environment.PRODUCTION: ["https://afdas.app"],
    Environment.TESTING: ["http://localhost:3000"],
}


def get_cors_origins() -> list:
    env = get_environment()
    return CORS_ORIGINS.get(env, CORS_ORIGINS[Environment.DEVELOPMENT])
