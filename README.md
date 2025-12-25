<div align="center">

<div style="margin: 20px 0;">
  <img src="./assets/logo.png" width="120" height="120" alt="LightRAG Logo" style="border-radius: 20px; box-shadow: 0 8px 32px rgba(0, 217, 255, 0.3);">
</div>

# 🚀 LightRAG Multi-User Edition

### Simple and Fast RAG with Multi-User Support

<p>
  <img src="https://img.shields.io/badge/🐍Python-3.10+-4ecdc4?style=for-the-badge&logo=python&logoColor=white&labelColor=1a1a2e">
  <img src="https://img.shields.io/badge/PostgreSQL-pgvector-336791?style=for-the-badge&logo=postgresql&logoColor=white&labelColor=1a1a2e">
  <img src="https://img.shields.io/badge/Redis-Rate_Limiting-DC382D?style=for-the-badge&logo=redis&logoColor=white&labelColor=1a1a2e">
</p>

> 🔱 **Fork of [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG)** with multi-user workspace isolation

</div>

---

## ✨ What's New in This Fork

| Feature | Description |
|---------|-------------|
| **👥 Multi-User Workspaces** | Each user gets isolated data storage (1 User = 1 Workspace) |
| **🔐 JWT Authentication** | Secure login with auto-logout on server restart |
| **🚦 Redis Rate Limiting** | Per-user request limits (uploads, queries, scans) |
| **🐘 Full PostgreSQL** | All storage types on PostgreSQL (KV, Graph, Vector, DocStatus) |
| **🐳 Production Docker** | Ready-to-deploy docker-compose with health checks |
| **🎛️ Debug Mode** | Environment-controlled log verbosity |
| **👤 Admin-Only API** | API documentation restricted to admin users |

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone this repository
git clone https://github.com/JKisotama/LightRAG.git
cd LightRAG

# Configure environment
cp .env.production.example .env
# Edit .env with your API keys (LLM, Embedding)

# Start all services
docker-compose up -d

# Access WebUI
open http://localhost:9621
```

### Option 2: Local Development

```bash
# Clone and install
git clone https://github.com/JKisotama/LightRAG.git
cd LightRAG
uv sync --extra api
source .venv/bin/activate

# Configure
cp .env.example .env
# Edit .env with your configuration

# Build frontend
cd lightrag_webui
bun install --frozen-lockfile
bun run build
cd ..

# Start server
lightrag-server
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      LightRAG Server                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Auth Layer  │  │ Rate Limit  │  │ Workspace Manager   │ │
│  │ (JWT)       │  │ (Redis)     │  │ (Per-user RAG)      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   ┌──────────┐     ┌──────────┐     ┌─────────┐
   │ PostgreSQL│    │  Redis   │     │ (Files) │
   │ (pgvector)│    │ (cache)  │     │ uploads │
   └──────────┘     └──────────┘     └─────────┘
```

### Multi-User Workspace Isolation

```
User A ──► Workspace A ──► /rag_storage/workspaces/userA/
                          ├── graph/
                          ├── vectors/
                          └── documents/

User B ──► Workspace B ──► /rag_storage/workspaces/userB/
                          ├── graph/
                          ├── vectors/
                          └── documents/
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# === Authentication ===
AUTH_ACCOUNTS=admin:password,user1:pass123
TOKEN_EXPIRE_HOURS=5
# TOKEN_SECRET=your-secret  # Uncomment to persist sessions across restarts

# === Rate Limiting ===
ENABLE_RATE_LIMITING=true
RATE_LIMIT_UPLOADS_PER_MINUTE=10
RATE_LIMIT_QUERIES_PER_MINUTE=30

# === Debug Mode ===
DEBUG=false  # true = all logs, false = warnings only

# === Storage (Full PostgreSQL) ===
LIGHTRAG_KV_STORAGE=PGKVStorage
LIGHTRAG_DOC_STATUS_STORAGE=PGDocStatusStorage
LIGHTRAG_GRAPH_STORAGE=PGGraphStorage
LIGHTRAG_VECTOR_STORAGE=PGVectorStorage

# === PostgreSQL ===
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=rag_user
POSTGRES_PASSWORD=rag_password
POSTGRES_DATABASE=lightrag_db

# === Redis ===
REDIS_URI=redis://redis:6379

# === LLM & Embedding ===
LLM_BINDING=gemini
LLM_MODEL=gemini-2.0-flash
LLM_BINDING_API_KEY=your_api_key

EMBEDDING_BINDING=gemini
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIM=768
EMBEDDING_BINDING_API_KEY=your_api_key
```

---

## 🐳 Docker Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `lightrag` | ghcr.io/hkuds/lightrag | 9621 | Main application |
| `postgres` | pgvector/pgvector:pg16 | 5432 | All data storage |
| `redis` | redis:7-alpine | 6379 | Rate limiting cache |

### Health Checks

All services include health checks for reliability:

- **LightRAG**: `GET /health`
- **PostgreSQL**: `pg_isready`
- **Redis**: `redis-cli ping`

---

## 🔒 Security Features

### Auto-Logout on Server Restart

- JWT secret is randomly generated on each server start
- All existing tokens become invalid after restart
- Set `TOKEN_SECRET` in .env to persist sessions

### Rate Limiting

- Per-user, per-action limits
- Redis-backed for persistence
- HTTP 429 response with `Retry-After` header

### Role-Based Access

- Admin users: Full access including API documentation
- Regular users: Documents, Knowledge Graph, Retrieval only

---

## 📊 Production Checklist

- [ ] Set `DEBUG=false`
- [ ] Set `ENABLE_RATE_LIMITING=true`
- [ ] Configure `AUTH_ACCOUNTS` with secure passwords
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Configure LLM/Embedding API keys
- [ ] (Optional) Set `TOKEN_SECRET` for session persistence
- [ ] (Optional) Configure SSL for external access

---

## 📁 File Structure

```
LightRAG/
├── docker-compose.yml       # Production-ready Docker setup
├── .env.example             # Development environment template
├── .env.production.example  # Production environment template
├── lightrag/
│   └── api/
│       ├── rate_limiter.py  # Redis rate limiting module
│       ├── auth.py          # JWT authentication
│       └── routers/         # API endpoints
└── lightrag_webui/          # React frontend
```

---

## 📚 Original Documentation

For detailed documentation on LightRAG core features, please refer to:

- [Original LightRAG README](https://github.com/HKUDS/LightRAG)
- [LightRAG Server API](./lightrag/api/README.md)
- [LightRAG Paper (arXiv)](https://arxiv.org/abs/2410.05779)

---

## 🙏 Credits

This is a fork of [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) with multi-user enhancements.

Original authors: The University of Hong Kong Data Science Lab (HKUDS)

---

## 📄 License

Same as the original LightRAG project.
