from app.utils.tracing import log
from app.core.messages import Msg
from app.core.bus import EventBus
import random

RULES = ["Rule A", "Rule B", "Rule C"]

async def kretrieve_listener(bus: EventBus, msg: Msg):
    anomaly_id = msg.payload["anomaly"]["id"]
    ctx = {"anomaly_id": anomaly_id, "rule": random.choice(RULES)}
    log("KRetriever ▶ context ready")
    await bus.publish(Msg(trace_id=msg.trace_id,
                          role="KRETRIEVE_VALIDATE",
                          payload=ctx))
