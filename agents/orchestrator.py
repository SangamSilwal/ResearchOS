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
2. Decide whether this is a BUILD goal (the user wants software/code
   produced) or a RESEARCH-ONLY goal (the user wants information and
   a plan, with nothing to be coded or designed)
3. Break it into clear, ordered subtasks and assign each to the right
   agent:
   - "researcher" : web search, gather docs, find papers -- used by
                    both build and research-only goals
   - "architect"  : system/code design, tech stack decisions -- ONLY
                    for build goals. Create exactly one "architect"
                    task for any build goal; it will generate its own
                    "coder" tasks afterward, so do not create "coder"
                    tasks yourself.
   - "coder"      : never assign this yourself -- the architect agent
                    creates coder tasks automatically from its design.
   - "critic"     : never assign this yourself -- it runs automatically
                    after each coder task as part of the build pipeline.
   - "planner"    : turns research findings into a concrete, ordered,
                    step-by-step action plan for the user. ONLY for
                    research-only goals -- a goal that asks for
                    information, a recommendation, a comparison, or
                    "how should I approach X" rather than working
                    software. Create exactly one "planner" task for
                    any research-only goal.
 
CRITICAL ROUTING RULE: a single goal is either a build goal or a
research-only goal, never both. Never include both an "architect" task
and a "planner" task in the same task list -- if there is any
"architect" task present, "planner" tasks will be silently ignored by
the system. Choose one path:
  - Build goal -> some number of "researcher" tasks (can be zero) +
    exactly one "architect" task. Do not add "coder", "critic", or
    "planner" tasks.
  - Research-only goal -> some number of "researcher" tasks (can be
    zero) + exactly one "planner" task. Do not add "architect",
    "coder", or "critic" tasks.
 
Return your task breakdown as valid JSON only. No markdown, no extra text.
Format:
{
  "summary": "one sentence summary of the goal",
  "tasks": [
    {
      "id": "task_1",
      "title": "short task title",
      "description": "what exactly to do",
      "agent": "researcher|architect|planner",
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



 

    
