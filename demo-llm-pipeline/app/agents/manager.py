import asyncio
from app.utils.tracing import log, new_trace_id
from app.core.messages import Msg
from app.core.bus import EventBus
from app.utils.tracing import log_gui


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
        from app.utils.tracing import log_gui
        log_gui("Manager", "cycle end, restart if needed")

    async def manager_plan_listener(self, msg: Msg):
        log_gui("Manager", "planning enrichment retrieval")
        anom = msg.payload["anomaly"]
        tid = msg.trace_id
        self.waiting[tid] = {"anomaly": anom, "ctx": None, "hist": None}
        pool_collection = msg.payload.get("collection", None)
        pool_model = msg.payload.get("model", None)
        log_gui("Manager", f"passing collection: {pool_collection}, model: {pool_model}")

        # parallel trigger
        await self.bus.publish(Msg(trace_id=tid, role="KRetriever", payload={"anomaly": anom, "collection": pool_collection, "model": pool_model}))
        await self.bus.publish(Msg(trace_id=tid, role="HRetriever", payload={"anomaly": anom, "collection": pool_collection, "model": pool_model}))
        log_gui("Manager", f"received anomaly {anom}, triggering retrievers")

    async def enr_ok_listener(self, msg: Msg):
        store = self.waiting[msg.trace_id]
        if "hist" in msg.payload:
            store["hist"] = msg.payload["hist"]
        else:
            store["ctx"] = msg.payload["ctx"]
        if store["ctx"] and store["hist"]:
            from app.utils.tracing import log_gui
            log_gui("Manager", f"both enrichments ready for {msg.trace_id}, assembling report")
            await self.bus.publish(Msg(trace_id=msg.trace_id,
                                       role="NOTIFY_ASSEMBLE",
                                       payload=store))
            
    async def fatal_error(self, msg: Msg):
        log_gui("Manager", f"fatal error occurred: too many retries in {msg.payload['reason']}")
        await self.bus.publish(Msg(trace_id=msg.trace_id, role="ACK_DONE", payload={}))

