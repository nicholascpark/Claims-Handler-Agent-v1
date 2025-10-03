# Payload Completeness Update - Both Injury and Damage Required

## Summary
Updated the `PropertyClaim.is_complete()` validation logic to align with the agent's prompt expectations. The agent is instructed to ask about BOTH personal injury AND property damage, so the validation now requires both to be explicitly addressed before considering a claim complete.

## Changes Made

### 1. Updated `is_complete()` Method (schema.py lines 67-128)

**Previous Logic:**
```python
# At least one type of damage (injury or property) must be complete
return has_injury or has_damage
```

**New Logic:**
```python
# BOTH personal_injury and property_damage must be explicitly addressed (not None)
has_addressed_injury = self.personal_injury is not None
has_addressed_damage = self.property_damage is not None

if not (has_addressed_injury and has_addressed_damage):
    # Agent must ask about both before claim is considered complete
    return False

# At least one type of damage (injury or property) must have valid data
return has_injury or has_damage
```

**Key Points:**
- Both `personal_injury` and `property_damage` must be **not None** (explicitly addressed)
- At least one must contain **valid data** (not just placeholders)
- This allows for scenarios like "no injury but has property damage" or vice versa

### 2. Updated `get_missing_fields()` Method (schema.py lines 167-191)

**Previous Logic:**
- Only checked fields if they were present (not None)
- Would report `damage_type_unknown` if neither was set

**New Logic:**
```python
if self.personal_injury is None:
    missing.append('personal_injury_not_addressed')
else:
    # Check for missing subfields...

if self.property_damage is None:
    missing.append('property_damage_not_addressed')
else:
    # Check for missing subfields...
```

### 3. Updated Field Collection Order (schema.py lines 216, 220)

Added friendly names for new missing field markers:
- `personal_injury_not_addressed` → "personal injury information"
- `property_damage_not_addressed` → "property damage information"

## Expected Behavior

### Scenario 1: Property Damage Only
**User:** "A tree fell on my house. No, I wasn't injured."

**Expected Flow:**
1. Agent collects property damage details (property type, damaged areas, etc.)
2. Agent asks about personal injury
3. User confirms no injury
4. Trustcall should create: `PersonalInjury(points_of_impact=[], injury_description="No personal injury reported", severity="none")`
5. Claim is complete: `has_addressed_injury=True, has_addressed_damage=True, has_damage=True`

### Scenario 2: Personal Injury Only
**User:** "I was in a car accident and hurt my neck. No vehicle damage to report."

**Expected Flow:**
1. Agent collects personal injury details
2. Agent asks about property damage
3. User confirms no property damage
4. Trustcall should create: `PropertyDamage(property_type="none", points_of_impact=[], damage_description="No property damage reported", estimated_damage_severity="none")`
5. Claim is complete: `has_addressed_injury=True, has_addressed_damage=True, has_injury=True`

### Scenario 3: Both Present
**User:** "Car accident - I hurt my back and my car's bumper is damaged."

**Expected Flow:**
1. Agent collects both injury and damage details
2. Both structures are populated with valid data
3. Claim is complete: `has_addressed_injury=True, has_addressed_damage=True, has_injury=True, has_damage=True`

## Testing Recommendations

### Test Case 1: Property Damage Only
```python
claim = PropertyClaim(
    claimant=ClaimantInfo(insured_name="John Doe", insured_phone="555-0100"),
    incident=IncidentDetails(...),
    personal_injury=PersonalInjury(
        points_of_impact=[],
        injury_description="No personal injury reported",
        severity="none"
    ),
    property_damage=PropertyDamage(
        property_type="auto",
        points_of_impact=["rear bumper"],
        damage_description="Rear bumper dented",
        estimated_damage_severity="minor"
    )
)
assert claim.is_complete() == True  # Should pass
```

### Test Case 2: Only Property Damage, No Injury Addressed Yet
```python
claim = PropertyClaim(
    claimant=ClaimantInfo(insured_name="John Doe", insured_phone="555-0100"),
    incident=IncidentDetails(...),
    personal_injury=None,  # Not addressed yet
    property_damage=PropertyDamage(...)
)
assert claim.is_complete() == False  # Should fail - injury not addressed
assert "personal_injury_not_addressed" in claim.get_missing_fields()
```

### Test Case 3: Both Addressed but Neither Valid
```python
claim = PropertyClaim(
    claimant=ClaimantInfo(insured_name="John Doe", insured_phone="555-0100"),
    incident=IncidentDetails(...),
    personal_injury=PersonalInjury(points_of_impact=[], injury_description="", severity=""),
    property_damage=PropertyDamage(property_type="", points_of_impact=[], damage_description="", estimated_damage_severity="")
)
assert claim.is_complete() == False  # Should fail - both addressed but neither valid
```

## Trustcall Extraction Guidance

The trustcall extractor should intelligently handle negatives:

**User says:** "No injury" or "I wasn't hurt" or "No one was injured"
**Should extract:**
```json
{
  "personal_injury": {
    "points_of_impact": [],
    "injury_description": "No personal injury reported",
    "severity": "none"
  }
}
```

**User says:** "No damage to property" or "Vehicle is fine"
**Should extract:**
```json
{
  "property_damage": {
    "property_type": "none",
    "points_of_impact": [],
    "damage_description": "No property damage reported",
    "estimated_damage_severity": "none"
  }
}
```

## Alignment with Prompt

This change aligns with the supervisor prompt (prompts.py lines 43-44):
```
7. Personal injury: affected body parts, description, severity
8. Property damage: type of property, damaged areas, description, severity
```

The agent is explicitly instructed to ask about BOTH, so the validation now enforces that both must be addressed before submission is allowed.

## Impact

✅ **Benefits:**
- Ensures complete intake process following the agent's conversation flow
- Prevents premature claim submission
- Better data quality - always know if injury/damage was discussed
- Aligns validation with conversational expectations

⚠️ **Potential Issues:**
- Trustcall may need additional prompting to create placeholder structures for "no injury" scenarios
- Frontend may need updates if it expects claims to be completable with only one damage type

## Related Files
- `voice_langgraph/schema.py` - Updated validation logic
- `voice_langgraph/prompts.py` - Contains agent instructions (unchanged)
- `voice_langgraph/nodes.py` - Uses `is_complete()` and `get_missing_fields()` for routing

