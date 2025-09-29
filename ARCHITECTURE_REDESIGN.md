# Claims Handler Agent v1 - Architecture Redesign

## Overview

This document summarizes the complete architectural redesign of the Claims Handler Agent to closely follow the OpenAI Realtime Agents supervisor pattern.

## Design Pattern Implementation

### 1. Junior/Supervisor Architecture

**Before**: Independent agents with separate conversation handling
**After**: Strict junior/supervisor delegation pattern

- **Junior Agent** (`src/agents/realtime_agent.py`): 
  - Minimal capabilities - only basic greetings and chitchat
  - Must use `getNextResponseFromSupervisor` for all complex decisions
  - Uses filler phrases before calling supervisor
  - Cannot make decisions or call tools directly

- **Supervisor Agent** (`src/agents/supervisor_agent.py`):
  - Receives full conversation history and context
  - Has access to all tools (policy lookup, claim validation, location services)
  - Returns formatted messages that junior agent reads verbatim
  - Handles iterative tool calling internally

### 2. Tool Architecture

**Before**: Direct tool access from multiple agents
**After**: Single supervisor tool pattern

- **Single Tool**: `getNextResponseFromSupervisor` is the only tool the junior agent can call
- **Tool Handler** (`src/tools/supervisor_tool.py`): Bridges realtime API with supervisor
- **Supervisor Tools**: All business logic tools are internal to supervisor only

### 3. API Structure

**Before**: Custom response handling with mixed patterns  
**After**: Exact replication of OpenAI `/api/responses` pattern

- **Responses API** (`src/api/responses_api.py`): 
  - Mirrors the TypeScript `fetchResponsesMessage` function
  - Handles iterative tool calling exactly like OpenAI implementation
  - Returns structured responses for realtime API consumption

### 4. Voice Interface

**Before**: Direct realtime API connection with custom event handling
**After**: Supervisor pattern integrated voice agent

- **Voice Agent** (`src/voice_agent.py`):
  - Uses junior agent configuration for realtime API
  - Automatically handles `getNextResponseFromSupervisor` tool calls
  - Tracks supervisor usage in performance metrics
  - Maintains exact OpenAI event handling patterns

## Files Changed/Removed

### New Files Created:
- `src/agents/realtime_agent.py` - Junior realtime agent (OpenAI pattern)
- `src/agents/supervisor_agent.py` - Supervisor with tool access
- `src/api/responses_api.py` - OpenAI-compatible responses API
- `src/voice_agent.py` - Voice interface with supervisor pattern
- `src/tools/supervisor_tool.py` - Tool handler for realtime API
- `src/agent_config.py` - Agent configuration (matches OpenAI agentConfigs)
- `run_voice_agent.py` - Main entry point

### Files Removed:
- `src/agents/junior_claims_agent.py` - Replaced with realtime_agent.py
- `src/agents/claims_supervisor.py` - Replaced with supervisor_agent.py  
- `src/api/responses_proxy.py` - Replaced with responses_api.py
- `src/test_voice.py` - Replaced with voice_agent.py
- `src/test_conversation.py` - No longer needed

### Files Preserved:
- `src/agents/payload_processor.py` - Unchanged (separate concern)
- `src/tools/claim_validation.py` - Unchanged (used by supervisor)
- `src/tools/policy_lookup.py` - Unchanged (used by supervisor)
- `src/tools/location_services.py` - Unchanged (used by supervisor)
- `src/schema/simplified_payload.py` - Unchanged
- `src/config/settings.py` - Unchanged

## Key Pattern Matches

### 1. Junior Agent Instructions
- Exact match of OpenAI chatAgent instructions structure
- Same filler phrase requirements
- Identical "allow list" of permitted actions
- Same tool restriction (only getNextResponseFromSupervisor)

### 2. Supervisor Tool Execution  
- Matches OpenAI `handleToolCalls` iterative pattern
- Same function call/output structure
- Identical error handling approach
- Same response formatting

### 3. Session Configuration
- Uses OpenAI realtime API session update format
- Same modality, voice, and turn detection settings
- Identical tool registration approach
- Same WebSocket event handling

### 4. Conversation Flow
- Junior agent says filler phrase → calls supervisor tool
- Supervisor receives context + history → makes decisions → calls internal tools → returns formatted message  
- Junior agent reads supervisor response verbatim
- Pattern repeats for each user interaction

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable
export OPENAI_API_KEY="your-key-here"

# Run voice agent
python run_voice_agent.py
```

## Benefits of New Architecture

1. **Pattern Compliance**: Exact match with OpenAI reference implementation
2. **Maintainability**: Clear separation of concerns between junior/supervisor
3. **Extensibility**: Easy to add new supervisor capabilities without touching junior agent
4. **Debugging**: Clear supervisor call tracking and performance metrics
5. **Scalability**: Supervisor can handle complex multi-step workflows
6. **Voice Quality**: Maintains natural conversation flow while ensuring intelligent responses

## Performance Tracking

The new implementation tracks:
- Total interactions
- Supervisor call frequency  
- Audio processing metrics
- Tool execution statistics
- Error rates by component

This provides clear visibility into how often the supervisor is being consulted vs. junior agent handling requests directly.

## Migration Notes

- All existing tool functionality is preserved within the supervisor
- Payload processing remains separate and unchanged
- Configuration settings are backward compatible
- Voice capabilities are enhanced, not reduced
- External API integrations continue to work through the payload processor

The redesign maintains all existing functionality while providing a much cleaner, more maintainable architecture that aligns perfectly with the OpenAI Realtime Agents pattern.









