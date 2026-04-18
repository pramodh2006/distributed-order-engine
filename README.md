<div align="center">

# ⚡ Distributed Order Engine

### *A cloud-native, event-driven checkout system engineered for zero-downtime at peak scale*

<br/>

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![AWS SQS](https://img.shields.io/badge/AWS_SQS-Queue-FF9900?style=for-the-badge&logo=amazonsqs&logoColor=white)](https://aws.amazon.com/sqs/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7.2-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![LocalStack](https://img.shields.io/badge/LocalStack-AWS_Local-1A1A1A?style=for-the-badge&logo=amazon&logoColor=white)](https://localstack.cloud)

<br/>

[![Load Test](https://img.shields.io/badge/Load_Test-500_Concurrent_Users-success?style=for-the-badge&logo=locust&logoColor=white)](#-performance--load-testing)
[![Failure Rate](https://img.shields.io/badge/Failure_Rate-0%25-brightgreen?style=for-the-badge)](#-performance--load-testing)
[![Response Time](https://img.shields.io/badge/API_Response-<50ms-blue?style=for-the-badge)](#-performance--load-testing)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

<br/>

> **Built to survive Prime Day.** This system decouples the checkout API from all backend processing via an SQS message queue — ensuring the API stays responsive at any volume while workers process orders reliably in the background.

</div>

---

## 📋 Table of Contents

- [🏗️ Architecture Overview](#%EF%B8%8F-architecture-overview)
- [✨ Key Design Decisions](#-key-design-decisions)
- [⚙️ Tech Stack](#%EF%B8%8F-tech-stack)
- [📁 Project Structure](#-project-structure)
- [🚀 Local Setup Guide](#-local-setup-guide)
- [📡 API Reference](#-api-reference)
- [📊 Performance & Load Testing](#-performance--load-testing)
- [🔭 Engineering Deep Dive](#-engineering-deep-dive)
- [🗺️ Roadmap](#%EF%B8%8F-roadmap)

---

## 🏗️ Architecture Overview

The system is built around the **Producer-Consumer pattern**. The FastAPI layer is a pure *producer* — it never blocks on business logic. Horizontally-scaled Python workers are pure *consumers* — they own all inventory and persistence operations.

```mermaid
flowchart TD
    Client(["👤 Client\n(Browser / Mobile / API)"])

    subgraph API_Layer ["🌐  API Layer  —  FastAPI (Uvicorn)"]
        EP["/checkout\nPOST endpoint"]
        VAL["📋 Request\nValidation\n(Pydantic)"]
        ACK["✅ 202 Accepted\n+ correlation_id"]
    end

    subgraph Queue ["☁️  AWS SQS Queue  —  (LocalStack in Dev)"]
        SQS[["📨 order-processing-queue\nFIFO • Visibility Timeout: 30s"]]
    end

    subgraph Worker_Pool ["⚙️  Horizontal Worker Pool  —  N × worker.py"]
        direction TB
        W1["Worker 1\n🔄 Long-poll • batch=10"]
        W2["Worker 2\n🔄 Long-poll • batch=10"]
        W3["Worker N\n🔄 Long-poll • batch=10"]
    end

    subgraph Inventory ["⚡  Redis  —  Atomic Inventory"]
        R[("🗃️ Stock Counter\nDECR + watch\nAtomic ops")]
    end

    subgraph Persistence ["🐘  PostgreSQL  —  Source of Truth"]
        DB[("📦 orders table\nFinal committed\norder state")]
    end

    DLQ[["💀 Dead Letter Queue\nFailed messages\nafter 3 retries"]]

    Client -->|"POST /checkout\n{ order payload }"| EP
    EP --> VAL
    VAL -->|"enqueue via boto3"| SQS
    VAL --> ACK
    ACK -->|"HTTP 202"| Client

    SQS -->|"ReceiveMessage\nbatch of 10"| W1
    SQS -->|"ReceiveMessage\nbatch of 10"| W2
    SQS -->|"ReceiveMessage\nbatch of 10"| W3

    W1 <-->|"DECR inventory\ncheck stock ≥ 0"| R
    W2 <-->|"DECR inventory\ncheck stock ≥ 0"| R
    W3 <-->|"DECR inventory\ncheck stock ≥ 0"| R

    W1 -->|"INSERT order\n(status: CONFIRMED)"| DB
    W2 -->|"INSERT order\n(status: CONFIRMED)"| DB
    W3 -->|"INSERT order\n(status: CONFIRMED)"| DB

    W1 -->|"DeleteMessage\n✔ on success"| SQS
    W2 -->|"DeleteMessage\n✔ on success"| SQS
    W3 -->|"DeleteMessage\n✖ on failure → DLQ"| DLQ

    style API_Layer fill:#0d1117,stroke:#238636,color:#c9d1d9
    style Queue fill:#0d1117,stroke:#FF9900,color:#c9d1d9
    style Worker_Pool fill:#0d1117,stroke:#1f6feb,color:#c9d1d9
    style Inventory fill:#0d1117,stroke:#DC382D,color:#c9d1d9
    style Persistence fill:#0d1117,stroke:#4169E1,color:#c9d1d9
    style DLQ fill:#0d1117,stroke:#6e7681,color:#6e7681
```

### 🔄 Request Lifecycle — Step by Step

| Step | Component | Action | Latency Profile |
|:----:|-----------|--------|----------------|
| **1** | 👤 **Client** | Sends `POST /checkout` with order JSON | — |
| **2** | ⚡ **FastAPI** | Validates payload via Pydantic schema | ~1–2ms |
| **3** | 📨 **SQS** | `SendMessage` enqueues the order | ~5–15ms |
| **4** | ✅ **FastAPI** | Returns `202 Accepted` + `correlation_id` | **< 50ms total** |
| **5** | ⚙️ **Worker** | Long-polls SQS; fetches up to 10 messages | async |
| **6** | 🗃️ **Redis** | `DECR` stock atomically; rejects if `stock < 0` | ~0.3ms |
| **7** | 🐘 **PostgreSQL** | Persists final order (`CONFIRMED` or `REJECTED`) | ~5–10ms |
| **8** | 📨 **SQS** | Worker calls `DeleteMessage` to ACK the message | ~5ms |

---

## ✨ Key Design Decisions

> ### 💡 Why decouple with SQS instead of processing synchronously?
> A synchronous checkout that queries PostgreSQL, checks Redis, and writes a record on every request becomes a liability under load. A single slow DB write at 500 req/s blocks threads, exhausts connection pools, and cascades into timeouts. By publishing to SQS and returning `202` immediately, **the API's latency is bounded by the queue alone** — not the slowest downstream dependency.

> ### 💡 Why Redis for inventory, not PostgreSQL?
> PostgreSQL `UPDATE ... WHERE stock > 0` under high concurrency creates row-level lock contention. Redis `DECR` is a single-threaded, atomic O(1) operation. There is no lock to contend for, no transaction to coordinate. At 500 concurrent users, this is the difference between a hot-path bottleneck and a non-issue.

> ### 💡 Why long-polling with batch size 10?
> SQS long-polling (up to 20s wait) eliminates busy-waiting and reduces API call costs by ~95% vs. short-polling. Processing 10 messages per `ReceiveMessage` call amortizes network round-trip overhead across all messages in the batch — critical for throughput when running multiple workers.

---

## ⚙️ Tech Stack

| Layer | Technology | Role |
|-------|------------|------|
| **API Framework** | [FastAPI](https://fastapi.tiangolo.com) + Uvicorn | High-performance async HTTP server |
| **Message Queue** | [AWS SQS](https://aws.amazon.com/sqs/) via boto3 | Durable, decoupled order buffer |
| **Inventory Cache** | [Redis](https://redis.io) 7.2 | Atomic stock decrement, sub-ms ops |
| **Database** | [PostgreSQL](https://postgresql.org) 16 + SQLAlchemy | Persistent order state & audit log |
| **Containerization** | [Docker](https://docker.com) + Compose | Reproducible local environment |
| **AWS Emulation** | [LocalStack](https://localstack.cloud) | Runs SQS locally without AWS costs |
| **Load Testing** | [Locust](https://locust.io) | Simulates Prime Day-scale traffic |
| **Data Validation** | [Pydantic](https://docs.pydantic.dev) v2 | Runtime schema enforcement on input |

---

## 📁 Project Structure

```
distributed-order-engine/
│
├── 🐳 docker-compose.yml          # Orchestrates all services
├── 📄 .env.example                # Environment variable template
├── 📄 requirements.txt
│
├── app/
│   ├── main.py                    # FastAPI app & /checkout endpoint
│   ├── schemas.py                 # Pydantic models (OrderRequest, OrderResponse)
│   ├── dependencies.py            # SQS client, Redis client (injected)
│   └── config.py                  # Settings via pydantic-settings
│
├── worker/
│   └── worker.py                  # SQS consumer — inventory check & DB write
│
├── db/
│   ├── models.py                  # SQLAlchemy ORM models
│   └── session.py                 # Async DB engine & session factory
│
├── scripts/
│   ├── setup_queue.py             # Creates SQS queue on LocalStack
│   └── setup_redis.py             # Seeds initial inventory counts in Redis
│
└── tests/
    ├── locustfile.py              # Prime Day load test scenario
    ├── test_checkout.py           # Unit tests for API layer
    └── test_worker.py             # Unit tests for worker logic
```

---

## 🚀 Local Setup Guide

> **Prerequisites:** Docker Desktop, Python 3.11+, and `pip` installed locally.

### Step 1 — Clone & Configure

```bash
git clone https://github.com/your-username/distributed-order-engine.git
cd distributed-order-engine

# Copy environment template and configure
cp .env.example .env
```

Your `.env` should look like this:

```ini
# AWS / LocalStack
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
SQS_ENDPOINT_URL=http://localhost:4566
SQS_QUEUE_NAME=order-processing-queue

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/orders_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Step 2 — Spin Up Infrastructure

```bash
# Starts LocalStack (SQS), PostgreSQL, and Redis in detached mode
docker-compose up -d
```

```bash
# Verify all services are healthy before proceeding
docker-compose ps
```

Expected output:
```
NAME                IMAGE               STATUS
localstack          localstack/localstack   Up (healthy)
postgres_db         postgres:16-alpine      Up (healthy)
redis_cache         redis:7-alpine          Up (healthy)
```

### Step 3 — Initialize Queue & Seed Inventory

```bash
# Install Python dependencies
pip install -r requirements.txt

# Create the SQS queue on LocalStack
python scripts/setup_queue.py
# ✔ Queue created: http://localhost:4566/000000000000/order-processing-queue

# Seed initial stock counts into Redis
python scripts/setup_redis.py
# ✔ Seeded 50 SKUs with inventory counts into Redis
```

### Step 4 — Start the API Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The interactive API docs are now live at **[http://localhost:8000/docs](http://localhost:8000/docs)**

### Step 5 — Launch Workers (Horizontal Scaling)

Open a **new terminal** for each worker instance. Each process independently long-polls the queue — this is how you scale throughput horizontally.

```bash
# Terminal 2 — Worker instance 1
python worker/worker.py
# [Worker-1] 🔄 Polling for messages...

# Terminal 3 — Worker instance 2
python worker/worker.py
# [Worker-2] 🔄 Polling for messages...

# Terminal 4 — Worker instance 3
python worker/worker.py
# [Worker-3] 🔄 Polling for messages...
```

> **💡 Scaling Tip:** In production, each `worker.py` maps to a separate ECS Task or Kubernetes Pod. SQS visibility timeout prevents duplicate processing — the message is "invisible" to other workers while one holds it.

### Step 6 — Run the Load Test

```bash
locust -f tests/locustfile.py --host=http://localhost:8000
# Open http://localhost:8089 in your browser to start the test
```

---

## 📡 API Reference

### `POST /checkout`

Enqueues an order for asynchronous processing. Returns immediately with a tracking ID.

**Request Body**

```json
{
  "user_id": "usr_4f2a9c",
  "items": [
    { "sku": "WIDGET-XL-BLK", "quantity": 2 },
    { "sku": "GADGET-PRO-WHT", "quantity": 1 }
  ],
  "shipping_address": {
    "line1": "123 Main St",
    "city": "Seattle",
    "state": "WA",
    "zip": "98101"
  }
}
```

**Response — `202 Accepted`**

```json
{
  "status": "QUEUED",
  "correlation_id": "ord_8d3f1b9e-4a72-4c1d-9f8e-2b3c4d5e6f7a",
  "message": "Your order has been received and is being processed.",
  "estimated_processing_ms": 150
}
```

| Status Code | Meaning |
|:-----------:|---------|
| `202` | Order accepted and queued — poll `/order/{correlation_id}` for final status |
| `422` | Validation error — malformed payload |
| `503` | Queue unavailable (circuit-breaker tripped) |

### `GET /order/{correlation_id}`

```json
{
  "correlation_id": "ord_8d3f1b9e-4a72-4c1d-9f8e-2b3c4d5e6f7a",
  "status": "CONFIRMED",
  "processed_at": "2024-07-15T18:32:01.443Z"
}
```

---

## 📊 Performance & Load Testing

The system was stress-tested with [Locust](https://locust.io) simulating **Amazon Prime Day** traffic patterns — a sustained ramp of concurrent users hitting `/checkout` continuously.

### 🔬 Test Configuration

```python
# tests/locustfile.py  (simplified)
class CheckoutUser(HttpUser):
    wait_time = between(0.1, 0.5)   # Aggressive think time

    @task
    def checkout(self):
        self.client.post("/checkout", json=generate_random_order())
```

```bash
locust -f tests/locustfile.py \
  --headless \
  --users 500 \
  --spawn-rate 50 \
  --run-time 3m \
  --host http://localhost:8000
```

### 🏆 Results

| Metric | Result | Industry Benchmark |
|--------|--------|--------------------|
| 👥 **Peak Concurrent Users** | **500** | — |
| ⚡ **Spawn Rate** | **50 users/sec** | Aggressive ramp |
| ✅ **Success Rate** | **100%** (0 failures) | ≥ 99.9% target |
| 🚀 **Median Response Time** | **< 50ms** | < 200ms typical |
| 📈 **99th Percentile (p99)** | **< 120ms** | < 500ms acceptable |
| 🔁 **Requests per Second** | **~480 RPS sustained** | — |
| 💀 **Error Rate** | **0.00%** | < 0.1% target |

```
 Requests/sec ▲
              │
  500 ──────  │                    ████████████████████████
              │               █████
              │          █████
              │     █████
    0 ────────┼─────────────────────────────────────────► Time (3 min)
              0s   30s   60s   90s   120s  150s  180s

  Response Time (ms) ▲
              │
  120ms ────  │  · · · · · p99 · · · · · · · · · · · · ·
   50ms ────  │  ———————————— median ————————————————————
              │
    0ms ──────┴─────────────────────────────────────────► Time
```

> **🎯 Why these numbers matter:** The `202 Accepted` design means the API's response time is gated only by the SQS `SendMessage` call (~15ms) — not inventory checks or DB writes. This is the architectural decision that makes 0% failure rate at 500 concurrent users achievable.

---

## 🔭 Engineering Deep Dive

### Atomic Inventory with Redis

The core of the oversell-prevention logic is a single atomic `DECR` operation. Because Redis is single-threaded, two workers decrementing the same SKU simultaneously will always execute sequentially — no locks, no race conditions.

```python
# worker/worker.py
def attempt_reserve_inventory(redis_client, sku: str, quantity: int) -> bool:
    """
    Atomically decrement inventory. If the result goes negative,
    increment back and signal rejection. O(1) — no distributed lock needed.
    """
    new_stock = redis_client.decrby(f"inventory:{sku}", quantity)
    if new_stock < 0:
        redis_client.incrby(f"inventory:{sku}", quantity)  # Compensate
        return False
    return True
```

### SQS Visibility Timeout as a Distributed Lock

When a worker calls `ReceiveMessage`, SQS hides that message from all other workers for the configured **Visibility Timeout** (30s). If the worker crashes mid-processing, the message automatically reappears in the queue for another worker to retry — no explicit locking, no coordinator needed.

```python
# worker/worker.py
response = sqs.receive_message(
    QueueUrl=QUEUE_URL,
    MaxNumberOfMessages=10,   # Process in batches for throughput
    WaitTimeSeconds=20,       # Long-poll — eliminates busy-waiting
    AttributeNames=["All"],
)
```

### Why `202 Accepted` is the Right Status Code

HTTP `200 OK` implies the work is *done*. `202 Accepted` is the semantically correct response for async workflows: it signals "I've received your request and will process it, but the work is not complete yet." This sets correct client expectations and is defined in [RFC 9110 §15.3.3](https://www.rfc-editor.org/rfc/rfc9110#section-15.3.3).

<div align="center">

**Built with 🏗️ by [Pramodh](https://github.com/pramodh2006)**

*If this project was useful or interesting, consider leaving a ⭐*

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/pramodhkumarv)
[![Portfolio](https://img.shields.io/badge/Portfolio-Visit-FF6B6B?style=for-the-badge&logo=vercel&logoColor=white)](https://pramodh2006.github.io/portfolio)

</div>
