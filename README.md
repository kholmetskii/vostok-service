# Vostok Service

Vostok Service is a warehouse-layout and routing application developed during a
Software Engineer internship. It models warehouse walkways as a weighted graph,
visualises each floor, and calculates routes between shelves while excluding paths
intersected by configured obstacles.

The repository is a portfolio project and a working prototype. It is not presented
as a production-ready warehouse management or safety system.

## Features

- Create, list, view, and delete warehouse records.
- Import a complete warehouse configuration from an Excel workbook.
- Export the current configuration as an `.xlsx` workbook.
- Visualise shelves and obstacles on a floor-by-floor canvas map.
- Optionally display graph nodes and edges; cross-floor edges are rendered as dashed lines.
- Calculate and highlight the shortest route between two shelves.
- Recalculate routes against the current obstacle configuration.
- Download all reachable shelf-to-shelf distances as newline-delimited JSON (JSONL).
- Validate configuration IDs, references, floor levels, dimensions, and warehouse bounds.

## Technology stack

| Area | Technologies |
| --- | --- |
| Frontend | React 19, Vite, React Router, React Konva, Axios, SheetJS (`xlsx`) |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy (async), asyncpg |
| Database | PostgreSQL 16, Alembic migrations |
| Tooling | Docker Compose, Nginx, pytest, Ruff, ESLint, GitHub Actions |

## Architecture

```text
Browser
  └─ React UI ── XLSX parsing/export and canvas rendering
       └─ /api (Nginx proxy)
            └─ FastAPI routes
                 └─ Application services and validation
                      └─ Unit of Work
                           └─ SQLAlchemy repositories
                                └─ PostgreSQL
                                     └─ Alembic migrations
```

The React frontend handles the user workflow, reads and writes Excel files in the
browser, and renders the warehouse with React Konva. FastAPI exposes warehouse,
configuration, routing, and distance-export endpoints. Application services contain
the use-case and graph logic. Repositories isolate SQLAlchemy persistence operations,
while the Unit of Work gives each service operation one transaction and centralises
commit or rollback. Alembic applies the PostgreSQL schema when the backend container
starts.

## Routing model

Each shelf references a graph node. Edges are undirected and weighted using the
two-dimensional Euclidean distance between their endpoint coordinates multiplied by
`weight_multiplier`. Dijkstra's algorithm selects the lowest-cost route.

Obstacles are line segments between nodes. Before each route calculation, the backend
builds the graph from the current database configuration and excludes same-floor edges
that geometrically intersect an obstacle. An edge and obstacle that share an endpoint
are allowed to meet at that node. This makes obstacle changes effective on the next
request without storing a separate blocked-edge cache.

Edges may connect nodes on different floors. They participate in routing and are shown
as dashed lines on each connected floor. Planar obstacle intersection checks do not
block cross-floor edges. Because edge length uses only `x`/`y` coordinates, a suitable
`weight_multiplier` is currently the only way to represent extra lift, stair, or ramp
cost.

## Run with Docker

### Prerequisites

- Docker Desktop, or Docker Engine with Docker Compose v2
- Ports `5432`, `8000`, and `8080` available, unless overridden in `.env`

### Start the application

```bash
git clone https://github.com/kholmetskii/vostok-service.git
cd vostok-service
cp .env.example .env
docker compose up --build
```

Change `POSTGRES_PASSWORD` in `.env` before starting if the database will be exposed
beyond a disposable local environment. The checked-in defaults are development values,
not production credentials.

Once the containers are healthy:

- Frontend: [http://localhost:8080](http://localhost:8080)
- Interactive API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- OpenAPI schema: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

Run in the background with `docker compose up -d --build`. Stop the application with
`docker compose down`. To also remove the local PostgreSQL volume and all application
data, use `docker compose down -v`.

### Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `POSTGRES_USER` | `vostok` | Local PostgreSQL user |
| `POSTGRES_PASSWORD` | `vostok-local` | Local PostgreSQL password |
| `POSTGRES_DB` | `vostok` | Local database name |
| `POSTGRES_PORT` | `5432` | Host database port |
| `BACKEND_PORT` | `8000` | Host API port |
| `FRONTEND_PORT` | `8080` | Host frontend port |

## Create and upload a warehouse configuration

1. Open the frontend and select **Create warehouse**.
2. Enter the warehouse name, width, length, and number of floors. Measurements are in metres.
3. Open the new warehouse and prepare an `.xlsx` workbook with four sheets named
   `nodes`, `shelves`, `edges`, and `obstacles` (sheet-name matching is case-insensitive).
4. Use the following first-row column names. Headers containing spaces are normalised
   to lowercase `snake_case`, but the names below are the clearest option.
5. Choose the file under **Warehouse Config (.xlsx)** and select **Upload & Apply**.

| Sheet | Required columns |
| --- | --- |
| `nodes` | `ext_id`, `floor_level`, `x_m`, `y_m` |
| `shelves` | `ext_id`, `floor_level`, `x_m`, `y_m`, `width_m`, `length_m`, `shelving_code`, `section_code`, `node_ext_id` |
| `edges` | `ext_id`, `from_node_ext_id`, `to_node_ext_id`; optional `weight_multiplier` defaults to `1.0` when omitted |
| `obstacles` | `ext_id`, `from_node_ext_id`, `to_node_ext_id` |

`ext_id` values are external IDs and must be unique within their sheet. Node references
must point to rows in the `nodes` sheet. Floor levels are one-based (`1` through the
warehouse's floor count). Node and shelf geometry must fit inside the warehouse bounds,
and shelf width and length must be positive.

Uploading is a full replacement, not a partial update: the workbook becomes the source
of truth for all nodes, shelves, edges, and obstacles in that warehouse. Validation and
replacement run inside one Unit of Work, so an exception rolls the transaction back.
After a successful upload, **Download XLSX** exports the stored configuration.

## Project structure

```text
.
├── backend/
│   ├── alembic/                 # Database migrations
│   ├── app/api/                 # FastAPI routes and schemas
│   ├── app/application/         # Services and configuration validation
│   ├── app/infrastructure/db/   # Models, repositories, session, Unit of Work
│   └── tests/                   # Synthetic routing, validation, and transaction tests
├── frontend/
│   ├── src/components/          # Map and workflow UI
│   ├── src/pages/               # Warehouse screens
│   ├── src/services/            # API client functions
│   └── src/utils/               # API and XLSX helpers
├── .github/workflows/ci.yml     # Backend and frontend checks
└── docker-compose.yml           # PostgreSQL, FastAPI, and Nginx/React services
```

## Development checks

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
ruff check app tests alembic/env.py
ruff format --check app tests alembic/env.py
python -m pytest
```

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm run build
```

GitHub Actions runs the same checks on pushes and pull requests. The unit tests use
small synthetic warehouse graphs and do not require PostgreSQL or external secrets.

## Screenshots and demo

Screenshots are not committed yet. Before featuring the repository, capture these with
synthetic warehouse data only:

1. **Warehouse list and creation** — the list plus the create form with sample dimensions.
2. **Obstacle-aware route** — a floor map showing shelves, an orange obstacle, graph edges,
   and the selected route highlighted in red.
3. **Multi-floor route** — the same route viewed on two floors, including a dashed
   cross-floor edge.
4. **Configuration workflow** — the XLSX upload/download controls and a successful map refresh.
5. **API documentation** — the FastAPI `/docs` page with the warehouse endpoints expanded.

Recommended filenames are `docs/screenshots/warehouse-list.png`,
`obstacle-route.png`, `cross-floor-route.png`, `xlsx-workflow.png`, and `api-docs.png`.
A short GIF showing XLSX upload followed by route calculation would also make a useful demo.

## Known limitations

- There is no authentication, authorisation, audit trail, or multi-tenant isolation.
- The UI is a functional prototype with a fixed map scale; it does not provide pan/zoom,
  responsive layout optimisation, or accessibility coverage.
- Configuration import replaces the whole graph and does not provide partial editing or preview.
- Cross-floor cost has no explicit vertical-distance model; configure a multiplier to represent it.
- Obstacles come from the uploaded configuration. There is no live sensor or real-time event feed.
- The current `xlsx` package has published prototype-pollution and ReDoS advisories, and npm reports
  no patched release. Only trusted workbooks should be opened until the dependency is replaced.
- Unreachable shelf pairs are omitted from the JSONL export rather than emitted with a null distance.
- Tests cover core logic and transaction boundaries, but not a live PostgreSQL migration cycle or
  end-to-end browser workflow.
- CORS and container settings target local development, and no production deployment is included.

## Possible improvements

- Add API integration tests against PostgreSQL and browser-level tests for the main workflow.
- Add pan, zoom, responsive styling, and clearer user-facing route errors.
- Add a configuration preview/diff before replacing warehouse data.
- Model explicit vertical travel costs and connector types for cross-floor routes.
- Add authentication and role-based access if the application moves beyond a local prototype.
- Move large all-pairs distance exports to a background job with progress reporting.
