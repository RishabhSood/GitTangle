"""
GitTangle Inference Script
===================================
MANDATORY env vars:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional

import httpx
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")

TEMPERATURE = 0.0
MAX_TOKENS = 1024
IDLE_ACTION = {"action_type": "idle"}
FALLBACK_ACTION = {"dev1_action": IDLE_ACTION, "dev2_action": IDLE_ACTION}

# ALL_SCENARIOS = [
#     "easy_1", "easy_2", "easy_3", "easy_4", "easy_5",
#     "medium_1", "medium_2", "medium_3", "medium_4", "medium_5",
#     "hard_1", "hard_2", "hard_3", "hard_4", "hard_5",
# ]

ALL_SCENARIOS = [
    "easy_3",
    "medium_3", "medium_5",
    "hard_1", "hard_2", "hard_5"
]

SYSTEM_PROMPT = """You control two software developers (dev1 and dev2) in a sprint simulation.
Your goal: complete as many high-priority tasks as possible before the sprint ends.

Each step, output a JSON action:
{
  "dev1_action": {"action_type": "...", "task_id": "...", "pr_id": "...", "comm_type": "...", "comm_target_task": "..."},
  "dev2_action": {"action_type": "...", "task_id": "...", "pr_id": "...", "comm_type": "...", "comm_target_task": "..."}
}

Action types: work_on_task, review_pr, fix_conflict, communicate, idle.
Communication types: ask_pm_clarification, sync_with_dev.
Only include fields relevant to the chosen action_type.
Output only valid JSON. No explanation."""

VALID_FIELDS = {"action_type", "task_id", "pr_id", "comm_type", "comm_target_task"}


def sanitize_action(raw: dict) -> dict:
    """Clean LLM output into a valid action payload."""
    def _clean(d):
        if not isinstance(d, dict):
            return IDLE_ACTION
        c = {k: v for k, v in d.items() if k in VALID_FIELDS and v is not None}
        return c if "action_type" in c else IDLE_ACTION

    d1 = raw.get("dev1_action") or raw.get("dev1") or IDLE_ACTION
    d2 = raw.get("dev2_action") or raw.get("dev2") or IDLE_ACTION
    return {"dev1_action": _clean(d1), "dev2_action": _clean(d2)}


def parse_json(text: str) -> Optional[dict]:
    """Try to extract JSON from model response."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    match = re.search(r'\{.*\}', text or "", re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def build_feedback(prev_reward: float, prev_breakdown: dict) -> str:
    """Build reward feedback string from previous step."""
    lines = [f"Previous reward: {prev_reward:+.1f}"]
    details = [f"  {k}: {v:+.1f}" for k, v in prev_breakdown.items() if v != 0 or "waiting" in k]
    if details:
        lines.append("Breakdown:")
        lines.extend(details)
    return "\n".join(lines)


def _fmt_action(dev: str, action: dict) -> str:
    """Format a dev action for logging."""
    at = action.get("action_type", "idle")
    if at == "work_on_task":
        return f"{dev}:work({action.get('task_id', '?')})"
    elif at == "review_pr":
        return f"{dev}:review({action.get('pr_id', '?')})"
    elif at == "fix_conflict":
        return f"{dev}:fix_conflict({action.get('task_id', '?')})"
    elif at == "communicate":
        ct = action.get("comm_type", "?")
        if ct == "ask_pm_clarification":
            return f"{dev}:ask_pm({action.get('comm_target_task', '?')})"
        return f"{dev}:sync_dev"
    return f"{dev}:idle"


def run_episode(client: OpenAI, task_id: str) -> tuple[float, int, list[float]]:
    """Run one episode and return (grader score, steps taken, rewards list)."""
    resp = httpx.post(f"{ENV_URL}/reset", params={"task_id": task_id}, timeout=30)
    resp.raise_for_status()
    obs = resp.json()

    print(f"[START] task={task_id} env=gittangle model={MODEL_NAME}", flush=True)

    # Print episode summary
    summary = obs.get("episode_summary", "")
    if summary:
        print(summary)

    done = False
    step = 0
    max_steps = 50
    prev_reward = None
    prev_breakdown = None
    all_rewards: list[float] = []

    while not done and step < max_steps:
        # Build user prompt: feedback + raw observation
        parts = []
        if prev_reward is not None:
            parts.append(build_feedback(prev_reward, prev_breakdown))
        parts.append(json.dumps(obs, indent=2))

        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": "\n\n".join(parts)},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            raw = parse_json(completion.choices[0].message.content)
            action = sanitize_action(raw) if raw else FALLBACK_ACTION
        except Exception as e:
            print(f"  Step {step}: LLM error ({e})")
            action = FALLBACK_ACTION

        try:
            step_resp = httpx.post(f"{ENV_URL}/step", json=action, timeout=30)
            step_resp.raise_for_status()
            result = step_resp.json()
            obs = result["observation"]
            done = result["done"]
            prev_reward = result["reward"]
            prev_breakdown = result.get("reward_breakdown", {})

            # Build descriptive log line
            d1a = action["dev1_action"]
            d2a = action["dev2_action"]
            d1_desc = _fmt_action("dev1", d1a)
            d2_desc = _fmt_action("dev2", d2a)

            # Annotate invalid actions
            if any(k.startswith("dev1_invalid") for k in prev_breakdown):
                d1_desc += " INVALID→idle"
            if any(k.startswith("dev2_invalid") for k in prev_breakdown):
                d2_desc += " INVALID→idle"

            # Annotate task completions with PR or CONFLICT
            new_prs = result["observation"].get("pr_queue", [])
            if "dev1_task_completion" in prev_breakdown:
                tid = d1a.get("task_id", "")
                pr = next((p for p in new_prs if p["task_id"] == tid), None)
                if pr:
                    d1_desc += f"→{pr['pr_id']}"
                elif "dev1_conflict_penalty" in prev_breakdown:
                    d1_desc += "→CONFLICT"
            if "dev2_task_completion" in prev_breakdown:
                tid = d2a.get("task_id", "")
                pr = next((p for p in new_prs if p["task_id"] == tid), None)
                if pr:
                    d2_desc += f"→{pr['pr_id']}"
                elif "dev2_conflict_penalty" in prev_breakdown:
                    d2_desc += "→CONFLICT"

            # Key events
            events = []
            for k in prev_breakdown:
                if "task_completion" in k:
                    prefix = k.split("_")[0]
                    tid = action.get(f"{prefix}_action", {}).get("task_id", "?")
                    events.append(f"{prefix} COMPLETED {tid}")
                elif "pr_merged" in k:
                    prefix = k.split("_")[0]
                    events.append(f"{prefix} MERGED")
                elif "conflict_penalty" in k:
                    events.append("CONFLICT!")
                elif "sprint_completion" in k:
                    events.append("SPRINT DONE!")
                elif "review_rejected" in k:
                    # key like dev1_review_rejected:PR-7_for_T5_bugs_found_rework_needed
                    parts = k.split(":")
                    detail = parts[1].replace("_", " ") if len(parts) > 1 else "rework needed"
                    events.append(f"REJECTED ({detail})")
                elif "pip_penalty" in k:
                    prefix = k.split("_")[0]
                    events.append(f"{prefix} PIP'd")
                elif "conflict_auto_resolved" in k:
                    events.append("AUTO-RESOLVED")

            event_str = f" [{', '.join(events)}]" if events else ""
            action_str = f"dev1={d1a.get('action_type','idle')}|dev2={d2a.get('action_type','idle')}"
            done_str = str(done).lower()
            all_rewards.append(prev_reward)
            print(f"[STEP] step={step} action={action_str} reward={prev_reward:.2f} done={done_str} error=null", flush=True)
            print(f"  Step {step}: {d1_desc} | {d2_desc} | reward={prev_reward:+.1f}{event_str}")
            step += 1
        except Exception as e:
            print(f"  Step {step}: Step error ({e}), using idle")
            step_resp = httpx.post(f"{ENV_URL}/step", json=FALLBACK_ACTION, timeout=30)
            step_resp.raise_for_status()
            result = step_resp.json()
            obs = result["observation"]
            done = result["done"]
            prev_reward = result["reward"]
            prev_breakdown = result.get("reward_breakdown", {})
            all_rewards.append(prev_reward)
            done_str = str(done).lower()
            print(f"[STEP] step={step} action=idle|idle reward={prev_reward:.2f} done={done_str} error={e}", flush=True)
            step += 1

    grader_resp = httpx.post(f"{ENV_URL}/grader", timeout=30)
    grader_resp.raise_for_status()
    score = grader_resp.json()["score"]
    # Clamp to strictly (0, 1) in case server hasn't updated yet
    score = max(0.01, min(0.99, score))
    success = str(score > 0.1).lower()
    rewards_str = ",".join(f"{r:.2f}" for r in all_rewards)
    print(f"[END] success={success} steps={step} score={score:.3f} rewards={rewards_str}", flush=True)
    return score, step, all_rewards


def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    scores = {}

    print(f"Model: {MODEL_NAME} at {API_BASE_URL}")

    for task_id in ALL_SCENARIOS:
        print(f"\n{'='*50}")
        print(f"Running: {task_id}")
        score, steps, rewards = run_episode(client, task_id)
        scores[task_id] = score
        print(f"Score: {score:.4f} in {steps} steps")

    # Per-difficulty averages
    by_diff: dict[str, list[float]] = {"easy": [], "medium": [], "hard": []}
    for tid, s in scores.items():
        diff = tid.rsplit("_", 1)[0]
        if diff in by_diff:
            by_diff[diff].append(s)

    print(f"\n{'='*50}")
    print("RESULTS")
    print(f"{'='*50}")
    for tid, s in scores.items():
        print(f"  {tid}: {s:.4f}")
    print()
    for diff, vals in by_diff.items():
        if vals:
            print(f"  {diff} avg: {sum(vals)/len(vals):.4f} (n={len(vals)})")


if __name__ == "__main__":
    main()
