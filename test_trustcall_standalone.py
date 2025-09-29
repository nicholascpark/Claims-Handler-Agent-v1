#!/usr/bin/env python3
"""Standalone test script for trustcall JSON extraction functionality

This script validates that the trustcall operation is functional based on user's spoken input.
It follows the pattern from the trustcall README but uses our AzureChatOpenAI implementation
and Claims Handler Agent schema.

Usage:
    python test_trustcall_standalone.py

Requirements:
    - trustcall package installed
    - langchain-openai package installed  
    - Azure OpenAI credentials configured in .env file
"""

import json
import asyncio
import os
from typing import Dict, Any, List
from datetime import datetime

# Add src to path for imports
import sys
sys.path.append('src')

from src.config.settings import settings, validate_required_settings
from src.agents.trustcall_agent import create_trustcall_agent, TrustcallExtractionResult
from src.schema.simplified_payload import SimplifiedClaim
from src.utils.json_patch import validate_trustcall_availability


class TrustcallStandaloneTest:
    """Standalone test class for trustcall operations"""
    
    def __init__(self):
        self.test_conversations = self._get_test_conversations()
        self.results = []
        
    def _get_test_conversations(self) -> List[Dict[str, Any]]:
        """Get test conversation scenarios"""
        return [
            {
                "name": "Basic Claim Report",
                "user_input": "My name is Nick Park. I ran into Emma Thompson at the park yesterday. Got into a car accident shortly after in Millburn, NJ.",
                "expected_fields": ["insured_name", "incident_location", "incident_description"],
                "existing_data": {}
            },
            {
                "name": "Policy Information Update", 
                "user_input": "My policy number is POL-123456 and you can reach me at 555-0123.",
                "expected_fields": ["policy_number", "insured_phone"],
                "existing_data": {
                    "claim_id": "CL-TEST-001",
                    "insured_name": "Nick Park"
                }
            },
            {
                "name": "Incident Details",
                "user_input": "The accident happened around 2:30 PM when I was making a left turn. The other driver ran a red light.",
                "expected_fields": ["incident_time", "incident_description"],
                "existing_data": {
                    "claim_id": "CL-TEST-002", 
                    "insured_name": "Nick Park",
                    "incident_location": "Millburn, NJ"
                }
            },
            {
                "name": "Vehicle and Injury Information",
                "user_input": "I was driving my 2020 Toyota Camry and the other car was a Ford F-150. Nobody was hurt, thankfully.",
                "expected_fields": ["vehicles_involved", "injuries_reported"],
                "existing_data": {
                    "claim_id": "CL-TEST-003",
                    "insured_name": "Nick Park"
                }
            },
            {
                "name": "Complete Claim Scenario",
                "user_input": "Hi, I need to report an accident. My name is Sarah Johnson, phone 555-9876. Yesterday at 3:15 PM I was rear-ended at the intersection of Main St and Oak Ave in Springfield, IL. I was stopped at a red light when the other driver hit me. I drive a 2019 Honda Civic and they had a 2021 Chevy Malibu. No one was injured but there was significant damage to both vehicles. The police report number is SPR-2025-0925-001.",
                "expected_fields": ["insured_name", "insured_phone", "incident_date", "incident_time", "incident_location", "incident_description", "vehicles_involved", "injuries_reported", "police_report_number"],
                "existing_data": {}
            }
        ]
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all trustcall tests"""
        print("=" * 80)
        print("TRUSTCALL STANDALONE TEST SUITE")
        print("=" * 80)
        print(f"Testing at: {datetime.now().isoformat()}")
        print(f"Azure Endpoint: {settings.AZURE_OPENAI_ENDPOINT}")
        print(f"Deployment: {settings.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME}")
        print()
        
        # Validate prerequisites
        if not await self._validate_prerequisites():
            return {"success": False, "error": "Prerequisites validation failed"}
        
        # Initialize trustcall agent
        try:
            trustcall_agent = create_trustcall_agent()
            print("✅ Trustcall agent initialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize trustcall agent: {e}"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Run individual tests
        test_results = []
        for i, test_case in enumerate(self.test_conversations, 1):
            print(f"\n{'='*20} TEST {i}: {test_case['name']} {'='*20}")
            result = await self._run_single_test(trustcall_agent, test_case)
            test_results.append(result)
            self._print_test_result(result)
        
        # Generate summary
        summary = self._generate_test_summary(test_results)
        self._print_test_summary(summary)
        
        return summary
    
    async def _validate_prerequisites(self) -> bool:
        """Validate that all prerequisites are met"""
        print("🔍 Validating prerequisites...")
        
        # Check environment variables
        try:
            validate_required_settings()
            print("✅ Azure OpenAI settings validated")
        except Exception as e:
            print(f"❌ Missing required settings: {e}")
            return False
        
        # Check trustcall availability
        if not validate_trustcall_availability():
            print("❌ Trustcall not available or not properly installed")
            print("Install with: pip install trustcall langchain-openai")
            return False
        else:
            print("✅ Trustcall availability confirmed")
        
        # Test Azure OpenAI connection
        try:
            from langchain_openai import AzureChatOpenAI
            test_llm = AzureChatOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_CHAT_API_VERSION,
                azure_endpoint=(settings.AZURE_OPENAI_ENDPOINT or "").rstrip('/'),
                azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
                temperature=0.1
            )
            # Quick test call
            response = test_llm.invoke("Test connection")
            print("✅ Azure OpenAI connection verified")
        except Exception as e:
            print(f"❌ Azure OpenAI connection failed: {e}")
            return False
        
        return True
    
    async def _run_single_test(self, agent, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single trustcall test"""
        test_name = test_case["name"]
        user_input = test_case["user_input"]
        expected_fields = test_case["expected_fields"]
        existing_data = test_case["existing_data"].copy()
        
        print(f"📝 Input: {user_input}")
        print(f"📋 Existing data: {json.dumps(existing_data, indent=2)}")
        print(f"🎯 Expected fields: {', '.join(expected_fields)}")
        
        try:
            # Run trustcall extraction
            result = await agent.extract_and_patch_claim_data(
                user_input=user_input,
                existing_data=existing_data,
                conversation_context=f"Test case: {test_name}"
            )
            
            if not result.extraction_successful:
                return {
                    "test_name": test_name,
                    "success": False,
                    "error": result.error_message or "Extraction failed",
                    "result": None
                }
            
            # Validate results
            extracted_fields = []
            updated_data = result.updated_data
            
            for field in expected_fields:
                if field in updated_data and updated_data[field] is not None:
                    extracted_fields.append(field)
            
            success = len(extracted_fields) >= (len(expected_fields) * 0.5)  # At least 50% of expected fields
            
            return {
                "test_name": test_name,
                "success": success,
                "extracted_fields": extracted_fields,
                "expected_fields": expected_fields,
                "patches_applied": result.patches_applied,
                "updated_data": updated_data,
                "field_extraction_rate": len(extracted_fields) / len(expected_fields) if expected_fields else 1.0
            }
            
        except Exception as e:
            return {
                "test_name": test_name,
                "success": False,
                "error": str(e),
                "result": None
            }
    
    def _print_test_result(self, result: Dict[str, Any]) -> None:
        """Print the result of a single test"""
        if result["success"]:
            print("✅ TEST PASSED")
            print(f"📊 Extracted {len(result.get('extracted_fields', []))} of {len(result.get('expected_fields', []))} expected fields")
            print(f"🔧 Applied {len(result.get('patches_applied', []))} patches")
            
            # Show extracted data
            if result.get("updated_data"):
                print("📋 Updated data:")
                print(json.dumps(result["updated_data"], indent=2, ensure_ascii=False))
            
            # Show patches applied
            if result.get("patches_applied"):
                print("🔧 Patches applied:")
                for patch in result["patches_applied"]:
                    op = patch.get("op", "unknown")
                    path = patch.get("path", "unknown")
                    value = patch.get("value", "N/A")
                    print(f"   {op} {path} = {value}")
        else:
            print("❌ TEST FAILED")
            error = result.get("error", "Unknown error")
            print(f"💥 Error: {error}")
    
    def _generate_test_summary(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate overall test summary"""
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        # Calculate average field extraction rate
        extraction_rates = [
            result.get("field_extraction_rate", 0.0) 
            for result in test_results 
            if result["success"]
        ]
        avg_extraction_rate = sum(extraction_rates) / len(extraction_rates) if extraction_rates else 0.0
        
        return {
            "success": passed_tests == total_tests,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "pass_rate": passed_tests / total_tests if total_tests > 0 else 0.0,
            "avg_extraction_rate": avg_extraction_rate,
            "test_results": test_results
        }
    
    def _print_test_summary(self, summary: Dict[str, Any]) -> None:
        """Print the overall test summary"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        total = summary["total_tests"]
        passed = summary["passed_tests"]
        failed = summary["failed_tests"]
        pass_rate = summary["pass_rate"] * 100
        extraction_rate = summary["avg_extraction_rate"] * 100
        
        if summary["success"]:
            print("🎉 ALL TESTS PASSED!")
        else:
            print(f"⚠️  {failed} of {total} tests failed")
        
        print(f"📊 Results: {passed}/{total} passed ({pass_rate:.1f}%)")
        print(f"📈 Average field extraction rate: {extraction_rate:.1f}%")
        
        if failed > 0:
            print("\n❌ Failed tests:")
            for result in summary["test_results"]:
                if not result["success"]:
                    print(f"   • {result['test_name']}: {result.get('error', 'Unknown error')}")
        
        print("\n💡 Integration notes:")
        print("   • All extractions use trustcall with AzureChatOpenAI")
        print("   • No fallback methods are available")
        print("   • JSON patches follow RFC 6902 standard")
        print("   • Field updates trigger callbacks for UI integration")
        
        print("=" * 80)


async def main():
    """Main test execution function"""
    try:
        print("🚀 Starting Trustcall Standalone Test Suite...")
        
        # Run tests
        test_suite = TrustcallStandaloneTest()
        summary = await test_suite.run_all_tests()
        
        # Exit with appropriate code
        if summary["success"]:
            print("\n🎯 All tests completed successfully!")
            exit(0)
        else:
            print(f"\n💥 {summary['failed_tests']} tests failed")
            exit(1)
            
    except KeyboardInterrupt:
        print("\n⚡ Test suite interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        raise


if __name__ == "__main__":
    # Run the test suite
    asyncio.run(main())
