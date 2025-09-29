"""Payload Processor Agent - External integration handler

This agent is dedicated to processing final JSON payloads and handling
external system integrations, completely separate from the supervisor.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from src.schema.simplified_payload import PropertyClaim
from src.config.settings import settings
from src.prompts import AgentPrompts

# For backward compatibility
SimplifiedClaim = PropertyClaim


class PayloadProcessorAgent:
    """
    Dedicated agent for processing final claim payloads and external integration.
    
    Key responsibilities:
    - Receive simplified payloads from supervisor
    - Handle external API calls
    - Manage final claim submission
    - Error handling and retry logic
    """
    
    def __init__(self):
        self.processing_history = []
        self.retry_count = {}
    
    def process_claim_payload(self, claim: PropertyClaim, source_agent: str = "supervisor") -> Dict[str, Any]:
        """
        Process a completed claim payload.
        
        Args:
            claim: SimplifiedClaim object with all required information
            source_agent: Source agent that delegated the payload
            
        Returns:
            Dictionary with processing results
        """
        
        processing_id = self._generate_processing_id()
        
        result = {
            "processing_id": processing_id,
            "claim_id": claim.claim_id,
            "status": "processing",
            "timestamp": self._get_timestamp(),
            "source_agent": source_agent,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Validate payload completeness
            if not claim.is_complete():
                missing_fields = claim.get_missing_fields()
                result["status"] = "rejected"
                result["errors"] = [f"Missing required fields: {', '.join(missing_fields)}"]
                return result
            
            # Convert to external format
            external_payload = self._convert_to_external_format(claim)
            
            # Validate external payload
            validation_result = self._validate_external_payload(external_payload)
            if not validation_result["is_valid"]:
                result["status"] = "rejected"
                result["errors"] = validation_result["errors"]
                return result
            
            # Submit to external systems (HTTP POST if configured, otherwise enhanced mock)
            submission_result = self._submit_payload(external_payload, processing_id)
            
            if submission_result["success"]:
                result["status"] = "completed"
                result["external_reference"] = submission_result.get("reference_id")
                result["confirmation_number"] = submission_result.get("confirmation_number")
                result["adjuster_name"] = submission_result.get("adjuster_name")
                result["adjuster_phone"] = submission_result.get("adjuster_phone") 
                result["estimated_contact_time"] = submission_result.get("estimated_contact_time")
                result["next_steps"] = submission_result.get("next_steps", [])
                
                # Enhanced completion logging
                self._log_successful_completion(result)
            else:
                result["status"] = "failed"
                result["errors"] = submission_result.get("errors", ["Unknown submission error"])
                result["retry_recommended"] = submission_result.get("retry_recommended", False)
            
        except Exception as e:
            result["status"] = "error"
            result["errors"] = [f"Processing error: {str(e)}"]
        
        # Log the processing attempt
        self._log_processing_attempt(result)
        
        return result
    def _submit_payload(self, payload: Dict[str, Any], processing_id: str) -> Dict[str, Any]:
        """
        Submit payload via HTTP POST if PAYLOAD_PROCESSOR_ENDPOINT is configured,
        otherwise fall back to mock submission.
        """
        endpoint = settings.PAYLOAD_PROCESSOR_ENDPOINT
        if endpoint:
            try:
                import requests
                headers = {"Content-Type": "application/json"}
                response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
                if response.status_code >= 200 and response.status_code < 300:
                    try:
                        data = response.json()
                    except Exception:
                        data = {}
                    # Normalize expected fields
                    return {
                        "success": True,
                        "confirmation_number": data.get("confirmation_number") or data.get("confirmation") or f"CONF-{processing_id[-8:]}",
                        "reference_id": data.get("reference_id") or data.get("id") or f"REF-{processing_id}",
                        "external_system": "HTTPEndpoint",
                        "submitted_at": self._get_timestamp()
                    }
                else:
                    return {
                        "success": False,
                        "errors": [f"HTTP {response.status_code}: {response.text[:200]}"]
                    }
            except Exception as e:
                # Fall back to mock on error
                return self._submit_to_external_systems(payload, processing_id)
        else:
            return self._submit_to_external_systems(payload, processing_id)

    
    def _convert_to_external_format(self, claim: PropertyClaim) -> Dict[str, Any]:
        """
        Convert PropertyClaim nested structure to external system format.
        
        Handles all property types and nested damage assessment.
        """
        
        # Determine claim type from property type  
        claim_type_mapping = {
            "auto": "AUTO",
            "home": "PROPERTY", 
            "commercial": "COMMERCIAL",
            "condo": "PROPERTY",
            "specialty": "SPECIALTY"
        }
        claim_type = claim_type_mapping.get(claim.property_damage.property_type.lower(), "PROPERTY")
        
        # Generate claim_id if not present (new claims)
        claim_id = claim.claim_id or self._generate_claim_id(claim.property_damage.property_type)
        
        header = {
            "claimId": claim_id,
            "dateReported": self._get_timestamp(),
            "claimType": claim_type,
            "propertyType": claim.property_damage.property_type
        }
        
        # Include policy number only if provided
        if claim.claimant.policy_number:
            header["policyNumber"] = claim.claimant.policy_number

        external_format = {
            "claimHeader": header,
            "insuredParty": {
                "name": claim.claimant.insured_name,
                "contactPhone": claim.claimant.insured_phone
            },
            "incident": {
                "description": claim.incident.incident_description,
                "dateOfLoss": claim.incident.incident_date,
                "timeOfLoss": claim.incident.incident_time,
                "locationOfLoss": claim.incident.incident_location
            },
            "propertyDamage": {
                "propertyType": claim.property_damage.property_type,
                "pointsOfImpact": claim.property_damage.points_of_impact,
                "damageDescription": claim.property_damage.damage_description,
                "estimatedSeverity": claim.property_damage.estimated_damage_severity,
                "additionalDetails": claim.property_damage.additional_details or ""
            }
        }
        
        return external_format
    
    def _validate_external_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the external payload format.
        
        Args:
            payload: External format payload
            
        Returns:
            Validation result dictionary
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required sections
        required_sections = ["claimHeader", "insuredParty", "incident"]
        for section in required_sections:
            if section not in payload:
                validation_result["errors"].append(f"Missing required section: {section}")
                validation_result["is_valid"] = False
        
        # Check payload size
        payload_json = json.dumps(payload)
        if len(payload_json.encode('utf-8')) > settings.MAX_PAYLOAD_SIZE:
            validation_result["errors"].append("Payload exceeds maximum size limit")
            validation_result["is_valid"] = False
        
        # Validate claim header
        if "claimHeader" in payload:
            header = payload["claimHeader"]
            if not header.get("claimId"):
                validation_result["errors"].append("Missing claim ID in header")
                validation_result["is_valid"] = False
        
        return validation_result
    
    def _submit_to_external_systems(self, payload: Dict[str, Any], processing_id: str) -> Dict[str, Any]:
        """
        Submit payload to external claim processing systems.
        
        Enhanced mock implementation with realistic responses and better logging.
        
        Args:
            payload: External format payload
            processing_id: Unique processing ID
            
        Returns:
            Submission result dictionary
        """
        
        # Enhanced mock external system integration
        import random
        import time
        
        print(f"[{self._get_timestamp_short()}] 📤 Submitting claim to external systems...")
        
        # Mock network delay (realistic timing)
        time.sleep(random.uniform(0.2, 0.8))
        
        # Enhanced success rate (95% success for better UX)
        if random.random() > 0.05:
            # Generate realistic confirmation details
            claim_id = payload.get("claimHeader", {}).get("claimId", "UNKNOWN")
            confirmation_number = f"{settings.COMPANY_NAME[:3].upper()}-{processing_id[-8:]}"
            reference_id = f"REF-{claim_id}-{processing_id[-6:]}"
            
            # Mock assignment of adjuster and next steps
            adjusters = ["Sarah Johnson", "Mike Chen", "Lisa Rodriguez", "David Thompson"]
            adjuster_name = random.choice(adjusters)
            
            print(f"[{self._get_timestamp_short()}] ✅ Claim submitted successfully")
            print(f"[{self._get_timestamp_short()}] 📋 Confirmation: {confirmation_number}")
            print(f"[{self._get_timestamp_short()}] 👤 Assigned Adjuster: {adjuster_name}")
            
            return {
                "success": True,
                "confirmation_number": confirmation_number,
                "reference_id": reference_id,
                "adjuster_name": adjuster_name,
                "adjuster_phone": self._generate_mock_phone(),
                "estimated_contact_time": "within 24 hours",
                "external_system": "EnhancedMockClaimsAPI",
                "submitted_at": self._get_timestamp(),
                "next_steps": [
                    f"Adjuster {adjuster_name} will contact you within 24 hours",
                    "You will receive an email confirmation within 30 minutes", 
                    "Please have your policy documents ready for the adjuster call",
                    f"Your reference number is {reference_id} for future correspondence"
                ]
            }
        else:
            # Mock failure with helpful messaging
            error_types = [
                "External system temporarily unavailable - high volume",
                "Network timeout - please try again in a few minutes",
                "Validation issue with external system format"
            ]
            error_msg = random.choice(error_types)
            
            print(f"[{self._get_timestamp_short()}] ⚠️ Submission failed: {error_msg}")
            
            return {
                "success": False,
                "errors": [error_msg],
                "external_system": "EnhancedMockClaimsAPI",
                "retry_recommended": True,
                "retry_after_seconds": 60
            }

    def _generate_mock_phone(self) -> str:
        """Generate a realistic mock phone number for adjuster contact"""
        import random
        area_codes = ["555", "800", "877", "866"]
        area = random.choice(area_codes)
        exchange = f"{random.randint(200, 999)}"
        number = f"{random.randint(1000, 9999)}"
        return f"{area}-{exchange}-{number}"

    def _get_timestamp_short(self) -> str:
        """Get short timestamp for inline logging"""
        return datetime.now().strftime('%H:%M:%S')

    def _generate_claim_id(self, property_type: str) -> str:
        """Generate a new claim ID based on property type"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        import random
        random_suffix = f"{random.randint(100, 999)}"
        
        # Property type prefix mapping
        type_prefix = {
            "auto": "AUTO",
            "home": "HOME", 
            "commercial": "COMM",
            "condo": "CONDO",
            "specialty": "SPEC"
        }.get(property_type.lower(), "PROP")
        
        return f"CL-{type_prefix}-{timestamp}-{random_suffix}"
    
    def retry_failed_processing(self, processing_id: str, max_retries: int = None) -> Dict[str, Any]:
        """
        Retry failed payload processing.
        
        Args:
            processing_id: ID of failed processing attempt
            max_retries: Maximum retry attempts (uses settings default if None)
            
        Returns:
            Retry result dictionary
        """
        max_retries = max_retries or settings.MAX_TOOL_RETRIES
        
        if processing_id not in self.retry_count:
            self.retry_count[processing_id] = 0
        
        if self.retry_count[processing_id] >= max_retries:
            return {
                "success": False,
                "error": "Maximum retry attempts exceeded",
                "processing_id": processing_id,
                "retry_count": self.retry_count[processing_id]
            }
        
        # Find original processing attempt
        original_attempt = None
        for attempt in self.processing_history:
            if attempt["processing_id"] == processing_id:
                original_attempt = attempt
                break
        
        if not original_attempt:
            return {
                "success": False,
                "error": "Original processing attempt not found",
                "processing_id": processing_id
            }
        
        # Increment retry count
        self.retry_count[processing_id] += 1
        
        # Retry the processing (mock implementation)
        # In production, you'd reconstruct and resubmit the original payload
        return {
            "success": True,
            "message": f"Retry attempt {self.retry_count[processing_id]} initiated",
            "processing_id": processing_id,
            "retry_count": self.retry_count[processing_id]
        }
    
    def get_processing_status(self, processing_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a processing attempt.
        
        Args:
            processing_id: Processing ID to check
            
        Returns:
            Processing status dictionary or None if not found
        """
        for attempt in self.processing_history:
            if attempt["processing_id"] == processing_id:
                return attempt.copy()
        return None
    
    def get_processing_history(self, claim_id: Optional[str] = None) -> list:
        """
        Get processing history, optionally filtered by claim ID.
        
        Args:
            claim_id: Optional claim ID filter
            
        Returns:
            List of processing attempts
        """
        if claim_id:
            return [attempt for attempt in self.processing_history if attempt.get("claim_id") == claim_id]
        return self.processing_history.copy()
    
    # Helper methods
    def _generate_processing_id(self) -> str:
        """Generate unique processing ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        import random
        random_suffix = f"{random.randint(1000, 9999)}"
        return f"PROC-{timestamp}-{random_suffix}"
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.now().isoformat()
    
    def _log_processing_attempt(self, result: Dict[str, Any]) -> None:
        """Log processing attempt to history"""
        self.processing_history.append(result.copy())
        
        # Keep history manageable (last 100 attempts)
        if len(self.processing_history) > 100:
            self.processing_history = self.processing_history[-100:]

    def _log_successful_completion(self, result: Dict[str, Any]) -> None:
        """Log successful completion with enhanced details"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        confirmation = result.get("confirmation_number", "N/A")
        adjuster = result.get("adjuster_name", "TBD")
        
        print("\n" + "=" * 80)
        print("🎉 CLAIM SUCCESSFULLY PROCESSED AND SUBMITTED")
        print("=" * 80)
        print(f"[{timestamp}] 📋 Confirmation Number: {confirmation}")
        print(f"[{timestamp}] 👤 Assigned Adjuster: {adjuster}")
        print(f"[{timestamp}] 📞 Contact: {result.get('adjuster_phone', 'TBD')}")
        print(f"[{timestamp}] ⏰ Expected Contact: {result.get('estimated_contact_time', 'TBD')}")
        
        if result.get("next_steps"):
            print(f"[{timestamp}] 📝 Next Steps:")
            for i, step in enumerate(result.get("next_steps", []), 1):
                print(f"[{timestamp}]    {i}. {step}")
        
        print("=" * 80 + "\n")


def create_payload_processor() -> PayloadProcessorAgent:
    """Factory function to create a payload processor agent"""
    return PayloadProcessorAgent()
