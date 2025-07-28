import pytz
from datetime import datetime
from langchain_core.tools import tool
from src.state import ConvoState
import aiohttp
import asyncio
import json
from typing import Union, Dict, Any

# Connection pool for reuse across requests
_http_session = None

async def get_http_session():
    """Get or create a reusable HTTP session for better performance."""
    global _http_session
    if _http_session is None or _http_session.closed:
        # Configure session with optimized settings
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(
            limit=100,  # Connection pool size
            limit_per_host=10,
            ttl_dns_cache=300,  # DNS cache for 5 minutes
            use_dns_cache=True,
        )
        _http_session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={'Content-Type': 'application/json'}
        )
    return _http_session

# @tool
# def lookup_time(tz: str) -> str:
#     """Lookup the current time in a given timezone."""
#     try:
#         # Convert the timezone string to a timezone object
#         timezone = pytz.timezone(tz)
#         # Get the current time in the given timezone
#         tm = datetime.now(timezone)
#         return f"The current time in {tz} is {tm.strftime('%H:%M:%S')}"
#     except pytz.UnknownTimeZoneError:
#         return f"Unknown timezone: {tz}"
    
@tool
async def get_preliminary_estimate(payload: Union[Dict[Any, Any], Any]) -> str:
    """
    Make an optimized POST request to get preliminary estimate for the claim.
    
    Performance optimizations:
    - Reuses HTTP session with connection pooling
    - Optimized timeout settings
    - Better error handling with specific error types
    """
    # Prepare request body
    if hasattr(payload, 'model_dump'):
        request_body = payload.model_dump()
    elif isinstance(payload, dict):
        request_body = payload
    else:
        return "Error: Invalid payload format"
    
    # Validate essential fields before making API call
    if not request_body:
        return "Error: Empty payload provided"
    
    try:
        session = await get_http_session()
        async with session.post(
            "http://localhost:8000/submit-loss-notice",
            json=request_body,
            timeout=aiohttp.ClientTimeout(total=20)  # Override default for this call
        ) as response:
            if response.status == 200:
                result = await response.json()
                return json.dumps(result, indent=2)
            else:
                error_text = await response.text()
                return f"API Error {response.status}: {error_text}"
                
    except aiohttp.ClientTimeout:
        return "Error: Request timeout - API took too long to respond"
    except aiohttp.ClientError as e:
        return f"Error: Network error - {str(e)}"
    except json.JSONDecodeError:
        return "Error: Invalid JSON response from API"
    except Exception as e:
        return f"Error: Unexpected error - {str(e)}"

async def cleanup_http_session():
    """Clean up HTTP session when application shuts down."""
    global _http_session
    if _http_session and not _http_session.closed:
        await _http_session.close()

