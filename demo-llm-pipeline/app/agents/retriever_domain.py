import json
import pathlib
from app.utils.tracing import log
from app.core.messages import Msg
from app.core.bus import EventBus
from app.utils.llm_factory import get_llm
from app.utils.tracing import log_gui


DK_PATH = str(pathlib.Path(__file__).parent.parent / "db" / "domain_knowledge.json")
RULE_PATH = str(pathlib.Path(__file__).parent.parent / "db" / "agents_cards" / "kretriever.json")

with open(RULE_PATH, "r", encoding="utf-8") as f:
    prompt = json.load(f)

llm = get_llm()

agent_instructions = prompt["instructions"]
prompt_template = agent_instructions["prompt_template"]
response_format = agent_instructions["response_format"]
response_properties = response_format["properties"]
required_fields = response_format["required"]

notes = agent_instructions.get("notes", "No additional notes provided.")

RAG_PROMPT = """
{prompt_template}:
---
Given the anomaly:
{anomaly}
---
and the following knowledge base:
{knowledge_base}
---
Extract and report ONLY the factual information directly related to the anomaly. 
Your output must be a JSON object with fields {required_fields} that follow these object rules but don't include objects types and meta-information:
{response_properties}
""" + (f"Be sure to follow the notes: {notes}." if "notes" in agent_instructions else "")

REFLECTION_PROMPT = """<GUARDRAIL>
You are a correction agent. Your last enrichment was REJECTED for this reason:
[ {feedback} ].
Re-generate the context/data, fixing the above issues.
Original payload:
{original_payload}
</GUARDRAIL>
"""

async def kretrieve_listener(bus: EventBus, msg: Msg):
    if msg.role == "KRetriever":
        log_gui("KRetriever", "received retrieval request")
        anomaly = msg.payload["anomaly"]
        # Load candidate "chunks" from domain_knowledge.json
        with open(DK_PATH, "r") as f:
            kb = json.load(f)["rules"]
        kb_str = "\n".join(
            f'- {r["rule"]}: {r.get("explaination", "")} Example: {", ".join([ex["description"] for ex in r.get("examples", [])[:1]])}'
            if isinstance(r, dict) else f'- {r}' for r in kb
        )
        prompt = RAG_PROMPT.format(prompt_template=prompt_template, anomaly=anomaly, knowledge_base=kb_str, response_properties=response_properties, required_fields=required_fields)
        log_gui("KRetriever", f"prompt: {prompt}")
        ctx_result = llm.invoke(prompt)
        log_gui("KRetriever", f"context result: {ctx_result}")
        retry_count = msg.payload.get("retry_count", 0)
        await bus.publish(Msg(
            trace_id=msg.trace_id,
            role="KRETRIEVE_VALIDATE",
            payload={"anomaly": anomaly, "ctx": ctx_result, "retry_count": retry_count}
        ))

    elif msg.role == "KRETRIEVE_VALIDATE_REFLECT":
        # Reflection: get feedback and use new prompt
        log_gui("KRetriever", "received reflection request")
        reflection = msg.payload
        anomaly = reflection["original_payload"]["anomaly"]
        feedback = reflection["feedback"]
        original_payload = reflection["original_payload"]
        prompt = REFLECTION_PROMPT.format(original_payload=original_payload, feedback=feedback)
        ctx_result = llm.invoke(prompt)
        log_gui("KRetriever", f"Reflection retry with feedback: {feedback}")
        log_gui("KRetriever", f"New context result: {ctx_result}")
        retry_count = msg.payload.get("retry_count", 0)
        await bus.publish(Msg(
            trace_id=msg.trace_id,
            role="KRETRIEVE_VALIDATE",
            payload={"anomaly": anomaly, "ctx": ctx_result, "retry_count": retry_count},
        ))
