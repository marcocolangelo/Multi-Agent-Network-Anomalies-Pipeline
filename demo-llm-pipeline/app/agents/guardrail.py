import json
from langchain_core.prompts import ChatPromptTemplate
from app.core.bus import EventBus
from app.core.messages import Msg
from app.utils.tracing import log
from app.utils.llm_factory import get_llm
from app.utils.tracing import log_gui

MAX_RETRIES = 2

PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a pipeline guardrail and validator for an LLM agent. "
        "If the payload is fully correct, answer: VALID. "
        "If NOT, answer: INVALID and then tell what MUST be fixed and "
        "give a suggested correction as a brief, strict instruction. "
        "Speak to the agent, not to the user."
        "A few examples to report as INVALID: "
        "1. The agent is hallucinating, "
        "2. The agent is reporting details not present in the context nor in the history. "
        # "3. The agent is providing meta-information instead of a direct answer, like info about objects types and properties."
        # "(e.g. {{ anomaly_summary: {{type: string, description: Excessive DNS NXDOMAIN responses indicating possible DGA}}, related_rules: {{type: array, items: {{type: string}}}}, related_fields: {{type: array, items: {{type: string}}}} }}) because it contains info about types and objects."
        "3. The agent is not following the instructions coming from its personal card: {agent_card}"
    ),
    ("human", "{payload}")
])

_llm = get_llm()  # Ollama or fallback

def _validate(text: str, tag: str):
    # According to the role of the agent, the validation criteria may vary.
    agent_card = {}
    if "kretriever" in tag.lower():
        agent_card = json.load("demo-llm-pipeline\\app\\db\\agents_cards\\kretriever.json")
    elif "hretriever" in tag.lower():
        # Specific validation for HRetriever
        # agent_card = json.load("demo-llm-pipeline\\app\\db\\agents_cards\\hretriever.json")
        agent_card = json.load("demo-llm-pipeline\\app\\db\\agents_cards\\hretriever.json")
    elif "notify" in tag.lower() or "report" in tag.lower():
        # Specific validation for Notifier
        # agent_card = json.load("demo-llm-pipeline\\app\\db\\agents_cards\\notify.json")
        agent_card = "Follow the previous instructions"

    resp = _llm.invoke(PROMPT.format(agent_card=agent_card,payload=text))
    # log(f"GuardRail ▶ RESPONSE {resp}")
    valid = str(resp).strip().upper().startswith("VALID")
    if valid:
        return True, ""
    else:
        feedback = resp.replace("INVALID", "").strip()
        return False, feedback

async def guard_listener(bus: EventBus, msg: Msg):
    tag = msg.role  # e.g. INGEST_VALIDATE, ENRICH_VALIDATE, REPORT_VALIDATE
    payload = msg.payload
    retry_count = msg.payload.get("retry_count", 0)
    ok, feedback = _validate(str(payload),tag)
    log_gui("GuardRail", f"{tag} ok={ok} retry_count={retry_count} feedback={feedback}")
    if ok:
        nxt = tag.replace("VALIDATE", "OK")   # simple mapping
        await bus.publish(Msg(
            trace_id=msg.trace_id,
            role=nxt,
            payload=payload
        ))
    else:
        new_retry = retry_count + 1
        if new_retry > MAX_RETRIES:
            log_gui("GuardRail", f"FATAL after {MAX_RETRIES} retries on {tag}", "error")
            await bus.publish(Msg(
                trace_id=msg.trace_id,
                role="FATAL",
                payload={"reason": tag, "last_feedback": feedback, "retry_count": new_retry},
            ))
        else:
            reflection_msg = {
                "original_payload": payload,
                "feedback": feedback,
                "retry_count": new_retry
            }
            await bus.publish(Msg(
                trace_id=msg.trace_id,
                role=f"{tag}_REFLECT",
                payload=reflection_msg,
            ))
