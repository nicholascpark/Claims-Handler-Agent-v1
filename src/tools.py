import pytz
from datetime import datetime
from langchain_core.tools import tool
from src.state import ConvoState
import requests
from src.schema import FNOLPayload

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
def get_preliminary_estimate(payload: FNOLPayload) -> str:
    """Once the form is complete, this makes a POST request to the API to get a preliminary estimate for the claim."""

    if hasattr(payload, 'model_dump'):
        request_body = payload.model_dump()
    else:
        request_body = payload
    
    # make the POST request to the API with try except
    try:
        response = requests.post(
            "http://localhost:8000/submit-loss-notice",
            json=request_body
        )
        return response.json()
    except Exception as e:
        return f"Error: {e}"

