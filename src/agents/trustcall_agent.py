"""Trustcall Extraction Agent (lean, background-friendly)

This module provides a thin wrapper around trustcall to perform inexpensive
JSON patch style updates from conversational text, keeping the public API
compatible with callers in `supervisor_agent.py` and tests.

Design goals:
- Pure trustcall for extraction and patch generation (no fallbacks)
- No hardcoded business context beyond prompts provided by callers
- Lightweight data transforms; safe to run in background threads
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from src.config.settings import settings
from src.schema.simplified_payload import PropertyClaim, ClaimantInfo, IncidentDetails, PropertyDamage
from src.utils.time_utils import create_temporal_context_system_message
from src.prompts import AgentPrompts


@dataclass
class TrustcallExtractionResult:
    patches_applied: List[Dict[str, Any]]
    updated_data: Dict[str, Any]
    extraction_successful: bool
    error_message: Optional[str] = None


class TrustcallExtractionAgent:
    """Minimal trustcall-based extractor for JSON updates.

    Public API intentionally mirrors previous implementation used by
    `ClaimsSupervisorAgent`:
    - extract_and_patch_claim_data(user_input, existing_data, conversation_context)
    - batch_extract_from_conversation(conversation_history, existing_data)
    - validate_extraction_completeness(claim_data)
    """
    
    def __init__(self, on_field_updated: Optional[Callable[[str], None]] = None):
        self.on_field_updated = on_field_updated or (lambda _path: None)
        self._trustcall_initialized = False
        self._initialize_trustcall()
        
    def _initialize_trustcall(self) -> None:
        try:
            from trustcall import create_extractor  # type: ignore
            from langchain_openai import AzureChatOpenAI  # type: ignore
            
            self.llm = AzureChatOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_CHAT_API_VERSION,
                azure_endpoint=(settings.AZURE_OPENAI_ENDPOINT or "").rstrip("/"),
                azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
                temperature=0.2,
                model_name=settings.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
            )
            
            # Enhanced tools: use PropertyClaim top-level schema only
            self.extractor = create_extractor(
                llm=self.llm,
                tools=[PropertyClaim],
                tool_choice="any",
                enable_inserts=True,
            )
            self._trustcall_initialized = True
        except Exception as e:  # propagate as runtime for callers to log
            raise RuntimeError(f"Failed to initialize trustcall: {e}")

    def _wrap_existing_for_trustcall(self, existing: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not existing:
            return {}
        # Handle both legacy SimplifiedClaim and new PropertyClaim format
        if any(k in existing for k in ("PropertyClaim", "SimplifiedClaim")):
            return existing
        
        # Handle nested structure if passed as flat dict
        if "claimant" in existing or "incident" in existing or "property_damage" in existing:
            return {"PropertyClaim": existing}
            
        # Default wrapper for backward compatibility
        return {"PropertyClaim": existing}

    def _conversation_prompt(self, user_input: str, context: Optional[str]) -> str:
        temporal = create_temporal_context_system_message()
        system_guidance = AgentPrompts.get_trustcall_system_message()
        
        parts = [
            f"System Guidance: {system_guidance}",
            f"Temporal Context: {temporal}", 
            f"User Input: {user_input}"
        ]
        if context:
            parts.insert(2, f"Conversation Context: {context}")
        return "\n\n".join(parts)

    def _diff_to_patches(self, prior: Dict[str, Any], new_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        patches: List[Dict[str, Any]] = []
        for key, value in new_data.items():
            if value is None:
                continue
            if key in prior:
                if prior.get(key) != value:
                    patches.append({"op": "replace", "path": f"/{key}", "value": value})
            else:
                patches.append({"op": "add", "path": f"/{key}", "value": value})
        return patches

    def _apply_local_patches(self, target: Dict[str, Any], patches: List[Dict[str, Any]]) -> None:
        for op in patches:
            kind = op.get("op")
            path = (op.get("path", "").lstrip("/") or "").strip()
            if not path:
                continue
            if kind in ("add", "replace"):
                target[path] = op.get("value")
            elif kind == "remove":
                if path in target:
                    del target[path]
    
    async def extract_and_patch_claim_data(
        self, 
        user_input: str, 
        existing_data: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[str] = None,
    ) -> TrustcallExtractionResult:
        if not self._trustcall_initialized:
            return TrustcallExtractionResult([], existing_data or {}, False, "Trustcall not initialized")

        try:
            prompt = self._conversation_prompt(user_input, conversation_context)
            existing = existing_data or {}
            wrapped = self._wrap_existing_for_trustcall(existing)

            result = self.extractor.invoke({
                "messages": [{"role": "user", "content": prompt}],
                "existing": wrapped,
            })

            patches_applied: List[Dict[str, Any]] = []
            updated = dict(existing)

            responses = result.get("responses", []) if isinstance(result, dict) else []
            metadata_list = result.get("response_metadata", []) if isinstance(result, dict) else []

            for response, _meta in zip(responses, metadata_list):
                data = response.model_dump() if hasattr(response, "model_dump") else dict(response)
                # Handle both PropertyClaim and legacy SimplifiedClaim keys
                if "PropertyClaim" in data and isinstance(data["PropertyClaim"], dict):
                    data = data["PropertyClaim"]
                elif "SimplifiedClaim" in data and isinstance(data["SimplifiedClaim"], dict):
                    data = data["SimplifiedClaim"]
                
                patches = self._diff_to_patches(updated, data)
                patches_applied.extend(patches)
                self._apply_local_patches(updated, patches)

            # Notify callback without values
            for p in patches_applied:
                path = p.get("path", "")
                if path:
                    try:
                        self.on_field_updated(path)
                    except Exception:
                        pass

            return TrustcallExtractionResult(patches_applied, updated, True)
        except Exception as e:
            return TrustcallExtractionResult([], existing_data or {}, False, f"Trustcall extraction failed: {e}")
    
    async def batch_extract_from_conversation(
        self, 
        conversation_history: List[Dict[str, str]], 
        existing_data: Optional[Dict[str, Any]] = None,
    ) -> TrustcallExtractionResult:
        content = "\n".join(
            f"{m.get('role','user')}: {m.get('content','')}" for m in conversation_history if m.get("content")
        )
        return await self.extract_and_patch_claim_data(
            user_input=content,
            existing_data=existing_data,
            conversation_context="Full conversation history",
        )
    
    def validate_extraction_completeness(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Try PropertyClaim validation with nested structure handling
            if self._is_nested_structure(claim_data):
                property_claim = PropertyClaim(**claim_data)
            else:
                # Handle flat structure by attempting to build nested structure
                nested_data = self._build_nested_structure(claim_data)
                property_claim = PropertyClaim(**nested_data)
                
            return {
                "is_complete": property_claim.is_complete(),
                "missing_fields": property_claim.get_missing_fields(),
                "validation_successful": True,
            }
        except Exception as e:
            return {
                "is_complete": False,
                "missing_fields": ["validation_error"],
                "validation_successful": False,
                "error": str(e),
            }

    def _is_nested_structure(self, data: Dict[str, Any]) -> bool:
        """Check if data already has nested structure"""
        return any(key in data for key in ["claimant", "incident", "property_damage"])

    def _build_nested_structure(self, flat_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build nested structure from flat data for backward compatibility"""
        nested = {}
        
        # Note: claim_id is system-generated, not collected during intake
        # Only map if it already exists (for existing claims)
        if "claim_id" in flat_data:
            nested["claim_id"] = flat_data["claim_id"]
        
        # Build claimant info
        claimant_fields = ["insured_name", "insured_phone", "policy_number"]
        claimant_data = {}
        for field in claimant_fields:
            if field in flat_data:
                claimant_data[field] = flat_data[field]
        if claimant_data:
            nested["claimant"] = claimant_data
        
        # Build incident details
        incident_fields = ["incident_date", "incident_time", "incident_location", "incident_description"]
        incident_data = {}
        for field in incident_fields:
            if field in flat_data:
                incident_data[field] = flat_data[field]
        if incident_data:
            nested["incident"] = incident_data
        
        # Build property damage info with defaults
        damage_data = {}
        if "property_type" in flat_data:
            damage_data["property_type"] = flat_data["property_type"]
        
        # Handle legacy fields mapping
        if "vehicles_involved" in flat_data and flat_data["vehicles_involved"]:
            damage_data["property_type"] = "auto"
            damage_data["points_of_impact"] = ["multiple areas"]
            damage_data["damage_description"] = f"Vehicle collision involving: {', '.join(flat_data['vehicles_involved'])}"
        
        if not damage_data.get("points_of_impact"):
            damage_data["points_of_impact"] = ["unspecified"]
        if not damage_data.get("damage_description"):
            damage_data["damage_description"] = "Damage details to be assessed"
        if not damage_data.get("estimated_damage_severity"):
            damage_data["estimated_damage_severity"] = "moderate"
        
        # Map additional legacy fields
        additional_details = []
        if flat_data.get("police_report_number"):
            additional_details.append(f"Police report: {flat_data['police_report_number']}")
        if flat_data.get("witness_present"):
            additional_details.append("Witnesses present")
        if flat_data.get("injuries_reported"):
            additional_details.append("Injuries reported")
        
        if additional_details:
            damage_data["additional_details"] = "; ".join(additional_details)
        
        if damage_data:
            nested["property_damage"] = damage_data
        
        return nested


def create_trustcall_agent(on_field_updated: Optional[Callable[[str], None]] = None) -> TrustcallExtractionAgent:
    return TrustcallExtractionAgent(on_field_updated=on_field_updated)


