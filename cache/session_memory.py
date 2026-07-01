"""
Redis-based session memory for AI chatbot conversations.

Stores conversation history per session in Redis with TTL expiration.
This gives the AI agent context from previous messages within the same session,
enabling multi-turn conversations (e.g. "now route me there" after a flood check).
"""

import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from cache.manager import CacheManager
from config.settings import settings
from utils.logger import cache_logger as logger


# TTL for session memory (default 1 hour — configurable via settings)
SESSION_TTL = getattr(settings, "REDIS_SESSION_TTL", 3600)
MAX_MESSAGES_PER_SESSION = 50  # Keep last N messages to avoid memory bloat


class ChatMessage:
    """Represents a single chat message in the session."""

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.role = role  # "user" or "assistant"
        self.content = content
        self.timestamp = timestamp or time.time()
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChatMessage":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


class SessionMemory:
    """
    Redis-backed session memory for AI chat conversations.

    Each session is identified by a session_id (e.g. UUID from frontend).
    Stores the last N messages with automatic TTL expiration.

    Key format: "afdas:session:{session_id}"
    
    Usage:
        memory = SessionMemory()
        await memory.add_message(session_id, "user", "Is Delhi flooded?")
        await memory.add_message(session_id, "assistant", "Yes, several areas...")
        history = await memory.get_history(session_id)
    """

    PREFIX = "afdas:session:"

    def __init__(self, ttl: int = SESSION_TTL, max_messages: int = MAX_MESSAGES_PER_SESSION):
        self.ttl = ttl
        self.max_messages = max_messages

    def _key(self, session_id: str) -> str:
        return f"{self.PREFIX}{session_id}"

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a message to the session's conversation history.

        Args:
            session_id: Unique session identifier
            role: "user" or "assistant"
            content: Message content
            metadata: Optional metadata (category, vehicle_type, routes_found, etc.)
        """
        try:
            client = CacheManager.get_client()
            key = self._key(session_id)

            message = ChatMessage(role=role, content=content, metadata=metadata)
            message_json = json.dumps(message.to_dict())

            # Push to list (right = newest)
            await client.rpush(key, message_json.encode("utf-8"))

            # Trim to max messages (keep the most recent)
            await client.ltrim(key, -self.max_messages, -1)

            # Refresh TTL on every message (session stays alive while active)
            await client.expire(key, self.ttl)

            logger.debug(f"Session {session_id}: added {role} message ({len(content)} chars)")

        except Exception as e:
            logger.warning(f"Failed to store session message: {e}")

    async def get_history(
        self,
        session_id: str,
        last_n: Optional[int] = None,
    ) -> List[ChatMessage]:
        """
        Retrieve conversation history for a session.

        Args:
            session_id: Unique session identifier
            last_n: Only return last N messages (default: all stored)

        Returns:
            List of ChatMessage objects, oldest first
        """
        try:
            client = CacheManager.get_client()
            key = self._key(session_id)

            if last_n:
                raw_messages = await client.lrange(key, -last_n, -1)
            else:
                raw_messages = await client.lrange(key, 0, -1)

            messages = []
            for raw in raw_messages:
                try:
                    data = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
                    messages.append(ChatMessage.from_dict(data))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

            return messages

        except Exception as e:
            logger.warning(f"Failed to retrieve session history: {e}")
            return []

    async def get_context_string(
        self,
        session_id: str,
        last_n: int = 10,
        max_chars: int = 3000,
    ) -> str:
        """
        Get conversation history formatted as a context string for the AI agent.
        This is injected into the agent's query to give it conversation context.

        Args:
            session_id: Unique session identifier
            last_n: Number of recent messages to include
            max_chars: Max total characters in context

        Returns:
            Formatted conversation history string
        """
        messages = await self.get_history(session_id, last_n=last_n)

        if not messages:
            return ""

        lines = ["[Previous conversation in this session:]"]
        total_chars = 0

        for msg in messages:
            prefix = "User" if msg.role == "user" else "Assistant"
            # Truncate individual messages if too long
            content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
            line = f"  {prefix}: {content}"

            if total_chars + len(line) > max_chars:
                lines.append("  ... (earlier messages truncated)")
                break

            lines.append(line)
            total_chars += len(line)

        return "\n".join(lines)

    async def clear_session(self, session_id: str) -> None:
        """Clear all messages for a session."""
        try:
            client = CacheManager.get_client()
            await client.delete(self._key(session_id))
            logger.info(f"Session {session_id}: cleared")
        except Exception as e:
            logger.warning(f"Failed to clear session: {e}")

    async def session_exists(self, session_id: str) -> bool:
        """Check if a session has any stored messages."""
        try:
            client = CacheManager.get_client()
            return await client.exists(self._key(session_id)) > 0
        except Exception:
            return False

    async def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get metadata about a session (message count, age, TTL remaining)."""
        try:
            client = CacheManager.get_client()
            key = self._key(session_id)

            exists = await client.exists(key)
            if not exists:
                return {"exists": False}

            length = await client.llen(key)
            ttl = await client.ttl(key)

            # Get first message timestamp
            first_raw = await client.lindex(key, 0)
            first_ts = None
            if first_raw:
                try:
                    data = json.loads(first_raw.decode("utf-8") if isinstance(first_raw, bytes) else first_raw)
                    first_ts = data.get("timestamp")
                except Exception:
                    pass

            return {
                "exists": True,
                "message_count": length,
                "ttl_remaining": ttl,
                "session_started": datetime.fromtimestamp(first_ts).isoformat() if first_ts else None,
            }

        except Exception as e:
            return {"exists": False, "error": str(e)}

    async def extend_session(self, session_id: str, extra_seconds: int = 3600) -> None:
        """Extend session TTL (e.g. when user is still actively chatting)."""
        try:
            client = CacheManager.get_client()
            key = self._key(session_id)
            current_ttl = await client.ttl(key)
            if current_ttl > 0:
                await client.expire(key, current_ttl + extra_seconds)
        except Exception as e:
            logger.warning(f"Failed to extend session TTL: {e}")
