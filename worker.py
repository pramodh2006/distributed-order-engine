import os
import json
import boto3
import time
import redis
from dotenv import load_dotenv

from database import SessionLocal, Order, init_db

load_dotenv()

redis_client = redis.Redis(host="localhost", port=6379)

# Initialize the SQS client exactly like the API
sqs = boto3.client(
    'sqs',
    region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
    endpoint_url=os.getenv('AWS_ENDPOINT_URL', 'http://127.0.0.1:4566'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
)

# Grab the queue URL from .env, but force it to use 127.0.0.1 so Windows doesn't block it
raw_queue_url = os.getenv('SQS_QUEUE_URL')
if raw_queue_url and "localhost.localstack.cloud" in raw_queue_url:
    QUEUE_URL = raw_queue_url.replace("sqs.us-east-1.localhost.localstack.cloud", "127.0.0.1")
else:
    QUEUE_URL = raw_queue_url


def poll_queue():
    print(f"Worker started. Listening to {QUEUE_URL}...")

    while True:
        try:
            # Long Polling (WaitTimeSeconds=20)
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20
            )

            messages = response.get('Messages', [])

            if not messages:
                print("No orders right now. Still listening...")
                continue

            for message in messages:
                # Parse the JSON order data
                order_data = json.loads(message['Body'])
                print(f"\n📦 PROCESSING NEW ORDER:")
                print(f"Order ID: {order_data['order_id']}")
                print(f"User {order_data['user_id']} bought {order_data['quantity']}x {order_data['item_id']}")

                # Simulate heavy processing
                time.sleep(2)

                item_id = order_data['item_id']
                qty = order_data['quantity']
                inv_key = f"inventory:{item_id}"
                new_stock = redis_client.decrby(inv_key, qty)

                if new_stock < 0:
                    print(f"Out of stock for item {item_id} (would go to {new_stock}). Order cancelled.")
                    redis_client.incrby(inv_key, qty)
                    order_status = "Failed"
                else:
                    order_status = "Completed"

                # 2. Save the order to PostgreSQL
                db = SessionLocal()
                try:
                    new_order = Order(
                        order_id=order_data['order_id'],
                        user_id=order_data['user_id'],
                        item_id=order_data['item_id'],
                        quantity=order_data['quantity'],
                        status=order_status
                    )
                    db.add(new_order)
                    db.commit()
                    print(f"💾 Saved Order {order_data['order_id']} to PostgreSQL database!")
                except Exception as db_err:
                    print(f"Database Error: {db_err}")
                    db.rollback()
                finally:
                    db.close()

                # 3. Delete the message so it doesn't get processed again
                sqs.delete_message(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=message['ReceiptHandle']
                )
                print(f"✅ Order {order_data['order_id']} finished and removed from queue!")

        except Exception as e:
            print(f"Worker Error: {e}")
            time.sleep(5)  # Pause briefly before trying again


if __name__ == "__main__":
    init_db()
    poll_queue()
