# GraphBus Starter Project

The official reference app for [graphbus.com](https://graphbus.com) — a full-stack task manager built with **GraphBus agents**, FastAPI, React, Docker, and Kubernetes.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│   Login ─── Register ─── Dashboard (TaskList + TaskForm)        │
└──────────────────────────┬──────────────────────────────────────┘
                           │  HTTP / JSON
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI  /api/*                              │
│  /auth/register  /auth/login  /auth/me  /tasks  /tasks/{id}    │
└──────────┬──────────┬──────────┬────────────────────────────────┘
           │          │          │
           ▼          ▼          ▼
┌──────────────┐ ┌──────────┐ ┌───────────────┐ ┌────────────────┐
│ Registration │ │   Auth   │ │ TaskManager   │ │ Notification   │
│    Agent     │ │  Agent   │ │    Agent      │ │    Agent       │
└──────┬───────┘ └────┬─────┘ └───────┬───────┘ └───────┬────────┘
       │              │               │                  │
       └──────────────┴───────────────┴──────────────────┘
                           │
                    ┌──────┴──────┐
                    │  MessageBus │  (pub/sub)
                    └──────┬──────┘
                           │
              Topics: /Auth/UserRegistered
                      /Auth/LoginSucceeded
                      /Tasks/Created
                      /Tasks/Updated
                      /Tasks/Deleted
```

## Quick Start (Docker Compose)

```bash
cp .env.example .env
docker-compose up --build
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Health check**: http://localhost:8000/api/health

## Local Development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs on http://localhost:3000 and proxies API calls to the backend on port 8000.

## Project Structure

```
graphbus-starter-project/
├── backend/
│   ├── agents/                  # GraphBus agent implementations
│   │   ├── auth_agent.py        # UserRegistrationAgent + AuthAgent
│   │   ├── task_agent.py        # TaskManagerAgent
│   │   └── notification_agent.py
│   ├── graphbus_core_mock.py    # Lightweight GraphBusNode base (no pip install)
│   ├── main.py                  # FastAPI routes
│   ├── database.py              # SQLAlchemy models (SQLite)
│   ├── auth.py                  # JWT helpers
│   ├── build.py                 # GraphBus build mode entry point
│   ├── run.py                   # Runtime bootstrap (bus + agent wiring)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/               # Login, Register, Dashboard
│   │   ├── components/          # TaskList, TaskForm
│   │   └── api/client.ts        # Typed fetch-based API client
│   └── ...
├── k8s/                         # Kubernetes manifests
├── docker-compose.yml
└── .env.example
```

## GraphBus Agent Guide

### How agents work

Every agent extends `GraphBusNode` from `graphbus_core_mock.py`. Agents:

1. Declare a `SYSTEM_PROMPT` describing their role (used by LLM build mode).
2. Use `@schema_method` to document input/output contracts.
3. Use `@subscribe("/Topic/Name")` to react to events from other agents.
4. Call `self.publish("/Topic/Name", payload)` to emit domain events.

### Adding a new agent

1. Create `backend/agents/my_agent.py`:

```python
from graphbus_core_mock import GraphBusNode, schema_method, subscribe

class MyAgent(GraphBusNode):
    SYSTEM_PROMPT = "You are MyAgent. You handle X and publish /My/Event."

    @subscribe("/Auth/UserRegistered")
    def on_user_registered(self, payload: dict):
        # React to new users
        ...

    @schema_method(
        input_schema={"data": str},
        output_schema={"result": str},
    )
    def do_something(self, data: str) -> dict:
        self.publish("/My/Event", {"data": data})
        return {"result": "done"}
```

2. Register it in `backend/run.py`:

```python
from agents.my_agent import MyAgent
my_agent = MyAgent(bus=bus)
_agents.append(my_agent)
```

3. Add routes in `backend/main.py` that delegate to your agent.

### Build Mode (LLM negotiation)

When `graphbus` is installed (`pip install graphbus`), run:

```bash
cd backend
python build.py
```

Build mode lets an LLM read every agent's `SYSTEM_PROMPT`, `@schema_method` contracts, and `@depends_on` declarations to propose improvements. Agents negotiate changes to schemas and behaviour before code is generated.

Set at least one LLM key in `.env`:
- `DEEPSEEK_API_KEY`
- `ANTHROPIC_API_KEY`

## Kubernetes Deployment

```bash
# Create namespace and apply manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml

# IMPORTANT: Update the secret before deploying
# Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
# Encode:   echo -n 'your-secret' | base64
# Then edit k8s/secrets.yaml with the real value
kubectl apply -f k8s/secrets.yaml

kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml
kubectl apply -f k8s/ingress.yaml
```

The ingress routes `starter.graphbus.com` to the frontend, with `/api/*` proxied to the backend.

## API Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | No | Register a new user |
| POST | `/api/auth/login` | No | Login and get JWT |
| GET | `/api/auth/me` | Yes | Get current user profile |
| GET | `/api/tasks` | Yes | List user's tasks |
| POST | `/api/tasks` | Yes | Create a new task |
| PUT | `/api/tasks/{id}` | Yes | Update a task |
| DELETE | `/api/tasks/{id}` | Yes | Delete a task |
| GET | `/api/health` | No | Health check |

## Links

- [graphbus.com](https://graphbus.com) — GraphBus platform
- [graphbus/graphbus-core](https://github.com/graphbus/graphbus-core) — Core library

## License

MIT
