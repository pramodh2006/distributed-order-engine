import os
import json
import uuid
import boto3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

app = FastAPI(title="Distributed Order Engine")

class OrderRequest(BaseModel):
    user_id: str
    item_id: str
    quantity: int

# Initialize the SQS client
sqs = boto3.client(
    'sqs',
    region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
    endpoint_url=os.getenv('AWS_ENDPOINT_URL', 'http://127.0.0.1:4566'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
)

# --- THE FIX IS HERE ---
raw_queue_url = os.getenv('SQS_QUEUE_URL')
if raw_queue_url and "localhost.localstack.cloud" in raw_queue_url:
    QUEUE_URL = raw_queue_url.replace("sqs.us-east-1.localhost.localstack.cloud", "127.0.0.1")
else:
    QUEUE_URL = raw_queue_url

@app.post("/checkout", status_code=202)
async def process_checkout(order: OrderRequest):
    try:
        order_id = str(uuid.uuid4())
        
        # Package the order data
        payload = {
            "order_id": order_id,
            "user_id": order.user_id,
            "item_id": order.item_id,
            "quantity": order.quantity
        }

        # Send it to SQS!
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(payload)
        )

        return {
            "message": "Order received and queued for processing",
            "order_id": order_id,
            "status": "Processing"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}