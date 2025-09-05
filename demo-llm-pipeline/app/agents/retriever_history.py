import csv
import json
import pathlib
from app.utils.tracing import log
from app.core.messages import Msg
from app.core.bus import EventBus
from app.utils.llm_factory import get_llm
from app.utils.tracing import log_gui
from app.utils.config import settings

POOLDB_PATH = settings.POOL_DB_PATH
RULE_PATH = str(pathlib.Path(__file__).parent.parent / "db" / "agents_cards" / "hretriever.json")

with open(RULE_PATH, "r", encoding="utf-8") as f:
    prompt = json.load(f)
    
agent_instructions = prompt["instructions"]
prompt_template = agent_instructions["prompt_template"]
response_format = agent_instructions["response_format"]
response_properties = response_format["properties"]
required_fields = response_format["required"]

notes = agent_instructions.get("notes", "No additional notes provided.")
llm = get_llm()

RAG_PROMPT = """
{prompt_template}:
---
Given the following knowledge base:
{knowledge_base}
---
Extract and report ONLY the factual information directly related to the anomaly. 
Your output must be a JSON object with fields {required_fields} that follow these object rules but don't include objects types and meta-information:
{response_properties}
""" + (f"EXTREMELY IMPORTANT: Be sure to follow the notes: {notes}." if "notes" in agent_instructions else "")

REFLECTION_PROMPT = """<GUARDRAIL>
You are a correction agent. Your last enrichment was REJECTED for this reason:
[ {feedback} ].
Re-generate the context/data, fixing the above issues.
Original payload:
{original_payload}
\n
History:
{history}
</GUARDRAIL>
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
        prompt = RAG_PROMPT.format(
            prompt_template=prompt_template,
            anomaly=anomaly,
            knowledge_base=context_hist,
            required_fields=required_fields,
            response_properties=response_properties,
            notes=notes
            )
        log_gui("HRetriever", f"prompt: {prompt}")
        rag_result = llm.invoke(prompt)
        log_gui("HRetriever", f"history result: {rag_result}")
        retry_count = msg.payload.get("retry_count", 0)
        await bus.publish(Msg(
            trace_id=msg.trace_id,
            role="HRETRIEVE_VALIDATE",
            payload={"anomaly": anomaly, "hist": rag_result, "retry_count": retry_count}
        ))

    ############## STILL WORK IN PROGRESS TO TRANSFORM IT INTO A RAG #################
    # if msg.role == "HRetriever":
    #     vector_collection = msg.payload["collection"]
    #     embedder = msg.payload["model"]
    #     log_gui("HRetriever", f"vector collection: {vector_collection}, embedder: {embedder}")
    #     anomaly = msg.payload["anomaly"]
    #     # Recupera i report più simili all'anomalia
    #     anomaly_embedding = embedder.encode(anomaly["description"]).tolist()
    #     results = vector_collection.query(
    #         query_embeddings=[anomaly_embedding],
    #         n_results=3
    #     )
    #     # Flatten the first 3 lists in results['documents'] and join their contents
    #     top_docs = results['documents'][:3]
    #     retrieved_reports = [item for sublist in top_docs for item in sublist]
    #     context_hist = "\n".join(retrieved_reports)
    #     log_gui("HRetriever", f"retrieved reports: {retrieved_reports}")
    #     prompt = RAG_PROMPT.format(
    #         prompt_template=prompt_template,
    #         knowledge_base=context_hist,
    #         required_fields=required_fields,
    #         response_properties=response_properties,
    #         notes=notes
    #     )
    #     log_gui("HRetriever", f"prompt: {prompt}")
    #     rag_result = llm.invoke(prompt)
    #     log_gui("HRetriever", f"history result: {rag_result}")
    #     retry_count = msg.payload.get("retry_count", 0)
    #     await bus.publish(Msg(
    #         trace_id=msg.trace_id,
    #         role="HRETRIEVE_VALIDATE",
    #         payload={"anomaly": anomaly, "hist": rag_result, "retry_count": retry_count}
    #     ))

    elif msg.role == "HRETRIEVE_VALIDATE_REFLECT":
        # Reflection: get feedback and use new prompt
        reflection = msg.payload
        original_payload = reflection["original_payload"]
        anomaly = original_payload["anomaly"]
        feedback = reflection["feedback"]
        history_rows = original_payload["hist"]
        prompt = REFLECTION_PROMPT.format(original_payload=original_payload, feedback=feedback, history=history_rows)
        rag_result = llm.invoke(prompt)
        log_gui("HRetriever", f"Reflection retry with feedback: {feedback}")
        log_gui("HRetriever", f"Reflection result: {rag_result}")
        retry_count = msg.payload.get("retry_count", 0)
        await bus.publish(Msg(
            trace_id=msg.trace_id,
            role="HRETRIEVE_VALIDATE",
            payload={"anomaly": anomaly, "hist": rag_result, "retry_count": retry_count},
        ))
        log_gui("HRetriever", f"Reflection retry with feedback: {feedback}", "warning")
