"""Heuristics for classifying a run as build vs research."""


def infer_run_type(goal: str) -> str:
    """Guess run type when the client doesn't specify build vs research."""
    goal_lower = goal.lower()
    build_signals = (
        "build", "create", "implement", "develop", "write code",
        "scaffold", "generate code", "rest api", "fastapi", "django",
        "flask", "web app", "backend", "frontend", "full stack",
    )
    if any(signal in goal_lower for signal in build_signals):
        return "build"
    return "research"


def detect_run_type_from_tasks(tasks: list[dict]) -> str:
    agents = {t.get("agent") for t in tasks}
    if "architect" in agents or "coder" in agents:
        return "build"
    if "planner" in agents:
        return "research"
    return "research"
