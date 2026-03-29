from __future__ import annotations

from env.models import (
    Action, Observation, Reward, GitTangleState, DevStatus, SprintProgress,
    ScenarioConfig,
)
from env.simulation import SprintSimulation
from env.tasks import SCENARIOS


def build_episode_summary(config: ScenarioConfig) -> str:
    """Build a human-readable episode summary."""
    lines = []
    lines.append(f"=== EPISODE: {config.name} ({config.scenario_id}) ===")
    lines.append(f"Difficulty: {config.difficulty} | Max steps: {config.max_steps} | Tasks: {len(config.tasks)}")

    # Task list
    lines.append("Task board:")
    for t in config.tasks:
        parts = [f"  {t.task_id}: {t.title} ({t.task_type.value}, effort={int(t.effort_total)}, p{t.priority})"]
        if t.depends_on:
            parts.append(f"deps=[{','.join(t.depends_on)}]")
        if t.conflicts_with:
            parts.append(f"conflicts=[{','.join(t.conflicts_with)}]")
        if t.rejection_on_first_review:
            parts.append("REJECTABLE")
        lines.append(" ".join(parts))

    # Conflict pairs
    seen: set[tuple[str, str]] = set()
    for t in config.tasks:
        for c in t.conflicts_with:
            pair = (min(t.task_id, c), max(t.task_id, c))
            if pair not in seen:
                seen.add(pair)
    if seen:
        lines.append(f"Conflict pairs: {', '.join(f'{a}<->{b}' for a, b in sorted(seen))}")

    # PM events
    if config.pm_events:
        lines.append(f"PM events ({len(config.pm_events)}):")
        for e in config.pm_events:
            lines.append(f"  Step {e.trigger_step}: {e.event_type.value}")

    # Active mechanics
    mechanics = []
    if config.enable_specialization:
        mechanics.append("Specialization")
    if config.enable_review_rejection:
        mechanics.append("Review Rejection")
    if config.enable_pip:
        mechanics.append(f"PIP (conflict>={config.pip_conflict_threshold}, idle>={config.pip_idle_threshold}, lock={config.pip_duration})")
    lines.append(f"Mechanics: {', '.join(mechanics) if mechanics else 'none'}")

    if config.dev_specializations:
        for dev, specs in config.dev_specializations.items():
            spec_names = [s.value if hasattr(s, 'value') else s for s in specs]
            lines.append(f"  {dev}: {', '.join(spec_names)}")

    # Rejection tasks
    rej_tasks = [t.task_id for t in config.tasks if t.rejection_on_first_review]
    if rej_tasks:
        lines.append(f"Review rejection on: {', '.join(rej_tasks)}")

    return "\n".join(lines)


class GitTangleEnv:
    """OpenEnv-compliant environment wrapping the sprint simulation."""

    def __init__(self):
        self._sim: SprintSimulation | None = None
        self._scenario_id: str = "easy"
        self._cumulative_reward: float = 0.0

    def reset(self, task_id: str = "easy") -> Observation:
        """Reset the environment for a given scenario."""
        if task_id not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {task_id}. Choose from: {list(SCENARIOS.keys())}")

        config = SCENARIOS[task_id]
        self._sim = SprintSimulation(config)
        self._scenario_id = task_id
        self._cumulative_reward = 0.0
        obs = self._sim.get_observation()
        obs.episode_summary = build_episode_summary(config)
        return obs

    def step(self, action: Action) -> tuple[Observation, Reward, bool, dict]:
        """Execute one step in the environment."""
        if self._sim is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")
        if self._sim.done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")

        reward_events = self._sim.step(action.dev1_action, action.dev2_action)

        total_reward = sum(reward_events.values())
        self._cumulative_reward += total_reward

        reward = Reward(total=total_reward, breakdown=reward_events)
        obs = self._sim.get_observation()
        info = self._sim.get_info()
        info["cumulative_reward"] = self._cumulative_reward
        info["step"] = self._sim.current_step

        return obs, reward, self._sim.done, info

    def state(self) -> GitTangleState:
        """Return full internal state."""
        if self._sim is None:
            return GitTangleState(
                dev1_status=DevStatus(dev_id="dev1"),
                dev2_status=DevStatus(dev_id="dev2"),
                sprint_progress=SprintProgress(),
            )

        obs = self._sim.get_observation()
        return GitTangleState(
            scenario_id=self._scenario_id,
            tasks=list(self._sim.tasks.values()),
            pr_queue=list(self._sim.pr_queue.values()),
            pm_messages_all=self._sim.pm_messages,
            dev1_status=self._sim.dev1.model_copy(),
            dev2_status=self._sim.dev2.model_copy(),
            sprint_progress=obs.sprint_progress,
            info=self._sim.get_info(),
        )
