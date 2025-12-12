# Technology Stack

## Architecture Overview
Full-stack application with Python backend and Next.js frontend, designed for enterprise data analytics.

## Backend Stack
- **Framework**: FastAPI with Python 3.11+
- **Package Management**: uv (Python package manager)
- **Database**: 
  - SQLite/MySQL for metadata storage
  - DuckDB for analytics workloads
  - Qdrant for vector storage
- **Query Engine**: Apache Spark (primary), with pluggable architecture for other engines
- **AI/ML**: 
  - LangChain + LangGraph for LLM workflows
  - OpenAI-compatible APIs
  - Vector embeddings for semantic search
- **Monitoring**: Arize Phoenix for LLM observability, Langfuse for tracing
- **Task Scheduling**: APScheduler for background jobs
- **Real-time**: Kafka integration for streaming data

## Frontend Stack
- **Framework**: Next.js 14 with React 18
- **Language**: TypeScript
- **Styling**: Tailwind CSS + shadcn/ui components
- **Charts**: Recharts for data visualization
- **State Management**: React Context + custom hooks
- **Build Tool**: Built-in Next.js tooling

## Development Tools
- **Linting**: ESLint for frontend
- **Type Checking**: TypeScript strict mode
- **Package Managers**: uv for Python, npm/pnpm for Node.js

## Common Commands

### Backend Development
```bash
# Start backend server
./sbackend.sh
# Or manually:
cd backend && uv run uvicorn main:app --workers=2 --port 50020

# Install dependencies
uv sync

# Run with specific config
uv run python main.py
```

### Frontend Development
```bash
# Start frontend server
./sfrontend.sh
# Or manually:
cd frontend && npm run dev

# Install dependencies
npm install
# or
pnpm install

# Build for production
npm run build
npm run start
```

### Configuration
- Backend config: `backend/config/config.yaml` (copy from `.example`)
- Environment variables: `.env` files
- Frontend config: `frontend/next.config.mjs`

## Key Dependencies
- **Backend**: fastapi, langchain, langgraph, sqlalchemy, duckdb, qdrant-client
- **Frontend**: next, react, tailwindcss, recharts, @radix-ui components