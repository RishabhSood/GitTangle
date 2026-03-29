"""Baseline inference script using OpenAI-compatible API (supports OpenAI, Ollama, etc.)."""
from __future__ import annotations

import json
import os
import sys

import httpx
from openai import OpenAI

# Defaults — override via env vars:
#   LLM_BASE_URL=http://localhost:11434/v1  (Ollama)
#   LLM_MODEL=qwen2.5:7b                    (any model name)
#   OPENAI_API_KEY=ollama                    (dummy for Ollama)
DEFAULT_LLM_BASE_URL = None  # None = default OpenAI endpoint
DEFAULT_LLM_MODEL = "gpt-4o-mini"


SYSTEM_PROMPT = """You are an AI agent controlling two software developers (dev1 and dev2) in a sprint simulator.

Your goal is to complete as many high-priority tasks as possible before the sprint ends. You are scored on task completion (weighted by priority), efficient use of time, and avoiding merge conflicts.

Each step, you MUST output a valid JSON action with this exact structure:
{
  "dev1_action": {
    "action_type": "<one of: work_on_task, review_pr, fix_conflict, communicate, idle>",
    "task_id": "<task id string, for work_on_task and fix_conflict>",
    "pr_id": "<pr id string, for review_pr>",
    "comm_type": "<ask_pm_clarification or sync_with_dev, for communicate>",
    "comm_target_task": "<task id, for ask_pm_clarification>"
  },
  "dev2_action": {
    "action_type": "<one of: work_on_task, review_pr, fix_conflict, communicate, idle>",
    "task_id": "<task id string>",
    "pr_id": "<pr id string>",
    "comm_type": "<communication type>",
    "comm_target_task": "<task id>"
  }
}

Strategy guidelines:
- Prioritize tasks with lower priority number (1 = highest priority)
- Respect dependencies: don't work on tasks whose depends_on tasks aren't DONE
- When a PR is pending, have the OTHER dev review it (a dev can't review their own PR)
- Conflicts only happen when a task COMPLETES while a conflicting task is in progress/review/done
- When conflicts occur: BOTH devs must sync_with_dev first. This auto-resolves the higher-priority task (creates its PR). Then use fix_conflict on the remaining task to create its PR.
- Use sync_with_dev before completing a task that conflicts with an in-progress task to prevent conflicts
- Use ask_pm_clarification on high-effort tasks to reduce their effort
- Keep both devs busy — avoid idle actions
- Two devs cannot work on the same task or review the same PR simultaneously

Advanced mechanics (may be active depending on scenario):
- Developer Specialization: Each dev may specialize in certain task types. Working on specialty = normal speed. Working outside specialty = half speed (0.5 effort/step). Testing tasks are always normal speed. Check dev_specializations in observation.
- Code Review Rejection: Some tasks get rejected on first PR review — task goes back to IN_PROGRESS with +1 effort. Rework and resubmit. Second review always succeeds.
- Developer PIP: If a dev causes too many conflicts or idles too much, they get locked out for N steps. During PIP, all actions forced to idle. Avoid triggering PIP by staying productive and avoiding conflicts.

Only output the JSON. No explanation text.
Only include fields that are relevant to the chosen action_type. Omit null/unused fields."""

VALID_ACTION_FIELDS = {"action_type", "task_id", "pr_id", "comm_type", "comm_target_task"}
IDLE_ACTION = {"action_type": "idle"}


def sanitize_dev_action(raw: dict) -> dict:
    """Strip unknown fields and ensure action_type is valid."""
    if not isinstance(raw, dict):
        return IDLE_ACTION
    cleaned = {k: v for k, v in raw.items() if k in VALID_ACTION_FIELDS and v is not None}
    if "action_type" not in cleaned:
        return IDLE_ACTION
    return cleaned


def sanitize_action(raw: dict) -> dict:
    """Sanitize LLM output into a valid Action payload."""
    d1 = raw.get("dev1_action") or raw.get("dev1") or IDLE_ACTION
    d2 = raw.get("dev2_action") or raw.get("dev2") or IDLE_ACTION
    return {
        "dev1_action": sanitize_dev_action(d1),
        "dev2_action": sanitize_dev_action(d2),
    }


def build_action_hint(obs: dict) -> str:
    """Build a concise summary of what actions are currently valid."""
    lines = []

    # Workable tasks (backlog or in_progress, deps met)
    done_ids = {t["task_id"] for t in obs.get("task_board", []) if t["status"] == "done"}
    workable = []
    for t in obs.get("task_board", []):
        if t["status"] in ("backlog", "in_progress"):
            deps = t.get("depends_on", [])
            if all(d in done_ids for d in deps):
                workable.append(f'{t["task_id"]}(p{t["priority"]}, effort={t["effort_remaining"]})')
    if workable:
        lines.append(f"WORKABLE TASKS: {', '.join(workable)}")
    else:
        lines.append("WORKABLE TASKS: none")

    # Reviewable PRs
    prs = obs.get("pr_queue", [])
    if prs:
        pr_descs = [f'{pr["pr_id"]} by {pr["submitted_by"]} for {pr["task_id"]}' for pr in prs]
        lines.append(f"REVIEWABLE PRs: {', '.join(pr_descs)}")

    # Conflicts to fix
    conflicts = obs.get("merge_conflicts", [])
    if conflicts:
        # Check if there are also PRs available (meaning sync already happened and one was auto-resolved)
        pr_task_ids = {pr["task_id"] for pr in prs} if prs else set()
        unresolved = [c for c in conflicts if c not in pr_task_ids]
        if unresolved and not prs:
            lines.append(f"CONFLICTS NEED SYNC: {', '.join(unresolved)}")
            lines.append("ACTION REQUIRED: BOTH devs must sync_with_dev together to start resolving conflicts.")
        elif unresolved and prs:
            lines.append(f"CONFLICTS READY TO FIX: {', '.join(unresolved)} — use fix_conflict to create PR, and review the available PR above")
        if not unresolved and conflicts:
            lines.append(f"CONFLICTS (auto-resolved via sync): check PRs above for review")
    else:
        lines.append("NO CONFLICTS — do NOT use sync_with_dev, focus on working and reviewing.")

    # PM messages
    pm = obs.get("pm_messages", [])
    if pm:
        msgs = [m["message"] for m in pm]
        if msgs:
            lines.append(f"PM MESSAGES: {len(msgs)} — read for context on priority/requirement changes")

    # Sprint status
    sp = obs.get("sprint_progress", {})
    lines.append(f"SPRINT: step {sp.get('current_step', '?')}/{sp.get('max_steps', '?')}, "
                 f"{sp.get('tasks_done', 0)} done, {sp.get('tasks_in_progress', 0)} in progress")

    # Conflict warnings
    for t in obs.get("task_board", []):
        if t["status"] in ("backlog", "in_progress") and t.get("conflicts_with"):
            for ct_id in t.get("conflicts_with", []):
                ct = next((x for x in obs.get("task_board", []) if x["task_id"] == ct_id), None)
                if ct and ct["status"] in ("backlog", "in_progress"):
                    lines.append(f"WARNING: {t['task_id']} conflicts with {ct_id} — don't work both simultaneously!")

    # PIP warnings
    dev1 = obs.get("dev1_status", {})
    dev2 = obs.get("dev2_status", {})
    if dev1.get("pip_active"):
        lines.append(f"WARNING: dev1 is PIP'd for {dev1.get('pip_steps_remaining', '?')} more steps — all actions forced idle!")
    if dev2.get("pip_active"):
        lines.append(f"WARNING: dev2 is PIP'd for {dev2.get('pip_steps_remaining', '?')} more steps — all actions forced idle!")

    # Specialization info
    specs = obs.get("dev_specializations", {})
    if specs:
        for dev_id, spec_list in specs.items():
            lines.append(f"{dev_id} specializes in: {', '.join(spec_list)} (half speed on other types except testing)")

    return "\n".join(lines)


def _describe_action(dev: str, action: dict) -> str:
    """Build a human-readable description of a dev action."""
    at = action.get("action_type", "idle")
    if at == "work_on_task":
        return f"{dev}:work({action.get('task_id', '?')})"
    elif at == "review_pr":
        return f"{dev}:review({action.get('pr_id', '?')})"
    elif at == "fix_conflict":
        return f"{dev}:fix_conflict({action.get('task_id', '?')})"
    elif at == "communicate":
        ct = action.get("comm_type", "?")
        target = action.get("comm_target_task", "")
        if ct == "ask_pm_clarification":
            return f"{dev}:ask_pm({target})"
        else:
            return f"{dev}:sync_dev"
    else:
        return f"{dev}:idle"


def run_episode(base_url: str, task_id: str, client: OpenAI, model: str) -> float:
    """Run a single episode and return the grader score."""
    resp = httpx.post(f"{base_url}/reset", params={"task_id": task_id}, timeout=30)
    resp.raise_for_status()
    obs = resp.json()

    # Print episode summary
    summary = obs.get("episode_summary", "")
    if summary:
        print(summary)

    done = False
    step_count = 0
    max_steps = 50  # safety limit
    prev_reward = None
    prev_breakdown = None

    while not done and step_count < max_steps:
        hint = build_action_hint(obs)
        obs_text = json.dumps(obs, indent=2)

        feedback = ""
        if prev_reward is not None:
            feedback = f"=== PREVIOUS STEP FEEDBACK ===\nReward: {prev_reward:+.1f}\n"
            if prev_breakdown:
                details = [f"  {k}: {v:+.1f}" for k, v in prev_breakdown.items() if v != 0 or "waiting" in k]
                if details:
                    feedback += "Breakdown:\n" + "\n".join(details) + "\n"
            if prev_reward < 0:
                feedback += "Note: negative reward. Review the breakdown to understand why.\n"
            feedback += "\n"

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": (
                        f"{feedback}"
                        f"=== ACTION SUMMARY ===\n{hint}\n\n"
                        f"=== FULL OBSERVATION ===\n{obs_text}\n\n"
                        f"Output your action as JSON:"
                    )},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )

            action_text = response.choices[0].message.content
            raw_action = json.loads(action_text)
            action = sanitize_action(raw_action)
        except Exception as e:
            print(f"  Step {step_count}: LLM error ({e}), using idle actions")
            action = {"dev1_action": IDLE_ACTION, "dev2_action": IDLE_ACTION}

        try:
            step_resp = httpx.post(f"{base_url}/step", json=action, timeout=30)
            step_resp.raise_for_status()
            result = step_resp.json()
            obs = result["observation"]
            done = result["done"]
            reward = result["reward"]
            breakdown = result.get("reward_breakdown", {})

            d1_desc = _describe_action("dev1", action["dev1_action"])
            d2_desc = _describe_action("dev2", action["dev2_action"])

            # Mark invalid actions
            if any(k.startswith("dev1_invalid") for k in breakdown):
                d1_desc += " INVALID→idle"
            if any(k.startswith("dev2_invalid") for k in breakdown):
                d2_desc += " INVALID→idle"

            # Annotate work actions that created PRs (task completed)
            if "dev1_task_completion" in breakdown:
                # Find the PR created for this task
                new_prs = result["observation"].get("pr_queue", [])
                tid = action["dev1_action"].get("task_id", "")
                pr = next((p for p in new_prs if p["task_id"] == tid), None)
                if pr:
                    d1_desc += f"→{pr['pr_id']}"
                elif "dev1_conflict_penalty" in breakdown:
                    d1_desc += "→CONFLICT"
            if "dev2_task_completion" in breakdown:
                new_prs = result["observation"].get("pr_queue", [])
                tid = action["dev2_action"].get("task_id", "")
                pr = next((p for p in new_prs if p["task_id"] == tid), None)
                if pr:
                    d2_desc += f"→{pr['pr_id']}"
                elif "dev2_conflict_penalty" in breakdown:
                    d2_desc += "→CONFLICT"

            # Build event signals from reward breakdown
            events = []
            for k, v in breakdown.items():
                # Extract dev name (dev1_ or dev2_ prefix)
                dev_prefix = k.split("_")[0] if k.startswith("dev") else ""
                if "task_completion" in k:
                    # Find which task was just completed by this dev
                    dev_act = action.get(f"{dev_prefix}_action", {})
                    tid = dev_act.get("task_id", "?")
                    events.append(f"{dev_prefix} COMPLETED {tid}")
                if "pr_merged" in k:
                    dev_act = action.get(f"{dev_prefix}_action", {})
                    prid = dev_act.get("pr_id", "?")
                    events.append(f"{dev_prefix} MERGED {prid}")
                if "conflict_penalty" in k:
                    events.append("CONFLICT!")
                if "sprint_completion" in k:
                    events.append("SPRINT DONE!")
                if "high_priority_bonus" in k:
                    dev_act = action.get(f"{dev_prefix}_action", {})
                    tid = dev_act.get("task_id", "?")
                    events.append(f"{dev_prefix} HIGH-PRI {tid}")
                if "communication_reward" in k:
                    dev_act = action.get(f"{dev_prefix}_action", {})
                    tid = dev_act.get("comm_target_task", "?")
                    events.append(f"{dev_prefix} CLARIFIED {tid}")
                if "sync_reward" in k:
                    events.append(f"{dev_prefix} SYNCED")

            event_str = f" [{', '.join(events)}]" if events else ""
            print(f"  Step {step_count}: {d1_desc} | {d2_desc} | reward={reward:+.1f}{event_str}")
            prev_reward = reward
            prev_breakdown = breakdown
            step_count += 1
        except Exception as e:
            print(f"  Step {step_count}: Step error ({e}), retrying with idle")
            action = {"dev1_action": IDLE_ACTION, "dev2_action": IDLE_ACTION}
            step_resp = httpx.post(f"{base_url}/step", json=action, timeout=30)
            step_resp.raise_for_status()
            result = step_resp.json()
            obs = result["observation"]
            done = result["done"]
            step_count += 1

    # Get grader score
    grader_resp = httpx.post(f"{base_url}/grader", timeout=30)
    grader_resp.raise_for_status()
    score = grader_resp.json()["score"]
    return score


ALL_SCENARIOS = [
    "easy_1", "easy_2", "easy_3", "easy_4", "easy_5",
    "medium_1", "medium_2", "medium_3", "medium_4", "medium_5",
    "hard_1", "hard_2", "hard_3", "hard_4", "hard_5",
]


def run_baseline(base_url: str = "http://localhost:7860", tasks: list[str] | None = None) -> dict[str, float]:
    """Run the baseline agent on selected tasks."""
    api_key = os.environ.get("OPENAI_API_KEY", "ollama")
    llm_base_url = os.environ.get("LLM_BASE_URL", DEFAULT_LLM_BASE_URL)
    model = os.environ.get("LLM_MODEL", DEFAULT_LLM_MODEL)

    if tasks is None:
        tasks = ALL_SCENARIOS

    client = OpenAI(api_key=api_key, base_url=llm_base_url)
    scores = {}

    print(f"Using model: {model}" + (f" at {llm_base_url}" if llm_base_url else ""))

    for task_id in tasks:
        print(f"\nRunning baseline on: {task_id}")
        # Print episode summary from reset
        obs_resp = None
        score = run_episode(base_url, task_id, client, model)
        scores[task_id] = score
        print(f"  Score: {score:.4f}")

    # Print per-difficulty averages
    by_difficulty: dict[str, list[float]] = {"easy": [], "medium": [], "hard": []}
    for tid, s in scores.items():
        diff = tid.rsplit("_", 1)[0]
        if diff in by_difficulty:
            by_difficulty[diff].append(s)

    if len(scores) > 1:
        print("\n--- Per-Difficulty Averages ---")
        for diff, vals in by_difficulty.items():
            if vals:
                print(f"  {diff}: {sum(vals)/len(vals):.4f} (n={len(vals)})")

    return scores


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GitTangle baseline inference")
    parser.add_argument("--url", default="http://localhost:7860", help="Environment server URL")
    parser.add_argument(
        "--task", default="all",
        choices=ALL_SCENARIOS + ["easy", "medium", "hard", "all"],
        help="Which task to run (default: all)",
    )
    args = parser.parse_args()

    if args.task == "all":
        tasks = ALL_SCENARIOS
    elif args.task in ("easy", "medium", "hard"):
        tasks = [t for t in ALL_SCENARIOS if t.startswith(args.task)]
    else:
        tasks = [args.task]

    scores = run_baseline(base_url=args.url, tasks=tasks)
    print("\n--- Baseline Scores ---")
    for tid, s in scores.items():
        print(f"  {tid}: {s:.4f}")
