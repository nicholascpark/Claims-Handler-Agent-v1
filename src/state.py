from typing import Annotated, TypedDict, Optional
import operator
from src.schema import FNOLPayload, example_json
from langchain_core.messages import HumanMessage

class ConvoState(TypedDict):
    messages: Annotated[list, operator.add]
    payload: Optional[FNOLPayload]
    is_form_complete: bool
    process_complete: bool
    api_retry_count: int
    api_call_successful: bool

def initialize_convo_state() -> ConvoState:
    return ConvoState(
        messages=[HumanMessage(content=".")],   
        payload=FNOLPayload(claim=example_json),
        is_form_complete=False,
        process_complete=False,
        api_retry_count=0,
        api_call_successful=False
    )