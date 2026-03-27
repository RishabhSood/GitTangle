from __future__ import annotations

from env.models import (
    Action, Observation, Reward, DevSimState, DevStatus, SprintProgress,
)
from env.simulation import SprintSimulation
from env.tasks import SCENARIOS


class DevSimEnv:
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
        return self._sim.get_observation()

    def step(self, action: Action) -> tuple[Observation, Reward, bool, dict]:
        """Execute one step in the environment."""
        if self._sim is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")
        if self._sim.done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")

        # Acknowledge PM messages if either dev communicates
        from env.models import DevActionType, CommunicationType
        for dev_action in [action.dev1_action, action.dev2_action]:
            if dev_action.action_type == DevActionType.COMMUNICATE:
                self._sim.acknowledge_pm_messages()
                break

        reward_events = self._sim.step(action.dev1_action, action.dev2_action)

        total_reward = sum(reward_events.values())
        self._cumulative_reward += total_reward

        reward = Reward(total=total_reward, breakdown=reward_events)
        obs = self._sim.get_observation()
        info = self._sim.get_info()
        info["cumulative_reward"] = self._cumulative_reward
        info["step"] = self._sim.current_step

        return obs, reward, self._sim.done, info

    def state(self) -> DevSimState:
        """Return full internal state."""
        if self._sim is None:
            return DevSimState(
                dev1_status=DevStatus(dev_id="dev1"),
                dev2_status=DevStatus(dev_id="dev2"),
                sprint_progress=SprintProgress(),
            )

        obs = self._sim.get_observation()
        return DevSimState(
            scenario_id=self._scenario_id,
            tasks=list(self._sim.tasks.values()),
            pr_queue=list(self._sim.pr_queue.values()),
            pm_messages_all=self._sim.pm_messages,
            dev1_status=self._sim.dev1.model_copy(),
            dev2_status=self._sim.dev2.model_copy(),
            sprint_progress=obs.sprint_progress,
            info=self._sim.get_info(),
        )
