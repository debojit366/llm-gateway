# ⚡ Semantic AI Gateway & Caching Proxy

An enterprise-grade, high-performance, and fault-tolerant AI Gateway designed to sit between consumers and LLM providers. Built using **FastAPI**, **MongoDB Vector Caching**, and **Redis**, this architecture delivers **90%+ cost and latency reduction** through semantic prompt caching, while ensuring zero downtime with resilient token budgeting and real-time dashboard analytics.

---

## 🏗️ System Architecture



The gateway filters and processes traffic in a strict, high-availability sequential pipeline:
1. **Inbound Traffic:** Client requests hit the Gateway API layer.
2. **Token & Cost Budgeting Middleware:** Ensures individual user/API-Key dollar consumption stays under the daily cap limit (`$0.50` default). Throws `429 Too Many Requests` if exceeded.
3. **Dynamic Rate Limiter:** Handles sudden burst traffic and peaks via Redis sliding window counters.
4. **Semantic Caching Engine:** Converts incoming prompts into vector embeddings and scans MongoDB utilizing vector index similarity search. 
   - **Cache Hit (Similarity Score >= 0.92):** Response is streamed instantly from the DB without hitting external LLM layers.
   - **Cache Miss:** Request seamlessly routes to primary LLM providers.
5. **High-Availability Fallback Routing:** In case the primary provider (Gemini) encounters rate limits (`429`) or service outages (`5xx`), the gateway triggers an automatic failover shift to the backup provider (OpenAI GPT).
6. **Async Analytics pipeline:** Complete execution logs, dynamic tokens utilized, and exact cost footprints are calculated and processed asynchronously via Python background tasks directly into MongoDB to maintain sub-millisecond response latency.

---

## 🔥 Key Features

- 🧠 **Semantic Prompt Caching:** Uses cosine similarity matching on embedded vector schemas to return contextual answers instantly, saving huge token footprints.
- 🔄 **High-Availability Failover:** Intelligent orchestration layer that automatically handles API rate limits/timeouts by migrating traffic seamlessly between Gemini and OpenAI models.
- ⏱️ **Async Non-Blocking Logging:** Python 3.12+ optimized background analytics processor that computes context tokens and saves entries without blocking the streaming loop.
- 💳 **Token Budgeting Middleware:** Granular control over platform pricing with real-time dynamic dollar spend caps stored inside active Redis hashes.
- 📊 **Real-time Analytics Dashboard:** Fully responsive React application integrated with **Recharts** displaying active sync loops for Cache Hit rates, dynamic usage metrics, and model/user volume distribution.

---

## 🛠️ Tech Stack

- **Backend Framework:** FastAPI (Asynchronous Python ASGI)
- **Vector & Storage DB:** MongoDB (Atlas Vector Search for semantic prompt embeddings, logs collection)
- **Caching & Rate Limiting:** Redis (Asynchronous IO cluster)
- **Frontend Dashboard:** React, Vite, Tailwind CSS, Recharts, Lucide React
- **HTTP Client Platform:** HTTPX (Async server pooling)

---

## ⚙️ Environment Configuration

Create a `.env` file in the root backend folder and fill in your environment access keys:

```env
# Server Port Configuration
PORT=8000

# Primary and Backup API Key Layers
GEMINI_API_KEY=AIzaSyYourRealGeminiAPIKeyHere
OPENAI_API_KEY=sk-proj-YourRealOpenAIKeyForBackup

# Distributed Databases Links
MONGODB_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/ai_gateway
REDIS_URL=redis://redis-container:6379

# Active Budget Profiles
DAILY_COST_CAP_USD=0.50
SEMANTIC_SIMILARITY_THRESHOLD=0.92
