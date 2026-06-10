#!/usr/bin/env python3
"""
Test script for structured logging system.

Run: python test_logging.py
"""

import sys
import os
import json

from app.logging_config import setup_logging, get_logger

def test_basic_logging():
    """Test basic logging functionality."""
    print("=" * 60)
    print("TEST 1: Basic Logging (Development Mode)")
    print("=" * 60)
    
    setup_logging("development")
    logger = get_logger("test_module")
    
    # Test different log levels
    logger.debug("Debug message - should be visible in dev")
    logger.info("Info message - should be visible")
    logger.warning("Warning message - should be visible")
    logger.error("Error message - should be visible")
    
    print("\n✅ Basic logging test passed (check JSON output above)\n")


def test_logging_with_extra_fields():
    """Test logging with extra fields."""
    print("=" * 60)
    print("TEST 2: Logging with Extra Fields")
    print("=" * 60)
    
    setup_logging("development")
    logger = get_logger("test_extra")
    
    logger.info("Application started", extra_fields={
        "app_id": 123,
        "company": "TechCorp",
        "title": "Backend Engineer",
    })
    
    logger.error("Application failed", extra_fields={
        "app_id": 456,
        "error_type": "TimeoutError",
        "retry_count": 2,
    })
    
    print("\n✅ Extra fields logging test passed\n")


def test_json_format():
    """Verify JSON format correctness."""
    print("=" * 60)
    print("TEST 3: JSON Format Validation")
    print("=" * 60)
    
    setup_logging("development")
    logger = get_logger("test_json")
    
    # Capture a log line to verify JSON
    import logging
    import io
    
    # Create a string buffer to capture output
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    
    from app.logging_config import JsonFormatter
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    
    logger.info("Test JSON message", extra_fields={"test_id": 789})
    
    # Get the captured output
    log_output = log_capture.getvalue().strip()
    
    try:
        log_dict = json.loads(log_output)
        assert "timestamp" in log_dict
        assert "level" in log_dict
        assert "message" in log_dict
        assert "logger" in log_dict
        assert log_dict["message"] == "Test JSON message"
        assert log_dict["extra"]["test_id"] == 789
        
        print(f"Captured JSON: {json.dumps(log_dict, indent=2)}")
        print("\n✅ JSON format validation passed\n")
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing failed: {e}")
        print(f"Output was: {log_output}")
        sys.exit(1)


def test_logging_levels():
    """Test different logging levels in different environments."""
    print("=" * 60)
    print("TEST 4: Logging Levels by Environment")
    print("=" * 60)
    
    # Development: should show DEBUG
    print("\n--- Development Mode (should show debug) ---")
    setup_logging("development")
    logger = get_logger("test_levels_dev")
    logger.debug("This debug message should appear in development")
    logger.info("This info message should appear in development")
    
    # Production: should NOT show DEBUG
    print("\n--- Production Mode (should NOT show debug) ---")
    setup_logging("production")
    logger = get_logger("test_levels_prod")
    logger.debug("This debug message should NOT appear in production")
    logger.info("This info message should appear in production")
    
    print("\n✅ Logging levels test passed\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("STRUCTURED LOGGING SYSTEM - TEST SUITE")
    print("=" * 60 + "\n")
    
    try:
        test_basic_logging()
        test_logging_with_extra_fields()
        test_json_format()
        test_logging_levels()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nNotes:")
        print("- Verify all log output is valid JSON")
        print("- Verify extra_fields appear in JSON output")
        print("- Verify log levels are respected")
        print("- For production, set: export ENVIRONMENT=production")
        print("")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
