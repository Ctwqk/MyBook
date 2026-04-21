# MyBook

Long-form Chinese web novel generation system with a FastAPI backend, React frontend, and modular writing workflow.

MyBook is structured around planning, memory, writing, review, and publishing services. It is designed to move from premise-level setup to chapter generation and publishing-oriented workflows with persistent project state.

## Highlights

- Modular writing workflow: planner, memory, writer, reviewer, and publish services
- FastAPI backend with layered API / service / repository structure
- React + TypeScript frontend for project and chapter workflows
- Pluggable LLM-provider architecture
- PostgreSQL-backed persistence with documented architecture and workflow notes
- Docker Compose setup for local development

## Tech Stack

- Python 3.11
- FastAPI
- SQLAlchemy
- Pydantic
- PostgreSQL
- React
- TypeScript
- Ant Design
- Zustand
- Docker Compose
- pytest / pytest-asyncio

## Repository Layout

```text
backend/
├── app/api/routes/       # API routes
├── app/core/             # Settings and shared backend config
├── app/db/               # Database session and metadata
├── app/llm/              # LLM provider abstraction
├── app/models/           # Persistence models
├── app/repositories/     # Data-access layer
└── app/services/         # Planner / memory / writer / reviewer / publish logic

frontend/                 # React + TypeScript UI
docs/                     # Architecture and workflow docs
docker-compose.yml        # Local stack definition
```

## Quick Start

### Docker

```bash
docker compose up -d
```

Main endpoints:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8888`

### Local development

```bash
cd backend
python -m pip install -e .

cd ../frontend
npm install
```

Then run the backend and frontend separately in development mode.

## Architecture

The codebase follows a layered design:

- API layer for request handling and route wiring
- service layer for planning, memory, writing, reviewing, and publishing
- repository layer for data access
- LLM-provider layer for model abstraction

Additional design and workflow details are documented under `docs/`.

## Testing

Backend tests can be run with:

```bash
cd backend
pytest
```

## Notes

- The repository is centered on Chinese-language fiction workflows.
- The docs folder contains substantial design context and is useful if you want to understand the intended roadmap beyond the current implementation.
