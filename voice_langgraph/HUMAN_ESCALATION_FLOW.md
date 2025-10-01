# Human Escalation Flow

## Overview

Added `get_human_representative` node to handle escalations to human agents. This node calls the `get_human_contact()` tool to retrieve contact information and generates an empathetic handoff message.

## Flow Diagram

```
┌─────────────────┐
│  voice_input    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ extraction_     │
│   worker        │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   supervisor    │ ← decides next_action
└────────┬────────┘
         │
    ┌────┴─────────────┬──────────────┐
    ↓                  ↓              ↓
┌──────────┐  ┌──────────────┐  ┌─────────┐
│submission│  │get_human_    │  │  END    │
│          │  │representative│  │(respond)│
└────┬─────┘  └──────┬───────┘  └─────────┘
     │               │
     ↓               ↓
   END             END
```

## When Escalation Triggers

The supervisor sets `next_action = "escalate"` when:
1. User explicitly requests a human agent
2. Multiple errors occur (retry_count >= 3)
3. Submission fails
4. LLM determines the query is beyond scope

## Node Implementation

### `get_human_representative(state)`

**Purpose:** Gracefully hand off to human support with contact details

**Process:**
1. Calls `get_human_contact()` tool → returns fixed JSON:
   ```json
   {
     "phone_number": "877-624-7775",
     "hours": "24/7",
     "notes": "Ask for Claims Intake; provide your policy number if available."
   }
   ```

2. Generates empathetic handoff message using tool response

3. Emits `AIMessage` via `messages` aggregator:
   ```python
   state["messages"] = [AIMessage(content=(
       f"I understand you'd like to speak with a human representative. "
       f"You can reach our Claims team at {phone} ({hours}). "
       f"I'll also note your request to escalate this call."
   ))]
   ```

4. Sets `next_action = "complete"` to end workflow

## Routing Logic

### In `route_after_supervisor()`:

```python
next_action = state.get("next_action", "respond")

if next_action == "submit":
    return "submission"
elif next_action == "escalate":
    return "get_human_representative"  # ← NEW
else:
    return "end"  # normal response turn
```

## Example Scenarios

### Scenario 1: User Requests Human
```
User: "I'd like to speak with a person"
   ↓
Supervisor: sets next_action = "escalate"
   ↓
get_human_representative:
   • Calls get_human_contact() tool
   • Generates: "I understand you'd like to speak with a human representative.
                You can reach our Claims team at 877-624-7775 (24/7).
                I'll also note your request to escalate this call."
   ↓
END (workflow completes, user sees contact info)
```

### Scenario 2: System Error Escalation
```
extraction_worker: fails 3 times
   ↓
error_handling_node: sets next_action = "escalate"
   ↓
supervisor: routes to escalation
   ↓
get_human_representative: provides contact info
   ↓
END
```

### Scenario 3: Submission Failure
```
submission_node: exception during submit
   ↓
Sets next_action = "escalate"
   ↓
get_human_representative: provides contact info
   ↓
END
```

## Benefits

1. **Tool-Driven**: Uses `get_human_contact()` tool for flexible contact info management
2. **Empathetic**: Warm handoff message acknowledges user's request
3. **Consistent**: Same escalation flow for all triggers (user request, errors, failures)
4. **Clean Separation**: Escalation logic isolated in dedicated node
5. **Messages Pattern**: Uses `add_messages` aggregator like all other nodes

## Configuration

To update contact information, modify the `get_human_contact()` tool in `tools.py`:

```python
@tool
def get_human_contact() -> Dict[str, Any]:
    """Return contact info for a human claims representative."""
    return {
        "phone_number": "877-624-7775",  # Update here
        "hours": "24/7",                  # Update here
        "notes": "Ask for Claims Intake; provide your policy number if available."
    }
```

The node will automatically use the updated values.

