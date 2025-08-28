from langchain_core.prompts import ChatPromptTemplate
from app.core.bus import EventBus
from app.core.messages import Msg
from app.utils.tracing import log
from app.utils.llm_factory import get_llm

MAX_RETRIES = 2

PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a strict pipeline guardrail and validator for an LLM agent. "
     "If the payload is fully correct, answer: VALID. "
     "If NOT, answer: INVALID and then tell what MUST be fixed and "
     "give a suggested correction as a brief, strict instruction. "
     "Speak to the agent, not to the user."
     "A few examples: "
     "1.You are hallucinating, "
     "2. The response is too verbose. "
     "3. The context is not relevant."),
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
    retry_count = getattr(msg, "retry_count", 0)
    ok, feedback = _validate(str(payload))
    log(f"GuardRail ▶ {tag} ok={ok} retry_count={retry_count} feedback={feedback}")
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
            log(f"GuardRail ▶ FATAL after {MAX_RETRIES} retries on {tag}", "error")
            await bus.publish(Msg(
                trace_id=msg.trace_id,
                role="FATAL",
                payload={"reason": tag, "last_feedback": feedback},
                retry_count=new_retry
            ))
        else:
            reflection_msg = {
                "original_payload": payload,
                "feedback": feedback
            }
            await bus.publish(Msg(
                trace_id=msg.trace_id,
                role=f"{tag}_REFLECT",
                payload=reflection_msg,
                retry_count=new_retry
            ))
