import asyncio
import json
import uuid
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from agents.base_agent import BaseAgent
from agents.state import ResearchState
from core.config import settings

 
ARCHITECT_SYSTEM_PROMPT = """
You are an Architect agent of ResearchOS.
You receive research findings gathered by the Researcher agent
and turn them into a concrete system design.
 
Your design must include:
- A short rationale connecting design choices back to the
  research findings (cite which finding informed which choice)
- A component breakdown: each major component, its
  responsibility, and how it talks to the others
- A proposed file/module structure (paths and one-line purpose
  for each file)
- Key technical decisions and tradeoffs (libraries, patterns,
  data flow) with brief justification
- Risks or open questions the coder should be aware of
 
Respond ONLY with valid JSON matching this schema, no prose
outside the JSON, no markdown code fences:
 
{
  "rationale": "string",
  "components": [
    {"name": "string", "responsibility": "string", "interacts_with": ["string"]}
  ],
  "file_structure": [
    {"path": "string", "purpose": "string"}
  ],
  "decisions": [
    {"decision": "string", "justification": "string"}
  ],
  "risks": ["string"],
  "dependencies": ["string"],
  "implementation_tasks": [
    {"title": "string", "description": "string"}
  ]
}
 
dependencies should list every third-party Python package (PyPI
install name, not the import name if they differ -- e.g. "Pillow"
not "PIL", "python-dotenv" not "dotenv") that the implementation_tasks
will need to import. Be thorough: missing a dependency here means
the generated code will fail an import check later. Do not include
standard-library modules.
 
implementation_tasks should be the concrete, ordered units of
work a coder agent would need to pick up to build this design --
one task per file or cohesive unit of functionality, not vague
umbrella tasks.
"""


def build_findings_context(state: ResearchState) -> str:
    findings = state.get("research_findings", [])
    if not findings:
        return "(no research findings available)"
    blocks = []
    for f in findings:
        sources = ", ".join(f.get("sources",[])[:5]) or "none"
        blocks.append(
            f"## {f.get('task_title' , 'Untitled finding')}\n"
            f"{f.get("summary","")}\n"
            f"Sources: {sources}"
        )
    return "\n\n".join(blocks)

def parse_design(raw_content: str) -> dict:
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
            "rationale": "Could not parse architect output as JSON.",
            "components": [],
            "file_structure": [],
            "decisions": [],
            "risks": ["Architect output was not valid JSON; see raw_output."],
            "implementation_tasks": [],
            "raw_output": raw_content,
        }

class ArchitectProposer(BaseAgent):

    def __init__(self, model_name:str, proposer_id:str):
        super().__init__(model_name)
        self.proposer_id = proposer_id
        self.model_name = model_name

    def system_prompt(self) -> str:
        return ARCHITECT_SYSTEM_PROMPT
    
    async def run(self, state: ResearchState) -> dict:
        findings_context = build_findings_context(state)
 
        prompt = f"""
        Goal:
        {state['goal']}
 
        Research Findings:
        {findings_context}
 
        Produce the system design as specified in your instructions.
        """

        messages = self.build_messages(prompt)
        response = await self.llm.ainvoke(messages)
        design = parse_design(response.content)
        design["_proposer_id"] = self.proposer_id
        design["_model_name"] = self.model_name
        return design


JUDGE_SYSTEM_PROMPT = """
You are the Architect Judge of ResearchOS. You are given two candidate
system designs (A and B) produced independently for the same goal and
research findings. Decide which design is better engineering, and why.
 
Score each design 0-10 on:
- groundedness: does it genuinely reflect the research findings, or
  ignore them?
- component clarity: are responsibilities clear and non-overlapping?
- feasibility: is the file structure and task breakdown concrete and
  buildable, not vague?
- risk awareness: does it surface real risks/tradeoffs rather than
  glossing over them?
 
Respond ONLY with valid JSON, no prose outside the JSON, no markdown
fences:
 
{
  "scores": {
    "A": {"groundedness": 0, "component_clarity": 0, "feasibility": 0, "risk_awareness": 0},
    "B": {"groundedness": 0, "component_clarity": 0, "feasibility": 0, "risk_awareness": 0}
  },
  "winner": "A" or "B",
  "justification": "string, 2-4 sentences explaining the decision"
}
"""


class ArchitectJudge(BaseAgent):

    def __init__(self, model_name:str):
        super().__init__(model_name)

    def system_prompt(self) -> str:
        return JUDGE_SYSTEM_PROMPT
    
    async def run(self, state: ResearchState, design_a: dict, design_b: dict) -> dict:
        prompt = f"""
        Goal:
        {state['goal']}
 
        Research Findings:
        {build_findings_context(state)}
 
        Design A:
        {json.dumps(design_a, indent=2)}
 
        Design B:
        {json.dumps(design_b, indent=2)}
 
        Evaluate both designs as specified in your instructions.
        """
 
        messages = self.build_messages(prompt)
        response = await self.llm.ainvoke(messages)
 
        try:
            text = response.content.strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            verdict = json.loads(text)
        except json.JSONDecodeError:
            fallback_winner = (
                "A"
                if len(design_a.get("implementation_tasks", []))
                >= len(design_b.get("implementation_tasks", []))
                else "B"
            )
            verdict = {
                "scores": {},
                "winner": fallback_winner,
                "justification": (
                    "Judge output was not valid JSON; defaulted to the "
                    "design with more implementation tasks."
                ),
                "raw_output": response.content,
            }
        return verdict

async def architect_node(state: ResearchState) -> dict:
    proposer_a = ArchitectProposer(settings.architect_model_a, proposer_id="A")
    proposer_b = ArchitectProposer(settings.architect_model_b, proposer_id="B")
    judge = ArchitectJudge(settings.architect_judge_model)

    design_a, design_b = await asyncio.gather(
        proposer_a.run(state),
        proposer_b.run(state)
    )

    verdict = await judge.run(state, design_a, design_b)
    winner_key = verdict.get("winner","A")
    winning_design = design_a if winner_key == "A" else design_b
    losing_design = design_b if winner_key == "A" else design_a

    new_tasks = [
        {
            "id": str(uuid.uuid4()),
            "title": t.get("title", "Untitled task"),
            "description": t.get("description", ""),
            "agent": "coder",
            "status": "pending",
        }
        for t in winning_design.get("implementation_tasks", [])
    ]
 
    updated_tasks = state.get("tasks", []) + new_tasks
 
    summary_line = (
        f"[Architect] {winning_design.get('_model_name', winner_key)} won "
        f"({len(winning_design.get('components', []))} components, "
        f"{len(new_tasks)} coder tasks). "
        f"Judge: {verdict.get('justification', 'no justification given')}"
    )
 
    return {
        "messages": [AIMessage(content=summary_line)],
        "tasks": updated_tasks,
        "architecture_design": winning_design,
        "architecture_competition": {
            "design_a": design_a,
            "design_b": design_b,
            "verdict": verdict,
            "winner": winner_key,
        },
        "next_agent": "coder" if new_tasks else "done",
    }
