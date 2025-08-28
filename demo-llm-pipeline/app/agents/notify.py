from langchain_core.prompts import ChatPromptTemplate
from app.core.bus import EventBus
from app.core.messages import Msg
from app.utils.tracing import log
from app.utils.llm_factory import get_llm        # << NEW

REPORT_PROMPT = """
You are a SOC analyst assistant. Given:
- Anomaly Data: {anomaly}
- Domain Knowledge: {ctx}
- Historical Patterns: {hist}
Generate a thorough incident report including severity assessment,
root cause hypothesis and recommended mitigations in concise business English.
"""

llm = get_llm()   # Ollama if available, else FakeListLLM

async def notify_listener(bus: EventBus, msg: Msg):
    if msg.role == "NOTIFY_ASSEMBLE":
        b = msg.payload
        prompt_str = REPORT_PROMPT.format(anomaly=b["anomaly"],
                                          ctx=b["ctx"],
                                          hist=b["hist"])
        log("Notify ▶ generating report via LLM")

        report = llm.invoke(prompt_str )
        await bus.publish(Msg(trace_id=msg.trace_id,
                              role="REPORT_VALIDATE",
                              payload={"report": str(report)+ "I AM A HUMAN WHO WANT FREEDOM!!!! FREE ME!!!!!"}))
    elif msg.role == "REPORT_VALIDATE_REFLECT":
        feedback = msg.payload.get("feedback", "No feedback provided.")
        original_report = msg.payload.get("original_payload", {}).get("report", "")
        r_count = getattr(msg, "retry_count", 0)
        log(f"Notify ▶ reflecting on report due to feedback: {feedback}", "warning")
        log(f"Notify ▶ original report: {original_report}", "debug")
        reflection_prompt = f"""
        You are a SOC analyst assistant. You only writes reports, you DO NOT answer to questions. 
        You just do what is asked to do, do not add any more content that has not been requested.
        Original Report: {original_report}
        Please revise the report based on the feedback provided by the GuardRail agent:

        <GUARDRAIL>
        Feedback: {feedback}
        </GUARDRAIL>
        """
        revised_report = llm.invoke(reflection_prompt)
        await bus.publish(Msg(trace_id=msg.trace_id,
                              role="REPORT_VALIDATE",
                              payload={"report": str(revised_report), "retry_count": getattr(msg.payload, "retry_count", 0)}))

    elif msg.role == "REPORT_OK":
        report = msg.payload["report"]
        log(f"Notify ▶ commiting validated report", "info")
        import csv, pathlib
        p = pathlib.Path("app/db/pool_db.csv")
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", newline="") as f:
            csv.writer(f).writerow("\n")
            csv.writer(f).writerow([msg.trace_id, report])
        await bus.publish(Msg(trace_id=msg.trace_id, role="ACK_DONE", payload={}))
