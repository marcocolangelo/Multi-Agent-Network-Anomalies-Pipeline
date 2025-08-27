# Multi-Agent-Network-Anomalies-Pipeline
# Demo LLM Pipeline

Hi there! 👋
This project is a modern, agent-based pipeline demo for network anomaly detection powered by LLMs (LangChain + Ollama-ready). Agents are decoupled, extensible, and communicate via a minimal async event-bus. Notify, not Manager, generates your final report with real LLM reasoning.

---

## 🚀 What’s Inside

- Fully modular design: each agent focuses on *one* job (processing, enrichment, validation, etc.)
- Async, event-driven "bus"—no agent knows implementation details of others!
- Dynamic, LLM-generated report by Notify
- GuardRail validates at multiple workflow steps, with retry; demo uses Fake LLM fallback if Ollama is down/offline
- Manager orchestrates, but does not hold business logic or data
- Entirely mock DBs and logs: rapid prototyping; easy to migrate to real storage
- Clean logging with trace IDs

---

## ⚡️ Quick Start

### 1. Environment (choose one)

**venv:**
python -m venv .venv
source .venv/bin/activate # or .\.venv\Scripts\activate on Windows

**conda:**
conda create -n demo-llm-pipeline python=3.10 -y
conda activate demo-llm-pipeline

### 2. Install dependencies

pip install -r requirements.txt

### 3. (Optional) Use a real LLM via Ollama

ollama pull llama3
ollama serve

*(You can run the demo without Ollama; it uses Fake LLM fallback and will "just work" anyway.)*

### 4. Fire up the pipeline
python main.py

---

## 🛠️ Architecture & Design Principles

- **Agents subscribe to event-topics**; all messaging is explicit, enabling easy plugging/removal.
- **Manager is stateless**, aware only of orchestration, never business rules or data.
- **GuardRail sits everywhere:** it validates data at ingest, enrichment, and before reports are committed.
- **Enrichment tasks (domain/historical) run in parallel;** manager waits for both, then passes them to Notify.
- **Notify aggregates & assembles the report, using the LLM for *true* reasoning**—not static strings.
- **Results committed atomically** to fake CSV; agent history is append-only.

---

## 🧩 Extending the Demo

- Swap `FakeListLLM` for a real LLM (Ollama or OpenAI) in config.py or agent files.
- Swap the async EventBus for Redis Streams, Kafka, RabbitMQ… with minor changes.
- Swap CSV/mock DBs for MongoDB or PostgreSQL—persistence logic is already isolated!
- Add new retrievers, validators, or report styles by creating a new listener and topic.
- Add observability (Prometheus, OpenTelemetry) by wrapping the bus or agent callables.

---

## 🏃 Example Output

12:01:01 T-01fa435b Proc ▶ start
12:01:01 T-01fa435b Proc ▶ produced 3 rows
12:01:01 T-01fa435b GuardRail ▶ INGEST_VALIDATE True
12:01:02 T-01fa435b AnomalyModel ▶ anomaly detected
12:01:02 T-01fa435b KRetriever ▶ context ready
12:01:02 T-01fa435b HRetriever ▶ history ready
12:01:03 T-01fa435b Notify ▶ Generating report with LLM
12:01:03 T-01fa435b GuardRail ▶ REPORT_VALIDATE True
12:01:03 T-01fa435b Notify ▶ commiting validated report
12:01:03 T-01fa435b Manager ▶ cycle end, restart if needed

---

## 🔧 Troubleshooting Tips

- If “Ollama not reachable,” you’re using the FakeLLM fallback—this is *OK* for demos!
- If pool_db.csv or agent_history.csv don’t exist, they are created automatically.
- Everything is run locally, no cloud dependency.

---

## 🤓 Project Layout

```
app/core/ # bus and msg schema
app/agents/ # all agent logic, decoupled
app/models/ # mock anomaly detector
app/db/ # fake domain knowledge and CSVs
app/utils/ # config & logging/tracing
main.py # bootstrap & wiring
requirements.txt
README.md
```

### 5. Project structure
text
```
demo-llm-pipeline/
│
├── app/
│   ├── core/
│   │   ├── bus.py                 # in-memory event bus (asyncio)
│   │   └── messages.py            # Pydantic Msg schema
│   │
│   ├── utils/
│   │   ├── config.py              # OLLAMA_MODEL/BASE_URL and future settings
│   │   └── tracing.py             # logger + trace_id
│   │
│   ├── db/                        # fake DB/knowledge
│   │   ├── domain_knowledge.json  # rule examples
│   │   ├── pool_db.csv            # created at runtime
│   │   └── agent_history.csv      # (optional) created at runtime
│   │
│   ├── models/
│   │   └── anomaly_dummy.py       # mock anomaly detector
│   │
│   ├── agents/                    # independent listeners
│   │   ├── proc.py                # preprocessing
│   │   ├── guardrail.py           # validation (Fake LLM by default)
│   │   ├── anomaly_model.py       # mock anomaly detector integration
│   │   ├── retriever_domain.py    # DK retriever (fake)
│   │   ├── retriever_history.py   # History retriever (fake)
│   │   ├── notify.py              # LLM-based report, validation, commit
│   │   └── manager.py             # sequencer + plan listeners
│   │
│   └── __init__.py
│
├── requirements.txt
├── raw_logs_demo.txt              # optional seed logs (fallback present in main.py)
├── main.py                        # wiring & bootstrap
└── README.md
```

### 6. Run the demo
bash
python main.py
Example console output:

text
```
12:00:01 INFO  T-a1b2c3d4 Proc ▶ start
12:00:02 INFO  T-a1b2c3d4 Proc ▶ produced 3 rows
12:00:02 INFO  T-a1b2c3d4 GuardRail ▶ INGEST_VALIDATE True
12:00:03 INFO  T-a1b2c3d4 AnomalyModel ▶ anomaly detected
12:00:03 INFO  T-a1b2c3d4 KRetriever ▶ context ready
12:00:03 INFO  T-a1b2c3d4 HRetriever ▶ history ready
12:00:04 INFO  T-a1b2c3d4 Notify ▶ Generating report with LLM
12:00:04 INFO  T-a1b2c3d4 GuardRail ▶ REPORT_VALIDATE True
12:00:04 INFO  T-a1b2c3d4 Notify ▶ commiting validated report
12:00:05 INFO  T-a1b2c3d4 Manager ▶ cycle end, restart if needed
```
The generated (fake) report is appended to app/db/pool_db.csv.

### 7. How it works
main.py wires the event bus and subscribes each agent to a topic (role).

Proc preprocesses raw logs and publishes for validation.

GuardRail validates at multiple steps with bounded retries (demo uses Fake LLM; replace with Ollama if available).

AnomalyModel (mock) outputs zero or one anomaly.

Manager (sequencer) orchestrates: when an anomaly arrives, triggers KRetriever and HRetriever in parallel, collects their validated outputs, and then publishes to Notify.

Notify composes a final report dynamically via the LLM (LangChain + Ollama or Fake), sends it to GuardRail for final validation, and commits to pool DB / agent history, then sends ACK back to Manager.

### 8. Configuration
Change Ollama model and base URL in app/utils/config.py:

OLLAMA_MODEL = "llama3"

OLLAMA_BASE_URL = "http://localhost:11434"

Load environment variables with .env if needed.

### 9. Extending
Replace Fake LLM in guardrail.py and notify.py with real Ollama or OpenAI (langchain-openai) without changing other modules.

Swap EventBus with Redis Streams / Kafka / RabbitMQ by replacing publish/subscribe but keeping Msg schema.

Replace CSV with Mongo/PostgreSQL; the persistence code is isolated in notify.py.

Add more retrievers: just add a new topic and listener, then include it in the Manager plan and Notify prompt.

### 10. Troubleshooting
If you see “Ollama not reachable”, the code uses a Fake LLM fallback—pipeline still completes.

Ensure Python 3.10+ and a clean virtual environment.

If CSV paths don’t exist, they are created at runtime (inside app/db/).

### 11. License
For demo and educational purposes.
