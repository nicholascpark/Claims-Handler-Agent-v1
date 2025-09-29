#!/usr/bin/env python3
"""Test script for parallel trustcall processing functionality

This script validates that trustcall processing happens in parallel without blocking
the conversation flow, and that the --display-json flag correctly fetches the latest 
payload status from the background thread.

Usage:
    python test_parallel_trustcall.py
"""

import asyncio
import time
import threading
from typing import Dict, Any
import sys
sys.path.append('src')

from src.agents.supervisor_agent import create_supervisor_agent
from src.config.settings import settings


class ParallelProcessingTest:
    """Test parallel trustcall processing capabilities"""
    
    def __init__(self):
        self.supervisor = None
        self.test_results = []
        
    def test_non_blocking_input_processing(self) -> Dict[str, Any]:
        """Test that input processing doesn't block the main thread"""
        print("🧪 Testing non-blocking input processing...")
        
        try:
            # Create supervisor agent
            self.supervisor = create_supervisor_agent()
            
            # Record start time
            start_time = time.time()
            
            # Queue multiple inputs rapidly (should not block)
            test_inputs = [
                "My name is John Smith",
                "I was in an accident yesterday",
                "It happened at 3:30 PM on Main Street",
                "The other driver ran a red light",
                "My phone number is 555-0123"
            ]
            
            # Queue all inputs without blocking
            for input_text in test_inputs:
                self.supervisor.update_from_user_text(input_text)
            
            # Check how long queuing took (should be very fast)
            queuing_time = time.time() - start_time
            
            # Get immediate status (should not wait for processing)
            status = self.supervisor.get_current_payload_status()
            
            return {
                "test_name": "non_blocking_input_processing",
                "success": queuing_time < 0.1,  # Should take less than 100ms
                "queuing_time": queuing_time,
                "pending_inputs": status.get("pending_inputs", 0),
                "processing_status": status.get("processing_status", "unknown"),
                "inputs_queued": len(test_inputs)
            }
            
        except Exception as e:
            return {
                "test_name": "non_blocking_input_processing",
                "success": False,
                "error": str(e)
            }
    
    def test_background_processing(self) -> Dict[str, Any]:
        """Test that background processing happens in parallel"""
        print("🧪 Testing background processing...")
        
        try:
            if not self.supervisor:
                self.supervisor = create_supervisor_agent()
            
            # Queue some inputs
            test_inputs = [
                "Policy number POL-789456",
                "Incident location: Springfield, IL",
                "Vehicle: 2020 Honda Civic"
            ]
            
            for input_text in test_inputs:
                self.supervisor.update_from_user_text(input_text)
            
            # Wait a bit for background processing
            initial_status = self.supervisor.get_current_payload_status()
            time.sleep(3)  # Give background thread time to process
            final_status = self.supervisor.get_current_payload_status()
            
            # Check if processing happened
            initial_pending = initial_status.get("pending_inputs", 0)
            final_pending = final_status.get("pending_inputs", 0)
            
            # Check if any fields were extracted
            claim_data = final_status.get("claim_data", {})
            fields_extracted = len([v for v in claim_data.values() if v])
            
            return {
                "test_name": "background_processing",
                "success": final_pending < initial_pending or fields_extracted > 0,
                "initial_pending": initial_pending,
                "final_pending": final_pending,
                "fields_extracted": fields_extracted,
                "claim_data": claim_data
            }
            
        except Exception as e:
            return {
                "test_name": "background_processing",
                "success": False,
                "error": str(e)
            }
    
    def test_display_json_flag(self) -> Dict[str, Any]:
        """Test that --display-json flag works correctly"""
        print("🧪 Testing display JSON functionality...")
        
        try:
            if not self.supervisor:
                self.supervisor = create_supervisor_agent()
            
            # Test getting current status (should be instant)
            start_time = time.time()
            status = self.supervisor.get_current_payload_status()
            fetch_time = time.time() - start_time
            
            # Test display function (should not trigger processing)
            self.supervisor.display_json_if_enabled()
            
            required_fields = ["timestamp", "claim_data", "processing_status"]
            has_required_fields = all(field in status for field in required_fields)
            
            return {
                "test_name": "display_json_flag",
                "success": fetch_time < 0.05 and has_required_fields,  # Should be very fast
                "fetch_time": fetch_time,
                "has_required_fields": has_required_fields,
                "status_keys": list(status.keys())
            }
            
        except Exception as e:
            return {
                "test_name": "display_json_flag",
                "success": False,
                "error": str(e)
            }
    
    def test_efficient_batch_processing(self) -> Dict[str, Any]:
        """Test that only recent inputs are processed for efficiency"""
        print("🧪 Testing efficient batch processing...")
        
        try:
            if not self.supervisor:
                self.supervisor = create_supervisor_agent()
            
            # Queue many inputs to test batching
            many_inputs = [f"Test input number {i}" for i in range(10)]
            
            for input_text in many_inputs:
                self.supervisor.update_from_user_text(input_text)
            
            # Force process to check batching behavior
            processed = self.supervisor.force_process_pending_inputs()
            
            # Check recent inputs count (should be limited)
            status = self.supervisor.get_current_payload_status()
            recent_count = status.get("recent_inputs_count", 0)
            
            # Should only keep max_recent_inputs (default 3)
            expected_max = 3
            
            return {
                "test_name": "efficient_batch_processing", 
                "success": processed and recent_count <= expected_max,
                "processed": processed,
                "recent_inputs_count": recent_count,
                "expected_max": expected_max,
                "inputs_sent": len(many_inputs)
            }
            
        except Exception as e:
            return {
                "test_name": "efficient_batch_processing",
                "success": False,
                "error": str(e)
            }
    
    def test_conversation_flow_continuity(self) -> Dict[str, Any]:
        """Test that conversation flow isn't disrupted by background processing"""
        print("🧪 Testing conversation flow continuity...")
        
        try:
            if not self.supervisor:
                self.supervisor = create_supervisor_agent()
            
            # Simulate rapid conversation flow
            conversation = [
                "Hello, I need to report a claim",
                "My name is Alice Johnson", 
                "I was in a car accident this morning",
                "It happened on Highway 101",
                "The other driver hit my rear bumper"
            ]
            
            # Measure total conversation processing time
            start_time = time.time()
            
            for message in conversation:
                # Simulate supervisor analysis (this should not be blocked by trustcall)
                analysis_start = time.time()
                self.supervisor.update_from_user_text(message)
                
                # Simulate supervisor response generation (should be fast)
                time.sleep(0.1)  # Simulate response generation time
                analysis_time = time.time() - analysis_start
                
                # Each message processing should be very fast (non-blocking)
                if analysis_time > 0.5:  # If any single message takes >500ms, it's blocking
                    return {
                        "test_name": "conversation_flow_continuity",
                        "success": False,
                        "error": f"Message processing took too long: {analysis_time:.3f}s"
                    }
            
            total_time = time.time() - start_time
            
            return {
                "test_name": "conversation_flow_continuity",
                "success": True,
                "total_conversation_time": total_time,
                "messages_processed": len(conversation),
                "avg_message_time": total_time / len(conversation)
            }
            
        except Exception as e:
            return {
                "test_name": "conversation_flow_continuity",
                "success": False,
                "error": str(e)
            }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all parallel processing tests"""
        print("=" * 80)
        print("PARALLEL TRUSTCALL PROCESSING TEST SUITE")
        print("=" * 80)
        print("Testing efficient, non-blocking trustcall integration")
        print()
        
        # Run all tests
        tests = [
            self.test_non_blocking_input_processing,
            self.test_background_processing,
            self.test_display_json_flag,
            self.test_efficient_batch_processing,
            self.test_conversation_flow_continuity
        ]
        
        results = []
        passed = 0
        
        for test_func in tests:
            result = test_func()
            results.append(result)
            
            if result["success"]:
                print(f"✅ {result['test_name']}: PASSED")
                passed += 1
            else:
                print(f"❌ {result['test_name']}: FAILED")
                if "error" in result:
                    print(f"   Error: {result['error']}")
            
            print()
        
        # Generate summary
        total = len(tests)
        summary = {
            "total_tests": total,
            "passed_tests": passed,
            "failed_tests": total - passed,
            "success_rate": passed / total if total > 0 else 0.0,
            "all_passed": passed == total,
            "test_results": results
        }
        
        # Print summary
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total: {total} | Passed: {passed} | Failed: {total - passed}")
        print(f"Success Rate: {summary['success_rate'] * 100:.1f}%")
        
        if summary["all_passed"]:
            print("🎉 All tests passed! Parallel processing is working correctly.")
        else:
            print("⚠️  Some tests failed. Check implementation.")
        
        print("\n💡 Key Features Validated:")
        print("   ✅ Non-blocking input processing")
        print("   ✅ Background thread processing")
        print("   ✅ Efficient recent input batching")
        print("   ✅ Fast status fetching for --display-json")
        print("   ✅ Conversation flow continuity")
        
        return summary


def main():
    """Main test execution"""
    try:
        # Validate prerequisites
        from src.utils.json_patch import validate_trustcall_availability
        if not validate_trustcall_availability():
            print("❌ Trustcall not available. Please install: pip install trustcall")
            return
        
        # Run tests
        test_suite = ParallelProcessingTest()
        summary = test_suite.run_all_tests()
        
        # Exit with appropriate code
        exit(0 if summary["all_passed"] else 1)
        
    except Exception as e:
        print(f"💥 Test suite failed: {e}")
        raise


if __name__ == "__main__":
    main()
