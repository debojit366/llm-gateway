# ⚡ Intelligent LLM Gateway

An API gateway built with **FastAPI** that provides a unified interface for multiple LLM providers, while adding caching, rate limiting, PII protection, model routing, retry/failover, streaming, and usage analytics.

The gateway sits between client applications and LLM providers such as **Google Gemini** and **Groq**, so client applications don't need to implement provider-specific logic themselves.

---

## 📑 Table of Contents

- [What Problem Does This Solve?](#-what-problem-does-this-solve)
- [Architecture](#️-architecture)
- [Request Flow](#-request-flow)
- [Key Features](#-key-features)
- [Tech Stack](#️-tech-stack)
- [Project Structure](#-project-structure)
- [Environment Variables](#️-environment-variables)
- [Running with Docker Compose](#-running-with-docker-compose)
- [Example Chat Request](#-example-chat-request)
- [Dashboard](#-dashboard)
- [Docker Services](#-docker-services)
- [Security Considerations](#-security-considerations)
- [Current Implementation Notes](#️-current-implementation-notes)
- [Why This Project?](#-why-this-project)
- [Future Improvements](#-future-improvements)
- [License](#-license)

---

## 🧠 What Problem Does This Solve?

Calling an LLM provider directly can create several problems:

- Every application has to manage provider-specific APIs.
- Repeated prompts can unnecessarily consume tokens and increase cost.
- Excessive traffic can hit provider rate limits.
- Sensitive information may be sent to external LLM providers.
- A temporary provider failure can make the application unavailable.
- It becomes difficult to track model usage, tokens, cache performance, and estimated cost.

This project centralizes those concerns inside one gateway.

---

## 🏗️ Architecture

```
                         ┌─────────────────────┐
                         │     Client App      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    FastAPI Gateway   │
                         └──────────┬──────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
                 ▼                  ▼                  ▼
          API Key Auth        Rate Limiting       PII Masking
                                   │                  │
                                   └────────┬─────────┘
                                            ▼
                                   ┌─────────────────┐
                                   │  Semantic Cache  │
                                   └────────┬────────┘
                                            │
                              ┌─────────────┴─────────────┐
                              │                           │
                              ▼                           ▼
                       Redis Exact Hit            Qdrant Vector Search
                              │                           │
                              └─────────────┬─────────────┘
                                            │ Cache Miss
                                            ▼
                                   ┌─────────────────┐
                                   │   Model Router   │
                                   └────────┬────────┘
                                            │
                              ┌─────────────┴─────────────┐
                              ▼                           ▼
                       Google Gemini                     Groq
                              │                           │
                              └─────────────┬─────────────┘
                                            ▼
                                      SSE Streaming
                                            │
                                            ▼
                                          Client

                         Background Analytics → MongoDB
                                            │
                                            ▼
                                    React Dashboard
```

---

## 🔄 Request Flow

A typical chat request follows this pipeline:

1. **Authentication** — The client sends an API key and the gateway verifies it against the configured user store.
2. **Rate Limiting** — Redis tracks requests using a sliding-window counter. The current implementation allows **5 chat requests per IP within 60 seconds**.
3. **PII Masking** — Sensitive information is detected using Microsoft Presidio + spaCy and replaced before the prompt is sent to an LLM provider. A custom regex also masks secret/token/password-style values.
4. **Cache Lookup** — The gateway first checks Redis for an exact prompt match. On an exact-cache miss, it generates a prompt embedding and performs a semantic similarity search in Qdrant.
5. **Cache Hit** — If a sufficiently similar response is found, the cached response can be returned without calling the external LLM provider.
6. **Model Routing** — On a cache miss, the gateway selects Gemini or Groq based on the requested model. When `model="auto"` is used, the router applies rule-based capability scoring using factors such as coding, reasoning, vision, context length, and speed.
7. **Retry and Failover** — Temporary provider failures are retried. Non-retryable client/authentication errors are not retried. After retry attempts are exhausted, the gateway switches to the other configured provider.
8. **Streaming** — Provider output is streamed to the client using Server-Sent Events (SSE), reducing perceived latency.
9. **Analytics** — Request metadata such as model, token usage, cache status, timestamp, and estimated cost is stored in MongoDB for dashboard reporting.

---

## 🔥 Key Features

### 1. Multi-Provider LLM Gateway
Provides one gateway interface for multiple LLM providers:
- Google Gemini
- Groq

The application can select a specific model or use auto routing.

### 2. Intelligent Model Routing
The auto router uses **rule-based capability scoring**. It considers:
- Vision requirements
- Coding-related requests
- Reasoning/analysis requests
- Prompt/context size
- Provider speed preference

Example routing logic:

| Request Type | Routing Behavior |
|---|---|
| Vision request | Gemini preference |
| Coding-heavy request | Groq gets strong preference |
| Long context | Provider capability is considered |
| General fast request | Speed contributes to routing score |

> This is a **rule-based router**, not an ML model.

### 3. Two-Layer Semantic Cache

```
Prompt
  │
  ├── Redis exact lookup
  │       └── Fast exact-match cache
  │
  └── Qdrant semantic lookup
          └── Embedding similarity search
```

- Prompt embeddings are generated using Google's embedding API with **768-dimensional vectors**.
- A semantic match is accepted when its similarity score reaches the configured threshold used by the cache service (**currently 0.88 by default**).
- On a semantic hit, the returned response is also written back to Redis as an exact-cache entry for faster future lookups.

### 4. PII Protection
PII masking is implemented as middleware before provider execution.

**Detected entities include:**
- Person names
- Email addresses
- Phone numbers
- IP addresses
- URLs
- Credit-card numbers
- Secret/token/password-style values using custom regex matching

**Technologies used:**
- Microsoft Presidio Analyzer
- Microsoft Presidio Anonymizer
- spaCy
- Custom regular expressions

### 5. Redis Rate Limiting
The gateway uses Redis for distributed rate limiting.

**Current chat endpoint policy:**
| Setting | Value |
|---|---|
| Limit | 5 requests |
| Window | 60 seconds |
| Key | Client IP |

When the limit is exceeded, the gateway returns **HTTP 429**.

### 6. Retry and Provider Failover

```
Primary Provider
      │
      ├── Attempt 1
      ├── Attempt 2
      │
      └── Failure
             │
             ▼
       Backup Provider
```

The router does **not** retry configured non-retryable status codes such as:
`400`, `401`, `403`, `404`, `422`

### 7. Streaming Responses
LLM responses are streamed to the client using Server-Sent Events (SSE) rather than waiting for the complete response before sending data.

### 8. Request Analytics
The gateway stores request analytics in MongoDB, including:
- User ID
- Client IP
- Model
- Prompt
- Cache hit/miss
- Timestamp
- Total tokens
- Prompt tokens
- Completion tokens
- Estimated cost

### 9. React Analytics Dashboard
A separate React + Vite dashboard visualizes gateway activity.

**Current dashboard metrics include:**
- Cached prompts
- Tokens saved
- Cache hit rate
- Daily cache hit/miss analysis
- Model distribution
- Request counts

The dashboard periodically refreshes analytics data from the gateway API.

---

## 🛠️ Tech Stack

**Backend**
- Python
- FastAPI
- Uvicorn
- Pydantic Settings
- HTTPX

**LLM Providers**
- Google Gemini
- Groq

**Data & Infrastructure**
- Redis
- MongoDB
- Qdrant

**Security / NLP**
- Microsoft Presidio
- spaCy

**Frontend**
- React
- Vite
- Tailwind CSS
- Recharts
- Lucide React

**Deployment / DevOps**
- Docker
- Docker Compose
- GitHub Actions workflow

---

## 📁 Project Structure

```
llm-gateway-main/
│
├── app/
│   ├── api/v1/endpoints/
│   │   ├── analytics.py
│   │   ├── auth.py
│   │   └── chat.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   │
│   ├── db/
│   │   ├── mongo.py
│   │   └── qdrant_client.py
│   │
│   ├── middlewares/
│   │   ├── pii_middleware.py
│   │   └── rate_limit_middleware.py
│   │
│   ├── providers/
│   │   ├── gemini/
│   │   ├── groq/
│   │   ├── base_provider.py
│   │   └── registry.py
│   │
│   ├── services/
│   │   ├── analytics_service.py
│   │   ├── cache_service.py
│   │   ├── embedding_service.py
│   │   ├── model_router.py
│   │   └── rate_limiter.py
│   │
│   ├── utils/
│   │   └── pii_masker.py
│   │
│   └── main.py
│
├── llm-gateway-ui/
│   └── src/
│       └── components/
│           └── AnalyticsDashboard.jsx
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## ⚙️ Environment Variables

Create a `.env` file in the project root:

```env
APP_ENV=development

GEMINI_API_KEY=your_gemini_api_key
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta

GROQ_API_KEY=your_groq_api_key
GROQ_BASE_URL=https://api.groq.com/openai/v1

REDIS_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333
```

MongoDB configuration should also be provided according to the database configuration used by the application.

> ⚠️ **Never commit real API keys or secrets to Git.**

---

## 🚀 Running with Docker Compose

**1. Clone the repository**
```bash
git clone <your-repository-url>
cd llm-gateway-main
```

**2. Create environment file**
```bash
cp .env.example .env
```
Fill in the required API keys and database settings.

**3. Start the backend and dependencies**
```bash
docker compose up --build
```

The services include:
| Service | URL |
|---|---|
| FastAPI Gateway | http://localhost:8000 |
| Redis | localhost:6379 |
| MongoDB | localhost:27018 |
| Qdrant | http://localhost:6333 |

**4. Check health**
```bash
curl http://localhost:8000/health
```

**5. API documentation**

FastAPI automatically provides:
- Swagger UI → http://localhost:8000/docs
- ReDoc → http://localhost:8000/redoc

---

## 💬 Example Chat Request

The main chat endpoint is:

```
POST /api/v1/chat/completions
```

**Example request:**
```json
{
  "model": "gemini-2.5-flash",
  "messages": [
    {
      "role": "user",
      "content": "Explain Docker containers in simple terms."
    }
  ],
  "temperature": 0.7,
  "stream": true
}
```

**For automatic provider selection:**
```json
{
  "model": "auto",
  "messages": [
    {
      "role": "user",
      "content": "Write a FastAPI implementation of Redis rate limiting."
    }
  ],
  "stream": true
}
```

---

## 📊 Dashboard

The frontend is located in `llm-gateway-ui`.

**Install dependencies:**
```bash
cd llm-gateway-ui
npm install
```

**Run the development server:**
```bash
npm run dev
```

**Build for production:**
```bash
npm run build
```

---

## 🐳 Docker Services

`docker-compose.yml` runs the following services:

```
┌────────────────────┐
│   FastAPI Gateway   │  :8000
└─────────┬──────────┘
          │
    ┌─────┼─────┐
    │     │     │
    ▼     ▼     ▼
 Redis Mongo  Qdrant
 :6379 :27018 :6333
```

Persistent Docker volumes are used for MongoDB and Qdrant storage.

---

## 🔐 Security Considerations

The gateway includes several application-level protections:

- API-key based authentication
- Redis rate limiting
- PII masking before LLM provider calls
- Environment-based secret configuration
- Non-retryable handling for authentication/client errors

For a production deployment, additional controls such as HTTPS termination, stronger secret management, request-size limits, authenticated dashboard access, and centralized observability would still be recommended.

---

## ⚠️ Current Implementation Notes

- The semantic cache currently uses **Redis + Qdrant**, not MongoDB Vector Search.
- The configured LLM providers are **Gemini and Groq**, not OpenAI.
- `model="auto"` uses **rule-based** capability scoring.
- The current rate limiter uses **client IP** as its primary key for chat requests.
- Analytics cost calculation is based on the pricing configuration present in the code and should be updated when provider pricing changes.
- The project is designed as a strong gateway **prototype**; some production-hardening concerns would need additional work before exposing it directly to the public internet.

---

## 🎯 Why This Project?

The main design goal is to make client applications **LLM-provider independent**.

Instead of every client implementing authentication, rate limiting, caching, PII protection, provider selection, retries, streaming, and analytics separately, these capabilities are centralized inside the gateway.

This makes the system easier to extend to additional providers and models without changing the application-facing interface.

---

## 📌 Future Improvements

- Per-user or per-API-key rate limits
- Dynamic rate-limit tiers such as Free / Pro / Enterprise
- Centralized API-key rotation
- More provider adapters
- Provider health monitoring
- Distributed tracing and metrics
- Authentication and authorization for the analytics dashboard
- Better cache invalidation and TTL policies
- Persistent model/cost configuration instead of hard-coded pricing
- Automated integration and load tests

---

## 📄 License

Add the project license of your choice here.
