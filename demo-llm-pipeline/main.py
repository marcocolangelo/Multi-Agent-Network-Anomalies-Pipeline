import asyncio, textwrap
from app.core.bus import EventBus
from app.utils.tracing import init_logger
from app.core.messages import Msg
from app.agents import proc, guardrail, anomaly_model, retriever_domain, retriever_history, notify, manager

RAW_LOGS = textwrap.dedent("""\
1693075200,10.1.1.105,93.184.216.34,443,52341,6,125680,89,45.2,CELL_001,usr_7f3a8b9c
1693075201,10.1.1.107,8.8.8.8,53,41829,17,124,2,0.1,CELL_001,usr_2d4c7e1a
1693075202,10.1.1.108,192.0.2.100,80,33845,6,2048576,1456,120.5,CELL_002,usr_9b5f3d7e
""")

async def bootstrap():
    bus = EventBus()
    seq = manager.ManagerSequencer(bus)

    # Topic → agent subscriptions
    bus.subscribe("Proc",               lambda m: proc.proc_listener(bus, m))
    bus.subscribe("INGEST_VALIDATE",    lambda m: guardrail.guard_listener(bus, m))
    bus.subscribe("INGEST_OK",          lambda m: anomaly_model.anomaly_listener(bus, m))
    bus.subscribe("MANAGER_PLAN",       seq.manager_plan_listener)
    bus.subscribe("KRetriever",         lambda m: retriever_domain.kretrieve_listener(bus, m))
    bus.subscribe("HRetriever",         lambda m: retriever_history.hretrieve_listener(bus, m))
    bus.subscribe("KRETRIEVE_VALIDATE", lambda m: guardrail.guard_listener(bus, m))
    bus.subscribe("HRETRIEVE_VALIDATE", lambda m: guardrail.guard_listener(bus, m))
    bus.subscribe("KRETRIEVE_OK",       seq.enr_ok_listener)
    bus.subscribe("HRETRIEVE_OK",       seq.enr_ok_listener)
    bus.subscribe("NOTIFY_ASSEMBLE",    lambda m: notify.notify_listener(bus, m))
    bus.subscribe("REPORT_VALIDATE",    lambda m: guardrail.guard_listener(bus, m))
    bus.subscribe("REPORT_OK",          lambda m: notify.notify_listener(bus, m))

    asyncio.create_task(bus.start())
    await seq.start_pipeline(RAW_LOGS)

if __name__ == "__main__":
    init_logger()
    asyncio.run(bootstrap())
