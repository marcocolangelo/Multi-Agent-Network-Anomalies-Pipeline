from app.models.anomaly_dummy import AnomalyDetectorMock
from app.core.messages import Msg
from app.core.bus import EventBus
from app.utils.tracing import log

_DETECT = AnomalyDetectorMock()

async def anomaly_listener(bus: EventBus, msg: Msg):
    df = msg.payload["df"]
    anomalies = _DETECT.detect(df)

    if not anomalies:
        log("AnomalyModel ▶ no anomalies found, signaling completion")
        await bus.publish(Msg(trace_id=msg.trace_id, role="ACK_DONE", payload={}))
        return

    for anom in anomalies:
        await bus.publish(Msg(trace_id=msg.trace_id,
                              role="MANAGER_PLAN",
                              payload={"anomaly": anom.__dict__}))
