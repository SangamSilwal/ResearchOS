from langchain_core.messages import AIMessage
from agents.base_agent import BaseAgent
from agents.state import ResearchState
from core.config import settings
from core.memory import get_recent_runs
from core.runtime import resolve_model

class PlannerAgent(BaseAgent):

    def __init__(self):
        model_key, api_key = resolve_model("planner_model", settings.planner_model)
        super().__init__(model_key, api_key)

    def system_prompt(self) -> str:
        return """
        You are the Planner agent of ResearchOS. You handle
        research-only goals -- the user wants information and a clear
        path forward, not code or a system design.

        You receive the research findings gathered earlier and must
        produce a concrete, ordered, step-by-step plan that tells the
        user exactly what to do, in what order, to act on this
        research and achieve their original goal.

        Your plan must:
        - Be grounded in the actual research findings -- reference
          specific facts, tools, or recommendations that were found,
          not generic advice
        - Be ordered: step 1, step 2, etc., in the sequence the user
          should actually follow them
        - Be concrete enough to act on (name specific tools, settings,
          commands, or resources where the research surfaced them)
        - Flag any open questions or gaps the research didn't resolve

        Respond ONLY with valid JSON, no prose outside the JSON, no
        markdown fences:

        {
          "summary": "one or two sentence summary of the plan's goal",
          "steps": [
            {"step_number": 1, "title": "string", "description": "string", "based_on": "string -- which finding(s) this step draws from"}
          ],
          "open_questions": ["string"]
        }
        """

    @staticmethod
    def _build_findings_context(state: ResearchState) -> str:
        findings = state.get("research_findings", [])
        if not findings:
            return "(no research findings available)"

        blocks = []
        for f in findings:
            sources = ", ".join(f.get("sources", [])[:5]) or "none"
            blocks.append(
                f"## {f.get('task_title', 'Untitled finding')}\n"
                f"{f.get('summary', '')}\n"
                f"Sources: {sources}"
            )
        return "\n\n".join(blocks)

    @staticmethod
    def _parse_plan(raw_content: str) -> dict:
        import json

        text = raw_content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                "summary": "Could not parse planner output as structured JSON.",
                "steps": [],
                "open_questions": [
                    "The planner's output could not be parsed -- see raw_output."
                ],
                "raw_output": raw_content,
            }

    async def run(self, state: ResearchState) -> dict:
        planner_tasks = [
            t
            for t in state.get("tasks", [])
            if t.get("agent") == "planner" and t.get("status") == "pending"
        ]

        if not planner_tasks:
            return {
                "messages": [AIMessage(content="[Planner] No pending planner tasks")],
                "next_agent": "done",
            }

        prompt = f"""
        Goal:
        {state['goal']}

        Research Findings:
        {self._build_findings_context(state)}

        Produce the step-by-step plan as specified in your instructions.
        """
        recent_runs = await get_recent_runs(n=3)
        messages = self.build_messages(prompt,state=state,recent_runs=recent_runs)
        response = await self.llm.ainvoke(messages)
        plan = self._parse_plan(response.content)

        updated_tasks = state.get("tasks", [])
        for t in updated_tasks:
            if t.get("agent") == "planner" and t.get("status") == "pending":
                t["status"] = "done"

        summary_line = (
            f"[Planner] Plan created: {len(plan.get('steps', []))} steps. "
            f"{plan.get('summary', '')}"
        )

        return {
            "messages": [AIMessage(content=summary_line)],
            "tasks": updated_tasks,
            "output": {**state.get("output", {}), "plan": plan},
            "next_agent": "done",
        }