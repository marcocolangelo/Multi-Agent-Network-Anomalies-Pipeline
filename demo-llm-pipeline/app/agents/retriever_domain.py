import json
import pathlib
from app.utils.tracing import log
from app.core.messages import Msg
from app.core.bus import EventBus
from app.utils.llm_factory import get_llm

DK_PATH = str(pathlib.Path(__file__).parent.parent / "db" / "domain_knowledge.json")
llm = get_llm()

RAG_PROMPT = """
You are a SOC expert. Given the following network anomaly:
---
{anomaly}
---
…and these knowledge base rules/examples:
---
{knowledge_base}
---
Synthesize a short and context-rich explanation and remediation suggestion for this type of case.
"""

REFLECTION_PROMPT = """
You are a correction agent. Your last enrichment was REJECTED for this reason:
[ {feedback} ].
Re-generate the context/data, fixing the above issues.
Original anomaly/context:
---
{anomaly}
---
Knowledge base:
---
{knowledge_base}
---
"""

async def kretrieve_listener(bus: EventBus, msg: Msg):
    if msg.role == "KRetriever":
        log("KRetriever ▶ received retrieval request")
        anomaly = msg.payload["anomaly"]
        # Load candidate "chunks" from domain_knowledge.json
        with open(DK_PATH, "r") as f:
            kb = json.load(f)["rules"]
        kb_str = "\n".join(
            f'- {r["rule"]}: {", ".join([ex["description"] for ex in r["examples"][:1]])}'
            if isinstance(r, dict) else f'- {r}' for r in kb
        )
        prompt = RAG_PROMPT.format(anomaly=anomaly, knowledge_base=kb_str)
        ctx_result = llm.invoke(prompt)
        log(f"KRetriever ▶ context result: {ctx_result}")
        await bus.publish(Msg(
            trace_id=msg.trace_id,
            role="KRETRIEVE_VALIDATE",
            payload={"anomaly": anomaly, "ctx": ctx_result, "retry_count": getattr(msg.payload, "retry_count", 0)}
        ))

    elif msg.role == "KRETRIEVE_VALIDATE_REFLECT":
        # Reflection: get feedback and use new prompt
        log("KRetriever ▶ received reflection request")
        reflection = msg.payload
        anomaly = reflection["original_payload"]["anomaly"]
        feedback = reflection["feedback"]
        # Load the knowledge base as above
        # with open(DK_PATH, "r") as f:
        #     kb = json.load(f)["rules"]
        # kb_str = "\n".join(
        #     f'- {r["rule"]}: {", ".join([ex["description"] for ex in r["examples"][:1]])}'
        #     if isinstance(r, dict) else f'- {r}' for r in kb
        # )
        ctx = reflection["original_payload"]["ctx"]
        prompt = REFLECTION_PROMPT.format(anomaly=anomaly, knowledge_base=ctx, feedback=feedback)
        ctx_result = llm.invoke(prompt)
        log(f"KRetriever ▶ Reflection retry with feedback: {feedback}")
        await bus.publish(Msg(
            trace_id=msg.trace_id,
            role="KRETRIEVE_VALIDATE",
            payload={"anomaly": anomaly, "ctx": ctx_result},
            retry_count=getattr(msg, "retry_count", 0)
        ))
