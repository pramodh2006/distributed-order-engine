import json
import uuid

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Distributed Order Engine")

QUEUE_NAME = "order-queue"

_cached_sqs = None


def _get_sqs():
    global _cached_sqs
    if _cached_sqs is None:
        sqs = boto3.client("sqs")
        url = sqs.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"]
        _cached_sqs = (sqs, url)
    return _cached_sqs


# This defines what the JSON payload should look like
class OrderRequest(BaseModel):
    user_id: str
    item_id: str
    quantity: int


@app.post("/checkout", status_code=202)
async def process_checkout(order: OrderRequest):
    order_id = str(uuid.uuid4())
    payload = {
        "order_id": order_id,
        "user_id": order.user_id,
        "item_id": order.item_id,
        "quantity": order.quantity,
    }

    try:
        sqs, queue_url = _get_sqs()
        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(payload))
    except ClientError as e:
        err = e.response.get("Error", {})
        raise HTTPException(
            status_code=502,
            detail=f"SQS error: {err.get('Code', 'Unknown')} — {err.get('Message', str(e))}",
        )
    except BotoCoreError as e:
        raise HTTPException(status_code=503, detail=f"AWS connectivity error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "message": "Order received and queued for processing",
        "order_id": order_id,
        "status": "Processing",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
