"""
OpenRouter API Key Validation Service

Tests API keys by making minimal, cost-free test requests to OpenRouter.
Distinguishes between different failure modes:
- Invalid/revoked API key
- No internet connection
- Provider unavailable (temporary outage)
- Insufficient credits
- Other errors
"""

import httpx
import asyncio
import json
from datetime import datetime


class APIKeyTestResult:
    """Result of an API key test."""
    
    def __init__(self, valid: bool, status: str, message: str, details: dict = None):
        """
        Args:
            valid: Whether the key is valid and usable
            status: Status code (e.g., "valid", "invalid_key", "no_internet", etc.)
            message: User-friendly message to display
            details: Additional error details
        """
        self.valid = valid
        self.status = status
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()


async def test_api_key_async(
    api_key: str,
    model: str = "z-ai/glm-5.2:free",
    timeout: int = 10
) -> APIKeyTestResult:
    """
    Test an OpenRouter API key asynchronously.
    
    Makes a minimal test request that doesn't consume allocated credits
    (or uses minimal credits for free tier).
    
    Args:
        api_key: The OpenRouter API key to test
        model: Model to use for testing (free tier by default)
        timeout: Request timeout in seconds
        
    Returns:
        APIKeyTestResult with detailed status
    """
    
    # Minimal test request - just get token count, doesn't actually run inference
    test_payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "[SETUP TEST]"
            }
        ],
        "max_tokens": 1,  # Minimal tokens for free tier
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "KanoonVault/1.0.0"
    }
    
    try:
        from config import OPENROUTER_URL
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_URL,
                json=test_payload,
                headers=headers
            )
        
        # Check response status
        if response.status_code == 200:
            # Successful response
            return APIKeyTestResult(
                valid=True,
                status="valid",
                message="✅ Connection successful\nYour AI provider is connected and ready."
            )
        
        elif response.status_code == 401:
            # Unauthorized - invalid API key
            return APIKeyTestResult(
                valid=False,
                status="invalid_key",
                message="❌ API key was rejected\n\nThe key doesn't match OpenRouter records.\n"
                       "Please check that you copied the key correctly.",
                details={
                    "status_code": 401,
                    "error": "Unauthorized - invalid API key"
                }
            )
        
        elif response.status_code == 429:
            # Rate limited — but this proves the key IS valid (authenticated successfully)
            # Free-tier models hit rate limits easily; the key itself works fine
            return APIKeyTestResult(
                valid=True,
                status="valid_rate_limited",
                message="✅ Connection successful\nYour API key is valid. Free-tier models may have brief rate limits — this is normal.",
                details={
                    "status_code": 429,
                    "note": "Key authenticated successfully, rate limit is temporary"
                }
            )
        
        elif response.status_code == 402:
            # Payment required - insufficient credits
            return APIKeyTestResult(
                valid=False,
                status="insufficient_credits",
                message="💳 Account is out of credits\n\nYour OpenRouter account doesn't have\n"
                       "available credits. Please add payment method.",
                details={
                    "status_code": 402,
                    "error": "Payment required - insufficient credits"
                }
            )
        
        elif response.status_code >= 500:
            # Provider error
            return APIKeyTestResult(
                valid=False,
                status="provider_unavailable",
                message="⚠️ AI provider temporarily unavailable\n\n"
                       "OpenRouter is experiencing issues.\n"
                       "Please try again in a few moments.",
                details={
                    "status_code": response.status_code,
                    "error": f"Provider error: {response.status_code}"
                }
            )
        
        else:
            # Other HTTP errors
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", str(response.status_code))
            except:
                error_msg = f"HTTP {response.status_code}"
            
            return APIKeyTestResult(
                valid=False,
                status="api_error",
                message=f"❌ Error from API provider\n\n{error_msg}",
                details={
                    "status_code": response.status_code,
                    "response": str(response.text)[:200]
                }
            )
    
    except httpx.ConnectError as e:
        # Network connection error
        return APIKeyTestResult(
            valid=False,
            status="no_internet",
            message="🌐 No internet connection\n\n"
                   "Check your network connection and try again.",
            details={
                "error": "Connection failed",
                "reason": str(e)
            }
        )
    
    except httpx.TimeoutException:
        # Request timeout - could be network or provider issue
        return APIKeyTestResult(
            valid=False,
            status="timeout",
            message="⏱️ Request timeout\n\n"
                   "The API provider isn't responding quickly.\n"
                   "Check your connection or try again later.",
            details={
                "error": "Request timeout"
            }
        )
    
    except Exception as e:
        # Unexpected error
        return APIKeyTestResult(
            valid=False,
            status="unknown_error",
            message=f"❌ Unexpected error\n\n{type(e).__name__}: {str(e)[:100]}",
            details={
                "error": type(e).__name__,
                "details": str(e)
            }
        )


def test_api_key(
    api_key: str,
    model: str = "z-ai/glm-5.2:free",
    timeout: int = 10
) -> APIKeyTestResult:
    """
    Synchronous wrapper for test_api_key_async.
    
    Args:
        api_key: The OpenRouter API key to test
        model: Model to use for testing
        timeout: Request timeout in seconds
        
    Returns:
        APIKeyTestResult with detailed status
    """
    try:
        return asyncio.run(test_api_key_async(api_key, model, timeout))
    except RuntimeError as e:
        # Event loop issues in some contexts
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(test_api_key_async(api_key, model, timeout))
        finally:
            loop.close()


if __name__ == "__main__":
    # Test the function
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_api_key.py <api_key>")
        sys.exit(1)
    
    api_key = sys.argv[1]
    print(f"\nTesting API key: {api_key[:20]}...")
    print()
    
    result = test_api_key(api_key)
    
    print(f"Status: {result.status}")
    print(f"Valid: {result.valid}")
    print(f"Message:\n{result.message}")
    
    if result.details:
        print(f"\nDetails: {json.dumps(result.details, indent=2)}")
