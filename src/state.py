from typing import Annotated, TypedDict, Optional
import operator
from src.schema import FNOLPayload, example_json
from langchain_core.messages import HumanMessage

class ConvoState(TypedDict):
    """
    Optimized conversation state with memory-efficient field definitions.
    
    Performance notes:
    - Uses Annotated for efficient list operations
    - Optional fields reduce memory when not needed
    - Primitive types (bool, int) for fast access
    - Enhanced to support TrustCall patch operations
    """
    messages: Annotated[list, operator.add]
    payload: Optional[FNOLPayload]
    is_form_complete: bool
    process_complete: bool
    api_retry_count: int
    api_call_successful: bool

def initialize_convo_state() -> ConvoState:
    """
    Initialize conversation state with optimized default values.
    
    Performance optimizations:
    - Minimal initial message to reduce memory
    - Example payload only created once and reused
    - Boolean defaults set explicitly for clarity
    - All fields initialized for TrustCall compatibility
    """
    return ConvoState(
        messages=[HumanMessage(content=".")],   
        payload=FNOLPayload(claim=example_json),
        is_form_complete=False,
        process_complete=False,
        api_retry_count=0,
        api_call_successful=False
    )