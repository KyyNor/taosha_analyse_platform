# Repository Guidelines

This guide helps contributors and agents work productively in this repo.

## Project Structure & Modules
- `backend/` FastAPI service (entry: `backend/main.py`).
  - `api/` routers, request/response models; `config/` settings; `services/` DB/NL2SQL; `utils/`; `database/` dev data.
  - Env files: `backend/.env`, `backend/.env.example`.
- `vue_devops/` Vue 3 + Vite front end.
  - `src/` components, views, router, stores, styles.
- Root: `pyproject.toml`, `uv.lock` (Python deps), `README.md`.

## Build, Test, and Development Commands
- Prereqs: Python 3.11, Node 18+, `uv` (recommended) and `npm`.
- Python deps: run at repo root: `uv sync`.
- Backend dev: `cd backend && uv run python main.py` (starts Uvicorn with debug reload per settings) or `uv run uvicorn main:app --reload`.
- Frontend dev: `cd vue_devops && npm ci && npm run dev`.
- Frontend build/preview: `npm run build` / `npm run preview`.
- Tests (Python): `uv run pytest -q`.

## Coding Style & Naming Conventions
- Python: PEP 8, 4‑space indent, type hints. Names: `snake_case` (functions/vars), `PascalCase` (classes), `UPPER_SNAKE_CASE` (constants). Prefer `loguru` logger; avoid `print`.
- Vue/TS: `<script setup lang="ts">`, components in `PascalCase` (e.g., `ResultDisplay.vue`), composables/utilities in `camelCase.ts`.
- Linting: Frontend `npm run lint` (ESLint). Python: follow repository style; no formatter is enforced—keep imports/typing consistent.

## Testing Guidelines
- Framework: `pytest` for backend.
- Location: add tests under `backend/tests/` mirroring module paths; filenames `test_*.py`.
- Run examples: `uv run pytest -k tracking`, `uv run pytest backend/tests/test_routes.py -q`.
- Target: prioritize API routers, services, and config parsing.

## Commit & PR Guidelines
- Commits: short, imperative; Chinese or English okay. Use optional scopes like `backend:`/`frontend:` (e.g., `backend: 增强操作日志步骤明细显示功能`).
- PRs: include summary, rationale, how-to-test, and screenshots for UI. Link issues. Avoid committing large binaries or generated artifacts; do not modify `backend/database/*` unless required and documented.

## Security & Config Tips
- Copy `backend/.env.example` to `backend/.env`; never commit secrets. Review `backend/config/settings.py` for available variables (e.g., paths for DuckDB/ChromaDB, log level, debug).
- CORS is open in dev; restrict origins for production.

