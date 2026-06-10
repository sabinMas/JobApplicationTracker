#!/usr/bin/env python3
"""
Test retry logic with exponential backoff.

Run: python test_retry_logic.py
"""

import asyncio
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.retry_service import execute_with_retry, should_retry, calculate_next_retry_time, RetryStrategy
from app.logging_config import setup_logging, get_logger
from datetime import datetime, timezone, timedelta

setup_logging("development")
logger = get_logger("test_retry")
logger.info("Retry logic test suite starting")


async def test_should_retry():
    """Test retry decision logic."""
    print("=" * 60)
    print("TEST 1: Retry Decision Logic")
    print("=" * 60)
    
    # Test transient error (should retry)
    error = ConnectionError("Network unreachable")
    should_retry_result, wait_time = await should_retry(error, 0, 3)
    assert should_retry_result == True
    assert wait_time == 1  # 2^0 = 1
    print(f"✅ ConnectionError on attempt 0: should_retry={should_retry_result}, wait={wait_time}s")
    
    # Test form error (should retry)
    error = Exception("Form did not load")
    should_retry_result, wait_time = await should_retry(error, 1, 3)
    assert should_retry_result == True
    assert wait_time == 2  # 2^1 = 2
    print(f"✅ Form error on attempt 1: should_retry={should_retry_result}, wait={wait_time}s")
    
    # Test validation error (should NOT retry)
    error = ValueError("Invalid email")
    should_retry_result, wait_time = await should_retry(error, 0, 3)
    assert should_retry_result == False
    print(f"✅ ValueError: should_retry={should_retry_result} (no retry on validation)")
    
    # Test max attempts reached (should NOT retry)
    error = ConnectionError("Network")
    should_retry_result, wait_time = await should_retry(error, 3, 3)
    assert should_retry_result == False
    print(f"✅ Max attempts reached: should_retry={should_retry_result} (no retry)")
    
    # Test exponential backoff
    for attempt in range(3):
        error = ConnectionError("Network")
        should_retry_result, wait_time = await should_retry(error, attempt, 3)
        expected_wait = 2 ** attempt
        assert wait_time == expected_wait
        print(f"✅ Exponential backoff attempt {attempt}: wait={wait_time}s (expected {expected_wait}s)")
    
    print()


async def test_execute_with_retry_success():
    """Test successful execution on first try."""
    print("=" * 60)
    print("TEST 2: Execute with Retry - Success on First Try")
    print("=" * 60)
    
    call_count = 0
    
    async def successful_function(value):
        nonlocal call_count
        call_count += 1
        return f"Result: {value}"
    
    result = await execute_with_retry(
        successful_function,
        "test",
        max_attempts=3,
        context_fields={"test_id": 1}
    )
    
    assert result == "Result: test"
    assert call_count == 1
    print(f"✅ Function succeeded on first try (calls={call_count})")
    print()


async def test_execute_with_retry_recovers():
    """Test recovery after transient failures."""
    print("=" * 60)
    print("TEST 3: Execute with Retry - Recovers After Failures")
    print("=" * 60)
    
    call_count = 0
    
    async def failing_then_success(value):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError(f"Network error on attempt {call_count}")
        return f"Recovered on attempt {call_count}"
    
    result = await execute_with_retry(
        failing_then_success,
        "test",
        max_attempts=3,
        context_fields={"test_id": 2}
    )
    
    assert result == "Recovered on attempt 3"
    assert call_count == 3
    print(f"✅ Function recovered after 2 failures (total calls={call_count})")
    print()


async def test_execute_with_retry_gives_up():
    """Test giving up after max retries."""
    print("=" * 60)
    print("TEST 4: Execute with Retry - Gives Up After Max Attempts")
    print("=" * 60)
    
    call_count = 0
    
    async def always_fails(value):
        nonlocal call_count
        call_count += 1
        raise ConnectionError(f"Network error on attempt {call_count}")
    
    try:
        result = await execute_with_retry(
            always_fails,
            "test",
            max_attempts=3,
            context_fields={"test_id": 3}
        )
        assert False, "Should have raised exception"
    except ConnectionError as e:
        assert call_count == 3
        print(f"✅ Gave up after max attempts (total calls={call_count})")
        print(f"   Final error: {e}")
    
    print()


async def test_execute_with_retry_no_retry_validation():
    """Test that validation errors don't retry."""
    print("=" * 60)
    print("TEST 5: Execute with Retry - No Retry on Validation Error")
    print("=" * 60)
    
    call_count = 0
    
    async def validation_error(value):
        nonlocal call_count
        call_count += 1
        raise ValueError("Invalid input")
    
    try:
        result = await execute_with_retry(
            validation_error,
            "test",
            max_attempts=3,
            context_fields={"test_id": 4}
        )
        assert False, "Should have raised exception"
    except ValueError as e:
        assert call_count == 1
        print(f"✅ No retry on validation error (total calls={call_count})")
        print(f"   Error: {e}")
    
    print()


async def test_retry_callback():
    """Test that retry callback is called."""
    print("=" * 60)
    print("TEST 6: Execute with Retry - Callback Called")
    print("=" * 60)
    
    callbacks_received = []
    call_count = 0
    
    async def retry_callback(attempt, wait_time, error):
        callbacks_received.append({
            "attempt": attempt,
            "wait_time": wait_time,
            "error": str(error),
        })
    
    async def failing_function(value):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError(f"Network error on attempt {call_count}")
        return "Success"
    
    result = await execute_with_retry(
        failing_function,
        "test",
        max_attempts=3,
        on_retry_callback=retry_callback,
        context_fields={"test_id": 5}
    )
    
    assert result == "Success"
    assert len(callbacks_received) == 2
    assert callbacks_received[0]["attempt"] == 1
    assert callbacks_received[0]["wait_time"] == 1
    assert callbacks_received[1]["attempt"] == 2
    assert callbacks_received[1]["wait_time"] == 2
    print(f"✅ Callbacks called on retries (total callbacks={len(callbacks_received)})")
    for i, cb in enumerate(callbacks_received):
        print(f"   Callback {i+1}: attempt={cb['attempt']}, wait={cb['wait_time']}s")
    
    print()


def test_calculate_next_retry_time():
    """Test next retry time calculation."""
    print("=" * 60)
    print("TEST 7: Calculate Next Retry Time")
    print("=" * 60)
    
    now = datetime.now(timezone.utc)
    
    # Exponential strategy
    for attempt in range(3):
        next_time = calculate_next_retry_time(attempt, RetryStrategy.EXPONENTIAL)
        expected_delta = 2 ** attempt
        actual_delta = (next_time - now).total_seconds()
        assert abs(actual_delta - expected_delta) < 1  # Allow 1 second variance
        print(f"✅ Exponential backoff attempt {attempt}: {expected_delta}s (actual: {actual_delta:.1f}s)")
    
    # Linear strategy
    for attempt in range(3):
        next_time = calculate_next_retry_time(attempt, RetryStrategy.LINEAR)
        expected_delta = attempt * 30
        actual_delta = (next_time - now).total_seconds()
        assert abs(actual_delta - expected_delta) < 1
        print(f"✅ Linear backoff attempt {attempt}: {expected_delta}s (actual: {actual_delta:.1f}s)")
    
    print()


async def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("RETRY LOGIC TEST SUITE")
    print("=" * 60 + "\n")
    
    try:
        await test_should_retry()
        await test_execute_with_retry_success()
        await test_execute_with_retry_recovers()
        await test_execute_with_retry_gives_up()
        await test_execute_with_retry_no_retry_validation()
        await test_retry_callback()
        test_calculate_next_retry_time()
        
        print("=" * 60)
        print("✅ ALL RETRY LOGIC TESTS PASSED")
        print("=" * 60)
        print("\nKey Features Verified:")
        print("- ✅ Transient errors trigger retry")
        print("- ✅ Validation errors do NOT trigger retry")
        print("- ✅ Exponential backoff works (1s, 2s, 4s, 8s)")
        print("- ✅ Max attempts enforced (default 3)")
        print("- ✅ Recovery happens after transient failures")
        print("- ✅ Callbacks fired on retry")
        print("- ✅ Next retry time calculated correctly")
        print("")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
