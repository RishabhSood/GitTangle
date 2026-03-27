# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

DevSim — a multi-agent sprint simulator built as an OpenEnv RL environment for the Scaler RL Hackathon. An AI agent controls two developers collaborating on a software sprint. The environment exposes a FastAPI server with OpenEnv-compliant endpoints.

## Commands

```bash
# Run tests
source .venv/bin/activate && python -m pytest tests/test_env.py -v

# Run a single test
python -m pytest tests/test_env.py::TestConflicts::test_conflict_at_completion_time -v

# Start server locally
uvicorn app:app --port 7860

# Test all endpoints quickly
python -c "from fastapi.testclient import TestClient; from app import app; c=TestClient(app); print(c.get('/health').json())"

# Run baseline (OpenAI-compatible)
LLM_BASE_URL=http://localhost:11434/v1 LLM_MODEL=qwen2.5:latest python -m baseline.inference --task easy

# Docker
docker build -t devsim . && docker run -p 7860:7860 devsim
```

## Architecture

```
app.py                    ← FastAPI endpoints (thin wrapper over DevSimEnv)
env/
  models.py               ← All Pydantic models: Action, Observation, Reward, DevSimState, etc.
  environment.py          ← DevSimEnv class: reset/step/state API + reward computation
  simulation.py           ← SprintSimulation: core engine (conflict detection, deps, PM events, action execution)
  tasks.py                ← 3 scenario configs as data (Easy/Medium/Hard ScenarioConfig objects)
  graders.py              ← Deterministic scoring functions per scenario (0.0-1.0)
baseline/
  inference.py            ← OpenAI-compatible baseline agent with action hints
```

**Data flow**: `app.py` → `DevSimEnv` (environment.py) → `SprintSimulation` (simulation.py). Models in `models.py` are imported everywhere. Scenarios in `tasks.py` are pure data. Graders in `graders.py` are pure functions of `DevSimState`.

## Key Mechanics

- **Conflicts happen at completion time**, not during simultaneous work. When a task completes and its `conflicts_with` partner is IN_PROGRESS/IN_REVIEW/DONE, the completing task goes to HAS_CONFLICT.
- **Conflict resolution flow**: Both devs must `sync_with_dev` → auto-resolves higher-priority task (creates PR) → other task needs `fix_conflict` → then PR review.
- `fix_conflict` requires the task to be in `_discussed_conflicts` (set during sync). Tasks whose conflict partner was already discussed auto-inherit discussed status.
- **Sync reward only given when there are undiscussed HAS_CONFLICT tasks**. Pointless syncs get `wasted_sync_penalty: -1.0`.
- **Invalid actions silently convert to idle** with `invalid_action_penalty`. Two devs cannot work on the same task or review the same PR.
- **PM events are deterministic** — fired at fixed step numbers per scenario for reproducible grading.
- **Devs cannot self-review PRs**. PR `submitted_by` tracks which dev created it.

## Testing Patterns

Tests use a `@pytest.fixture` returning `DevSimEnv()`. Test classes: `TestReset`, `TestStep`, `TestDependencies`, `TestConflicts`, `TestCommunication`, `TestPMEvents`, `TestGraders`, `TestState`. The medium scenario is commonly used for conflict/dependency tests since T2 and T3 conflict with each other and both depend on T1.

## Baseline Inference

`baseline/inference.py` exports shared utilities used by other inference scripts: `SYSTEM_PROMPT`, `IDLE_ACTION`, `sanitize_action`, `build_action_hint`, `_describe_action`. The `build_action_hint` function generates a concise action summary from the observation (workable tasks, reviewable PRs, conflict status, PM messages). The baseline is stateless per step — each LLM call gets previous step reward feedback + action hint + full observation JSON.
