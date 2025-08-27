from pydantic import BaseModel
from typing import Any, Dict

class Msg(BaseModel):
    trace_id: str
    role: str
    payload: Dict[str, Any]
