.PHONY: format lint check run dev

# ── Formatting ─────────────────────────────────────────────

format:
	ruff format app/

lint:
	ruff check app/

lint-fix:
	ruff check app/ --fix

# Run both format + lint check (use before committing)
check:
	ruff format app/ --check
	ruff check app/

# ── Local Dev ──────────────────────────────────────────────

run:
	export $$(cat .env.local | xargs) && uvicorn app.main:app --host 0.0.0.0 --port 9000

dev:
	export $$(cat .env.local | xargs) && uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload

# ── Docker ─────────────────────────────────────────────────

docker-up:
	docker compose up -d

docker-build:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f chroma-wrapper
