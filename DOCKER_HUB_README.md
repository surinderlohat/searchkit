# SearchKit

> **Plug-in vector search for any stack — one container, zero config, production ready.**

A lightweight, production-ready **FastAPI wrapper** around embedded ChromaDB for semantic search and vector storage. Drop it into any stack via a single Docker container — no separate ChromaDB server needed.

---

## What Can You Build With This?

This service acts as a **dedicated semantic search layer** that sits alongside your main application. Here are some real-world use cases:

🔍 **AI-Powered Search** — replace keyword search in your app with meaning-based search. Users search for _"comfortable running shoes"_ and find relevant products even if the description says _"lightweight athletic footwear"_.

🤖 **RAG (Retrieval-Augmented Generation)** — feed relevant context to your LLM before generating a response. Store your documents here, search by query, pass top results to GPT/Claude as context.

📄 **Document Similarity** — find related articles, tickets, or records. _"Show me support tickets similar to this one"_ or _"find blog posts related to this topic"_.

🛒 **Product Recommendations** — embed product descriptions and find semantically similar items. _"Customers who viewed this also liked..."_ without collaborative filtering.

💬 **FAQ & Chatbot Matching** — match user questions to the closest FAQ entry or support article, even when the wording is completely different.

🏷️ **Smart Tagging & Categorisation** — automatically classify incoming content by comparing it against category embeddings.

---

## Features

- 🔍 **Semantic search** via REST API
- 📦 **Embedded ChromaDB** — single container, no extra services
- 💾 **Persistent storage** via Docker volume — survives restarts
- 🔒 **Safe concurrent writes** via async locking
- 🧠 **Auto embedding generation** using `BAAI/bge-small-en-v1.5`
- 📚 **Multi-collection** support
- 📖 **Auto-generated API docs** at `/docs`

---

## Quick Start

```bash
docker run -d \
  --name searchkit \
  -p 9000:9000 \
  -v chroma-data:/app/chromadb \
  surinderlohat/searchkit:latest
```

Or with Docker Compose:

```yaml
services:
  searchkit:
    image: surinderlohat/searchkit:latest
    container_name: searchkit
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

## API Endpoints

Full interactive docs at **`http://localhost:9000/docs`**

### Insert / Update — Single Document

```bash
curl -X POST http://localhost:9000/documents/upsert \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "default",
    "id": "doc_1",
    "text": "Machine learning is a subset of artificial intelligence",
    "metadata": { "source": "wiki", "topic": "ai" }
  }'
```

### Insert / Update — Bulk Documents

```bash
curl -X POST http://localhost:9000/documents/upsert/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "default",
    "documents": [
      { "id": "doc_1", "text": "Machine learning is a subset of AI", "metadata": { "source": "wiki" } },
      { "id": "doc_2", "text": "FastAPI is a modern Python web framework", "metadata": { "source": "blog" } }
    ]
  }'
```

### Semantic Search

```bash
curl -X POST http://localhost:9000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "what is artificial intelligence?",
    "top_k": 5,
    "collection": "default",
    "where": { "source": "wiki" }
  }'
```

### Delete Documents

```bash
curl -X DELETE http://localhost:9000/documents/delete \
  -H "Content-Type: application/json" \
  -d '{ "collection": "default", "ids": ["doc_1"] }'
```

### Collections

```
GET    /collections           # list all
GET    /collections/{name}    # get one
DELETE /collections/{name}    # drop one
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

| Records | RAM Required |
| ------- | ------------ |
| 100K    | ~1 GB        |
| 500K    | ~4 GB        |
| 1M      | ~8 GB        |
| 2M      | ~16 GB       |

---

## Tags

| Tag      | Description                   |
| -------- | ----------------------------- |
| `latest` | Latest stable build from main |
| `1.x.x`  | Specific release version      |

---

## Acknowledgements

This project is built on the shoulders of some fantastic open source tools and models. Huge thanks to the teams and communities behind them:

| Tool                                                                       | What it does in this project                                                       |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 🤗 [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5) | The embedding model that powers semantic search — fast, accurate, and CPU-friendly |
| 🟣 [ChromaDB](https://www.trychroma.com)                                   | The embedded vector store that handles storage, indexing, and similarity search    |
| ⚡ [FastAPI](https://fastapi.tiangolo.com)                                 | The web framework powering the REST API and auto-generated Swagger docs            |
| 🐳 [Docker](https://www.docker.com)                                        | Containerisation that makes the whole service portable and production-ready        |
| 🐙 [GitHub Actions](https://github.com/features/actions)                   | CI/CD pipeline for automated linting, building, and publishing to Docker Hub       |
| 🤗 [Sentence Transformers](https://www.sbert.net)                          | Python library that makes embedding generation simple and model-agnostic           |
| 🔥 [PyTorch](https://pytorch.org)                                          | The deep learning backbone that runs the embedding model                           |
| 🦄 [Uvicorn](https://www.uvicorn.org)                                      | The lightning-fast ASGI server that runs FastAPI in production                     |
| ✅ [Pydantic](https://docs.pydantic.dev)                                   | Data validation and serialisation for all request and response models              |
| 🐍 [psutil](https://github.com/giampaolo/psutil)                           | System memory monitoring to keep the service within safe RAM limits                |
| 🧹 [Ruff](https://docs.astral.sh/ruff)                                     | Blazing-fast Python linter and formatter that keeps the codebase clean             |

---

## Author & License

Created by **Surinder Singh** — [github.com/surinderlohat](https://github.com/surinderlohat)

Licensed under the [MIT License](https://github.com/surinderlohat/searchkit/blob/main/LICENSE).
© 2026 Surinder Singh. All rights reserved.
