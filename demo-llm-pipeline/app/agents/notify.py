from langchain_core.prompts import ChatPromptTemplate
from app.core.bus import EventBus
from app.core.messages import Msg
from app.utils.tracing import log
from langchain_community.llms import FakeListLLM
from app.utils.config import settings

REPORT_PROMPT = """
You are a SOC analyst assistant. Given:
- Anomaly Data: {anomaly}
- Domain Knowledge: {ctx}
- Historical Patterns: {hist}
Generate a thorough incident report including severity assessment, suggested root cause, recommended preventive action in concise business English.
"""

llm = FakeListLLM(responses=["Sample incident report."])  # Replace with Ollama if ready

async def notify_listener(bus: EventBus, msg: Msg):
    if msg.role == "NOTIFY_ASSEMBLE":
        bundle = msg.payload
        prompt_str = REPORT_PROMPT.format(
            anomaly=bundle["anomaly"],
            ctx=bundle["ctx"],
            hist=bundle["hist"]
        )
        log("Notify ▶ Generating report with LLM", "info")
        report_content = llm.invoke(prompt_str)
        await bus.publish(Msg(trace_id=msg.trace_id, role="REPORT_VALIDATE", payload={"report": report_content}))
    elif msg.role == "REPORT_OK":
        report = msg.payload["report"]
        log(f"Notify ▶ commiting validated report", "info")
        import csv, pathlib
        p = pathlib.Path("app/db/pool_db.csv")
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", newline="") as f:
            csv.writer(f).writerow([msg.trace_id, report])
        await bus.publish(Msg(trace_id=msg.trace_id, role="ACK_DONE", payload={}))
