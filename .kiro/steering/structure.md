# Project Structure

## Root Directory Layout
```
├── backend/           # Python FastAPI backend
├── frontend/          # Next.js React frontend  
├── docs/             # Project documentation
├── scripts/          # Utility scripts
├── .kiro/            # Kiro IDE configuration
├── .claude/          # Claude AI agent configurations
└── .trae/            # Additional documentation
```

## Backend Structure (`backend/`)
```
backend/
├── main.py                    # FastAPI application entry point
├── api/                       # API route definitions
│   ├── nlquey_routes.py      # Natural language query endpoints
│   ├── metadata_routes.py    # Metadata management APIs
│   ├── agents_routes.py      # AI agent endpoints
│   └── fraudhunter/          # FraudHunter module APIs
├── models/                    # SQLAlchemy ORM models
│   ├── db_base.py            # Database base configuration
│   └── fraudhunter/          # FraudHunter data models
├── services/                  # Business logic layer
│   ├── agents/               # AI agent services
│   ├── nlquery_service/      # Natural language processing
│   ├── query_engine/         # Database query abstraction
│   ├── vector_store/         # Vector database operations
│   └── fraudhunter/          # FraudHunter business logic
├── repositories/              # Data access layer
├── schemas/                   # Pydantic request/response schemas
├── utils/                     # Utility functions
│   ├── config.py             # Configuration management
│   └── logger.py             # Logging setup
├── config/                    # Configuration files
└── database/                  # Local database files
```

## Frontend Structure (`frontend/`)
```
frontend/
├── app/                       # Next.js 14 app router
│   ├── (main)/               # Main application layout
│   │   ├── agent/            # AI chat interface
│   │   ├── nlquery/          # Natural language query UI
│   │   ├── metadata/         # Metadata management UI
│   │   └── fraudhunter/      # FraudHunter module UI
│   ├── layout.tsx            # Root layout
│   └── page.tsx              # Home page
├── components/                # Reusable React components
│   ├── ui/                   # shadcn/ui base components
│   ├── agent/                # AI chat components
│   ├── common/               # Shared components
│   └── generative_ui/        # Dynamic UI components
├── lib/                       # Utility libraries
│   ├── services/             # API service functions
│   ├── state/                # React context providers
│   └── utils/                # Helper functions
├── types/                     # TypeScript type definitions
├── styles/                    # Global CSS styles
└── public/                    # Static assets
```

## Key Architectural Patterns

### Backend Patterns
- **Layered Architecture**: API → Services → Repositories → Models
- **Dependency Injection**: FastAPI's dependency system for database sessions
- **Plugin Architecture**: Pluggable query engines and AI services
- **Event-Driven**: Background tasks and real-time data processing
- **Configuration Management**: YAML-based config with Pydantic validation

### Frontend Patterns
- **App Router**: Next.js 14 file-based routing
- **Component Composition**: Radix UI + shadcn/ui design system
- **State Management**: React Context for global state, local state for components
- **Service Layer**: Centralized API calls in `lib/services/`
- **Type Safety**: Strict TypeScript configuration

### File Naming Conventions
- **Backend**: Snake case (`nlquery_service.py`, `metadata_routes.py`)
- **Frontend**: Camel case for files (`ChatInput.tsx`), kebab case for routes (`/metadata/fine-reports`)
- **Components**: PascalCase (`ChatMessagesArea.tsx`)
- **Services**: Descriptive names ending in `Service` or `Manager`

### Module Organization
- **Feature-based**: Each major feature (nlquery, metadata, fraudhunter) has its own directory structure
- **Shared utilities**: Common functionality in `utils/` and `lib/`
- **Clear separation**: API, business logic, and data access layers are distinct
- **Modular services**: Each service is self-contained with clear interfaces

### Configuration Files
- `backend/config/config.yaml.example` - Backend configuration template
- `frontend/.env.local.example` - Frontend environment variables template
- `pyproject.toml` - Python project configuration
- `frontend/package.json` - Node.js dependencies and scripts