# Messages State Refactor Summary

## Overview

Refactored the voice agent to use LangGraph's native `messages` state aggregator pattern with `add_messages` reducer. This eliminates custom message tracking and response formatting in favor of the standard LangGraph approach.

## Key Changes

### 1. State Schema (`voice_langgraph/state.py`)

**Before:**
```python
class VoiceAgentState(TypedDict, total=False):
    conversation_history: List[ConversationMessage]
    current_user_message: str
    last_assistant_message: str
    session_id: str
    # ... other fields
```

**After:**
```python
class VoiceAgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    claim_data: Dict[str, Any]
    next_action: str
    is_claim_complete: bool
    submission_result: Optional[Dict[str, Any]]
    timestamp: str
    current_timezone: str
    error: Optional[str]
    retry_count: int
```

**Rationale:**
- `messages` with `add_messages` reducer automatically handles message history aggregation
- No need for separate `conversation_history`, `current_user_message`, or `last_assistant_message`
- Removed `session_id` - use LangGraph's native thread management via `thread_id` in config

### 2. Node Updates (`voice_langgraph/nodes.py`)

#### Voice Input Node
- Reads latest `HumanMessage` from `messages` list
- Always routes to extraction (simplified from keyword-based routing)

#### Extraction Worker Node
- Uses trustcall invoke pattern: `{"messages": [("user", prompt)], "existing": {"PropertyClaim": data}}`
- Builds context from last 5 messages in `messages` list
- Patches `claim_data` using trustcall's JSON patch approach

#### Supervisor Node
- Computes next missing field from `PropertyClaim.get_missing_fields()`
- Emits response via `state["messages"] = [AIMessage(content=...)]`
- Routes based on `next_action` (submit/escalate/respond)

#### All Response Nodes
- Emit messages via `state["messages"] = [AIMessage(content=...)]` instead of `last_assistant_message`

### 3. Edges Simplification (`voice_langgraph/edges.py`)

**Removed:**
- `format_state_for_response()` - no longer needed
- `route_after_response()` - human contact node removed
- References to `last_assistant_message` and `invoke_human_tool`

**Simplified:**
- `route_after_supervisor()` now only routes to `submission` or `end`
- Messages are automatically tracked by LangGraph's `add_messages` reducer

### 4. Graph Builder (`voice_langgraph/graph_builder.py`)

**Removed:**
- `get_human_representative` node
- Associated routing logic

**Simplified routing:**
```python
supervisor -> {submission, end, error_handler}
```

### 5. Voice Agent (`voice_langgraph/voice_agent.py`)

**State Construction:**
```python
state: VoiceAgentState = {
    "messages": [HumanMessage(content=user_message)],
    "claim_data": self.current_claim_data,
    "timestamp": datetime.now().isoformat(),
    "current_timezone": self.current_timezone,
}
```

**Response Extraction:**
```python
# Find last AIMessage in result["messages"]
for m in reversed(result.get("messages", [])):
    if isinstance(m, AIMessage):
        response_message = m.content
        break
```

### 6. Supervisor Prompt (`voice_langgraph/prompts.py`)

**Enhanced with:**
- "Begin each response with a brief, empathetic acknowledgement"
- "Ask only for the single next missing field"
- "Never claim we have information unless it is present in the provided claim JSON"

## Benefits

1. **Standard LangGraph Pattern**: Uses `add_messages` reducer as documented in [LangGraph concepts](https://langchain-ai.github.io/langgraph/concepts/low_level/#serialization)
2. **Automatic Message Tracking**: No manual message list management
3. **Simpler Code**: Removed ~50 lines of custom formatting/tracking logic
4. **Better Trustcall Integration**: Proper invoke pattern with `existing` parameter
5. **Empathetic Flow**: Supervisor now asks one question at a time with warm acknowledgements
6. **Thread Management**: Uses LangGraph's native thread_id for conversation continuity

## Migration Notes

- Old checkpointed conversations will need new sessions (state schema changed)
- `session_id` replaced with `thread_id` in graph config
- All message emissions now use `AIMessage` objects in `messages` list
- Response extraction reads from `messages` instead of dedicated field

## Testing

All modified files pass linter checks. The graph now:
1. Accepts user input as `HumanMessage`
2. Always runs trustcall extraction with proper invoke pattern
3. Supervisor validates completeness and asks for next field
4. Emits response as `AIMessage` via `add_messages`
5. Graph ends turn, checkpointer saves state
6. Next user input starts new graph execution with accumulated messages

