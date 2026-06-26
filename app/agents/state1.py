from typing import TypedDict, Optional, Literal, List

class AgentState(TypedDict):
    dataset_id: int
    session_id: str
    question: str
    sql_query: Optional[str]
    raw_result: Optional[str]
    final_response: Optional[str]
    image_base64: Optional[str]
    next_step: Optional[Literal["sql_agent", "clarifier"]]
    agent_logs: List[str] 