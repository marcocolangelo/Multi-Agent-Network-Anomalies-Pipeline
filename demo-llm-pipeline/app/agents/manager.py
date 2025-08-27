import asyncio
from app.utils.tracing import log, new_trace_id
from app.core.messages import Msg
from app.core.bus import EventBus

class ManagerSequencer:
    def __init__(self, bus: EventBus):
        self.bus, self.waiting = bus, {}

    async def start_pipeline(self, raw_logs: str):
        tid = new_trace_id()
        await self.bus.publish(Msg(trace_id=tid, role="Proc", payload={"raw_logs": raw_logs}))
        fut = asyncio.get_running_loop().create_future()

        async def done(msg: Msg):
            if msg.trace_id == tid and not fut.done():
                fut.set_result(True)
        self.bus.subscribe("ACK_DONE", done)
        await fut
        log("Manager ▶ cycle end, restart if needed")

    async def manager_plan_listener(self, msg: Msg):
        anom = msg.payload["anomaly"]
        tid   = msg.trace_id
        self.waiting[tid] = {"anomaly": anom, "ctx": None, "hist": None}

        # parallel trigger
        await self.bus.publish(Msg(trace_id=tid, role="KRetriever", payload={"anomaly": anom}))
        await self.bus.publish(Msg(trace_id=tid, role="HRetriever", payload={"anomaly": anom}))

    async def enr_ok_listener(self, msg: Msg):
        store = self.waiting[msg.trace_id]
        if "rule" in msg.payload:
            store["ctx"] = msg.payload
        else:
            store["hist"] = msg.payload
        if store["ctx"] and store["hist"]:
            await self.bus.publish(Msg(trace_id=msg.trace_id,
                                       role="NOTIFY_ASSEMBLE",
                                       payload=store))
