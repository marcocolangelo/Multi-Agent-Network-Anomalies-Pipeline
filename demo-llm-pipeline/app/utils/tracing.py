from app.utils.config import settings


def log_gui(agent: str, msg: str, level: str = "info"):
    AGENT_LOG_DIR = settings.AGENT_LOG_DIR
    AGENT_LOG_FILE = settings.AGENT_LOG_FILE

    log(f"{agent} ▶ {msg}", level)
    # Scrivi su GUI se disponibile
    try:
        from app.global_gui import gui
        if gui:
            gui.gui_log(agent, msg)
    except Exception:
        pass
    # Scrivi su file storico
    try: 
        log_dir = AGENT_LOG_DIR
    except NameError:
        log_dir = pathlib.Path("demo-llm-pipeline/app/db/agents_logs")
        log_dir.mkdir(parents=True, exist_ok=True)

    # Usa una variabile globale per il nome file

    pathlib.Path(AGENT_LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    if not pathlib.Path(AGENT_LOG_FILE).exists():
        pathlib.Path(AGENT_LOG_FILE).touch()
    
    # Format log line
    log_line = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {agent}: {msg}\n"
    with open(AGENT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)

        
import logging, uuid, contextvars
import pathlib, datetime

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
