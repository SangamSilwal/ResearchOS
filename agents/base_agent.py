from abc import ABC, abstractmethod
from langchain_core.messages import SystemMessage, HumanMessage
from llm.router import get_llm
from agents.state import ResearchState

class BaseAgent(ABC):

    def __init__(self,model_key:str, api_key: str | None = None):
        self.llm = get_llm(model_key, api_key)
        self.name = self.__class__.__name__

    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent"""
        ...
    
    @abstractmethod
    async def run(self, state: ResearchState) -> dict:
        """
        Core agent logic. Receives current state, returns a dict of state fields to update
        """
        ...

    async def __call__(self, state: ResearchState) -> dict:
        """LangGraph node entrypoint."""
        try:
            return await self.run(state)
        except Exception as e:
            return {
                "error": f"{self.name} failed: {str(e)}",
                "next_agent": "critic",
            }
        
    def build_messages(self, user_content: str, state: ResearchState | None = None, recent_runs: list[dict] | None = None) -> list:
        messages = [SystemMessage(content=self.system_prompt())]
        if recent_runs:
            from core.memory import format_run_memory_for_prompt
            memory_block = format_run_memory_for_prompt(recent_runs)
            messages.append(SystemMessage(content=(
                "Context from previous ResearchOS runs -- use this to "
                "avoid repeating known mistakes or re-researching topics "
                "that were already covered:\n\n"
                + memory_block
            )))
        if state:
            history = state.get("messages",[])[-5:]
            if history:
                history_lines = []
                for m in history_lines:
                    speaker = type(m).__name__.replace("Message", "")
                    history_lines.append(f"[{speaker}]: {m.content}")
                messages.append(SystemMessage(content=(
                    "Recent activity in this run (last 5 messages):\n"
                    + "\n".join(history_lines)
                )))
 
        messages.append(HumanMessage(content=user_content))
        return messages

