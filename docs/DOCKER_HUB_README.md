# LightRAG Multi-User Edition

RAG system with multi-user workspace isolation, rate limiting, and full PostgreSQL storage.

## 🚀 Quick Start

```bash
docker run -d -p 9621:9621 \
  -e LLM_BINDING=gemini \
  -e LLM_MODEL=gemini-2.0-flash \
  -e LLM_BINDING_API_KEY=your_gemini_key \
  -e EMBEDDING_BINDING=gemini \
  -e EMBEDDING_MODEL=gemini-embedding-001 \
  -e EMBEDDING_DIM=768 \
  -e EMBEDDING_BINDING_API_KEY=your_gemini_key \
  kisotama/lightrag-multi:latest
```

Access WebUI: <http://localhost:9621>

## 📦 Full Stack (PostgreSQL + Redis)

Create a `docker-compose.yml` file:

```yaml
services:
  lightrag:
    image: kisotama/lightrag-multi:latest
    ports:
      - "9621:9621"
    volumes:
      - ./data:/app/data
    environment:
      LLM_BINDING: gemini
      LLM_MODEL: gemini-2.0-flash
      LLM_BINDING_API_KEY: your_gemini_key_here
      EMBEDDING_BINDING: gemini
      EMBEDDING_MODEL: gemini-embedding-001
      EMBEDDING_DIM: 768
      EMBEDDING_BINDING_API_KEY: your_gemini_key_here
      POSTGRES_HOST: postgres
      REDIS_URI: redis://redis:6379
      LIGHTRAG_KV_STORAGE: PGKVStorage
      LIGHTRAG_DOC_STATUS_STORAGE: PGDocStatusStorage
      LIGHTRAG_GRAPH_STORAGE: NetworkXStorage
      LIGHTRAG_VECTOR_STORAGE: PGVectorStorage
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: rag_user
      POSTGRES_PASSWORD: rag_password
      POSTGRES_DB: lightrag_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rag_user -d lightrag_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

Then run:

```bash
docker-compose up -d
```

## ✨ Features

- 👥 **Multi-user workspaces** - Each user has isolated data
- 🚦 **Redis rate limiting** - Protect against abuse
- 🐘 **PostgreSQL storage** - Production-ready persistence
- 🔐 **JWT authentication** - Auto-logout on server restart
- 📊 **Knowledge graph** - Interactive visualization
- 🔍 **RAG queries** - Local, global, hybrid, and mix modes

## 🔧 Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_BINDING` | LLM provider | `gemini`, `openai`, `ollama` |
| `LLM_MODEL` | Model name | `gemini-2.0-flash` |
| `LLM_BINDING_API_KEY` | API key | Your API key |
| `EMBEDDING_BINDING` | Embedding provider | `gemini`, `openai` |
| `EMBEDDING_MODEL` | Model name | `gemini-embedding-001` |
| `EMBEDDING_DIM` | Embedding dimension | `768` |
| `AUTH_ACCOUNTS` | User accounts | `admin:password,user:pass` |

## 📚 Documentation

- [GitHub Repository](https://github.com/JKisotama/LightRAG)
- [Original LightRAG](https://github.com/HKUDS/LightRAG)

## 📝 License

MIT License - Fork of [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG)
