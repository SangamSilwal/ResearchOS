import os
import re
from langchain_core.messages import AIMessage
from agents.base_agent import BaseAgent
from agents.state import ResearchState
from core.config import settings
from core.memory import get_recent_runs
from core.runtime import resolve_model

class CoderAgent(BaseAgent):

    def __init__(self):
        model_key, api_key = resolve_model("coder_model", settings.coder_model)
        super().__init__(model_key, api_key)

    def system_prompt(self) -> str:
        return """
        You are the Coder agent of ResearchOS.
        You receive one implementation task plus the overall system
        design, and must produce the complete, working content for
        exactly one file.
 
        Rules:
        - Output ONLY the raw file content -- no markdown code fences,
          no explanations, no commentary before or after.
        - The content must be complete and runnable/valid for its
          file type, not a partial sketch or "...rest of code here".
        - Follow the conventions implied by the design's file
          structure and decisions (imports, naming, structure).
        - If the task is ambiguous, make the most reasonable concrete
          choice and proceed -- do not ask questions, since there is
          no one to answer them.
        """
    
    def _find_file_path(self, task: dict, design: dict) -> str:
        file_structure = design.get("file_structure", [])
        task_text = f"{task.get('title', '')} {task.get('description', '')}".lower()
        for entry in file_structure:
            path = entry.get("path","")
            purpose = entry.get("purpose","").lower()
            if path and path.lower() in task_text:
                return path
            if purpose and purpose in task_text:
                return path
        slug = re.sub(r"[^a-z0-9]+", "_", task.get("title", "untitled").lower()).strip("_")
        return f"_unmatched/{slug or 'untitled'}.txt"
    
    @staticmethod
    def _strip_code_fences(content: str) -> str:
        text = content.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return text
    
    def _resolve_output_path(self, project_id: str | None, relative_path: str) -> str:
        base = os.path.abspath(settings.output_dir)
        if project_id:
            base = os.path.join(base, project_id)

        candidate = os.path.abspath(os.path.join(base, relative_path))
        if not candidate.startswith(base + os.sep) and candidate != base:
            safe_name = relative_path.replace("..","_").lstrip("/\\")
            candidate = os.path.abspath(os.path.join(base, "_unsafe_paths", safe_name))
        return candidate
    
    async def run(self, state: ResearchState) -> dict:
        coder_tasks = [
            t
            for t in state.get("tasks",[])
            if t.get("agent") == "coder" and t.get("status") == "pending"
        ]

        if not coder_tasks:
            return {
                "messages":[AIMessage(content="[Coder] No Pending coder Tasks")],
                "next_agent":"done",
            }
        
        task = coder_tasks[0]
        design = state.get("architecture_design", {})
        relative_path = self._find_file_path(task,design)
        prompt = f"""
        Overall system design rationale:
        {design.get('rationale', '(no rationale available)')}
 
        Relevant file structure (for conventions/context):
        {design.get('file_structure', [])}
 
        Key decisions:
        {design.get('decisions', [])}
 
        Your task:
        Title: {task.get('title')}
        Description: {task.get('description')}
        Target file path: {relative_path}
 
        Write the complete content for this file now.
        """
        recent_runs = await get_recent_runs(n=3)
        messages = self.build_messages(prompt,state=state,recent_runs=recent_runs)
        response = await self.llm.ainvoke(messages)
        file_content = self._strip_code_fences(response.content)
        output_path = self._resolve_output_path(
            state.get("project_id"), relative_path
        )

        write_error = None
        try:
            os.makedirs(os.path.dirname(output_path),exist_ok=True)
            with open(output_path,"w",encoding="utf-8") as f:
                f.write(file_content)
        except OSError as e:
            write_error = f"{type(e).__name__}: {e}"

        updated_tasks = state.get("tasks",[])
        for t in updated_tasks:
            if t["id"] == task["id"]:
                t["status"] = "coded" if write_error is None else "failed"
                t["output_path"] = output_path
                if write_error:
                    t["error"] = write_error
        remaining = [
            t
            for t in updated_tasks
            if t.get("agent") == "coder" and t.get("status") == "pending"
        ]

        if write_error:
            next_agent = "coder" if remaining else "done"
            summary_line = (
                f"[Coder] FAILED to write {output_path} for "
                f"'{task.get('title')}': {write_error}"
            )
        else:
            next_agent="critic"
            summary_line = f"[Coder] Wrote {output_path} for '{task.get('title')}'"

        return {
            "messages": [AIMessage(content=summary_line)],
            "tasks":updated_tasks,
            "next_agent":next_agent
        }

   