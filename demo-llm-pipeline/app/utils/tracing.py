
def log_gui(agent: str, msg: str, level: str = "info"):
    log(f"{agent} ▶ {msg}", level)
    try:
        from app.global_gui import gui
        if gui:
            gui.gui_log(agent, msg)
    except Exception:
        pass
import logging, uuid, contextvars

trace_var = contextvars.ContextVar("trace_id", default=None)

def init_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
        force=True
    )

def new_trace_id() -> str:
    tid = f"T-{uuid.uuid4().hex[:8]}"
    trace_var.set(tid)
    return tid

def get_trace_id() -> str:
    return trace_var.get() or "-"

def log(msg: str, level: str = "info"):
    getattr(logging, level)(f"{get_trace_id()} {msg}")
