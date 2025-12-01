# Taosha Analyse Platform - Project Context for Gemini

## Project Overview
Taosha Analyse Platform (淘沙分析平台) is an AI-driven business intelligence platform. It converts natural language queries into SQL, provides agent-based conversational capabilities with tool integration, and manages metadata.

**Key Components:**
*   **Backend:** FastAPI service handling NL2SQL, Agent conversations (LangChain/LangGraph), and metadata management.
*   **Frontend:** Next.js (React) application with real-time streaming UI (Vercel AI SDK).
*   **Database:** DuckDB (OLAP), SQLite/MySQL (Metadata), Qdrant (Vector Store).

## Directory Structure
*   `backend/`: Python backend source code.
    *   `api/`: FastAPI route handlers.
    *   `services/`: Core business logic (Agents, NLQuery, etc.).
    *   `models/`: SQLAlchemy ORM models.
    *   `config/`: Configuration files (`config.yaml`).
*   `frontend/`: Next.js frontend source code.
    *   `app/`: App Router pages.
    *   `components/`: React components.
    *   `lib/`: Utilities and API services.
*   `docs/`: Documentation and design files.
*   `testcases/`: Pytest test suites.
*   `scripts/`: Utility scripts.

## Development Workflow

### Prerequisites
*   **Python:** 3.11+ (Managed by `uv`)
*   **Node.js:** (Managed by `npm`)

### Setup & Installation
1.  **Backend:**
    ```bash
    # Install dependencies
    uv sync
    # Or
    pip install -r requirements-lock.txt
    ```
2.  **Frontend:**
    ```bash
    cd frontend
    npm install
    ```

### Running the Application
**Option 1: Shell Scripts (Recommended)**
*   **Backend:** `./sbackend.sh` (Starts on port 50020)
*   **Frontend:** `./sfrontend.sh` (Starts on port 3000)

**Option 2: Manual Start**
*   **Backend:**
    ```bash
    cd backend
    uv run uvicorn main:app --workers=2 --port 50020
    ```
*   **Frontend:**
    ```bash
    cd frontend
    npm run dev
    ```

### Testing
*   **Backend Tests:**
    ```bash
    pytest testcases/
    ```
*   **Frontend Linting:**
    ```bash
    cd frontend
    npm run lint
    ```

## Key Technologies & Libraries
*   **Backend:** FastAPI, LangChain, LangGraph, SQLAlchemy, Pydantic, DuckDB, Qdrant Client.
*   **Frontend:** Next.js 14, React 18, Tailwind CSS, Radix UI, Vercel AI SDK (Streaming), Axios.
*   **Observability:** Langfuse.

## Configuration
*   Main configuration is in `backend/config/config.yaml`.
*   Environment variables are handled via `.env` files and `uv` / `npm` configurations.
