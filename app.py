from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from env.models import Action, Observation, GitTangleState
from env.environment import GitTangleEnv
from env.graders import grade
from env.tasks import SCENARIOS

app = FastAPI(
    title="GitTangle - Multi-Agent Sprint Simulator",
    description="Two developers collaborate on a sprint. An RL agent controls both.",
    version="1.0.0",
)

env = GitTangleEnv()


class StepResponse(BaseModel):
    observation: Observation
    reward: float
    reward_breakdown: dict[str, float]
    done: bool
    info: dict


class GraderResponse(BaseModel):
    task_id: str
    score: float


class TaskInfo(BaseModel):
    id: str
    name: str
    difficulty: str
    description: str


class TasksResponse(BaseModel):
    tasks: list[TaskInfo]
    action_schema: dict


@app.post("/reset", response_model=Observation)
def reset(task_id: str = "easy"):
    """Reset the environment for a given scenario."""
    try:
        obs = env.reset(task_id=task_id)
        return obs
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step", response_model=StepResponse)
def step(action: Action):
    """Execute one step in the environment."""
    try:
        obs, reward, done, info = env.step(action)
        return StepResponse(
            observation=obs,
            reward=reward.total,
            reward_breakdown=reward.breakdown,
            done=done,
            info=info,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state", response_model=GitTangleState)
def state():
    """Return full internal state."""
    return env.state()


@app.get("/tasks", response_model=TasksResponse)
def tasks():
    """Return list of available tasks and the action schema."""
    # Deduplicate (backward-compat aliases point to same config)
    seen = set()
    task_list = []
    for cfg in SCENARIOS.values():
        if cfg.scenario_id not in seen:
            seen.add(cfg.scenario_id)
            task_list.append(TaskInfo(
                id=cfg.scenario_id,
                name=cfg.name,
                difficulty=cfg.difficulty,
                description=cfg.description,
            ))
    return TasksResponse(
        tasks=task_list,
        action_schema=Action.model_json_schema(),
    )


@app.post("/grader", response_model=GraderResponse)
def grader():
    """Return grader score for the current episode."""
    current_state = env.state()
    if not current_state.scenario_id:
        raise HTTPException(status_code=400, detail="No episode in progress. Call /reset first.")
    score = grade(current_state)
    return GraderResponse(task_id=current_state.scenario_id, score=score)


@app.post("/baseline")
def baseline():
    """Run baseline inference and return scores. Requires OPENAI_API_KEY env var."""
    import os
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=400,
            detail="OPENAI_API_KEY environment variable not set.",
        )
    from baseline.inference import run_baseline
    scores = run_baseline(base_url="http://localhost:7860")
    return {"scores": scores}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/metadata")
def metadata():
    """Return environment metadata."""
    return {
        "name": "GitTangle",
        "description": "Multi-Agent Sprint Simulator — an RL environment where an AI agent controls two developers collaborating on a software sprint.",
    }


@app.get("/schema")
def schema():
    """Return action, observation, and state JSON schemas."""
    return {
        "action": Action.model_json_schema(),
        "observation": Observation.model_json_schema(),
        "state": GitTangleState.model_json_schema(),
    }


@app.get("/summary")
def summary():
    """Return episode summary for the current scenario."""
    from env.environment import build_episode_summary
    if env._scenario_id not in SCENARIOS:
        raise HTTPException(status_code=400, detail="No episode in progress.")
    config = SCENARIOS[env._scenario_id]
    return {"summary": build_episode_summary(config)}
