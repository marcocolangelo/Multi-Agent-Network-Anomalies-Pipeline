from langchain_core.prompts import ChatPromptTemplate
from app.core.bus import EventBus
from app.core.messages import Msg
from app.utils.tracing import log
from app.utils.llm_factory import get_llm
from app.utils.tracing import log_gui

MAX_RETRIES = 2

PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a pipeline guardrail and validator for an LLM agent. "
     "If the payload is fully correct, answer: VALID. "
     "If NOT, answer: INVALID and then tell what MUST be fixed and "
     "give a suggested correction as a brief, strict instruction. "
     "Speak to the agent, not to the user."
     "A few examples to report as INVALID: "
     "1.You are hallucinating, "
     "2. You are reporting details not present in the context nor in the history. "
     "3. The context is not relevant."
     "4. For every piece of information you provide, ensure it is backed by either the context or the history."
     "5. If you are unsure about something, ask for clarification instead of making assumptions."
     "6. No timeline information should be included since there is no explicit mention of time except for the raw network logs."
     ""
     "A few examples of what to NOT report as INVALID:"
     "1. Too verbose but still talking about the issue."
     "2. JSON formatting issues."
     "3. Minor typos or grammatical errors."
     "4. If still talking about the problem without hallucinating you should not consider it invalid just because it's not precise enough."
     "5. It's okay if we don't have time references since time is not explicitly mentioned."
     "6. it's okay if we don't have space references since space is not explicitly mentioned."

     ),
    ("human", "{payload}")
])

_llm = get_llm()  # Ollama or fallback

def _validate(text: str):
    resp = _llm.invoke(PROMPT.format(payload=text))
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
    ok, feedback = _validate(str(payload))
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
