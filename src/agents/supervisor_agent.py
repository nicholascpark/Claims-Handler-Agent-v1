"""Claims Supervisor Agent - Following OpenAI Realtime Agents pattern

This supervisor agent receives conversation history and returns formatted responses
that the junior agent reads verbatim, exactly like the OpenAI implementation.
"""

import json
import os
import asyncio
from threading import Thread
from queue import Queue, Empty
from typing import Dict, List, Any, Optional
from datetime import datetime
from src.config.settings import settings
from src.agents.trustcall_agent import create_trustcall_agent, TrustcallExtractionAgent
from src.prompts import AgentPrompts


class ClaimsSupervisorAgent:
    """
    Expert supervisor agent following OpenAI pattern.
    
    Receives full conversation history, has access to all tools,
    and returns formatted messages that junior agent reads verbatim.
    """
    
    def __init__(self):
        self.instructions = self._get_supervisor_instructions()
        self.tools = self._get_supervisor_tools()
        self.current_claim_data = {}
        self._completion_logged = False
        # Display flag (legacy cache); actual check is dynamic per update
        self._display_json_updates = bool(getattr(settings, "DISPLAY_CLAIM_JSON", False))
        
        # Initialize dedicated trustcall extraction agent
        self.trustcall_agent = create_trustcall_agent(on_field_updated=self._on_field_updated)
        
        # Background processing for non-blocking trustcall updates
        self._input_queue = Queue()
        self._recent_inputs = []  # Keep last N inputs for efficient batch processing
        self._processing_thread = None
        self._is_processing = False
        self._max_recent_inputs = 3  # Only process last 3 inputs for efficiency
        
        # Start background processing thread
        self._start_background_processor()

    def _on_field_updated(self, field_path: str) -> None:
        """Log field-level updates without values. Display logic is separate."""
        try:
            print(f"[CLAIM UPDATE] field updated: {field_path}")
        except Exception:
            pass
    
    def get_current_payload_status(self) -> Dict[str, Any]:
        """Get the latest payload status for --display-json flag (non-blocking)."""
        try:
            return {
                "timestamp": datetime.now().isoformat(),
                "claim_data": self.current_claim_data.copy(),
                "processing_status": "processing" if self._is_processing else "idle",
                "pending_inputs": self._input_queue.qsize(),
                "recent_inputs_count": len(self._recent_inputs)
            }
        except Exception:
            return {
                "timestamp": datetime.now().isoformat(),
                "error": "Failed to get payload status",
                "processing_status": "error"
            }
    
    def display_json_if_enabled(self) -> None:
        """Display JSON only if flag is enabled - separate from processing."""
        try:
            show_json = (
                self._display_json_updates
                or bool(getattr(settings, "DISPLAY_CLAIM_JSON", False))
                or os.getenv("DISPLAY_CLAIM_JSON", "").lower() == "true"
            )
            if show_json:
                status = self.get_current_payload_status()
                print("🧾 Current Claim JSON:")
                print(json.dumps(status["claim_data"], indent=2, ensure_ascii=False))
                print(f"📊 Status: {status['processing_status']} | Pending: {status['pending_inputs']}")
        except Exception:
            pass
    
    def _start_background_processor(self) -> None:
        """Start the background thread for processing trustcall updates."""
        if self._processing_thread is None or not self._processing_thread.is_alive():
            self._processing_thread = Thread(target=self._background_processor, daemon=True)
            self._processing_thread.start()
    
    def _background_processor(self) -> None:
        """Background thread that processes trustcall updates without blocking conversation."""
        while True:
            try:
                # Wait for new input with timeout
                try:
                    user_input = self._input_queue.get(timeout=1.0)  # 1 second timeout
                    
                    # Add to recent inputs for efficient batching
                    self._recent_inputs.append(user_input)
                    
                    # Keep only last N inputs for efficiency
                    if len(self._recent_inputs) > self._max_recent_inputs:
                        self._recent_inputs = self._recent_inputs[-self._max_recent_inputs:]
                    
                    # Process the recent inputs batch
                    self._process_recent_inputs_batch()
                    
                    self._input_queue.task_done()
                    
                except Empty:
                    # No new inputs, continue loop
                    continue
                    
            except Exception as e:
                print(f"⚠️  Background processor error: {str(e)}")
                continue
    
    def _process_recent_inputs_batch(self) -> None:
        """Process recent inputs as a batch for efficient trustcall operation."""
        if not self._recent_inputs:
            return
            
        try:
            self._is_processing = True
            
            # Combine recent inputs into a single context for efficiency
            combined_input = " ".join(self._recent_inputs[-self._max_recent_inputs:])
            
            # Create async loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Process with trustcall agent
                result = loop.run_until_complete(
                    self.trustcall_agent.extract_and_patch_claim_data(
                        user_input=combined_input,
                        existing_data=self.current_claim_data,
                        conversation_context=f"Batch of {len(self._recent_inputs)} recent inputs"
                    )
                )
                
                if result.extraction_successful:
                    # Update current claim data with extracted information
                    self.current_claim_data.update(result.updated_data)
                    # Field update callbacks are triggered automatically by trustcall agent
                else:
                    if result.error_message:
                        print(f"⚠️  Background trustcall warning: {result.error_message}")
                        
            finally:
                loop.close()
                
        except Exception as e:
            print(f"⚠️  Batch processing error: {str(e)}")
        finally:
            self._is_processing = False
    
    def _get_supervisor_instructions(self) -> str:
        """Get supervisor instructions from centralized prompts"""
        return AgentPrompts.get_supervisor_instructions()

    def _get_supervisor_tools(self) -> List[Dict[str, Any]]:
        """Get simplified supervisor tool definitions - trustcall handles the complexity"""
        return [
            {
                "type": "function",
                "name": "checkClaimCompleteness",
                "description": "Check if trustcall has extracted enough information to process the claim.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            },
            {
                "type": "function",
                "name": "submitCompletedClaim",
                "description": "Submit the claim for final processing when all information has been collected.",
                "parameters": {
                    "type": "object", 
                    "properties": {},
                    "additionalProperties": False
                }
            }
        ]

    async def get_next_response(self, conversation_history: List[Dict[str, Any]], relevant_context: str) -> Dict[str, Any]:
        """
        Get next response from supervisor following OpenAI pattern.
        
        Args:
            conversation_history: Full conversation history
            relevant_context: Key context from junior agent about user's message
            
        Returns:
            Response dictionary with message for junior agent to read verbatim
        """
        
        # Analyze the conversation and context
        analysis = self._analyze_conversation(conversation_history, relevant_context)
        
        # Determine if we need to call tools
        if analysis["needs_tool_call"]:
            return await self._handle_with_tools(analysis)
        else:
            return self._generate_direct_response(analysis)

    def _analyze_conversation(self, conversation_history: List[Dict[str, Any]], relevant_context: str) -> Dict[str, Any]:
        """Simplified conversation analysis - trustcall handles the complexity"""
        
        # Get recent user input for context
        recent_messages = conversation_history[-3:] if len(conversation_history) > 3 else conversation_history
        user_messages = [msg for msg in recent_messages if msg.get("role") == "user"]
        latest_user_input = user_messages[-1]["content"] if user_messages else ""
        
        analysis = {
            "intent": "continue_conversation",
            "needs_tool_call": False,
            "tool_to_call": None,
            "latest_user_input": latest_user_input,
            "context": relevant_context
        }
        
        # Queue user input for background trustcall processing (non-blocking)
        if latest_user_input:
            try:
                self._queue_input_for_processing(latest_user_input)
            except Exception:
                pass

        # Simple intent detection - let trustcall handle field specifics
        context_lower = relevant_context.lower()
        
        # Check if this seems like a new claim starting
        if any(keyword in context_lower for keyword in ["accident", "collision", "report", "incident", "claim"]):
            if not self._has_basic_claim_info():
                analysis["intent"] = "start_claim" 
                return analysis
        
        # Check if claim might be complete (let tool decide)
        if self._has_basic_claim_info():
            analysis["intent"] = "check_completeness"
            analysis["needs_tool_call"] = True
            analysis["tool_to_call"] = "checkClaimCompleteness"
            return analysis
        
        return analysis

    def _has_basic_claim_info(self) -> bool:
        """Simple check if we have any claim data - trustcall handles validation"""
        return bool(self.current_claim_data and len(self.current_claim_data) > 0)

    async def _handle_with_tools(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Handle simplified tool calls - trustcall handles complexity"""
        
        tool_name = analysis["tool_to_call"]
        
        try:
            if tool_name == "checkClaimCompleteness":
                return await self._check_claim_completeness(analysis)
            elif tool_name == "submitCompletedClaim":
                return await self._submit_completed_claim(analysis)
            
            # Fallback if unknown tool
            return self._generate_direct_response(analysis)
            
        except Exception as e:
            return {
                "message": "I'm having trouble processing that information. Let me connect you with a specialist who can help.",
                "error": str(e)
            }

    async def _check_claim_completeness(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Check if trustcall has collected enough information"""
        try:
            # Use trustcall's built-in validation via schema
            validation_result = self.trustcall_agent.validate_extraction_completeness(self.current_claim_data)
            
            if validation_result.get("is_complete"):
                if not self._completion_logged:
                    self._log_completion_banner()
                    self._completion_logged = True
                
                return {
                    "message": "Thank you for providing all that information. I have everything needed for your claim. I'm submitting this now.",
                    "needs_submission": True
                }
            else:
                missing_count = len(validation_result.get("missing_fields", []))
                return {
                    "message": f"I still need a few more details to complete your claim. Can you tell me more about what happened?",
                    "missing_fields": missing_count
                }
                
        except Exception as e:
            return {
                "message": "Let's continue gathering your information. Can you tell me more about the incident?",
                "error": str(e)
            }

    async def _submit_completed_claim(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Submit completed claim for processing with enhanced response"""
        try:
            from src.agents.payload_processor import create_payload_processor
            from src.schema.simplified_payload import PropertyClaim
            
            # Create property claim from current data (handles nested structure)
            property_claim = PropertyClaim(**self.current_claim_data)
            processor = create_payload_processor()
            delegation_result = processor.process_claim_payload(property_claim, "supervisor")
            
            if delegation_result.get("status") == "completed":
                confirmation = delegation_result.get('confirmation_number', 'pending')
                adjuster_name = delegation_result.get('adjuster_name', 'your assigned adjuster')
                adjuster_phone = delegation_result.get('adjuster_phone', 'the number on file')
                contact_time = delegation_result.get('estimated_contact_time', '24 hours')
                
                # Enhanced success message with specific details
                message = f"Perfect! Your claim has been successfully submitted. Your confirmation number is {confirmation}. {adjuster_name} will be contacting you at {contact_time} at {adjuster_phone}. You'll also receive an email confirmation within 30 minutes."
                
                return {
                    "message": message,
                    "confirmation_number": confirmation,
                    "submission_successful": True,
                    "next_steps": delegation_result.get("next_steps", [])
                }
            else:
                # Handle failed submission
                errors = delegation_result.get("errors", ["Unknown processing error"])
                return {
                    "message": "I have all your information, but I'm experiencing a technical issue with the submission. Let me connect you with a specialist who can complete this for you right away.",
                    "submission_successful": False,
                    "technical_issue": True,
                    "errors": errors
                }
            
        except Exception as e:
            return {
                "message": "I have all your information but I'm having trouble with the final submission. I'll connect you with a specialist to complete this right away.",
                "submission_successful": False,
                "error": str(e)
            }

    # Removed _format_tool_response - simplified tools return ready messages

    def _generate_direct_response(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate direct response - simplified and schema-agnostic"""
        
        intent = analysis.get("intent", "continue_conversation")
        context_lower = analysis["context"].lower()
        
        # Simple intent-based responses - no hardcoded fields
        if intent == "start_claim":
            message = "I'm sorry to hear about your incident. I'll help you report this claim right away. Let's start with your full name and the best phone number to reach you, then I'll need to know what happened."
        elif "how long" in context_lower:
            message = "Claim processing typically takes 3-5 business days once we have all the required information."
        elif "what do you need" in context_lower or "what information" in context_lower:
            message = "I'll need some basic information about you and what happened. Can you tell me your name and describe the incident?"
        elif "deductible" in context_lower or "coverage" in context_lower:
            message = "I can help with coverage questions once I have your claim details. Let's get the incident information first."
        else:
            message = "I'm here to help with your claim. Can you tell me more about what happened?"
        
        return {
            "message": message,
            "tool_call_made": None
        }

    # Helper methods - simplified, trustcall handles complexity

    def _queue_input_for_processing(self, text: str) -> None:
        """Queue user input for background trustcall processing (non-blocking)."""
        try:
            # Add input to queue for background processing
            self._input_queue.put_nowait(text)
        except Exception as e:
            print(f"⚠️  Input queuing error: {str(e)}")
    
    def force_process_pending_inputs(self) -> bool:
        """Force process any pending inputs synchronously (use sparingly)."""
        try:
            # Process any remaining inputs in queue immediately
            pending_inputs = []
            while not self._input_queue.empty():
                try:
                    pending_inputs.append(self._input_queue.get_nowait())
                except Empty:
                    break
            
            if pending_inputs:
                # Add to recent inputs
                self._recent_inputs.extend(pending_inputs)
                if len(self._recent_inputs) > self._max_recent_inputs:
                    self._recent_inputs = self._recent_inputs[-self._max_recent_inputs:]
                
                # Process synchronously
                self._process_recent_inputs_batch()
                return True
            return False
            
        except Exception as e:
            print(f"⚠️  Force processing error: {str(e)}")
            return False

    def _log_completion_banner(self) -> None:
        """Print a prominent banner indicating completion of required info."""
        try:
            line = "=" * 80
            msg = "ALL REQUIRED CLAIM INFORMATION HAS BEEN COLLECTED"
            print(line)
            print(f"{msg}")
            print(line)
        except Exception:
            pass

    # Removed apply_claim_patches - trustcall handles all patching

    def update_from_user_text(self, text: str) -> None:
        """Update claim state using trustcall-based patches from user text without validation gates."""
        try:
            self._queue_input_for_processing(text)
        except Exception:
            # Never let logging or extraction failures break conversation
            pass


def create_supervisor_agent() -> ClaimsSupervisorAgent:
    """Factory function to create supervisor agent"""
    return ClaimsSupervisorAgent()

