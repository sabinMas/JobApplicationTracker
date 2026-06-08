"""
AWS Lambda handler for JobApplicationTracker.

Uses Mangum to wrap the FastAPI application for Lambda execution.
Handles API Gateway events (REST API or HTTP API) and Function URLs.

Deployment:
    - Package this file + app/ directory into a Lambda deployment zip
    - Set handler to: lambda_handler.handler
    - Configure environment variables (DATABASE_URL, S3_BUCKET, etc.)
"""

from mangum import Mangum
from app.main import app
import json

# Mangum adapter: converts Lambda events → ASGI → FastAPI
# Supports: API Gateway REST API, HTTP API, ALB, Function URL
handler = Mangum(app, lifespan="auto", api_gateway_base_path="")

# For debugging: log the event structure
def lambda_handler_with_logging(event, context):
    """Wrapper that logs event structure for debugging."""
    try:
        return handler(event, context)
    except Exception as e:
        print(f"Error: {e}")
        print(f"Event type: {type(event)}")
        print(f"Event: {json.dumps(event, default=str)}")
        raise
