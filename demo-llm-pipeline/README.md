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

app/core/ # bus and msg schema
app/agents/ # all agent logic, decoupled
app/models/ # mock anomaly detector
app/db/ # fake domain knowledge and CSVs
app/utils/ # config & logging/tracing
main.py # bootstrap & wiring
requirements.txt
README.md

---

Happy hacking & experimenting!
If you expand this to production, just swap messaging/db layers and you’re set.

---
