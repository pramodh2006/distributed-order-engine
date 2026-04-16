from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid

app = FastAPI(title="Distributed Order Engine")

# This defines what the JSON payload should look like
class OrderRequest(BaseModel):
    user_id: str
    item_id: str
    quantity: int

@app.post("/checkout", status_code=202)
async def process_checkout(order: OrderRequest):
    try:
        # Generate a unique order ID
        order_id = str(uuid.uuid4())
        
        # We will add AWS SQS logic here in the next step!
        
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