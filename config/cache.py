"""
Redis cache configuration.
"""

from config.settings import settings


REDIS_CONFIG = {
    "host": settings.REDIS_HOST,
    "port": settings.REDIS_PORT,
    "password": settings.REDIS_PASSWORD,
    "db": settings.REDIS_DB,
    "decode_responses": False,  # We store binary (pickle) for graphs
}

# TTL values for different cache types
GRAPH_TTL = settings.REDIS_GRAPH_TTL
WEIGHT_TTL = settings.REDIS_WEIGHT_TTL
ROUTE_TTL = settings.REDIS_ROUTE_TTL
