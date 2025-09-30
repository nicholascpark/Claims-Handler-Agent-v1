# FNOL Voice Agent - Testing Guide

Comprehensive testing guide for validating the FNOL Voice Agent application.

## 🧪 Test Scenarios

### Scenario 1: Basic Claim Initiation

**Test Flow:**
1. Start application
2. Click "Call Agent"
3. Wait for agent greeting
4. Respond with name and basic incident

**Expected Behavior:**
- Agent greets with company name
- Asks for caller's name
- Transcription appears in chat history
- JSON payload updates with `claimant.insured_name`

**Test Input:**
```
User: "Hello"
Agent: "Hello! This is IntactBot from Intact Specialty Insurance..."
User: "Hi, my name is Sarah Johnson"
```

**Expected JSON:**
```json
{
  "claimant": {
    "insured_name": "Sarah Johnson"
  }
}
```

### Scenario 2: Complete Home Claim

**Test Flow:**
1. Start new session
2. Provide complete claim information
3. Verify all fields extracted
4. Confirm claim submission

**Test Input:**
```
User: "Hi, I need to report damage to my home. My name is Michael Chen, you can reach me at 555-0123."

Agent: "I'm sorry to hear that, Michael. Can you tell me what happened?"

User: "Yesterday at 3 PM, a tree fell on my roof during the storm at 456 Oak Street in Portland."

Agent: "I understand. Can you describe the damage?"

User: "The roof is punctured, shingles are broken, and my living room window shattered. It looks pretty severe."
```

**Expected Final JSON:**
```json
{
  "claimant": {
    "insured_name": "Michael Chen",
    "insured_phone": "555-0123"
  },
  "incident": {
    "incident_date": "2025-09-29",
    "incident_time": "15:00",
    "incident_location": "456 Oak Street, Portland",
    "incident_description": "Tree fell on roof during storm"
  },
  "property_damage": {
    "property_type": "home",
    "points_of_impact": ["roof", "living room window"],
    "damage_description": "Roof punctured, shingles broken, window shattered",
    "estimated_damage_severity": "severe"
  }
}
```

### Scenario 3: Auto Claim

**Test Input:**
```
User: "I was in a car accident. My name is Lisa Rodriguez, phone 555-7890."

Agent: "I'm sorry to hear that. When and where did this happen?"

User: "Today at 2:30 PM at the intersection of Main and 5th in Seattle. I was rear-ended while stopped at a red light."

Agent: "Can you describe the damage to your vehicle?"

User: "My rear bumper is crushed, the trunk won't close, and both taillights are broken. Seems moderate damage."
```

**Expected Final JSON:**
```json
{
  "claimant": {
    "insured_name": "Lisa Rodriguez",
    "insured_phone": "555-7890"
  },
  "incident": {
    "incident_date": "2025-09-30",
    "incident_time": "14:30",
    "incident_location": "Main and 5th intersection, Seattle",
    "incident_description": "Rear-ended while stopped at red light"
  },
  "property_damage": {
    "property_type": "auto",
    "points_of_impact": ["rear bumper", "trunk", "taillights"],
    "damage_description": "Rear bumper crushed, trunk damaged, taillights broken",
    "estimated_damage_severity": "moderate"
  }
}
```

## ✅ Validation Checklist

### Backend Validation

- [ ] Server starts without errors
- [ ] Health endpoint returns 200
- [ ] WebSocket accepts connections
- [ ] Voice settings validated
- [ ] LangGraph workflow initializes
- [ ] Azure OpenAI connection successful

### Frontend Validation

- [ ] Development server starts
- [ ] Logo displays correctly
- [ ] UI renders without errors
- [ ] WebSocket connects to backend
- [ ] Audio worklets load successfully
- [ ] Tailwind styles applied

### Integration Validation

- [ ] WebSocket bidirectional communication
- [ ] Audio streaming works (both directions)
- [ ] Chat history updates in real-time
- [ ] JSON payload updates dynamically
- [ ] Progress bar reflects completion
- [ ] Error handling works correctly
- [ ] Session cleanup on disconnect

### Audio Validation

- [ ] Microphone captures audio
- [ ] Audio sent to backend (PCM16 format)
- [ ] Transcription appears in chat
- [ ] Agent audio plays back
- [ ] No audio glitches or delays
- [ ] VAD triggers appropriately

### UI/UX Validation

- [ ] Logo in top-left corner
- [ ] Call Agent button prominent
- [ ] Chat history scrolls automatically
- [ ] JSON payload syntax-highlighted
- [ ] Hide/show chat works
- [ ] Status indicator updates
- [ ] Responsive on mobile
- [ ] Color scheme (white/gray/black/red)

## 🔍 Debug Mode

### Enable Backend Debug Logging

Edit `backend/server.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Enable Frontend Console Logging

Open browser DevTools (F12) and monitor:
- Console tab: JavaScript logs
- Network tab: WebSocket messages
- Application tab: Storage and state

### Enable LangGraph Tracing

Add to `.env`:
```bash
LANGCHAIN_TRACING=true
LANGSMITH_API_KEY=your-langsmith-key
```

## 🐛 Common Test Failures

### Audio Not Capturing

**Symptoms**: No transcription appears, agent doesn't hear you

**Checks**:
1. Browser microphone permissions granted
2. Correct microphone selected in system settings
3. Audio worklet loaded (check console)
4. WebSocket connection active

**Fix**:
```javascript
// Check in browser console:
navigator.mediaDevices.getUserMedia({ audio: true })
  .then(stream => console.log('Microphone access granted'))
  .catch(err => console.error('Microphone error:', err))
```

### JSON Not Updating

**Symptoms**: Claim data stays empty despite conversation

**Checks**:
1. Backend LangGraph workflow executing
2. Trustcall extraction working
3. WebSocket messages being sent
4. Keywords triggering extraction

**Debug**:
```bash
# Backend logs should show:
# "Workflow executing..."
# "Extraction worker processing..."
# "Claim data updated"

# Check backend logs for extraction errors
```

### Agent Not Responding

**Symptoms**: No audio playback, agent silent

**Checks**:
1. Azure OpenAI Realtime API connected
2. Audio playback worklet initialized
3. Browser audio not muted
4. AudioContext resumed (requires user interaction)

**Fix**:
```javascript
// In browser console:
const ctx = new AudioContext()
console.log('AudioContext state:', ctx.state)
// Should be 'running', not 'suspended'

// If suspended:
ctx.resume()
```

### WebSocket Disconnects

**Symptoms**: Connection drops frequently

**Checks**:
1. Backend server running
2. Network connectivity stable
3. Firewall not blocking WebSocket
4. No proxy interference

**Fix**:
- Implement reconnection logic (already in useVoiceAgent hook)
- Check network tab for disconnect reason
- Verify backend logs for errors

## 📊 Performance Testing

### Latency Benchmarks

**Target Metrics:**
- User speech → Transcription: < 1 second
- Transcription → Agent response: < 2 seconds
- Total round-trip time: < 3 seconds

**Measure:**
```javascript
// In browser console
performance.mark('user-speaks')
// ... wait for agent response ...
performance.mark('agent-responds')
performance.measure('total-latency', 'user-speaks', 'agent-responds')
console.log(performance.getEntriesByType('measure'))
```

### Load Testing

**Backend:**
```bash
# Install wrk
# Linux: apt-get install wrk
# Mac: brew install wrk

# Test WebSocket endpoint
wrk -t4 -c100 -d30s http://localhost:8000/health
```

**Concurrent Sessions:**
- Open multiple browser tabs
- Start sessions simultaneously
- Verify each session independent
- Check memory usage

## 🔄 Regression Testing

After any code changes, verify:

1. **Basic Flow**: Greeting → Name collection → Incident report → Claim submission
2. **Edge Cases**: Empty responses, interrupted speech, background noise
3. **Error Recovery**: Network interruption, API errors, invalid data
4. **UI Updates**: Chat, JSON, status all update correctly
5. **Audio Quality**: No distortion, proper volume, no echo

## 📝 Test Documentation

### Creating Test Reports

Document each test with:
- Date/time of test
- Tester name
- Test scenario executed
- Expected vs actual results
- Screenshots (if UI issue)
- Logs (backend and frontend)
- Resolution (if issue found)

### Test Report Template

```markdown
# Test Report

**Date**: 2025-09-30
**Tester**: John Doe
**Scenario**: Basic Claim Initiation
**Status**: ✅ PASS / ❌ FAIL

## Steps Executed
1. Started application
2. Clicked "Call Agent"
3. Provided name and incident

## Expected Results
- Agent greeting heard
- Transcription in chat
- JSON updated with name

## Actual Results
- [Describe what happened]

## Issues Found
- [List any issues]

## Logs
[Attach relevant logs]

## Screenshots
[Attach screenshots if applicable]
```

## 🎓 User Acceptance Testing (UAT)

### UAT Checklist

- [ ] Non-technical user can start application
- [ ] UI is intuitive without training
- [ ] Audio quality is clear and natural
- [ ] Conversation feels natural
- [ ] Data extracted accurately
- [ ] Errors handled gracefully
- [ ] Session can be restarted easily

### UAT Feedback Form

```
1. How easy was it to start a conversation? (1-5)
2. Was the agent's voice clear and natural? (1-5)
3. Did the agent understand you correctly? (1-5)
4. Was the UI easy to navigate? (1-5)
5. Would you use this for real claims? (Yes/No)
6. Additional comments: ___________
```

## 🔐 Security Testing

### Security Checklist

- [ ] API keys not exposed in frontend
- [ ] WebSocket messages encrypted (wss://)
- [ ] Input validation on backend
- [ ] XSS protection enabled
- [ ] CORS properly configured
- [ ] No sensitive data in logs
- [ ] Microphone access requires user permission

## 📦 Deployment Testing

### Pre-Deployment

- [ ] All tests pass
- [ ] No console errors
- [ ] Production build successful
- [ ] Environment variables configured
- [ ] SSL certificates valid
- [ ] Monitoring configured

### Post-Deployment

- [ ] Health check returns healthy
- [ ] WebSocket connects successfully
- [ ] Audio streams working
- [ ] Data persists correctly
- [ ] Logs are being collected
- [ ] Alerts configured

## 🎯 Success Criteria

A successful test run should demonstrate:

1. ✅ **Connection**: Both frontend and backend start without errors
2. ✅ **Audio**: Bidirectional audio streaming works
3. ✅ **Transcription**: Speech-to-text accurate
4. ✅ **Extraction**: Claim data extracted correctly
5. ✅ **UI Updates**: Chat and JSON update in real-time
6. ✅ **Completion**: Full claim can be collected and submitted
7. ✅ **Error Handling**: Errors don't crash the application

---

**Last Updated**: September 30, 2025  
**Version**: 1.0.0
