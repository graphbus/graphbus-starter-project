# GraphBus Starter Project

The official reference app for [graphbus.com](https://graphbus.com) — a full-stack task manager built with **GraphBus agents**, FastAPI, React, Docker, and Kubernetes.

> **This app requires a GraphBus API key.** Get yours free at [graphbus.com/onboarding](https://graphbus.com/onboarding).

---

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

---

## Step 1 — Get your GraphBus API key

```
https://graphbus.com/onboarding
```

The app **will not start** without a valid `GRAPHBUS_API_KEY`. The key is free and takes 30 seconds to get.

---

## Quick Start (Docker Compose)

```bash
git clone https://github.com/graphbus/graphbus-starter-project.git
cd graphbus-starter-project

cp .env.example .env
# Open .env and fill in your GRAPHBUS_API_KEY

docker-compose up --build
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Health check**: http://localhost:8000/api/health

---

## Local Development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # fill in GRAPHBUS_API_KEY
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs on http://localhost:3000 and proxies API calls to the backend.

---

## Project Structure

```
graphbus-starter-project/
├── backend/
│   ├── agents/                  # GraphBus agents
│   │   ├── auth_agent.py        # UserRegistrationAgent + AuthAgent
│   │   ├── task_agent.py        # TaskManagerAgent
│   │   └── notification_agent.py
│   ├── main.py                  # FastAPI routes (delegates to agents)
│   ├── database.py              # SQLAlchemy models (SQLite)
│   ├── auth.py                  # JWT helpers
│   ├── build.py                 # GraphBus Build Mode entry point
│   ├── run.py                   # Runtime bootstrap (bus + agent wiring)
│   └── requirements.txt         # Includes `graphbus`
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

---

## GraphBus Agent Guide

### How agents work

Every agent extends `GraphBusNode` from the `graphbus` package (`pip install graphbus`). Agents:

1. Declare a `SYSTEM_PROMPT` describing their role (used in LLM Build Mode).
2. Use `@schema_method` to document typed input/output contracts.
3. Use `@subscribe("/Topic/Name")` to react to events from other agents.
4. Call `self.publish("/Topic/Name", payload)` to emit domain events.

### Adding a new agent

**1.** Create `backend/agents/my_agent.py`:

```python
from graphbus_core import GraphBusNode, schema_method, subscribe

class MyAgent(GraphBusNode):
    SYSTEM_PROMPT = (
        "You are MyAgent. You handle X and publish /My/Event. "
        "In Build Mode you can propose: better validation, retry logic."
    )

    @subscribe("/Auth/UserRegistered")
    def on_user_registered(self, payload: dict) -> None:
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

**2.** Register it in `backend/run.py`:

```python
from agents.my_agent import MyAgent
my_agent = MyAgent(bus=bus)
_agents.append(my_agent)
```

**3.** Add routes in `backend/main.py` that delegate to your agent methods.

---

## Build Mode (LLM negotiation)

Build Mode lets agents read each other's `SYSTEM_PROMPT` and `@schema_method` contracts, then propose and vote on improvements. Changes are committed directly to your source files.

```bash
# In your .env, also set an LLM provider key:
#   DEEPSEEK_API_KEY=...   ← recommended (deepseek-reasoner)
#   ANTHROPIC_API_KEY=...
#   OPENROUTER_API_KEY=...

cd backend
python build.py
python build.py --dry-run   # analyse only, no writes
```

Both `GRAPHBUS_API_KEY` and an LLM key are required. Negotiation history is stored in your GraphBus account and queryable via [graphbus.com](https://graphbus.com).

---

## Kubernetes Deployment

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml

# Fill in your real keys before applying secrets:
#   GRAPHBUS_API_KEY: echo -n 'gb_your_key' | base64
#   SECRET_KEY:       python -c "import secrets; print(secrets.token_urlsafe(32))" | tr -d '\n' | base64
# Edit k8s/secrets.yaml with those values, then:
kubectl apply -f k8s/secrets.yaml

kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml
kubectl apply -f k8s/ingress.yaml
```

The ingress routes `starter.graphbus.com` → frontend, `/api/*` → backend.

---

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

---

## Links

- [graphbus.com/onboarding](https://graphbus.com/onboarding) — Get your free API key
- [graphbus.com/docs](https://graphbus.com/docs) — Full documentation
- [graphbus/graphbus-core](https://github.com/graphbus/graphbus-core) — Core library (open source)

---

MIT License
