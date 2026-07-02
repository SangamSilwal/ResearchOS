import argparse
import asyncio
import sys
import uuid

from agents.graph import build_graph
from agents.state import ResearchState
from core.memory import save_run_memory, get_recent_runs, format_run_memory_for_prompt


async def main(goal: str, project_id: str) -> None:
    recent_runs = await get_recent_runs(n=3)
    if recent_runs:
        print("Memory from previous runs:")
        print(format_run_memory_for_prompt(recent_runs))
        print()

    state: ResearchState = {
        "goal": goal,
        "messages": [],
        "tasks": [],
        "research_findings": [],
        "output": {},
        "summary": None,
        "next_agent": "orchestrator",
        "error": None,
        "project_id": project_id,
    }

    print(f"Goal: {goal}")
    print(f"Project ID: {project_id}\n")
    print("Running ResearchOS graph...\n")

    compiled_graph = build_graph()

    final_state = None
    async for event in compiled_graph.astream(state, stream_mode="values"):
        final_state = event
        messages = event.get("messages", [])
        if messages:
            print(messages[-1].content)

    print("\n--- Done ---")
    if final_state is None:
        print("(graph produced no events -- check for an early error)")
        return

    summary_text = final_state.get("summary")
    if summary_text:
        print("\nFinal summary:\n")
        print(summary_text)
        print()

    tasks = final_state.get("tasks", [])
    by_status: dict[str, int] = {}
    for t in tasks:
        status = t.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1
    print(f"Tasks by status: {by_status}")

    written = [t.get("output_path") for t in tasks if t.get("output_path")]
    if written:
        print("\nFiles written:")
        for path in written:
            print(f"  - {path}")

    flagged = [t for t in tasks if t.get("status") == "flagged"]
    if flagged:
        print("\nFlagged for human review (failed critic 3x):")
        for t in flagged:
            print(f"\n  - {t.get('title')} ({t.get('output_path')})")
            verdict = t.get("critic_verdict", {})
            print(f"    passed: {verdict.get('passed')}")
            print(f"    issues: {verdict.get('issues')}")
            print(f"    feedback: {verdict.get('feedback')}")
            for check in verdict.get("execution_checks", []):
                status = "OK" if check.get("passed") else "FAIL"
                print(f"    [{status}] {check.get('name')}: {check.get('output', '')[:300]}")

    competition = final_state.get("architecture_competition", {})
    if competition:
        print(f"\nArchitecture competition winner: {competition.get('winner')}")
        print(f"Judge justification: {competition.get('verdict', {}).get('justification', '')}")

    # Persist this run's summary for future runs to reference
    await save_run_memory(
        project_id=project_id,
        goal=goal,
        files=written,
        flagged=[t.get("title", "") for t in flagged],
        task_summary=by_status,
        summary=final_state.get("summary", ""),
    )
    print(f"\nRun summary saved to memory (project_id={project_id})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the ResearchOS graph directly.")
    parser.add_argument("goal", help='The goal to test, e.g. "Build a FastAPI REST API"')
    parser.add_argument(
        "--project-id",
        default=None,
        help=(
            "Project/thread ID, used for crash-recovery checkpointing. "
            "If omitted, a new random ID is generated -- IMPORTANT: a new "
            "random ID means resuming is impossible, since nothing matches "
            "a previous checkpoint. To resume an interrupted run, you MUST "
            "pass the exact same --project-id it used."
        ),
    )
    args = parser.parse_args()

    project_id = args.project_id or f"test_{uuid.uuid4().hex[:8]}"

    if not args.project_id:
        print(
            f"No --project-id given -- generated a new one: {project_id}\n"
            f"Save this if you might want to resume later: "
            f"--project-id {project_id}\n"
        )

    try:
        asyncio.run(main(args.goal, project_id))
    except KeyboardInterrupt:
        print(f"\nInterrupted. Resume with: --project-id {project_id}")
        sys.exit(1)
    except Exception:
        print(f"\nRun failed. Resume with: --project-id {project_id}")
        raise