from __future__ import annotations

from env.models import DevSimState, TaskStatus


def grade_easy(state: DevSimState) -> float:
    """Grade the easy scenario: completion + efficiency."""
    total_tasks = len(state.tasks)
    if total_tasks == 0:
        return 0.0

    tasks_done = sum(1 for t in state.tasks if t.status == TaskStatus.DONE)
    steps_used = state.sprint_progress.current_step
    max_steps = state.sprint_progress.max_steps

    completion_score = tasks_done / total_tasks
    efficiency_score = (
        max(0.0, 1.0 - (steps_used / max_steps))
        if tasks_done == total_tasks else 0.0
    )

    score = 0.7 * completion_score + 0.3 * efficiency_score
    return round(max(0.0, min(1.0, score)), 4)


def grade_medium(state: DevSimState) -> float:
    """Grade the medium scenario: completion + priority + efficiency - conflicts."""
    total_tasks = len(state.tasks)
    if total_tasks == 0:
        return 0.0

    tasks_done = sum(1 for t in state.tasks if t.status == TaskStatus.DONE)
    high_pri_done = sum(
        1 for t in state.tasks
        if t.status == TaskStatus.DONE and t.priority <= 2
    )
    high_pri_total = sum(1 for t in state.tasks if t.priority <= 2)
    total_conflicts = state.info.get("total_conflicts_created", 0)
    steps_used = state.sprint_progress.current_step
    max_steps = state.sprint_progress.max_steps

    completion_score = tasks_done / total_tasks
    priority_score = high_pri_done / max(high_pri_total, 1)
    efficiency_score = (
        max(0.0, 1.0 - (steps_used / max_steps))
        if tasks_done == total_tasks else 0.0
    )
    conflict_penalty = min(total_conflicts * 0.1, 0.3)

    score = (
        0.4 * completion_score
        + 0.3 * priority_score
        + 0.15 * efficiency_score
        - conflict_penalty
    )
    return round(max(0.0, min(1.0, score)), 4)


def grade_hard(state: DevSimState) -> float:
    """Grade the hard scenario: priority-weighted completion + PM responsiveness + comms - conflicts."""
    total_tasks = len(state.tasks)
    if total_tasks == 0:
        return 0.0

    priority_weights = {1: 5, 2: 3, 3: 2, 4: 1}
    weighted_done = sum(
        priority_weights.get(t.priority, 1)
        for t in state.tasks if t.status == TaskStatus.DONE
    )
    weighted_total = sum(
        priority_weights.get(t.priority, 1)
        for t in state.tasks
    )
    weighted_completion = weighted_done / max(weighted_total, 1)

    total_conflicts = state.info.get("total_conflicts_created", 0)
    conflict_penalty = min(total_conflicts * 0.08, 0.25)

    pm_messages_total = state.info.get("total_pm_messages", 0)
    pm_acknowledged = state.info.get("pm_messages_acknowledged", 0)
    pm_responsiveness = pm_acknowledged / max(pm_messages_total, 1)

    comms_used = state.info.get("communications_sent", 0)
    comm_score = min(comms_used / 3.0, 1.0)

    score = (
        0.50 * weighted_completion
        + 0.20 * pm_responsiveness
        + 0.10 * comm_score
        - conflict_penalty
    )
    return round(max(0.0, min(1.0, score)), 4)


GRADERS = {
    "easy": grade_easy,
    "medium": grade_medium,
    "hard": grade_hard,
}


def grade(state: DevSimState) -> float:
    """Grade the current state using the appropriate grader."""
    grader = GRADERS.get(state.scenario_id)
    if grader is None:
        return 0.0
    return grader(state)
