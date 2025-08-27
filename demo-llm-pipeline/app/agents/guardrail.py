from langchain_community.llms import FakeListLLM
from langchain_core.prompts import ChatPromptTemplate
from app.core.bus import EventBus
from app.core.messages import Msg
from app.utils.tracing import log

_FAKE = FakeListLLM(responses=["VALID"])

PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a strict validator, answer only VALID or INVALID."),
    ("human", "{payload}")
])

def _validate(text: str) -> bool:
    resp = _FAKE.invoke(PROMPT.format(payload=text))
    return resp.startswith("VALID")

async def guard_listener(bus: EventBus, msg: Msg):
    tag = msg.role
    payload = msg.payload
    ok = _validate(str(payload))
    log(f"GuardRail ▶ {tag} {ok}")
    if ok:
        nxt = tag.replace("VALIDATE", "OK")
        await bus.publish(Msg(trace_id=msg.trace_id, role=nxt, payload=payload))
    else:
        await bus.publish(Msg(trace_id=msg.trace_id, role="FATAL", payload={"reason": tag}))
