from abc import ABC, abstractmethod
from langchain_core.messages import SystemMessage, HumanMessage
from llm.router import get_llm
from agents.state import ResearchState

class BaseAgent(ABC):

    def __init__(self,model_key:str):
        self.llm = get_llm(model_key)
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
        
    def build_messages(self, user_content: str) -> list:
        return [
            SystemMessage(content=self.system_prompt()),
            HumanMessage(content=user_content)
        ]
