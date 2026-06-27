import json
from langchain_core.messages import AIMessage
from agents.base_agent import BaseAgent
from agents.state import ResearchState
from sandbox.code_checks import run_execution_checks
from sandbox.project_venv import ensure_venv, install_packages, detect_missing_imports
from core.config import settings

MAX_RETRIES_PER_TASK = 3

class CriticAgent(BaseAgent):

    def __init__(self):
        super().__init__(settings.critic_model)

    def system_prompt(self) -> str:
        return """
        You are the Critic agent of ResearchOS. You review one
        generated file that has already passed basic execution
        checks (it compiles and imports without error). Your job is
        to judge whether the CONTENT is actually good, not just
        whether it runs.
 
        Check for:
        - Does it actually fulfill the task description?
        - Are there logic errors, missing edge cases, or obvious bugs
          that execution checks wouldn't catch?
        - Is it reasonably clean and idiomatic for its language?
        - Are there security issues (e.g. SQL injection, hardcoded
          secrets, unsafe deserialization)?
 
        Respond ONLY with valid JSON, no prose outside the JSON, no
        markdown fences:
 
        {
          "passed": true or false,
          "issues": ["string", ...],
          "feedback": "string -- concrete, actionable guidance for a
                        rewrite if passed is false; empty string if passed is true"
        }
 
        Be reasonably strict but pragmatic: minor style nitpicks alone
        should not fail a review. Fail it for real bugs, unmet
        requirements, or security problems.
        """
    
    @staticmethod
    def _parse_verdict(raw_content: str, execution_checks: list[dict]) -> dict:
        text = raw_content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
 
        try:
            verdict = json.loads(text)
        except json.JSONDecodeError:
            verdict = {
                "passed": False,
                "issues": ["Critic output was not valid JSON."],
                "feedback": (
                    "The critic's review could not be parsed. Re-attempt "
                    "the implementation, focusing on fulfilling the task "
                    "description precisely."
                ),
                "raw_output": raw_content,
            }
 
        verdict["execution_checks"] = execution_checks
        return verdict
    
    def _run_checks_with_deps(self, state: ResearchState, task: dict, output_path:str) -> dict:
        project_id = state.get("project_id") or "default"
        design = state.get("architecture_design", {})
        declared_deps = design.get("dependencies", [])
        python_path = ensure_venv(project_id)
        install_ok, install_output = install_packages(project_id, declared_deps)

        with open(output_path,"r",encoding="utf-8") as f:
            file_content = f.read()
        missing = detect_missing_imports(file_content, declared_deps)
        if missing:
            extra_ok, extra_output = install_packages(project_id, missing)
            install_ok = install_ok and extra_ok
            install_output += "\n" + extra_output

        exec_result = run_execution_checks(output_path, python_executable=str(python_path))

        if not install_ok and not exec_result["passed"]:
            exec_result["checks"].append(
                {
                    "name": "dependency_install",
                    "passed": False,
                    "output": install_output,
                }
            )
        return exec_result
    
    async def run(self, state: ResearchState) -> dict:
        tasks = state.get("tasks", [])
        coded_tasks = [t for t in tasks if t.get("status") == "coded"]
 
        if not coded_tasks:
            return {
                "messages": [AIMessage(content="[Critic] No coded tasks pending review")],
                "next_agent": "done",
            }
 
        task = coded_tasks[0]
        output_path = task.get("output_path")
 
        if not output_path:
            task["status"] = "failed"
            task["error"] = "No output_path recorded; cannot review."
            return {
                "messages": [AIMessage(content=f"[Critic] '{task.get('title')}' has no output_path -- marking failed")],
                "tasks": tasks,
                "next_agent": "coder",
            }
 
        exec_result = self._run_checks_with_deps(state, task, output_path)
 
        if not exec_result["passed"]:
            verdict = {
                "passed": False,
                "issues": [c["output"] for c in exec_result["checks"] if not c["passed"]],
                "feedback": (
                    "The file fails to execute. Fix the following error(s) and "
                    "rewrite the complete file:\n\n"
                    + "\n\n".join(c["output"] for c in exec_result["checks"] if not c["passed"])
                ),
                "execution_checks": exec_result["checks"],
            }
        else:
            with open(output_path, "r", encoding="utf-8") as f:
                file_content = f.read()
 
            prompt = f"""
            Task:
            Title: {task.get('title')}
            Description: {task.get('description')}
 
            File path: {output_path}
 
            File content:
            {file_content}
 
            Review this file as specified in your instructions.
            """
            messages = self.build_messages(prompt)
            response = await self.llm.ainvoke(messages)
            verdict = self._parse_verdict(response.content, exec_result["checks"])
 
        updated_tasks = tasks
        retry_count = task.get("retry_count", 0)
 
        if verdict["passed"]:
            for t in updated_tasks:
                if t["id"] == task["id"]:
                    t["status"] = "done"
                    t["critic_verdict"] = verdict
            summary_line = f"[Critic] PASSED: {task.get('title')} ({output_path})"
 
            remaining_coded = [
                t for t in updated_tasks
                if t.get("status") == "coded" and t["id"] != task["id"]
            ]
            next_agent = "critic" if remaining_coded else "coder"
 
        else:
            retry_count += 1
            if retry_count >= MAX_RETRIES_PER_TASK:
                for t in updated_tasks:
                    if t["id"] == task["id"]:
                        t["status"] = "flagged"
                        t["retry_count"] = retry_count
                        t["critic_verdict"] = verdict
                summary_line = (
                    f"[Critic] FLAGGED for human review after {retry_count} attempts: "
                    f"{task.get('title')} ({output_path})"
                )
                next_agent = "coder"  
            else:
                for t in updated_tasks:
                    if t["id"] == task["id"]:
                        t["status"] = "pending" 
                        t["retry_count"] = retry_count
                        t["critic_verdict"] = verdict
                        t["revision_feedback"] = verdict.get("feedback", "")
                summary_line = (
                    f"[Critic] FAILED (attempt {retry_count}/{MAX_RETRIES_PER_TASK}): "
                    f"{task.get('title')} -- sending back to coder"
                )
                next_agent = "coder"
 
        return {
            "messages": [AIMessage(content=summary_line)],
            "tasks": updated_tasks,
            "next_agent": next_agent,
        }