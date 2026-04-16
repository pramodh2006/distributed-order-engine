"""
Standalone worker: long-polls order-queue, prints each order, then deletes the message.
Requires AWS credentials and permission on the queue (same as the API).
"""

import json
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError

QUEUE_NAME = "order-queue"
WAIT_TIME_SECONDS = 20


def main():
    sqs = boto3.client("sqs")
    try:
        queue_url = sqs.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"]
    except ClientError as e:
        print(f"Failed to resolve queue URL: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Polling '{QUEUE_NAME}' (WaitTimeSeconds={WAIT_TIME_SECONDS}). Ctrl+C to stop.\n")

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=WAIT_TIME_SECONDS,
                AttributeNames=["All"],
 )
            for message in response.get("Messages", []):
                body = message.get("Body", "")
                try:
                    data = json.loads(body)
                    print("Order details:")
                    print(json.dumps(data, indent=2))
                except json.JSONDecodeError:
                    print("Order details (non-JSON body):")
                    print(body)
                print("---")

                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=message["ReceiptHandle"],
                )
        except KeyboardInterrupt:
            print("\nWorker stopped.")
            break
        except (ClientError, BotoCoreError) as e:
            print(f"SQS error (will retry): {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
