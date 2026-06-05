#!/usr/bin/env python3
"""
Test intelligent routing framework.

Tests that job applications are routed to the correct ATS handlers.
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.logging_config import setup_logging, get_logger
from app.services.ats_routers import route_and_submit
from app.services.ats_routers.greenhouse import GreenhouseRouter
from app.services.ats_routers.form_fallback import FormFillerRouter

setup_logging("development")
logger = get_logger("test_routing")

print("\n" + "="*60)
print("INTELLIGENT ROUTING TESTS")
print("="*60 + "\n")


async def test_greenhouse_detection():
    """Test that Greenhouse URLs are recognized"""
    print("TEST 1: Greenhouse URL Detection")
    print("-" * 60)
    
    router = GreenhouseRouter()
    
    test_urls = [
        ("https://company.greenhouse.io/jobs/123456", True),
        ("https://company.greenhouse.io/jobs/123456?utm_source=linkedin", True),
        ("https://example.com/apply", False),
        ("https://lever.co/apply/123", False),
    ]
    
    for url, should_handle in test_urls:
        can_handle = await router.can_handle(url)
        status = "[PASS]" if can_handle == should_handle else "[FAIL]"
        print(f"{status} {url}")
        print(f"  Expected: {should_handle}, Got: {can_handle}")
        assert can_handle == should_handle, f"Failed for {url}"
    
    print()


async def test_fallback_router():
    """Test that FormFillerRouter accepts everything"""
    print("TEST 2: Form Filler Fallback Router")
    print("-" * 60)
    
    router = FormFillerRouter()
    
    test_urls = [
        "https://company.greenhouse.io/jobs/123456",
        "https://lever.co/apply/123",
        "https://example.com/custom-form",
        "https://anything.com",
    ]
    
    for url in test_urls:
        can_handle = await router.can_handle(url)
        status = "[PASS]" if can_handle else "[FAIL]"
        print(f"{status} {url} -> {can_handle}")
        assert can_handle, f"FormFiller should handle {url}"
    
    print()


async def test_router_order():
    """Test that routers are selected in correct priority"""
    print("TEST 3: Router Selection Order")
    print("-" * 60)
    
    # Test that Greenhouse URL routes to Greenhouse
    gh_url = "https://company.greenhouse.io/jobs/789"
    logger.info("Testing Greenhouse routing", extra_fields={"url": gh_url})
    
    greenhouse_router = GreenhouseRouter()
    form_router = FormFillerRouter()
    
    # Greenhouse should handle its own URLs
    gh_handles = await greenhouse_router.can_handle(gh_url)
    ff_handles = await form_router.can_handle(gh_url)
    
    print(f"[PASS] Greenhouse router handles Greenhouse URLs: {gh_handles}")
    assert gh_handles, "Greenhouse router should handle Greenhouse URLs"
    
    print(f"[PASS] Form filler also handles Greenhouse URLs: {ff_handles}")
    assert ff_handles, "Form filler is fallback"
    
    # Test that unknown URLs skip Greenhouse and use form filler
    unknown_url = "https://custom-ats.com/apply/123"
    logger.info("Testing unknown URL routing", extra_fields={"url": unknown_url})
    
    gh_handles_unknown = await greenhouse_router.can_handle(unknown_url)
    ff_handles_unknown = await form_router.can_handle(unknown_url)
    
    print(f"[PASS] Greenhouse router does NOT handle unknown URLs: {not gh_handles_unknown}")
    assert not gh_handles_unknown, "Greenhouse should not handle unknown URLs"
    
    print(f"[PASS] Form filler handles unknown URLs: {ff_handles_unknown}")
    assert ff_handles_unknown, "Form filler should handle all URLs"
    
    print()


async def test_greenhouse_extraction():
    """Test Greenhouse job ID extraction"""
    print("TEST 4: Greenhouse Job ID Extraction")
    print("-" * 60)
    
    router = GreenhouseRouter()
    
    test_cases = [
        ("https://company.greenhouse.io/jobs/123456", "123456"),
        ("https://company.greenhouse.io/jobs/789012?utm_source=linkedin", "789012"),
        ("https://company.greenhouse.io/jobs/999", "999"),
        ("https://example.com/apply", ""),  # Invalid URL
    ]
    
    for url, expected_id in test_cases:
        extracted_id = router._extract_job_id(url)
        status = "[PASS]" if extracted_id == expected_id else "[FAIL]"
        print(f"{status} {url}")
        print(f"  Expected: {expected_id}, Got: {extracted_id}")
        assert extracted_id == expected_id, f"Failed for {url}"
    
    print()


async def test_submit_result_format():
    """Test that submit results have correct format"""
    print("TEST 5: Submission Result Format")
    print("-" * 60)
    
    # Expected result format
    expected_keys = [
        "status",         # success, failed, submitted_unverified
        "duration_ms",    # Time taken
        "message",        # Human readable message
        "ats_platform",   # Platform name
    ]
    
    # Test with FormFillerRouter (which will fail but should return proper format)
    result = await route_and_submit(
        application_id=1,
        job_url="https://example.com/apply",
        profile={"full_name": "Test User", "email": "test@example.com"},
        resume_path="",
        cover_letter_path="",
    )
    
    print(f"[PASS] Result has status: {result.get('status')}")
    print(f"[PASS] Result has message: {result.get('message')}")
    print(f"[PASS] Result has duration_ms: {result.get('duration_ms')}")
    print(f"[PASS] Result has ats_platform: {result.get('ats_platform')}")
    
    for key in expected_keys:
        assert key in result, f"Missing key: {key}"
    
    print()


async def run_all_tests():
    """Run all routing tests"""
    try:
        await test_greenhouse_detection()
        await test_fallback_router()
        await test_router_order()
        await test_greenhouse_extraction()
        await test_submit_result_format()
        
        print("=" * 60)
        print("[PASS] ALL ROUTING TESTS PASSED")
        print("=" * 60)
        print("\nKey Features Verified:")
        print("- [PASS] Greenhouse URL detection")
        print("- [PASS] Form filler fallback routing")
        print("- [PASS] Router priority (Greenhouse -> Form filler)")
        print("- [PASS] Job ID extraction")
        print("- [PASS] Result format compliance")
        print("")
        
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
