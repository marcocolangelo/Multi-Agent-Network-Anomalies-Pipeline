from app.utils.tracing import log
from app.core.messages import Msg
from app.core.bus import EventBus
import random

async def hretrieve_listener(bus: EventBus, msg: Msg):
    anomaly_id = msg.payload["anomaly"]["id"]
    hist = {"anomaly_id": anomaly_id, "history": f"prev-{random.randint(1,5)}"}
    log("HRetriever ▶ history ready")
    await bus.publish(Msg(trace_id=msg.trace_id,
                          role="HRETRIEVE_VALIDATE",
                          payload=hist))
