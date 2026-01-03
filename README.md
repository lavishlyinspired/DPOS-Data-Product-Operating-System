# DPOS - Data Product Operating System

A comprehensive data product management platform built with FastAPI, Neo4j, and React. Features AI-powered agents using LangGraph for automated data governance, quality monitoring, and incident response.

## Features

- **Data Products Catalog**: Manage and discover data products across your organization
- **Data Contracts**: Define producer-consumer agreements with SLA enforcement
- **Data Lineage**: Trace data flow and understand dependencies
- **Quality Monitoring**: Track data quality metrics and health scores
- **Incident Management**: Automated incident detection and AI-powered remediation
- **Policy Enforcement**: Define and enforce data governance policies
- **AI Agents**: Intelligent agents for discovery, Q&A, impact analysis, and self-healing
- **Marketplace**: Discover and subscribe to data products

## Architecture

```
dpos-ecommerce/
├── src/
│   ├── api/              # FastAPI backend
│   ├── agents/           # LangGraph AI agents
│   ├── graph/            # Neo4j graph database
│   ├── contracts/        # Data contract validation
│   ├── enforcement/      # Policy enforcement engine
│   ├── marketplace/      # Semantic search marketplace
│   └── observability/    # Metrics and monitoring
├── frontend/             # React + Vite frontend
├── tests/                # Test suites
├── scripts/              # Utility scripts
└── docs/                 # Documentation
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- Neo4j 5.x (optional, for full functionality)
- Ollama (optional, for AI embeddings)

## Quick Start

### 1. Clone and Setup

```bash
cd dpos-ecommerce

# Create Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Ollama Configuration (optional)
OLLAMA_BASE_URL=http://localhost:11434

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

### 3. Start Services

#### Option A: Start Both (Full Stack)

Windows:
```bash
scripts\start_all.bat
```

Linux/macOS:
```bash
./scripts/start_all.sh
```

#### Option B: Start Separately

**Backend:**
```bash
python scripts/start_backend.py
```

**Frontend:**
```bash
cd frontend
npm run dev
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## AI Agents

The platform includes several LangGraph-powered agents:

| Agent | Description |
|-------|-------------|
| **Discovery Agent** | Discovers and catalogs data assets |
| **Q&A Agent** | Answers questions about data products |
| **Impact Agent** | Analyzes change impact across lineage |
| **Healing Agent** | Auto-remediates data quality issues |
| **Steward Agent** | Manages data quality assessments |

### Agent Features

- **Checkpointing**: All agents support persistence and resumability
- **Conditional Routing**: Intelligent decision-making based on context
- **Human-in-the-Loop**: Support for human approval workflows
- **Retry Policies**: Automatic retry for transient failures

## Testing

```bash
# Run all tests
pytest

# Run E2E tests
pytest tests/e2e -s

# Run with coverage
pytest --cov=src tests/
```

## API Endpoints

### Dashboard
- `GET /api/dashboard/stats` - Get dashboard statistics

### Products
- `GET /api/products` - List all products
- `GET /api/products/{id}` - Get product details
- `GET /api/products/{id}/health` - Get product health score

### Contracts
- `GET /api/contracts` - List all contracts
- `GET /api/contracts/{id}/rules` - Get contract rules
- `POST /api/validate` - Validate data against contract

### Lineage
- `GET /api/lineage/{product_id}` - Get product lineage
- `GET /api/lineage/{product_id}/impact` - Get impact analysis

### Incidents
- `GET /api/incidents` - List all incidents
- `POST /api/incidents/{id}/handle` - Handle incident with AI agent

### Agents
- `POST /api/agents/discovery` - Run discovery agent
- `POST /api/agents/qa` - Run Q&A agent
- `POST /api/agents/impact` - Run impact analysis agent
- `POST /api/agents/healing` - Run healing agent

### Marketplace
- `GET /api/marketplace/search?q={query}` - Search marketplace

## Development

### Project Structure

- `src/api/main.py` - FastAPI application entry point
- `src/agents/enhanced_agents.py` - LangGraph agent implementations
- `src/graph/manager.py` - Neo4j database manager
- `frontend/src/` - React application source

### Code Style

```bash
# Format Python code
black src/ tests/

# Lint Python code
flake8 src/ tests/

# Format frontend code
cd frontend && npm run lint
```

## Documentation

- [Complete Technical Document](docs/DPOS_COMPLETE_TECHNICAL_DOCUMENTATION.md)
- [Complete Implemetation Grounded Walkthough](docs/DPOS_walkthrough.md)

## License

MIT License
