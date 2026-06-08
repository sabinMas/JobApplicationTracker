FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install
COPY backend/requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy application code
COPY backend/app ${LAMBDA_TASK_ROOT}/app
COPY backend/lambda_handler.py ${LAMBDA_TASK_ROOT}/

# Set the Lambda handler
CMD ["lambda_handler.handler"]
