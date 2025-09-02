import datetime
from typing import ClassVar
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    AGENT_LOG_DIR: str = "demo-llm-pipeline/app/db/agents_logs"
    now: ClassVar[str] = str(datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    AGENT_LOG_FILE: ClassVar[str] = str(AGENT_LOG_DIR) + f"/agent_log_data_{now}.txt"
    AGENT_CARDS_DIR: ClassVar[str] = "demo-llm-pipeline/app/db/agents_cards"

settings = Settings()
