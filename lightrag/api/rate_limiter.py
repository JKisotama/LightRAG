"""
Redis-based Rate Limiter for LightRAG API

This module provides rate limiting functionality using Redis to prevent
abuse and ensure fair usage across multiple users.
"""

import os
import asyncio
from typing import Optional
from functools import wraps

from fastapi import HTTPException, Request
from lightrag.utils import logger

# Redis client (lazy loaded)
_redis_client = None


async def get_redis_client():
    """Get or create Redis client for rate limiting"""
    global _redis_client
    
    if _redis_client is not None:
        return _redis_client
    
    try:
        import redis.asyncio as redis
        
        redis_uri = os.getenv("REDIS_URI", "redis://localhost:6379")
        socket_timeout = int(os.getenv("REDIS_SOCKET_TIMEOUT", "30"))
        connect_timeout = int(os.getenv("REDIS_CONNECT_TIMEOUT", "10"))
        
        _redis_client = redis.from_url(
            redis_uri,
            socket_timeout=socket_timeout,
            socket_connect_timeout=connect_timeout,
            decode_responses=True,
        )
        
        # Test connection
        await _redis_client.ping()
        logger.info("Rate limiter connected to Redis")
        return _redis_client
        
    except ImportError:
        logger.warning("redis package not installed, rate limiting disabled")
        return None
    except Exception as e:
        logger.warning(f"Failed to connect to Redis for rate limiting: {e}")
        return None


async def check_rate_limit(
    username: str,
    action: str,
    limit: int,
    window_seconds: int = 60,
) -> tuple[bool, int, int]:
    """
    Check if user is within rate limit for given action.
    
    Args:
        username: User identifier
        action: Action type (e.g., 'upload', 'query')
        limit: Maximum requests allowed in window
        window_seconds: Time window in seconds
        
    Returns:
        Tuple of (is_allowed, remaining_requests, retry_after_seconds)
    """
    redis_client = await get_redis_client()
    
    if redis_client is None:
        # Rate limiting disabled, allow all
        return True, limit, 0
    
    try:
        key = f"ratelimit:{action}:{username}"
        
        # Use Redis MULTI/EXEC for atomic operation
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        results = await pipe.execute()
        
        current_count = results[0]
        ttl = results[1]
        
        # Set expiry on first request in window
        if ttl == -1:  # Key exists but has no expiry
            await redis_client.expire(key, window_seconds)
            ttl = window_seconds
        elif ttl == -2:  # Key doesn't exist (shouldn't happen after INCR)
            await redis_client.expire(key, window_seconds)
            ttl = window_seconds
            
        remaining = max(0, limit - current_count)
        
        if current_count > limit:
            return False, 0, ttl
            
        return True, remaining, 0
        
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        # On error, allow the request (fail open)
        return True, limit, 0


def get_rate_limit_config():
    """Get rate limit configuration from environment"""
    return {
        "upload": {
            "limit": int(os.getenv("RATE_LIMIT_UPLOADS_PER_MINUTE", "10")),
            "window": 60,
        },
        "query": {
            "limit": int(os.getenv("RATE_LIMIT_QUERIES_PER_MINUTE", "30")),
            "window": 60,
        },
        "scan": {
            "limit": int(os.getenv("RATE_LIMIT_SCANS_PER_MINUTE", "5")),
            "window": 60,
        },
    }


async def rate_limit_check(request: Request, action: str) -> None:
    """
    FastAPI dependency for rate limiting.
    Raises HTTPException if rate limit exceeded.
    
    Args:
        request: FastAPI request object
        action: Action type to rate limit
    """
    # Check if rate limiting is enabled
    if os.getenv("ENABLE_RATE_LIMITING", "false").lower() != "true":
        return
    
    # Get username from request state (set by auth middleware)
    username = "anonymous"
    if hasattr(request.state, "user") and request.state.user:
        username = request.state.user.get("username", "anonymous")
    
    config = get_rate_limit_config()
    action_config = config.get(action, {"limit": 30, "window": 60})
    
    is_allowed, remaining, retry_after = await check_rate_limit(
        username=username,
        action=action,
        limit=action_config["limit"],
        window_seconds=action_config["window"],
    )
    
    if not is_allowed:
        logger.warning(f"Rate limit exceeded for user {username} on action {action}")
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "action": action,
                "retry_after_seconds": retry_after,
                "message": f"Too many {action} requests. Please try again in {retry_after} seconds.",
            },
            headers={"Retry-After": str(retry_after)},
        )
    
    # Log for monitoring
    if remaining <= 3:
        logger.info(f"User {username} has {remaining} {action} requests remaining")


# Convenience functions for common actions
async def rate_limit_upload(request: Request) -> None:
    """Rate limit for document uploads"""
    await rate_limit_check(request, "upload")


async def rate_limit_query(request: Request) -> None:
    """Rate limit for queries"""
    await rate_limit_check(request, "query")


async def rate_limit_scan(request: Request) -> None:
    """Rate limit for document scans"""
    await rate_limit_check(request, "scan")
