# GitTangle - Multi-Agent Sprint Simulator

An OpenEnv RL environment where an AI agent controls two software developers collaborating on a sprint. The agent must coordinate task assignments, PR reviews, and communication to maximize feature delivery while avoiding merge conflicts and respecting task dependencies.

## Why This Environment?

Real software teams face coordination challenges daily: dependency management, merge conflicts, shifting priorities, and resource allocation. GitTangle models these dynamics in a tractable RL environment, making it useful for evaluating an agent's ability to plan, prioritize, and coordinate under constraints.

## Action Space

Each step, the agent provides actions for both developers:

```json
{
  "dev1_action": {
    "action_type": "work_on_task | review_pr | fix_conflict | communicate | idle",
    "task_id": "T1",
    "pr_id": "PR-1",
    "comm_type": "ask_pm_clarification | sync_with_dev",
    "comm_target_task": "T3"
  },
  "dev2_action": { ... }
}
```

| Action | Description |
|--------|-------------|
| `work_on_task` | Progress a task by 1 effort unit. Requires `task_id`. Task must be workable (not blocked, not done). |
| `review_pr` | Review and merge another dev's PR. Requires `pr_id`. Cannot self-review. |
| `fix_conflict` | Resolve a merge conflict on a task. Requires prior sync discussion. Creates a PR. |
| `communicate` | Ask PM for clarification (reduces task effort by 1, once per task) or sync with other dev (required for conflict resolution). |
| `idle` | Do nothing. Penalized (-1.0). |

**Constraints**: Two devs cannot work on the same task or review the same PR simultaneously. Invalid actions are silently converted to idle with a penalty.

## Observation Space

Each step returns:

| Field | Description |
|-------|-------------|
| `task_board` | All tasks with status, effort, priority, dependencies, conflict info |
| `pr_queue` | Pending PRs awaiting review (includes `submitted_by` for self-review prevention) |
| `pm_messages` | PM messages (observation-only context) |
| `dev1_status` / `dev2_status` | Current activity, idle count, tasks completed |
| `sprint_progress` | Step counter, task counts by status, velocity |
| `merge_conflicts` | Task IDs currently in HAS_CONFLICT status |

## Core Mechanics

### Task Lifecycle
```
BACKLOG → IN_PROGRESS → IN_REVIEW → DONE
              ↓
        HAS_CONFLICT → (fix_conflict) → IN_REVIEW → DONE
BACKLOG ↔ BLOCKED (dependency check)
```

### Merge Conflicts
Conflicts are detected at **task completion time**, not during simultaneous work. Two devs can freely work on conflicting tasks — the conflict only triggers when one completes while the other is IN_PROGRESS, IN_REVIEW, or DONE.

**Resolution flow**:
1. Task completes → goes to `HAS_CONFLICT` instead of `IN_REVIEW`
2. Both devs `sync_with_dev` → the higher-priority conflicted task auto-resolves (gets a PR)
3. Remaining task needs `fix_conflict` → creates its PR
4. Both PRs get reviewed by the other dev → both DONE

### PM Events
The PM fires deterministic events at scheduled steps: priority changes, requirement changes (increased effort), new task injections, and deadline warnings.

### Communication
- `ask_pm_clarification`: Reduces a task's effort by 1 (once per task). Useful for high-effort tasks.
- `sync_with_dev`: Required before `fix_conflict` can be used. Also prevents conflicts when used on the same step a task completes.

## Tasks

### Easy: Quick Launch
5 independent tasks, no dependencies, no conflicts, no PM events. 20 steps.
- **Challenge**: Efficient parallel work assignment and review coordination
- **Grading**: 70% completion + 30% efficiency
- **Expected score range**: 0.4 - 0.85

### Medium: Feature Pipeline
8 tasks with dependency chains. T2 and T3 conflict with each other. PM changes priority at step 10. 25 steps.
- **Challenge**: Dependency sequencing, conflict avoidance, priority adaptation
- **Grading**: 40% completion + 30% priority completion + 15% efficiency - conflict penalty
- **Expected score range**: 0.3 - 0.75

### Hard: Crunch Time
10 tasks, complex DAG, multiple conflict pairs. PM changes requirements (step 5), priorities (step 10), and injects a new emergency task (step 14). Total effort exceeds budget — cannot complete everything. 20 steps.
- **Challenge**: Triage under pressure, PM responsiveness, strategic communication
- **Grading**: 60% priority-weighted completion + 20% communication - conflict penalty
- **Expected score range**: 0.1 - 0.65

## Setup

### Local
Requires Python 3.11+. Install dependencies with [uv](https://docs.astral.sh/uv/):
```bash
uv sync
```

Run the OpenEnv FastAPI Server:
```bash
uvicorn app:app --port 7860
```

### Docker
```bash
docker build -t gittangle .
docker run -p 7860:7860 gittangle
```

### Run Baseline
```bash
# With OpenAI
export OPENAI_API_KEY=your-key-here
python -m baseline.inference --task easy

# With Ollama (local)
LLM_BASE_URL=http://localhost:11434/v1 LLM_MODEL=qwen2.5:latest python -m baseline.inference --task medium

# With OpenRouter (free models)
LLM_BASE_URL=https://openrouter.ai/api/v1 LLM_MODEL=qwen/qwen3-235b-a22b:free OPENAI_API_KEY=your-key python -m baseline.inference

# Run specific task or all
python -m baseline.inference --task hard
python -m baseline.inference --task all
```

### Run Tests
```bash
python -m pytest tests/test_env.py -v
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/reset?task_id=easy` | Reset environment for a scenario (easy/medium/hard) |
| POST | `/step` | Submit action JSON, returns observation, reward, done, info |
| GET | `/state` | Get full internal state (used by graders) |
| GET | `/tasks` | List available scenarios and action schema |
| POST | `/grader` | Get grader score (0.0-1.0) for current episode |
| POST | `/baseline` | Run baseline agent (requires OPENAI_API_KEY env var) |
| GET | `/health` | Health check |

## Reward Function

Rewards are provided per-step (not just end-of-episode) to guide agent learning:

| Component | Value |
|-----------|-------|
| Task progress (+1 effort unit) | +1.0 |
| Task completed (moved to review) | +3.0 |
| PR merged | +5.0 |
| High priority task bonus (p1/p2) | +2.0 |
| PM clarification used | +0.5 |
| Useful dev sync (undiscussed conflicts exist) | +1.0 |
| Conflict auto-resolved via sync | +2.0 |
| All tasks completed (sprint done) | +10.0 |
| Idle developer | -1.0 |
| Merge conflict created | -3.0 |
| Invalid action (converted to idle) | -1.0 |
| Wasted sync (no conflicts to discuss) | -1.0 |