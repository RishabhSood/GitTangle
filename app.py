from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
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


@app.get("/", response_class=HTMLResponse)
def landing():
    """Landing page for HF Spaces."""
    # Build scenario table rows
    seen = set()
    rows = []
    for cfg in SCENARIOS.values():
        if cfg.scenario_id in seen:
            continue
        seen.add(cfg.scenario_id)
        mechanics = []
        if cfg.enable_specialization:
            mechanics.append("Specialization")
        if cfg.enable_review_rejection:
            mechanics.append("Review Rejection")
        if cfg.enable_pip:
            mechanics.append("PIP")
        mech_str = ", ".join(mechanics) if mechanics else "—"
        tasks_count = len(cfg.tasks)
        rows.append(
            f"<tr><td><code>{cfg.scenario_id}</code></td><td>{cfg.name}</td>"
            f"<td><span class='badge {cfg.difficulty}'>{cfg.difficulty}</span></td>"
            f"<td>{tasks_count}</td><td>{cfg.max_steps}</td><td>{mech_str}</td></tr>"
        )
    table_rows = "\n".join(rows)

    base_url = "https://arcticbot-gittangle.hf.space"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GitTangle</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@400;700;900&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'JetBrains Mono', monospace;
         background: #0a0a0f; color: #b0b8c8; line-height: 1.6;
         background-image: radial-gradient(ellipse at 50% 0%, rgba(88, 28, 135, 0.15) 0%, transparent 60%),
                           radial-gradient(ellipse at 80% 80%, rgba(6, 182, 212, 0.08) 0%, transparent 40%); }}
  .container {{ max-width: 960px; margin: 0 auto; padding: 3rem 1.5rem; }}
  .glow {{ text-shadow: 0 0 20px rgba(6, 182, 212, 0.5), 0 0 40px rgba(6, 182, 212, 0.2); }}
  .glow-pink {{ text-shadow: 0 0 20px rgba(236, 72, 153, 0.5), 0 0 40px rgba(236, 72, 153, 0.2); }}
  h1 {{ font-family: 'Orbitron', sans-serif; font-size: 2.8rem; font-weight: 900;
       color: #06b6d4; margin-bottom: 0.2rem; letter-spacing: 0.05em; }}
  h1 span {{ color: #ec4899; }}
  .subtitle {{ color: #64748b; font-size: 0.95rem; margin-bottom: 0.5rem; }}
  .tagline {{ color: #06b6d4; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.15em;
              margin-bottom: 2.5rem; opacity: 0.7; }}
  h2 {{ font-family: 'Orbitron', sans-serif; color: #06b6d4; font-size: 1rem;
       margin: 2.5rem 0 1rem; text-transform: uppercase; letter-spacing: 0.1em;
       border-bottom: 1px solid rgba(6, 182, 212, 0.2); padding-bottom: 0.5rem; }}
  table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.8rem; }}
  th {{ text-align: left; padding: 0.6rem 0.8rem; background: rgba(6, 182, 212, 0.05);
       color: #06b6d4; font-weight: 700; text-transform: uppercase; font-size: 0.65rem;
       letter-spacing: 0.1em; border-bottom: 1px solid rgba(6, 182, 212, 0.15); }}
  td {{ padding: 0.5rem 0.8rem; border-bottom: 1px solid rgba(255, 255, 255, 0.03); }}
  tr:hover td {{ background: rgba(6, 182, 212, 0.04); }}
  code {{ background: rgba(6, 182, 212, 0.08); padding: 0.15rem 0.4rem; border-radius: 3px;
         font-size: 0.8rem; color: #ec4899; border: 1px solid rgba(236, 72, 153, 0.15); }}
  .badge {{ padding: 0.2rem 0.6rem; border-radius: 2px; font-size: 0.65rem; font-weight: 700;
           text-transform: uppercase; letter-spacing: 0.08em; font-family: 'Orbitron', sans-serif; }}
  .badge.easy {{ background: rgba(34, 197, 94, 0.1); color: #22c55e; border: 1px solid rgba(34, 197, 94, 0.3); }}
  .badge.medium {{ background: rgba(234, 179, 8, 0.1); color: #eab308; border: 1px solid rgba(234, 179, 8, 0.3); }}
  .badge.hard {{ background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }}
  .endpoints {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.6rem; margin: 1rem 0; }}
  .endpoint {{ background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(6, 182, 212, 0.1);
              border-radius: 4px; padding: 0.7rem 1rem; transition: all 0.2s; }}
  .endpoint:hover {{ border-color: rgba(6, 182, 212, 0.3); background: rgba(6, 182, 212, 0.04);
                    box-shadow: 0 0 15px rgba(6, 182, 212, 0.05); }}
  .endpoint .method {{ font-family: 'Orbitron', sans-serif; font-weight: 700; font-size: 0.6rem;
                      padding: 0.15rem 0.5rem; border-radius: 2px; margin-right: 0.5rem; letter-spacing: 0.05em; }}
  .method.get {{ background: rgba(34, 197, 94, 0.1); color: #22c55e; border: 1px solid rgba(34, 197, 94, 0.3); }}
  .method.post {{ background: rgba(6, 182, 212, 0.1); color: #06b6d4; border: 1px solid rgba(6, 182, 212, 0.3); }}
  .endpoint .path {{ color: #e2e8f0; font-size: 0.85rem; }}
  .endpoint .desc {{ color: #475569; font-size: 0.75rem; margin-top: 0.3rem; }}
  .try-it {{ background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(6, 182, 212, 0.1);
            border-radius: 4px; padding: 1rem 1.2rem; margin: 1rem 0; }}
  .try-it code {{ display: block; padding: 0.5rem 0.8rem; margin: 0.4rem 0; white-space: pre-wrap;
                 word-break: break-all; background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(6, 182, 212, 0.08);
                 color: #94a3b8; font-size: 0.78rem; }}
  .try-it code .cmd {{ color: #06b6d4; }}
  a {{ color: #06b6d4; text-decoration: none; transition: color 0.2s; }}
  a:hover {{ color: #ec4899; text-shadow: 0 0 10px rgba(236, 72, 153, 0.3); }}
  .footer {{ margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid rgba(6, 182, 212, 0.1);
            color: #334155; font-size: 0.75rem; text-align: center; }}
  .stats {{ display: flex; gap: 2rem; margin: 1.5rem 0; }}
  .stat {{ text-align: center; }}
  .stat-val {{ font-family: 'Orbitron', sans-serif; font-size: 1.8rem; font-weight: 900; color: #06b6d4; }}
  .stat-label {{ font-size: 0.7rem; color: #475569; text-transform: uppercase; letter-spacing: 0.1em; }}
  .desc-text {{ color: #64748b; font-size: 0.85rem; line-height: 1.7; margin: 0.5rem 0 1rem; }}
  .desc-text em {{ color: #06b6d4; font-style: normal; }}
  .mechanic-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.8rem; margin: 1rem 0; }}
  .mechanic-card {{ background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(6, 182, 212, 0.08);
                   border-radius: 4px; padding: 1rem; transition: all 0.2s; position: relative; }}
  .mechanic-card:hover {{ border-color: rgba(236, 72, 153, 0.3); box-shadow: 0 0 20px rgba(236, 72, 153, 0.05); }}
  .mechanic-icon {{ font-size: 1.4rem; margin-bottom: 0.4rem; }}
  .mechanic-title {{ font-family: 'Orbitron', sans-serif; font-size: 0.75rem; color: #e2e8f0;
                    font-weight: 700; margin-bottom: 0.4rem; text-transform: uppercase; letter-spacing: 0.03em; }}
  .mechanic-desc {{ font-size: 0.75rem; color: #64748b; line-height: 1.5; }}
  .mechanic-desc code {{ font-size: 0.7rem; padding: 0.1rem 0.3rem; word-break: break-all; }}
  .mechanic-desc em {{ color: #ec4899; font-style: normal; }}
  .mechanic-where {{ font-family: 'Orbitron', sans-serif; font-size: 0.6rem; color: #06b6d4; margin-top: 0.5rem;
                    text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.7; }}
</style>
</head>
<body>
<div class="container">
  <h1 class="glow">GIT<span class="glow-pink">TANGLE</span></h1>
  <p class="subtitle">Multi-Agent Sprint Simulator</p>
  <p class="tagline">// OpenEnv RL Environment</p>

  <div class="stats">
    <div class="stat"><div class="stat-val">15</div><div class="stat-label">Scenarios</div></div>
    <div class="stat"><div class="stat-val">2</div><div class="stat-label">Agents</div></div>
    <div class="stat"><div class="stat-val">3</div><div class="stat-label">Mechanics</div></div>
    <div class="stat"><div class="stat-val">5</div><div class="stat-label">Actions</div></div>
  </div>

  <h2>// Why GitTangle?</h2>
  <p class="desc-text">Real engineering teams don't work in isolation. They face dependency chains, merge conflicts, shifting priorities, and the constant tension between speed and quality. GitTangle models these dynamics as an RL environment — an AI agent controls two developers through a sprint, and must learn to coordinate, triage, and adapt.</p>

  <h2>// Core Loop</h2>
  <div class="mechanic-grid">
    <div class="mechanic-card">
      <div class="mechanic-icon">&#9881;</div>
      <div class="mechanic-title">Work &rarr; Review &rarr; Merge</div>
      <div class="mechanic-desc">Devs work on tasks (effort decrements per step). Completed tasks become PRs. The <em>other</em> dev must review — no self-reviews. Merged PRs unlock dependent tasks.</div>
    </div>
    <div class="mechanic-card">
      <div class="mechanic-icon">&#9889;</div>
      <div class="mechanic-title">Merge Conflicts</div>
      <div class="mechanic-desc">Conflicts trigger at <em>completion time</em>, not during work. When a task completes while its conflict partner is active, it enters HAS_CONFLICT. Resolution requires both devs to sync, then fix.</div>
    </div>
    <div class="mechanic-card">
      <div class="mechanic-icon">&#128172;</div>
      <div class="mechanic-title">Conflict Resolution</div>
      <div class="mechanic-desc">Both devs must <code>sync_with_dev</code> simultaneously. The higher-priority task auto-resolves to a PR. The other needs <code>fix_conflict</code> to create its PR. Requires coordination.</div>
    </div>
    <div class="mechanic-card">
      <div class="mechanic-icon">&#127919;</div>
      <div class="mechanic-title">PM Events</div>
      <div class="mechanic-desc">Deterministic events fire at scheduled steps: priority changes, scope expansion, emergency task injections. The agent sees updated state and must adapt its strategy mid-sprint.</div>
    </div>
  </div>

  <h2>// Advanced Mechanics</h2>
  <div class="mechanic-grid">
    <div class="mechanic-card">
      <div class="mechanic-icon">&#127911;</div>
      <div class="mechanic-title">Developer Specialization</div>
      <div class="mechanic-desc">Each dev specializes in certain task types (e.g. backend, frontend). Working on specialty = normal speed. Outside specialty = half speed. Testing is always neutral. Forces smart task assignment.</div>
      <div class="mechanic-where">Medium + Hard</div>
    </div>
    <div class="mechanic-card">
      <div class="mechanic-icon">&#10060;</div>
      <div class="mechanic-title">Code Review Rejection</div>
      <div class="mechanic-desc">Some tasks are flagged REJECTABLE. First PR review gets rejected — task returns to IN_PROGRESS with +1 rework effort. Second review always succeeds. Teaches: rushing = rework.</div>
      <div class="mechanic-where">Medium + Hard</div>
    </div>
    <div class="mechanic-card">
      <div class="mechanic-icon">&#128683;</div>
      <div class="mechanic-title">Developer PIP</div>
      <div class="mechanic-desc">If a dev causes too many conflicts or idles excessively, they get locked out for N steps. All actions forced to idle. Counters reset after PIP ends. Punishes sloppy coordination.</div>
      <div class="mechanic-where">Hard only</div>
    </div>
    <div class="mechanic-card">
      <div class="mechanic-icon">&#128200;</div>
      <div class="mechanic-title">Descriptive Rewards</div>
      <div class="mechanic-desc">Reward keys describe <em>why</em> they fired: <code>needs_sync_first</code>, <code>dev2_must_also_sync</code>. The agent learns mechanics from feedback, not instructions.</div>
      <div class="mechanic-where">All scenarios</div>
    </div>
  </div>

  <h2>// Scenarios</h2>
  <table>
    <thead><tr><th>ID</th><th>Name</th><th>Difficulty</th><th>Tasks</th><th>Steps</th><th>Mechanics</th></tr></thead>
    <tbody>{table_rows}</tbody>
  </table>

  <h2>// API Endpoints</h2>
  <div class="endpoints">
    <div class="endpoint"><span class="method post">POST</span><span class="path">/reset?task_id=easy_1</span><div class="desc">Initialize episode</div></div>
    <div class="endpoint"><span class="method post">POST</span><span class="path">/step</span><div class="desc">Execute agent actions</div></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path">/state</span><div class="desc">Internal state dump</div></div>
    <div class="endpoint"><span class="method post">POST</span><span class="path">/grader</span><div class="desc">Episode score [0.0-1.0]</div></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path">/tasks</span><div class="desc">Scenario manifest</div></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path">/health</span><div class="desc">System status</div></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path">/schema</span><div class="desc">Type schemas</div></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path">/docs</span><div class="desc">Swagger UI</div></div>
  </div>

  <h2>// Quick Start</h2>
  <div class="try-it">
    <code>curl -X POST {base_url}/reset?task_id=easy_1</code>
    <code>curl -X POST {base_url}/step -H "Content-Type: application/json" \\
  -d '{{"dev1_action": {{"action_type": "work_on_task", "task_id": "T1"}}, "dev2_action": {{"action_type": "work_on_task", "task_id": "T2"}}}}'</code>
    <code>curl -X POST {base_url}/grader</code>
  </div>

  <div class="footer">
    <a href="/docs">API Docs</a> &middot; <a href="/ui/scenarios">Scenarios</a> &middot; <a href="/ui/schemas">Schemas</a>
  </div>
</div>
</body>
</html>"""


SHARED_STYLES = """
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@400;700;900&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'JetBrains Mono', monospace;
         background: #0a0a0f; color: #b0b8c8; line-height: 1.6;
         background-image: radial-gradient(ellipse at 50% 0%, rgba(88, 28, 135, 0.15) 0%, transparent 60%),
                           radial-gradient(ellipse at 80% 80%, rgba(6, 182, 212, 0.08) 0%, transparent 40%); }
  .container { max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem; }
  h1 { font-family: 'Orbitron', sans-serif; font-size: 2rem; font-weight: 900;
       color: #06b6d4; margin-bottom: 0.3rem; letter-spacing: 0.05em; }
  h1 span { color: #ec4899; }
  h1 a { color: inherit; text-decoration: none; }
  h1 a:hover { text-decoration: none; opacity: 0.8; }
  h2 { font-family: 'Orbitron', sans-serif; color: #06b6d4; font-size: 1rem;
       margin: 2rem 0 1rem; text-transform: uppercase; letter-spacing: 0.1em;
       border-bottom: 1px solid rgba(6, 182, 212, 0.2); padding-bottom: 0.5rem; }
  h3 { font-family: 'Orbitron', sans-serif; color: #ec4899; font-size: 0.85rem;
       margin: 1.5rem 0 0.5rem; text-transform: uppercase; letter-spacing: 0.05em; }
  a { color: #06b6d4; text-decoration: none; transition: color 0.2s; }
  a:hover { color: #ec4899; }
  code { background: rgba(6, 182, 212, 0.08); padding: 0.15rem 0.4rem; border-radius: 3px;
         font-size: 0.8rem; color: #ec4899; border: 1px solid rgba(236, 72, 153, 0.15); }
  .back { display: inline-block; margin-bottom: 1.5rem; font-size: 0.8rem; color: #64748b; }
  .back:hover { color: #06b6d4; }
  .card { background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(6, 182, 212, 0.1);
          border-radius: 4px; padding: 1rem 1.2rem; margin: 0.8rem 0; }
  .card:hover { border-color: rgba(6, 182, 212, 0.25); }
  .badge { padding: 0.2rem 0.6rem; border-radius: 2px; font-size: 0.65rem; font-weight: 700;
           text-transform: uppercase; letter-spacing: 0.08em; font-family: 'Orbitron', sans-serif; }
  .badge.easy { background: rgba(34, 197, 94, 0.1); color: #22c55e; border: 1px solid rgba(34, 197, 94, 0.3); }
  .badge.medium { background: rgba(234, 179, 8, 0.1); color: #eab308; border: 1px solid rgba(234, 179, 8, 0.3); }
  .badge.hard { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
  .tag { font-size: 0.7rem; color: #475569; margin-left: 0.5rem; }
  .task-list { font-size: 0.78rem; color: #64748b; margin: 0.4rem 0; line-height: 1.8; }
  .task-list .tid { color: #06b6d4; font-weight: 700; }
  .task-list .ttype { color: #ec4899; }
  .task-list .dep { color: #eab308; }
  .task-list .conflict { color: #ef4444; }
  .task-list .rej { color: #f97316; font-weight: 700; }
  .pm-event { font-size: 0.75rem; color: #8b5cf6; margin: 0.2rem 0; }
  .schema-block { background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(6, 182, 212, 0.08);
                  border-radius: 4px; padding: 1rem; margin: 0.5rem 0; overflow-x: auto;
                  font-size: 0.75rem; color: #94a3b8; white-space: pre-wrap; max-height: 400px; overflow-y: auto; }
  .footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid rgba(6, 182, 212, 0.1);
            color: #334155; font-size: 0.75rem; text-align: center; }
"""


@app.get("/ui/scenarios", response_class=HTMLResponse)
def ui_scenarios():
    """Formatted scenarios page."""
    from env.environment import build_episode_summary

    seen = set()
    cards = []
    for cfg in SCENARIOS.values():
        if cfg.scenario_id in seen:
            continue
        seen.add(cfg.scenario_id)

        # Task list
        task_lines = []
        for t in cfg.tasks:
            parts = [f'<span class="tid">{t.task_id}</span>: {t.title}']
            parts.append(f'<span class="ttype">{t.task_type.value}</span>')
            parts.append(f'effort={int(t.effort_total)} p{t.priority}')
            if t.depends_on:
                parts.append(f'<span class="dep">deps=[{",".join(t.depends_on)}]</span>')
            if t.conflicts_with:
                parts.append(f'<span class="conflict">conflicts=[{",".join(t.conflicts_with)}]</span>')
            if t.rejection_on_first_review:
                parts.append('<span class="rej">REJECTABLE</span>')
            task_lines.append(" ".join(parts))

        tasks_html = "<br>".join(task_lines)

        # PM events
        pm_html = ""
        if cfg.pm_events:
            pm_lines = [f'<div class="pm-event">Step {e.trigger_step}: {e.event_type.value} — {e.message[:80]}</div>' for e in cfg.pm_events]
            pm_html = "".join(pm_lines)

        # Mechanics
        mechs = []
        if cfg.enable_specialization:
            specs = ", ".join(f"{d}: {', '.join(s.value if hasattr(s, 'value') else s for s in sp)}" for d, sp in cfg.dev_specializations.items())
            mechs.append(f"Specialization ({specs})")
        if cfg.enable_review_rejection:
            rej = [t.task_id for t in cfg.tasks if t.rejection_on_first_review]
            mechs.append(f"Review Rejection on {', '.join(rej)}")
        if cfg.enable_pip:
            mechs.append(f"PIP (conflict>={cfg.pip_conflict_threshold}, idle>={cfg.pip_idle_threshold}, lock={cfg.pip_duration})")
        mech_html = f'<div style="font-size:0.72rem; color:#06b6d4; margin-top:0.5rem;">{" | ".join(mechs)}</div>' if mechs else ''

        cards.append(f"""
        <div class="card">
          <span class="badge {cfg.difficulty}">{cfg.difficulty}</span>
          <strong style="color:#e2e8f0; margin-left:0.5rem;">{cfg.name}</strong>
          <span class="tag">{cfg.scenario_id} | {len(cfg.tasks)} tasks | {cfg.max_steps} steps</span>
          <div class="task-list" style="margin-top:0.6rem;">{tasks_html}</div>
          {pm_html}
          {mech_html}
        </div>""")

    cards_html = "\n".join(cards)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>GitTangle — Scenarios</title><style>{SHARED_STYLES}</style></head>
<body><div class="container">
  <a href="/" class="back">&larr; Back to GitTangle</a>
  <h1><a href="/">GIT<span>TANGLE</span></a></h1>
  <h2>// All Scenarios</h2>
  {cards_html}
  <div class="footer"><a href="/">Home</a> &middot; <a href="/ui/schemas">Schemas</a> &middot; <a href="/docs">API Docs</a></div>
</div></body></html>"""


@app.get("/ui/schemas", response_class=HTMLResponse)
def ui_schemas():
    """Formatted schemas page."""
    import json
    action_schema = json.dumps(Action.model_json_schema(), indent=2)
    obs_schema = json.dumps(Observation.model_json_schema(), indent=2)
    state_schema = json.dumps(GitTangleState.model_json_schema(), indent=2)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>GitTangle — Schemas</title><style>{SHARED_STYLES}</style></head>
<body><div class="container">
  <a href="/" class="back">&larr; Back to GitTangle</a>
  <h1><a href="/">GIT<span>TANGLE</span></a></h1>
  <h2>// Type Schemas</h2>

  <h3>Action</h3>
  <p style="font-size:0.8rem; color:#64748b; margin-bottom:0.5rem;">The agent sends this each step — actions for both dev1 and dev2.</p>
  <div class="schema-block">{action_schema}</div>

  <h3>Observation</h3>
  <p style="font-size:0.8rem; color:#64748b; margin-bottom:0.5rem;">Returned after each step — task board, PRs, dev status, sprint progress.</p>
  <div class="schema-block">{obs_schema}</div>

  <h3>State</h3>
  <p style="font-size:0.8rem; color:#64748b; margin-bottom:0.5rem;">Full internal state — used by graders. Available via GET /state.</p>
  <div class="schema-block">{state_schema}</div>

  <div class="footer"><a href="/">Home</a> &middot; <a href="/ui/scenarios">Scenarios</a> &middot; <a href="/docs">API Docs</a></div>
</div></body></html>"""
