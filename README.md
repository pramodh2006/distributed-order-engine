# 🛒 Distributed Order Processing Engine
*An event-driven, cloud-native microservices architecture designed to handle high-throughput e-commerce checkouts.*

![Status](https://img.shields.io/badge/Status-Active_Development-brightgreen)
![Architecture](https://img.shields.io/badge/Architecture-Event--Driven-blue)
![Stack](https://img.shields.io/badge/Stack-Python_|_FastAPI_|_AWS_SQS-orange)

## 🎯 The Problem
Standard REST APIs often fail under sudden traffic spikes (e.g., Flash Sales, Prime Day) because the database locks up under heavy concurrent write loads. 

## 💡 The Solution
This project completely decouples the incoming web request from the backend database processing using an **Event-Driven Architecture**. 
1. The FastAPI endpoint receives an order and immediately pushes it to an **AWS SQS** message queue, returning a fast `202 Accepted` response to the user.
2. Horizontal backend **Worker Nodes** use long-polling to asynchronously pull messages from the queue, validate inventory, and securely process the orders at their own pace without overwhelming the system.

## 🏗️ Architecture & Tech Stack (In Progress)
- **API Gateway:** FastAPI / Python
- **Message Broker:** AWS SQS (Simple Queue Service) via `boto3`
- **Compute:** Decoupled Worker Daemon
- **Infrastructure Emulation:** LocalStack / Docker

## 🚀 Current Features
- [x] **Asynchronous Order Ingestion:** Non-blocking `/checkout` API endpoint.
- [x] **AWS SQS Integration:** Producer/Consumer model using standard queues.
- [x] **Long-Polling Workers:** Optimized `WaitTimeSeconds` to reduce AWS API calls and computing costs.
- [x] **Message Visibility Management:** Safe `ReceiptHandle` deletion only after successful processing to guarantee zero data loss.
- [ ] **Data Persistence:** PostgreSQL (AWS RDS) integration (Upcoming).
- [ ] **Inventory Caching:** Redis (ElastiCache) integration (Upcoming).
- [ ] **Load Testing:** Locust metrics for concurrent user benchmarking (Upcoming).

## 🏃‍♂️ How to Run Locally
*Note: Requires Docker and Python 3.10+*

1. Start the local AWS infrastructure (LocalStack):
```bash
docker-compose up -d
python setup_queue.py
```
2. Start the API server:
```bash
uvicorn main:app --reload
```
3. Start the background worker daemon in a separate terminal:
```bash
python worker.py
```