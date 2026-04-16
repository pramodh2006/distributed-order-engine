import os
import json
import boto3
import time
from dotenv import load_dotenv

load_dotenv()

# Initialize the SQS client exactly like the API
sqs = boto3.client(
    'sqs',
    region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
    endpoint_url=os.getenv('AWS_ENDPOINT_URL', 'http://127.0.0.1:4566'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
)

QUEUE_URL = os.getenv('SQS_QUEUE_URL')

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
                
                # Simulate heavy processing (like checking inventory or charging a credit card)
                time.sleep(2)
                
                # Delete the message so it doesn't get processed again
                sqs.delete_message(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=message['ReceiptHandle']
                )
                print(f"✅ Order {order_data['order_id']} finished and removed from queue!")

        except Exception as e:
            print(f"Worker Error: {e}")
            time.sleep(5) # Pause briefly before trying again

if __name__ == "__main__":
    poll_queue()