import boto3
from botocore.config import Config
import time

def create_local_queue():
    # Adding a custom config with retries and longer timeouts
    my_config = Config(
        retries={'max_attempts': 10, 'mode': 'standard'},
        connect_timeout=5,
        read_timeout=10
    )

    sqs = boto3.client(
        'sqs',
        region_name='us-east-1',
        endpoint_url='http://127.0.0.1:4566',  # Using 127.0.0.1 instead of localhost for Windows
        aws_access_key_id='test',
        aws_secret_access_key='test',
        config=my_config
    )
    
    print("Waiting 5 seconds for LocalStack to fully initialize...")
    time.sleep(5)
    
    print("Creating order-queue in LocalStack...")
    try:
        response = sqs.create_queue(QueueName='order-queue')
        print("Success! Queue URL:")
        print(response.get('QueueUrl'))
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    create_local_queue()