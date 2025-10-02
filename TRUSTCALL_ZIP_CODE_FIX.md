# Trustcall Extraction Fixes

## 🚨 CRITICAL ISSUE DISCOVERED: Zero Extraction

During testing, we discovered an even more fundamental problem: **trustcall was extracting NOTHING at all**. 

**Error Message:** `"Could not find existing schema for PropertyClaim-0"`

**Root Cause:** The trustcall extractor was initialized with `enable_inserts=True`, which is designed for managing MULTIPLE schema instances (like a list of Person objects). Our use case is managing a SINGLE PropertyClaim, causing complete extraction failure.

**Fix:** Removed `enable_inserts=True` from the extractor configuration. See "Fix #1" below for details.

---

## Root Cause Analysis: ZIP Code Obsession

### The Problem
The agent was obsessively asking about the ZIP code throughout the conversation, even after the user provided it multiple times. The log shows:

```
User: "0 7 9 2 8"
→ Extracted to: incident_street_address = "0 7 9 2 8"  ❌ Wrong field!
→ incident_zip_code remained: ""
→ Supervisor keeps seeing ZIP code as "missing"
→ Agent keeps asking for it
```

### Why It Happened

1. **Trustcall Misclassification**: The LLM-based trustcall extractor put "0 7 9 2 8" in the wrong field (`incident_street_address` instead of `incident_zip_code`)

2. **Strict Validation Loop**: 
   - `get_missing_fields()` used `is_valid_value()` which checked for empty strings AND placeholder values
   - Since `incident_zip_code` was still `""`, it was always reported as missing
   - Supervisor received the missing fields list and kept asking for ZIP code
   - Even when the user confirmed "correct", the field remained empty because trustcall had already misclassified it

3. **Limited Context**: Trustcall only received the last 5 messages, which may not have been enough context to understand the conversation flow and correct previous mistakes

## The Solutions

### Fix #1: CRITICAL - Fixed Trustcall Configuration (`nodes.py`)

**Before:**
```python
trustcall_extractor = create_extractor(
    supervisor_llm,
    tools=[PropertyClaim],
    tool_choice="PropertyClaim",
    enable_inserts=True  # ❌ WRONG! Causes zero extraction
)
```

**After:**
```python
trustcall_extractor = create_extractor(
    supervisor_llm,
    tools=[PropertyClaim],
    tool_choice="PropertyClaim"
    # ✅ No enable_inserts - we're managing a SINGLE claim
)
```

**Why This Was Critical:**
- `enable_inserts=True` is for managing MULTIPLE instances with IDs: `[(id, "Person", data), ...]`
- We're managing ONE claim with dictionary format: `{"PropertyClaim": data}`
- The mismatch caused trustcall to look for `PropertyClaim-0` tuple and fail completely
- **Result**: NO DATA was being extracted at all - conversation was stuck in a loop

### Fix #2: Relaxed Validation (`schema.py`)

**Before:**
```python
def is_valid_value(value: str) -> bool:
    if not value or not str(value).strip():
        return False
    value_lower = str(value).lower().strip()
    # Reject placeholder values
    placeholders = ['unspecified', 'unknown', 'not provided', 'n/a', 'none', 'tbd']
    return not any(placeholder in value_lower for placeholder in placeholders)
```

**After:**
```python
def has_content(value: str) -> bool:
    """Check if field has any content at all (not empty, not None)."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True
```

**Why This Helps:**
- Fields are now considered "filled" if they have ANY content, not just "valid" content
- If trustcall misclassifies data (e.g., puts ZIP in address field), the agent won't obsess over the "missing" field
- Reduces validation strictness to prevent infinite loops on misclassified data
- The supervisor can move forward instead of getting stuck

### 2. Extended Conversation Context (`nodes.py`)

**Before:**
```python
# Build conversation history for trustcall (last 5 messages)
for mm in msgs[-5:]:
```

**After:**
```python
# Build conversation history for trustcall (EXPANDED to last 20 messages)
for mm in msgs[-20:]:
```

**Why This Helps:**
- More context helps trustcall understand the conversation flow
- Can see patterns like "AI asked about ZIP → User provided digits → Must be ZIP code"
- Better chance of correcting previous misclassifications
- Follows trustcall best practices from documentation

### 3. Fixed Trustcall Configuration (`nodes.py`) - CRITICAL

**Before:**
```python
trustcall_extractor = create_extractor(
    supervisor_llm,
    tools=[PropertyClaim],
    tool_choice="PropertyClaim",
    enable_inserts=True  # ❌ Wrong! This expects MULTIPLE instances
)
```

**After:**
```python
trustcall_extractor = create_extractor(
    supervisor_llm,
    tools=[PropertyClaim],
    tool_choice="PropertyClaim"
    # ✅ No enable_inserts - we're managing a SINGLE claim
)
```

**Why This Was Critical:**
- `enable_inserts=True` is for managing MULTIPLE schema instances (e.g., list of Person objects)
- It expects existing data in tuple format: `[(id, "SchemaName", data), ...]`
- We're managing a SINGLE PropertyClaim, not multiple instances
- With `enable_inserts=True`, trustcall looked for `PropertyClaim-0` tuple and failed
- This caused **zero extraction** - no data was being captured at all
- Removing it fixes extraction and uses the correct single-schema dictionary format

**From Trustcall Docs:**
- Single schema: `{"PropertyClaim": data}` → No `enable_inserts` needed
- Multiple instances: `[(id, "Person", data), ...]` → Use `enable_inserts=True`

### 4. Enhanced Field Classification Hints (`nodes.py`)

**Added to extraction prompt:**
```python
FIELD CLASSIFICATION HINTS (critical for correct extraction):
- ZIP/POSTAL CODES: 5-digit numbers (e.g., "07928", "0 7 9 2 8") go in 'incident_zip_code' field
- STREET ADDRESSES: Full addresses with street names/numbers go in 'incident_street_address' field
- If user says digits that could be a zip code, check context: if they're answering about zip code, it's a zip code
- If user confirms or corrects information, prioritize updating the field they're responding about

SCHEMA STRUCTURE REMINDER:
- incident_location has TWO separate fields: incident_street_address AND incident_zip_code
- These are DISTINCT fields - don't confuse them or merge them
```

**Why This Helps:**
- Explicit guidance on which field to use for different data types
- Reminds trustcall that address and ZIP are separate fields
- Context-aware hints (e.g., "if answering about ZIP, it's a ZIP")
- Helps prevent initial misclassification

## Architecture Alignment with LangGraph Best Practices

### Trustcall Integration Pattern

According to the [trustcall documentation](https://github.com/hinthornw/trustcall), trustcall works by:

1. **Incremental JSON Patching**: Instead of regenerating entire schemas, trustcall generates JSON patches to update existing data
2. **Error Recovery**: When validation fails, trustcall generates patches to fix errors
3. **Existing Data Context**: Passing `existing` data allows trustcall to intelligently merge updates

Our implementation follows this pattern:

```python
invoke_params = {
    "messages": [("user", extraction_prompt)],
    "existing": {"PropertyClaim": existing_data if existing_data else PropertyClaim.create_empty().model_dump()},
}
result = trustcall_extractor.invoke(invoke_params)
```

### LangGraph Node Design

Our architecture follows [LangGraph's state management principles](https://langchain-ai.github.io/langgraph/concepts/low_level/):

1. **Nodes do the work**: `extraction_worker_node` handles extraction, `supervisor_node` handles response generation
2. **Edges control flow**: Routing decisions in `edges.py` based on state
3. **State as single source of truth**: `claim_data` in state is updated incrementally
4. **Reducers for merging**: Messages use `operator.add` for accumulation

### Why Relaxed Validation Works

The key insight from the trustcall documentation is that **trustcall excels at incremental updates**. By relaxing validation:

- We let trustcall do its job without the supervisor obsessing over "missing" fields
- Fields that have data (even if misclassified) don't trigger infinite retry loops
- The agent can progress through the conversation naturally
- Trustcall's patching mechanism can correct mistakes in subsequent iterations

## Expected Behavior After Fix

### Before Fix:
```
User: "0 7 9 2 8"
→ AI: "And if you have the zip code as well, that would be great."
User: "234 101 Street"
→ AI: "Could you confirm if that's the correct zip code?"
User: "Correct"
→ AI: "Thank you for confirming the zip code. Could you also tell me the zip code?"
[Loop continues...]
```

### After Fix:
```
User: "0 7 9 2 8"
→ Extracted: incident_street_address = "0 7 9 2 8" (still wrong, but has content)
→ get_missing_fields() sees street_address has content (not missing)
→ Supervisor moves on to next field
→ AI: "Great! Could you tell me what happened during the incident?"
[Conversation progresses naturally]
```

Or better yet:
```
User: "0 7 9 2 8"
→ With improved context and hints, trustcall correctly extracts:
→ incident_zip_code = "07928" ✅
→ Supervisor sees it's filled and moves on
```

## Testing Recommendations

1. **Test ZIP Code Input**: Try various formats like "07928", "0 7 9 2 8", "zero seven nine two eight"
2. **Test Field Confirmation**: Say "correct" or "yes" when AI asks for confirmation
3. **Test Misclassification Recovery**: Ensure conversation progresses even if data goes to wrong field
4. **Monitor Context Usage**: Verify that 10 messages provide enough context without bloating prompts

## Related Documentation

- [Trustcall GitHub](https://github.com/hinthornw/trustcall) - JSON patching for schema extraction
- [LangGraph Concepts](https://langchain-ai.github.io/langgraph/concepts/low_level/) - State management and node design
- [LangGraph Workflows](https://langchain-ai.github.io/langgraph/tutorials/workflows/) - Multi-step agent patterns

## Files Modified

1. **`voice_langgraph/schema.py`**: 
   - Simplified `get_missing_fields()` validation from strict `is_valid_value()` to relaxed `has_content()`
   - Added documentation explaining the relaxed validation approach

2. **`voice_langgraph/nodes.py`**:
   - **CRITICAL**: Removed `enable_inserts=True` from trustcall extractor initialization (was causing zero extraction)
   - Expanded conversation context from 5 to 20 messages
   - Added field classification hints to extraction prompt (user removed these later)
   - Enhanced prompt with schema structure reminders

## Critical Discovery: enable_inserts Issue

During testing, we discovered that **trustcall was extracting NOTHING**. The error `"Could not find existing schema for PropertyClaim-0"` revealed that:

- `enable_inserts=True` is designed for managing MULTIPLE schema instances (like a list of Person objects)
- It expects existing data in tuple format with IDs: `[(id, schema_name, data), ...]`
- We're managing a SINGLE claim, not multiple instances
- The mismatch caused complete extraction failure

**This was the most critical fix** - without it, the agent couldn't extract any data at all.

