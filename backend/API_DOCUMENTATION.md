# FNOL Voice Agent - API Documentation

Complete API reference for the FNOL Voice Agent backend server.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: Configure as needed

## Authentication

Currently no authentication required (add JWT/OAuth as needed for production).

## HTTP Endpoints

### GET /

**Health Check**

Returns basic server status.

**Response:**
```json
{
  "status": "healthy",
  "service": "FNOL Voice Agent API"
}
```

**Status Codes:**
- `200 OK`: Server is running

---

### GET /health

**Detailed Health Check**

Returns comprehensive health status including service availability.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-30T12:34:56.789Z",
  "services": {
    "langgraph": "available",
    "voice_settings": "configured"
  }
}
```

**Status Codes:**
- `200 OK`: All services healthy
- `500 Internal Server Error`: Configuration issues

**Example:**
```bash
curl http://localhost:8000/health
```

---

### GET /api/session/{session_id}

**Get Session Data**

Retrieve data for a specific session (placeholder for production implementation).

**Parameters:**
- `session_id` (path): Session identifier

**Response:**
```json
{
  "session_id": "20250930_123456_789",
  "status": "active",
  "message": "Session data endpoint"
}
```

**Status Codes:**
- `200 OK`: Session found
- `404 Not Found`: Session doesn't exist

---

## WebSocket Endpoint

### WS /ws/voice

**Voice Agent WebSocket**

Main WebSocket endpoint for real-time voice agent communication.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/voice')
```

**Protocol:** JSON-based message exchange

---

## WebSocket Messages

### Client → Server

#### Start Session

```json
{
  "type": "start_session"
}
```

Initiates a new voice agent session and connects to Azure OpenAI Realtime API.

**Response**: `agent_ready` event

---

#### Audio Data

```json
{
  "type": "audio_data",
  "audio": "base64_encoded_pcm16_audio"
}
```

Sends audio data from microphone to the agent.

**Format:**
- Encoding: Base64
- Audio Format: PCM16
- Sample Rate: 24000 Hz
- Channels: 1 (mono)

**Example:**
```javascript
// Capture audio
const audioData = new Int16Array(buffer)
const base64Audio = btoa(String.fromCharCode(...new Uint8Array(audioData.buffer)))

ws.send(JSON.stringify({
  type: 'audio_data',
  audio: base64Audio
}))
```

---

#### Stop Session

```json
{
  "type": "stop_session"
}
```

Ends the current voice agent session.

---

### Server → Client

#### Connected

```json
{
  "type": "connected",
  "data": {
    "session_id": "20250930_123456_789",
    "message": "Connected to FNOL Voice Agent"
  },
  "timestamp": "12:34:56"
}
```

Sent immediately after WebSocket connection is established.

---

#### Agent Ready

```json
{
  "type": "agent_ready",
  "data": {
    "message": "Agent is listening"
  },
  "timestamp": "12:34:57"
}
```

Sent when the agent is ready to start listening.

---

#### Chat Message

```json
{
  "type": "chat_message",
  "data": {
    "role": "user",
    "content": "My name is John Smith",
    "timestamp": "12:35:01"
  },
  "timestamp": "12:35:01"
}
```

```json
{
  "type": "chat_message",
  "data": {
    "role": "assistant",
    "content": "Thank you, John. Can you tell me what happened?",
    "timestamp": "12:35:03"
  },
  "timestamp": "12:35:03"
}
```

Sent for each transcribed message (user or agent).

**Fields:**
- `role`: Either `"user"` or `"assistant"`
- `content`: Message text
- `timestamp`: When message was created (HH:MM:SS)

---

#### Claim Data Update

```json
{
  "type": "claim_data_update",
  "data": {
    "claim_data": {
      "claimant": {
        "insured_name": "John Smith",
        "insured_phone": "",
        "policy_number": null
      },
      "incident": {
        "incident_date": "",
        "incident_time": "",
        "incident_location": "",
        "incident_description": ""
      },
      "property_damage": {
        "property_type": "",
        "points_of_impact": [],
        "damage_description": "",
        "estimated_damage_severity": "",
        "additional_details": null
      }
    },
    "is_complete": false
  },
  "timestamp": "12:35:02"
}
```

Sent whenever claim data is updated by the extraction workflow.

**Fields:**
- `claim_data`: PropertyClaim schema object
- `is_complete`: Boolean indicating if claim is ready for submission

---

#### Audio Delta

```json
{
  "type": "audio_delta",
  "data": {
    "audio": "base64_encoded_pcm16_audio"
  },
  "timestamp": "12:35:04"
}
```

Sent continuously while agent is speaking.

**Format:**
- Same as audio_data (PCM16, 24kHz, mono)
- Client should decode and play immediately

**Example:**
```javascript
ws.onmessage = (event) => {
  const message = JSON.parse(event.data)
  if (message.type === 'audio_delta') {
    const audioBytes = Uint8Array.from(atob(message.data.audio), c => c.charCodeAt(0))
    const audioData = new Int16Array(audioBytes.buffer)
    // Play through audio worklet
    playbackNode.port.postMessage({ audio: audioData })
  }
}
```

---

#### Claim Complete

```json
{
  "type": "claim_complete",
  "data": {
    "claim_data": {
      "claimant": { /* complete data */ },
      "incident": { /* complete data */ },
      "property_damage": { /* complete data */ },
      "claim_id": "CLM-20250930-ABC12345"
    },
    "submission_result": {
      "success": true,
      "claim_id": "CLM-20250930-ABC12345",
      "status": "submitted",
      "message": "Claim has been successfully submitted",
      "submitted_at": "2025-09-30T12:35:30.123Z",
      "next_steps": "A claims adjuster will contact you within 24-48 hours."
    }
  },
  "timestamp": "12:35:30"
}
```

Sent when all required fields are collected and claim is submitted.

---

#### Error

```json
{
  "type": "error",
  "data": {
    "message": "Connection to Azure OpenAI failed"
  },
  "timestamp": "12:35:15"
}
```

Sent when an error occurs.

**Common Errors:**
- Connection failures
- Configuration issues
- Extraction errors
- API rate limits

---

## Data Models

### PropertyClaim Schema

```typescript
interface PropertyClaim {
  claimant: ClaimantInfo
  incident: IncidentDetails
  property_damage: PropertyDamage
  claim_id?: string  // Generated on submission
}

interface ClaimantInfo {
  insured_name: string
  insured_phone: string
  policy_number?: string
}

interface IncidentDetails {
  incident_date: string      // YYYY-MM-DD
  incident_time: string      // HH:MM
  incident_location: string
  incident_description: string
}

interface PropertyDamage {
  property_type: string
  points_of_impact: string[]
  damage_description: string
  estimated_damage_severity: string  // minor | moderate | severe
  additional_details?: string
}
```

### ConversationMessage

```typescript
interface ConversationMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string  // HH:MM:SS
}
```

## Message Flow Example

### Complete Session Flow

```
1. Client connects to WebSocket
   ← Server: { type: "connected", data: { session_id: "..." } }

2. Client starts session
   → Client: { type: "start_session" }
   ← Server: { type: "agent_ready", data: { message: "Agent is listening" } }

3. Client sends audio
   → Client: { type: "audio_data", audio: "..." }
   → Client: { type: "audio_data", audio: "..." }
   ...

4. Server transcribes and responds
   ← Server: { type: "chat_message", data: { role: "user", content: "..." } }
   ← Server: { type: "claim_data_update", data: { claim_data: {...} } }
   ← Server: { type: "audio_delta", data: { audio: "..." } }
   ← Server: { type: "audio_delta", data: { audio: "..." } }
   ← Server: { type: "chat_message", data: { role: "assistant", content: "..." } }

5. Conversation continues...
   (Steps 3-4 repeat)

6. Claim complete
   ← Server: { type: "claim_complete", data: { claim_data: {...}, submission_result: {...} } }

7. Client stops session
   → Client: { type: "stop_session" }
   WebSocket closes
```

## Error Handling

### Client-Side Error Handling

```javascript
ws.onerror = (error) => {
  console.error('WebSocket error:', error)
  // Display error to user
  // Attempt reconnection
}

ws.onclose = (event) => {
  if (event.code !== 1000) {
    // Abnormal closure
    console.error('Connection closed unexpectedly:', event.code, event.reason)
    // Attempt reconnection after delay
  }
}
```

### Server-Side Error Responses

All errors sent as:
```json
{
  "type": "error",
  "data": {
    "message": "Human-readable error description"
  },
  "timestamp": "HH:MM:SS"
}
```

## Rate Limiting

Currently no rate limiting implemented. For production, consider:

- Max connections per IP
- Max messages per second
- Max audio data per minute
- Session timeout after inactivity

## Monitoring Endpoints

### Metrics (Future Enhancement)

```
GET /metrics
```

Prometheus-compatible metrics:
- Active WebSocket connections
- Total sessions created
- Messages processed
- Errors encountered

### Logging

All important events logged:
- Session start/end
- Message exchange
- Errors and exceptions
- Performance metrics

## Development Tips

### Testing WebSocket Locally

```python
import asyncio
import websockets
import json

async def test():
    uri = "ws://localhost:8000/ws/voice"
    async with websockets.connect(uri) as websocket:
        # Receive connection message
        response = await websocket.recv()
        print("Connected:", json.loads(response))
        
        # Start session
        await websocket.send(json.dumps({"type": "start_session"}))
        
        # Listen for messages
        while True:
            message = await websocket.recv()
            print("Received:", json.loads(message))

asyncio.run(test())
```

### Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Log all WebSocket messages
logger.debug(f"Sending: {json.dumps(event)}")
logger.debug(f"Received: {json.dumps(message)}")
```

## Production Considerations

### Security
- Implement authentication (JWT tokens)
- Use WSS (secure WebSocket) in production
- Validate all incoming messages
- Rate limit to prevent abuse

### Scalability
- Use Redis for session storage
- Implement load balancing
- Add connection pooling
- Cache claim schemas

### Reliability
- Implement automatic reconnection
- Add message queueing
- Handle API failures gracefully
- Monitor and alert on errors

---

**Last Updated**: September 30, 2025  
**Version**: 1.0.0
