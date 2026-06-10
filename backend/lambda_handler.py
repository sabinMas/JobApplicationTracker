"""
AWS Lambda handler — wraps the FastAPI app with Mangum.

Mangum translates API Gateway HTTP API (v2) events into ASGI calls
that FastAPI understands, and returns proper Lambda responses.

Deployed via Dockerfile.lambda → ECR → Lambda function URL or API Gateway.
"""

from mangum import Mangum

from app.main import app

# Mangum handles API Gateway HTTP API v2 (payload format 2.0) by default.
# lifespan="off" prevents Mangum from running FastAPI's lifespan events on
# every cold start — the Lambda initializes quickly without them.
handler = Mangum(app, lifespan="off")
