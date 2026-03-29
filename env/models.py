from __future__ import annotations

from enum import Enum
from typing import Optional, Literal

from pydantic import BaseModel


# --- Enums ---

class TaskType(str, Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    TESTING = "testing"
    DEVOPS = "devops"


class TaskStatus(str, Enum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    HAS_CONFLICT = "has_conflict"
    DONE = "done"
    BLOCKED = "blocked"


class DevActionType(str, Enum):
    WORK_ON_TASK = "work_on_task"
    REVIEW_PR = "review_pr"
    FIX_CONFLICT = "fix_conflict"
    COMMUNICATE = "communicate"
    IDLE = "idle"


class CommunicationType(str, Enum):
    ASK_PM_CLARIFICATION = "ask_pm_clarification"
    SYNC_WITH_DEV = "sync_with_dev"


class PMEventType(str, Enum):
    PRIORITY_CHANGE = "priority_change"
    REQUIREMENT_CHANGE = "requirement_change"
    NEW_TASK = "new_task"
    DEADLINE_WARNING = "deadline_warning"


# --- Core data models ---

class ProjectTask(BaseModel):
    task_id: str
    title: str
    task_type: TaskType
    effort_remaining: float
    effort_total: float
    status: TaskStatus = TaskStatus.BACKLOG
    assigned_to: Optional[str] = None
    depends_on: list[str] = []
    conflicts_with: list[str] = []
    priority: int  # 1 (highest) - 5 (lowest)
    pr_id: Optional[str] = None
    progress_pct: float = 0.0
    rejection_on_first_review: bool = False
    review_count: int = 0


class PMEvent(BaseModel):
    trigger_step: int
    event_type: PMEventType
    target_task_id: Optional[str] = None
    details: dict = {}
    message: str


# --- Action models ---

class DevAction(BaseModel):
    model_config = {"extra": "ignore"}
    action_type: DevActionType = DevActionType.IDLE
    task_id: Optional[str] = None
    pr_id: Optional[str] = None
    comm_type: Optional[CommunicationType] = None
    comm_target_task: Optional[str] = None


class Action(BaseModel):
    model_config = {"extra": "ignore"}
    dev1_action: DevAction
    dev2_action: DevAction


# --- Observation models ---

class TaskObservation(BaseModel):
    task_id: str
    title: str
    task_type: TaskType
    effort_remaining: float
    effort_total: float
    status: TaskStatus
    assigned_to: Optional[str] = None
    depends_on: list[str] = []
    conflicts_with: list[str] = []
    priority: int
    progress_pct: float
    pr_id: Optional[str] = None


class PRObservation(BaseModel):
    pr_id: str
    task_id: str
    submitted_by: str
    status: Literal["pending_review", "has_conflict"]


class PMMessage(BaseModel):
    step: int
    message: str
    event_type: str
    acknowledged: bool = False


class DevStatus(BaseModel):
    dev_id: str
    current_task: Optional[str] = None
    current_action: str = "idle"
    steps_idle: int = 0
    tasks_completed: int = 0
    conflicts_caused: int = 0
    pip_active: bool = False
    pip_steps_remaining: int = 0


class SprintProgress(BaseModel):
    current_step: int = 0
    max_steps: int = 20
    total_tasks: int = 0
    tasks_done: int = 0
    tasks_in_progress: int = 0
    tasks_blocked: int = 0
    tasks_in_review: int = 0
    velocity: float = 0.0


class Observation(BaseModel):
    task_board: list[TaskObservation] = []
    pr_queue: list[PRObservation] = []
    pm_messages: list[PMMessage] = []
    dev1_status: DevStatus
    dev2_status: DevStatus
    sprint_progress: SprintProgress
    merge_conflicts: list[str] = []
    dev_specializations: dict[str, list[str]] = {}
    episode_summary: Optional[str] = None


# --- Reward model ---

class Reward(BaseModel):
    total: float = 0.0
    breakdown: dict[str, float] = {}


# --- Full state model ---

class GitTangleState(BaseModel):
    scenario_id: str = ""
    tasks: list[ProjectTask] = []
    pr_queue: list[PRObservation] = []
    pm_messages_all: list[PMMessage] = []
    dev1_status: DevStatus
    dev2_status: DevStatus
    sprint_progress: SprintProgress
    info: dict = {}


# --- Scenario config ---

class ScenarioConfig(BaseModel):
    scenario_id: str
    name: str
    description: str
    difficulty: str
    max_steps: int
    tasks: list[ProjectTask]
    pm_events: list[PMEvent] = []
    # Mechanic flags
    enable_pip: bool = False
    pip_conflict_threshold: int = 3
    pip_idle_threshold: int = 5
    pip_duration: int = 2
    enable_review_rejection: bool = False
    enable_specialization: bool = False
    dev_specializations: dict[str, list[TaskType]] = {}
