import csv
from app.utils.tracing import log
from app.core.messages import Msg
from app.core.bus import EventBus
from app.utils.llm_factory import get_llm

POOLDB_PATH = "app/db/pool_db.csv"
llm = get_llm()

RAG_PROMPT = """
You are a SOC analyst. Given the anomaly:
---
{anomaly}
---
…and these historical reports:
---
{history_examples}
---
Summarize useful patterns or lessons learned and explain their relevance to the current incident.
"""

REFLECTION_PROMPT = """
Your previous history/context enrichment was rejected for this reason:
[ {feedback} ].
Re-compose the historical enrichment accordingly.
Anomaly:
---
{anomaly}
---
Recent incident reports:
---
{history_examples}
---
"""

async def hretrieve_listener(bus: EventBus, msg: Msg):
    if msg.role == "HRetriever":
        anomaly = msg.payload["anomaly"]
        # Load up to 5 recent history reports
        history_rows = []
        try:
            with open(POOLDB_PATH, "r") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row:
                        history_rows.append(row[-1])
        except FileNotFoundError:
            history_rows = ["No prior incidents recorded yet."]
        context_hist = "\n".join(history_rows)
        prompt = RAG_PROMPT.format(anomaly=anomaly, history_examples=context_hist)
        rag_result = llm.invoke(prompt)
        log(f"HRetriever ▶ history result: {rag_result}")
        await bus.publish(Msg(
            trace_id=msg.trace_id,
            role="HRETRIEVE_VALIDATE",
            payload={"anomaly": anomaly, "hist": rag_result},
            retry_count=getattr(msg, "retry_count", 0)
        ))

    elif msg.role == "HRETRIEVE_VALIDATE_REFLECT":
        # Reflection: get feedback and use new prompt
        reflection = msg.payload
        anomaly = reflection["original_payload"]["anomaly"]
        feedback = reflection["feedback"]
        # Reload history as above
        history_rows = reflection["original_payload"]["hist"]
        # try:
        #     with open(POOLDB_PATH, "r") as f:
        #         reader = csv.reader(f)
        #         for row in reader:
        #             if row:
        #                 history_rows.append(row[-1])
        # except FileNotFoundError:
        #     history_rows = ["No prior incidents recorded yet."]
        # context_hist = "\n".join(history_rows[-5:])
        prompt = REFLECTION_PROMPT.format(anomaly=anomaly, history_examples=history_rows, feedback=feedback)
        rag_result = llm.invoke(prompt)
        log(f"HRetriever ▶ Reflection result: {rag_result}")
        await bus.publish(Msg(
            trace_id=msg.trace_id,
            role="HRETRIEVE_VALIDATE",
            payload={"anomaly": anomaly, "hist": rag_result, "retry_count": getattr(msg.payload, "retry_count", 0)},
        ))
        log(f"HRetriever ▶ Reflection retry with feedback: {feedback}", "warning")
