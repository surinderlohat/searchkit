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
| ----------- | -------------------------- |
| Wrapper API | http://localhost:9000      |
| API Docs    | http://localhost:9000/docs |

---

## API Endpoints

### Health

```
GET /health
```

```json
{ "status": "ok", "chromadb": "embedded", "collections": 1 }
```

---

### Insert / Update — Single Document

```
POST /documents/upsert
```

```json
{
  "collection": "default",
  "id": "doc_1",
  "text": "Machine learning is a subset of artificial intelligence",
  "metadata": { "source": "wiki", "topic": "ai" }
}
```

```json
{
  "status": "ok",
  "message": "Upserted document 'doc_1' into 'default'. Total: 1"
}
```

---

### Insert / Update — Bulk Documents

```
POST /documents/upsert/bulk
```

```json
{
  "collection": "default",
  "documents": [
    {
      "id": "doc_1",
      "text": "Machine learning is a subset of AI",
      "metadata": { "source": "wiki" }
    },
    {
      "id": "doc_2",
      "text": "FastAPI is a modern Python web framework",
      "metadata": { "source": "blog" }
    }
  ]
}
```

```json
{ "status": "ok", "message": "Upserted 2 documents into 'default'. Total: 2" }
```

> Both endpoints behave as **upsert** — if the ID exists it gets updated, if not it gets inserted.

---

### Delete Documents

```
DELETE /documents/delete
```

```json
{
  "collection": "default",
  "ids": ["doc_1", "doc_2"]
}
```

```json
{
  "status": "ok",
  "message": "Deleted 2 documents from 'default'. Remaining: 0"
}
```

---

### Semantic Search

```
POST /search
```

```json
{
  "query": "what is artificial intelligence?",
  "top_k": 3,
  "collection": "default",
  "where": { "source": "wiki" }
}
```

```json
{
  "query": "what is artificial intelligence?",
  "total": 1,
  "results": [
    {
      "id": "doc_1",
      "text": "Machine learning is a subset of artificial intelligence",
      "metadata": { "source": "wiki", "topic": "ai" },
      "distance": 0.082
    }
  ]
}
```

> `where` is optional — use it to filter results by metadata fields.

---

### Collections

```
GET    /collections           # list all collections with document counts
GET    /collections/{name}    # get a specific collection
DELETE /collections/{name}    # drop an entire collection
```

---

## Environment Variables

| Variable             | Default                  | Description                       |
| -------------------- | ------------------------ | --------------------------------- |
| `CHROMA_PERSIST_DIR` | `/app/chromadb`          | Path where ChromaDB persists data |
| `EMBEDDING_MODEL`    | `BAAI/bge-small-en-v1.5` | SentenceTransformer model name    |
| `DEFAULT_COLLECTION` | `default`                | Default collection name           |

---

## Capacity Guide

Using the default `BAAI/bge-small-en-v1.5` model (384 dimensions):

| Records | RAM Required |
| ------- | ------------ |
| 100K    | ~1 GB        |
| 500K    | ~4 GB        |
| 1M      | ~8 GB        |
| 2M      | ~16 GB       |

> Recommended for up to **2 million records**. For larger scale, switch to a dedicated ChromaDB or Qdrant server.

---

## Docker Compose

```yaml
services:
  chroma-wrapper:
    image: yourname/chroma-wrapper:latest
    container_name: chroma-wrapper
    restart: unless-stopped
    ports:
      - "9000:9000"
    environment:
      - CHROMA_PERSIST_DIR=/app/chromadb
      - EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
      - DEFAULT_COLLECTION=default
    volumes:
      - chroma-data:/app/chromadb

volumes:
  chroma-data:
```

---

## How Your Main Service Uses This

```python
import httpx

async def insert_document(id: str, text: str, metadata: dict):
    async with httpx.AsyncClient() as client:
        await client.post("http://chroma-wrapper:9000/documents/upsert", json={
            "collection": "default",
            "id": id,
            "text": text,
            "metadata": metadata,
        })

async def search(query: str) -> list:
    async with httpx.AsyncClient() as client:
        res = await client.post("http://chroma-wrapper:9000/search", json={
            "query": query,
            "top_k": 5,
            "collection": "default",
        })
        return res.json()["results"]
```

Your main service never touches ChromaDB directly — it just calls HTTP endpoints.

---

## Author & License

Created by **Surinder Singh** — [github.com/surinderlohat](https://github.com/surinderlohat)

Licensed under the [MIT License](./LICENSE).
© 2025 Surinder Singh. All rights reserved.
