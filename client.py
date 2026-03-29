"""GitTangle Environment Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from env.models import Action, Observation


class GitTangleEnvClient(
    EnvClient[Action, Observation, State]
):
    """
    Client for the GitTangle Environment.

    Maintains a persistent WebSocket connection to the environment server.

    Example:
        >>> with GitTangleEnvClient(base_url="http://localhost:7860") as client:
        ...     result = client.reset()
        ...     result = client.step(Action(
        ...         dev1_action=DevAction(action_type="work_on_task", task_id="T1"),
        ...         dev2_action=DevAction(action_type="work_on_task", task_id="T2"),
        ...     ))

    Example with Docker:
        >>> client = GitTangleEnvClient.from_docker_image("gittangle:latest")
        >>> with client:
        ...     result = client.reset()
        ...     result = client.step(action)
    """

    def _step_payload(self, action: Action) -> Dict:
        """Convert Action to JSON payload for step message."""
        if isinstance(action, dict):
            return action
        if hasattr(action, "model_dump"):
            return action.model_dump()
        return dict(action)
