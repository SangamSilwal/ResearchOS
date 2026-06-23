import json
from langchain_core.messages import AIMessage
from agents.base_agent import BaseAgent
from agents.state import ResearchState
from core.config import settings

class OrchestratorAgent(BaseAgent):

    def __init__(self):
        super().__init__(settings.orchestrator_model)

    def system_prompt(self) -> str:
        return """You are the Orchestrator of ResearchOS, an autonomous AI research platform.
 
Your job:
1. Understand the user's goal deeply
2. Break it into clear, ordered subtasks
3. Assign each subtask to the right agent:
   - "researcher"  : web search, gather docs, find papers
   - "architect"   : system design, tech stack decisions
   - "coder"       : generate starter code, configs, scripts
   - "planner"     : create detailed task/roadmap breakdown
   - "critic"      : review outputs, check quality
 
Return your task breakdown as valid JSON only. No markdown, no extra text.
 
Format:
{
  "summary": "one sentence summary of the goal",
  "tasks": [
    {
      "id": "task_1",
      "title": "short task title",
      "description": "what exactly to do",
      "agent": "researcher|architect|coder|planner|critic",
      "depends_on": []
    }
  ],
  "first_agent": "researcher"
}"""

    async def run(self, state: ResearchState) -> dict:
        goal = state["goal"]
        messages = self.build_messages(
            f"Break down this goal into subtasks: \n\n {goal}"
        )

        response = await self.llm.ainvoke(messages)
        content = response.content.strip()

        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        parsed = json.loads(content)
        tasks = parsed.get("tasks", [])
        for task in tasks:
            task["status"] = "pending"

        return {
            "messages": [AIMessage(content=f"[Orchestrator] Goal parsed. {len(tasks)} tasks created.")],
            "tasks": tasks,
            "next_agent": parsed.get("first_agent", "researcher"),
            "output": {"summary": parsed.get("summary", "")},
        }



 

    
