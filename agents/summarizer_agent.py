import json
from langchain_core.messages import AIMessage
from agents.base_agent import BaseAgent
from agents.state import ResearchState
from core.config import settings

class SummarizerAgent(BaseAgent):

    def __init__(self):
        super().__init__(settings.summarizer_model)

    def system_prompt(self) -> str:
        return """
        You are the Summarizer agent for ResearchOS.
        Your job is to read the completed run state and produce one concise,
        high-level conclusion that captures:
        - what was learned from research
        - the selected architecture decisions
        - files that were written
        - any critic feedback or unresolved issues
        Output a final conclusion in one paragraph. If there are outstanding
        problems, mention them briefly.
        """

    @staticmethod
    def _summarize_findings(findings: list[dict]) -> str:
        if not findings:
            return "No research findings were captured."
        lines = []
        for idx, finding in enumerate(findings[:5], start=1):
            summary = finding.get("summary") or finding.get("title") or finding.get("content")
            if summary:
                lines.append(f"{idx}. {summary}")
        return "\n".join(lines) if lines else "Research findings were captured but not summarized."

    @staticmethod
    def _summarize_tasks(tasks: list[dict]) -> str:
        if not tasks:
            return "No tasks were executed."
        lines = []
        for t in tasks[:8]:
            title = t.get("title") or "unnamed task"
            status = t.get("status", "unknown")
            if t.get("agent"):
                lines.append(f"{title} [{t.get('agent')}] -> {status}")
            else:
                lines.append(f"{title} -> {status}")
        return "\n".join(lines)

    async def run(self, state: ResearchState) -> dict:
        research_findings = state.get("research_findings", [])
        architecture_design = state.get("architecture_design", {})
        tasks = state.get("tasks", [])
        existing_summary = state.get("output", {}).get("summary", "")

        prompt = (
            "Summarize the completed ResearchOS run. Include the goal, the main research findings, "
            "the architecture decisions, what files were written, and any critic feedback or failed tasks. "
            "If there were unresolved issues, mention them. Keep the conclusion concise and direct.\n\n"
            f"Goal: {state.get('goal', '')}\n\n"
            f"Existing goal summary: {existing_summary}\n\n"
            f"Research findings:\n{self._summarize_findings(research_findings)}\n\n"
            f"Architecture design:\n{json.dumps(architecture_design, indent=2)[:2000]}\n\n"
            f"Tasks:\n{self._summarize_tasks(tasks)}\n\n"
            "Do not invent new facts. Base the conclusion only on the provided run data."
        )

        messages = self.build_messages(prompt, state=state)
        response = await self.llm.ainvoke(messages)
        summary_text = response.content.strip()

        return {
            "messages": [AIMessage(content=f"[Summarizer] {summary_text}")],
            "summary": summary_text,
            "next_agent": "done",
        }
