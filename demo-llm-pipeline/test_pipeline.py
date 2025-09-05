import asyncio, textwrap, pathlib, functools
from app.core.bus import EventBus
from app.utils.tracing import init_logger
from app.agents import proc, guardrail, anomaly_model, retriever_domain, retriever_history, notify, manager
from app.GUI import PipelineGUI
import chromadb
from sentence_transformers import SentenceTransformer
import csv
from app.utils.config import settings

RAW_LOGS_PATH = pathlib.Path("demo-llm-pipeline/raw_logs_demo.txt")
POOLDB_PATH = settings.POOL_DB_PATH

with RAW_LOGS_PATH.open() as f:
    RAW_LOGS = f.read()

async def test_pipeline():
    bus = EventBus()
    seq = manager.ManagerSequencer(bus)
    results = {}

    # --- Topic → agent subscriptions (reflection logic included) ---
    bus.subscribe("Proc",               functools.partial(proc.proc_listener, bus))
    # bus.subscribe("INGEST_VALIDATE",    functools.partial(guardrail.guard_listener, bus))
    bus.subscribe("INGEST_OK",          functools.partial(anomaly_model.anomaly_listener, bus))
    bus.subscribe("MANAGER_PLAN",       seq.manager_plan_listener)

    # KRetriever and reflection/validate loop
    bus.subscribe("KRetriever",                 functools.partial(retriever_domain.kretrieve_listener, bus))
    bus.subscribe("KRETRIEVE_VALIDATE",         functools.partial(guardrail.guard_listener, bus))
    bus.subscribe("KRETRIEVE_OK",               seq.enr_ok_listener)
    bus.subscribe("KRETRIEVE_VALIDATE_REFLECT", functools.partial(retriever_domain.kretrieve_listener, bus))  # <-- reflection

    # HRetriever and reflection/validate loop
    bus.subscribe("HRetriever",                 functools.partial(retriever_history.hretrieve_listener, bus))
    bus.subscribe("HRETRIEVE_VALIDATE",         functools.partial(guardrail.guard_listener, bus))
    bus.subscribe("HRETRIEVE_OK",               seq.enr_ok_listener)
    bus.subscribe("HRETRIEVE_VALIDATE_REFLECT", functools.partial(retriever_history.hretrieve_listener, bus))  # <-- reflection

    # Notify and reporting logic
    bus.subscribe("NOTIFY_ASSEMBLE",    functools.partial(notify.notify_listener, bus))
    bus.subscribe("REPORT_VALIDATE",    functools.partial(guardrail.guard_listener, bus))
    bus.subscribe("REPORT_OK",          functools.partial(notify.notify_listener, bus))
    bus.subscribe("REPORT_VALIDATE_REFLECT", functools.partial(notify.notify_listener, bus))  # <-- reflection

    # Fatal error
    bus.subscribe("FATAL",           seq.fatal_error)  # <-- fatal error handling

    # Intercetta la fine della pipeline (ACK_DONE)
    async def ack_done(msg):
        results['done'] = True
    bus.subscribe("ACK_DONE", ack_done)

    asyncio.create_task(bus.start())
    await seq.start_pipeline(RAW_LOGS)

    # Attendi fine pipeline (max ~6 secondi per 30 tentativi a 0.2s)
    for _ in range(30):
        if results.get('done'):
            break
        await asyncio.sleep(0.2)

    # Verifica che il file CSV sia stato scritto
    csv_path = pathlib.Path("demo-llm-pipeline/app/db/pool_db.csv")
    assert csv_path.exists(), "Il file pool_db.csv non è stato creato!"
    # with csv_path.open() as f:
    #     content = f.read()
    #     print("Contenuto pool_db.csv:\n", content)
    print("Test completato: la pipeline e il bus funzionano correttamente.")

def setup_vector_db():
    db = chromadb.Client()
    collection = db.create_collection("incident_reports")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    # Indicizza i report storici
    with open(POOLDB_PATH, "r") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if row:
                text = row[-1]
                embedding = model.encode(text).tolist()
                collection.add(
                    documents=[text],
                    embeddings=[embedding],
                    ids=[str(i)]
                )
    return collection, model

if __name__ == "__main__":
    init_logger()
    import logging
    logging.info("Logger attivo: questo è un test di log visibile.")
    asyncio.run(test_pipeline())
