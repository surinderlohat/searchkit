# ChromaDB Wrapper Service

Single-container FastAPI service with **embedded ChromaDB**. No separate ChromaDB container needed — everything runs in one service, data persists via a Docker volume.

## Architecture

```
Your Main Service
      │
      ▼  HTTP
chroma-wrapper (FastAPI :9000)
   └── ChromaDB (embedded, in-process)
         │
         ▼
   chroma-data (Docker volume)
```

## Quick Start

```bash
docker compose up -d
```

| Service     | URL                        |
|-------------|----------------------------|
| Wrapper API | http://localhost:9000      |
| API Docs    | http://localhost:9000/docs |

---

## API Endpoints

### Health
```
GET /health
```

### Documents

**Upsert (add or update):**
```bash
curl -X POST http://localhost:9000/documents/upsert \
  -H "Content-Type: application/json" \
  -d '{
    "ids": ["doc_1", "doc_2"],
    "documents": ["Machine learning is a subset of AI", "FastAPI is a modern web framework"],
    "metadatas": [{"source": "wiki"}, {"source": "blog"}],
    "collection": "default"
  }'
```

**Delete:**
```bash
curl -X DELETE http://localhost:9000/documents/delete \
  -H "Content-Type: application/json" \
  -d '{"ids": ["doc_1"], "collection": "default"}'
```

### Search
```bash
curl -X POST http://localhost:9000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "what is artificial intelligence?",
    "top_k": 5,
    "collection": "default"
  }'
```

### Collections
```
GET    /collections          # list all
GET    /collections/{name}   # get one
DELETE /collections/{name}   # drop one
```

---

## Environment Variables

| Variable             | Default                  | Description                    |
|----------------------|--------------------------|--------------------------------|
| `CHROMA_PERSIST_DIR` | `/app/chromadb`          | Where ChromaDB stores data     |
| `EMBEDDING_MODEL`    | `BAAI/bge-small-en-v1.5` | SentenceTransformer model name |
| `DEFAULT_COLLECTION` | `default`                | Default collection name        |
