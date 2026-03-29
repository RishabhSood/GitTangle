from __future__ import annotations

from typing import Optional

from env.models import (
    ProjectTask, PMEvent, DevAction, DevActionType, CommunicationType,
    TaskStatus, TaskType, PMEventType, PRObservation, PMMessage, DevStatus,
    SprintProgress, TaskObservation, Observation, ScenarioConfig,
)


class SprintSimulation:
    """Core simulation engine for a software sprint with 2 developers."""

    def __init__(self, config: ScenarioConfig):
        self.scenario_id = config.scenario_id
        self.max_steps = config.max_steps
        self.tasks: dict[str, ProjectTask] = {
            t.task_id: t.model_copy(deep=True) for t in config.tasks
        }
        self.pm_events: list[PMEvent] = [e.model_copy(deep=True) for e in config.pm_events]
        self.pr_queue: dict[str, PRObservation] = {}
        self.pm_messages: list[PMMessage] = []
        self.current_step = 0
        self.done = False

        self.dev1 = DevStatus(dev_id="dev1")
        self.dev2 = DevStatus(dev_id="dev2")

        # Tracking counters for graders
        self.total_conflicts_created = 0
        self.communications_sent = 0
        self.pm_messages_acknowledged = 0
        self.clarified_tasks: set[str] = set()

        self._pr_counter = 0
        self._synced_devs: set[str] = set()
        self._discussed_conflicts: set[str] = set()

        # Mechanic flags from config
        self.enable_specialization = config.enable_specialization
        self.dev_specializations = {
            k: [v.value if isinstance(v, TaskType) else v for v in vals]
            for k, vals in config.dev_specializations.items()
        }
        self.enable_review_rejection = config.enable_review_rejection
        self.enable_pip = config.enable_pip
        self.pip_conflict_threshold = config.pip_conflict_threshold
        self.pip_idle_threshold = config.pip_idle_threshold
        self.pip_duration = config.pip_duration

        self._update_dependency_statuses()

    def _next_pr_id(self) -> str:
        self._pr_counter += 1
        return f"PR-{self._pr_counter}"

    def _update_dependency_statuses(self):
        """Update BLOCKED/BACKLOG status based on dependency satisfaction."""
        for task in self.tasks.values():
            if task.status in (TaskStatus.DONE, TaskStatus.IN_REVIEW, TaskStatus.IN_PROGRESS, TaskStatus.HAS_CONFLICT):
                continue
            deps_met = all(
                self.tasks[dep].status == TaskStatus.DONE
                for dep in task.depends_on
                if dep in self.tasks
            )
            if deps_met:
                if task.status == TaskStatus.BLOCKED:
                    task.status = TaskStatus.BACKLOG
            else:
                if task.status == TaskStatus.BACKLOG:
                    task.status = TaskStatus.BLOCKED

    def _process_pm_events(self):
        """Fire PM events scheduled for the current step."""
        for event in self.pm_events:
            if event.trigger_step != self.current_step:
                continue

            if event.event_type == PMEventType.PRIORITY_CHANGE:
                task = self.tasks.get(event.target_task_id)
                if task:
                    task.priority = event.details.get("new_priority", task.priority)

            elif event.event_type == PMEventType.REQUIREMENT_CHANGE:
                task = self.tasks.get(event.target_task_id)
                if task:
                    increase = event.details.get("effort_increase", 0)
                    task.effort_remaining += increase
                    task.effort_total += increase

            elif event.event_type == PMEventType.NEW_TASK:
                task_data = event.details.get("task", {})
                if task_data:
                    new_task = ProjectTask(**task_data)
                    self.tasks[new_task.task_id] = new_task

            self.pm_messages.append(PMMessage(
                step=self.current_step,
                message=event.message,
                event_type=event.event_type.value,
            ))

    def _validate_action(self, action: DevAction, dev_id: str) -> tuple[DevAction, str]:
        """Validate an action; return (idle, reason) if invalid, or (action, "") if valid."""
        idle = DevAction(action_type=DevActionType.IDLE)

        if action.action_type == DevActionType.WORK_ON_TASK:
            task = self.tasks.get(action.task_id)
            if not task:
                return idle, f"task_{action.task_id}_not_found"
            if task.status not in (TaskStatus.BACKLOG, TaskStatus.IN_PROGRESS):
                return idle, f"task_{action.task_id}_status_{task.status.value}"
            for dep_id in task.depends_on:
                dep = self.tasks.get(dep_id)
                if dep and dep.status != TaskStatus.DONE:
                    return idle, f"task_{action.task_id}_blocked_by_{dep_id}"
            return action, ""

        elif action.action_type == DevActionType.REVIEW_PR:
            pr = self.pr_queue.get(action.pr_id)
            if not pr:
                return idle, f"pr_{action.pr_id}_not_found"
            if pr.submitted_by == dev_id:
                return idle, f"cannot_self_review_{action.pr_id}"
            if pr.status != "pending_review":
                return idle, f"pr_{action.pr_id}_status_{pr.status}"
            return action, ""

        elif action.action_type == DevActionType.FIX_CONFLICT:
            task = self.tasks.get(action.task_id)
            if not task or task.status != TaskStatus.HAS_CONFLICT:
                return idle, f"task_{action.task_id}_not_in_conflict"
            if action.task_id not in self._discussed_conflicts:
                return idle, f"fix_conflict_{action.task_id}_needs_sync_first"
            return action, ""

        elif action.action_type == DevActionType.COMMUNICATE:
            if action.comm_type == CommunicationType.ASK_PM_CLARIFICATION:
                if not action.comm_target_task or action.comm_target_task in self.clarified_tasks:
                    return idle, f"already_clarified_{action.comm_target_task}"
                if action.comm_target_task not in self.tasks:
                    return idle, f"task_{action.comm_target_task}_not_found"
            return action, ""

        elif action.action_type == DevActionType.IDLE:
            return action, ""

        return idle, "unknown_action_type"

    def _has_merge_conflict(self, task: ProjectTask, dev_id: str) -> bool:
        """Check if a completing task has merge conflicts with other tasks."""
        if dev_id in self._synced_devs:
            return False
        for conflict_id in task.conflicts_with:
            ct = self.tasks.get(conflict_id)
            if ct and ct.status in (TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW, TaskStatus.DONE):
                return True
        return False

    def _get_effort_decrement(self, dev_id: str, task: ProjectTask) -> float:
        """Get effort decrement for a dev working on a task, accounting for specialization."""
        if not self.enable_specialization:
            return 1.0
        if task.task_type == TaskType.TESTING:
            return 1.0  # Testing is neutral for all devs
        dev_specs = self.dev_specializations.get(dev_id, [])
        if task.task_type.value in dev_specs:
            return 1.0
        return 0.5  # Non-specialty: half speed

    def _execute_action(self, action: DevAction, dev_id: str) -> dict:
        """Execute a single dev's action. Returns reward events."""
        dev = self.dev1 if dev_id == "dev1" else self.dev2
        events: dict[str, float] = {}

        if action.action_type == DevActionType.WORK_ON_TASK:
            task = self.tasks[action.task_id]
            task.status = TaskStatus.IN_PROGRESS
            task.assigned_to = dev_id
            effort_decrement = self._get_effort_decrement(dev_id, task)
            task.effort_remaining -= effort_decrement
            task.progress_pct = 1.0 - (task.effort_remaining / task.effort_total)
            events["task_progress"] = effort_decrement
            dev.current_task = action.task_id
            dev.current_action = "working"

            if task.effort_remaining <= 0:
                task.effort_remaining = 0
                task.progress_pct = 1.0
                if self._has_merge_conflict(task, dev_id):
                    task.status = TaskStatus.HAS_CONFLICT
                    task.review_count = 0
                    self.total_conflicts_created += 1
                    dev.conflicts_caused += 1
                    events["task_completion"] = 3.0
                    events["conflict_penalty"] = -3.0
                    if task.priority <= 2:
                        events["high_priority_bonus"] = 2.0
                    for cid in task.conflicts_with:
                        if cid in self._discussed_conflicts:
                            self._discussed_conflicts.add(task.task_id)
                            break
                else:
                    task.status = TaskStatus.IN_REVIEW
                    pr_id = self._next_pr_id()
                    task.pr_id = pr_id
                    self.pr_queue[pr_id] = PRObservation(
                        pr_id=pr_id, task_id=task.task_id,
                        submitted_by=dev_id, status="pending_review",
                    )
                    events["task_completion"] = 3.0
                    if task.priority <= 2:
                        events["high_priority_bonus"] = 2.0

        elif action.action_type == DevActionType.REVIEW_PR:
            pr = self.pr_queue[action.pr_id]
            task = self.tasks[pr.task_id]
            task.review_count += 1
            dev.current_action = "reviewing"

            # Code review rejection: first review of flagged tasks gets rejected
            if (
                self.enable_review_rejection
                and task.rejection_on_first_review
                and task.review_count == 1
            ):
                task.status = TaskStatus.IN_PROGRESS
                task.effort_remaining += 1
                task.effort_total += 1
                task.progress_pct = 1.0 - (task.effort_remaining / task.effort_total)
                task.pr_id = None
                del self.pr_queue[action.pr_id]
                events[f"review_rejected:{action.pr_id}_for_{pr.task_id}_bugs_found_rework_needed"] = -1.0
            else:
                task.status = TaskStatus.DONE
                task.assigned_to = None
                del self.pr_queue[action.pr_id]
                dev.tasks_completed += 1
                events["pr_merged"] = 5.0

        elif action.action_type == DevActionType.FIX_CONFLICT:
            task = self.tasks[action.task_id]
            task.status = TaskStatus.IN_REVIEW
            pr_id = self._next_pr_id()
            task.pr_id = pr_id
            self.pr_queue[pr_id] = PRObservation(
                pr_id=pr_id, task_id=task.task_id,
                submitted_by=task.assigned_to or dev_id, status="pending_review",
            )
            dev.current_task = action.task_id
            dev.current_action = "fixing_conflict"

        elif action.action_type == DevActionType.COMMUNICATE:
            dev.current_action = "communicating"
            self.communications_sent += 1
            if action.comm_type == CommunicationType.ASK_PM_CLARIFICATION:
                task = self.tasks.get(action.comm_target_task)
                if task and action.comm_target_task not in self.clarified_tasks:
                    self.clarified_tasks.add(action.comm_target_task)
                    task.effort_remaining = max(1, task.effort_remaining - 1)
                    task.effort_total = max(task.effort_total, task.effort_remaining)
                    events["communication_reward"] = 0.5
                    self.pm_messages.append(PMMessage(
                        step=self.current_step,
                        message=f"PM clarified requirements for {action.comm_target_task}. Effort reduced.",
                        event_type="clarification_response",
                        acknowledged=True,
                    ))
            elif action.comm_type == CommunicationType.SYNC_WITH_DEV:
                self._synced_devs.add(dev_id)
                has_undiscussed = any(
                    t.status == TaskStatus.HAS_CONFLICT
                    and t.task_id not in self._discussed_conflicts
                    for t in self.tasks.values()
                )
                if has_undiscussed:
                    events["sync_reward"] = 1.0
                else:
                    events["wasted_sync_penalty"] = -1.0
                    dev.steps_idle += 1

        elif action.action_type == DevActionType.IDLE:
            dev.current_action = "idle"
            dev.steps_idle += 1
            events["idle_penalty"] = -1.0

        return events

    def _resolve_conflict_discussion(self, reward_events: dict):
        """When both devs sync, find conflicting HAS_CONFLICT task pairs.

        The higher-priority task (lower number) gets auto-resolved to IN_REVIEW
        with a PR. The lower-priority one stays HAS_CONFLICT but is marked as
        'discussed' so fix_conflict can be used on it next step.
        """
        conflicted = [
            t for t in self.tasks.values()
            if t.status == TaskStatus.HAS_CONFLICT
        ]
        if not conflicted:
            return

        if len(conflicted) == 1:
            task = conflicted[0]
            self._discussed_conflicts.add(task.task_id)
            task.status = TaskStatus.IN_REVIEW
            pr_id = self._next_pr_id()
            task.pr_id = pr_id
            self.pr_queue[pr_id] = PRObservation(
                pr_id=pr_id, task_id=task.task_id,
                submitted_by=task.assigned_to or "dev1",
                status="pending_review",
            )
            reward_events["conflict_auto_resolved"] = 2.0
            return

        resolved = set()
        for i, t1 in enumerate(conflicted):
            if t1.task_id in resolved:
                continue
            for t2 in conflicted[i + 1:]:
                if t2.task_id in resolved:
                    continue
                if t2.task_id in t1.conflicts_with or t1.task_id in t2.conflicts_with:
                    if t1.priority < t2.priority or (t1.priority == t2.priority and t1.task_id < t2.task_id):
                        winner, loser = t1, t2
                    else:
                        winner, loser = t2, t1

                    winner.status = TaskStatus.IN_REVIEW
                    pr_id = self._next_pr_id()
                    winner.pr_id = pr_id
                    self.pr_queue[pr_id] = PRObservation(
                        pr_id=pr_id, task_id=winner.task_id,
                        submitted_by=winner.assigned_to or "dev1",
                        status="pending_review",
                    )
                    reward_events["conflict_auto_resolved"] = 2.0

                    self._discussed_conflicts.add(loser.task_id)
                    self._discussed_conflicts.add(winner.task_id)
                    resolved.add(winner.task_id)
                    resolved.add(loser.task_id)
                    break

        for t in conflicted:
            if t.task_id not in resolved:
                self._discussed_conflicts.add(t.task_id)

    def _tick_pip(self):
        """Decrement active PIP timers."""
        for dev in (self.dev1, self.dev2):
            if dev.pip_steps_remaining > 0:
                dev.pip_steps_remaining -= 1
                if dev.pip_steps_remaining == 0:
                    dev.pip_active = False
                    # Reset counters so PIP-locked idle steps don't re-trigger
                    dev.conflicts_caused = 0
                    dev.steps_idle = 0

    def _check_pip_triggers(self):
        """Check if any dev should be PIP'd based on conflict/idle thresholds."""
        for dev in (self.dev1, self.dev2):
            if not dev.pip_active:
                if (dev.conflicts_caused >= self.pip_conflict_threshold
                        or dev.steps_idle >= self.pip_idle_threshold):
                    dev.pip_active = True
                    dev.pip_steps_remaining = self.pip_duration
                    dev.conflicts_caused = 0
                    dev.steps_idle = 0

    def step(self, dev1_action: DevAction, dev2_action: DevAction) -> dict:
        """Process one step of the simulation. Returns reward events dict."""
        self.current_step += 1
        self._synced_devs.clear()

        # 1. Process PM events
        self._process_pm_events()

        # 2. Tick PIP timers (decrement before this step's actions)
        if self.enable_pip:
            self._tick_pip()

        # 3. Validate actions
        valid_d1, reason_d1 = self._validate_action(dev1_action, "dev1")
        valid_d2, reason_d2 = self._validate_action(dev2_action, "dev2")

        reward_events: dict[str, float] = {}

        # 4. PIP lock-out: PIP'd devs skip everything (no idle tracking)
        dev1_pip_locked = False
        dev2_pip_locked = False
        if self.enable_pip:
            if self.dev1.pip_active:
                valid_d1 = DevAction(action_type=DevActionType.IDLE)
                reward_events["dev1_pip_penalty"] = -1.5
                self.dev1.current_action = "pip_locked"
                dev1_pip_locked = True
            if self.dev2.pip_active:
                valid_d2 = DevAction(action_type=DevActionType.IDLE)
                reward_events["dev2_pip_penalty"] = -1.5
                self.dev2.current_action = "pip_locked"
                dev2_pip_locked = True

        # 5. Track invalid actions (skip PIP'd devs — they're already penalized)
        if not dev1_pip_locked and valid_d1.action_type == DevActionType.IDLE and dev1_action.action_type != DevActionType.IDLE:
            key = f"dev1_invalid:{reason_d1}" if reason_d1 else "dev1_invalid_action_penalty"
            reward_events[key] = -1.0
            self.dev1.steps_idle += 1
            self.dev1.current_action = "idle"
        if not dev2_pip_locked and valid_d2.action_type == DevActionType.IDLE and dev2_action.action_type != DevActionType.IDLE:
            key = f"dev2_invalid:{reason_d2}" if reason_d2 else "dev2_invalid_action_penalty"
            reward_events[key] = -1.0
            self.dev2.steps_idle += 1
            self.dev2.current_action = "idle"

        # 6. Prevent both devs from targeting the same task or PR
        if (
            valid_d1.action_type == DevActionType.WORK_ON_TASK
            and valid_d2.action_type == DevActionType.WORK_ON_TASK
            and valid_d1.task_id == valid_d2.task_id
        ):
            valid_d2 = DevAction(action_type=DevActionType.IDLE)
            reward_events["dev2_invalid:same_task_as_dev1"] = -1.0
            self.dev2.steps_idle += 1
            self.dev2.current_action = "idle"

        if (
            valid_d1.action_type == DevActionType.REVIEW_PR
            and valid_d2.action_type == DevActionType.REVIEW_PR
            and valid_d1.pr_id == valid_d2.pr_id
        ):
            valid_d2 = DevAction(action_type=DevActionType.IDLE)
            reward_events["dev2_invalid:same_pr_as_dev1"] = -1.0
            self.dev2.steps_idle += 1
            self.dev2.current_action = "idle"

        # 7. Execute actions (skip PIP'd devs)
        d1_events = {} if dev1_pip_locked else self._execute_action(valid_d1, "dev1")
        d2_events = {} if dev2_pip_locked else self._execute_action(valid_d2, "dev2")

        # 7. Fix simultaneous completion bias
        if "task_completion" in d1_events and "task_completion" in d2_events:
            t1_id = valid_d1.task_id
            t2_id = valid_d2.task_id
            t1 = self.tasks.get(t1_id)
            t2 = self.tasks.get(t2_id)
            if t1 and t2:
                mutual_conflict = (
                    t2_id in t1.conflicts_with or t1_id in t2.conflicts_with
                )
                if mutual_conflict:
                    if t2.status == TaskStatus.IN_REVIEW and t2.pr_id:
                        del self.pr_queue[t2.pr_id]
                        t2.pr_id = None
                        t2.status = TaskStatus.HAS_CONFLICT
                        t2.review_count = 0
                        self.total_conflicts_created += 1
                        self.dev2.conflicts_caused += 1
                        d2_events["conflict_penalty"] = -3.0

        # Merge reward events
        for k, v in d1_events.items():
            reward_events[f"dev1_{k}"] = reward_events.get(f"dev1_{k}", 0) + v
        for k, v in d2_events.items():
            reward_events[f"dev2_{k}"] = reward_events.get(f"dev2_{k}", 0) + v

        # 8. Sync discussion: check if both devs synced for conflict resolution
        if len(self._synced_devs) == 2:
            self._resolve_conflict_discussion(reward_events)
        elif len(self._synced_devs) == 1:
            # Only one dev synced — check if there are conflicts needing both
            has_undiscussed = any(
                t.status == TaskStatus.HAS_CONFLICT
                and t.task_id not in self._discussed_conflicts
                for t in self.tasks.values()
            )
            if has_undiscussed:
                solo_dev = next(iter(self._synced_devs))
                other_dev = "dev2" if solo_dev == "dev1" else "dev1"
                reward_events[f"{solo_dev}_sync_waiting:{other_dev}_must_also_sync_to_resolve_conflict"] = 0.0

        # 9. Update dependencies
        self._update_dependency_statuses()

        # 10. Check PIP triggers
        if self.enable_pip:
            self._check_pip_triggers()

        # 11. Check done condition
        all_done = all(t.status == TaskStatus.DONE for t in self.tasks.values())
        if all_done:
            reward_events["sprint_completion_bonus"] = 10.0
        self.done = all_done or self.current_step >= self.max_steps

        return reward_events

    def get_observation(self) -> Observation:
        """Build the current observation for the agent."""
        task_board = [
            TaskObservation(
                task_id=t.task_id, title=t.title, task_type=t.task_type,
                effort_remaining=t.effort_remaining, effort_total=t.effort_total,
                status=t.status, assigned_to=t.assigned_to,
                depends_on=t.depends_on, conflicts_with=t.conflicts_with,
                priority=t.priority, progress_pct=t.progress_pct, pr_id=t.pr_id,
            )
            for t in self.tasks.values()
        ]

        pr_queue = list(self.pr_queue.values())
        pm_messages = [m for m in self.pm_messages if m.event_type != "clarification_response"]
        merge_conflicts = [
            t.task_id for t in self.tasks.values()
            if t.status == TaskStatus.HAS_CONFLICT
        ]

        tasks_by_status: dict[TaskStatus, int] = {}
        for t in self.tasks.values():
            tasks_by_status[t.status] = tasks_by_status.get(t.status, 0) + 1

        sprint = SprintProgress(
            current_step=self.current_step,
            max_steps=self.max_steps,
            total_tasks=len(self.tasks),
            tasks_done=tasks_by_status.get(TaskStatus.DONE, 0),
            tasks_in_progress=tasks_by_status.get(TaskStatus.IN_PROGRESS, 0),
            tasks_blocked=tasks_by_status.get(TaskStatus.BLOCKED, 0),
            tasks_in_review=tasks_by_status.get(TaskStatus.IN_REVIEW, 0),
            velocity=(
                tasks_by_status.get(TaskStatus.DONE, 0) / self.current_step
                if self.current_step > 0 else 0.0
            ),
        )

        return Observation(
            task_board=task_board,
            pr_queue=pr_queue,
            pm_messages=pm_messages,
            dev1_status=self.dev1.model_copy(),
            dev2_status=self.dev2.model_copy(),
            sprint_progress=sprint,
            merge_conflicts=merge_conflicts,
            dev_specializations=self.dev_specializations if self.enable_specialization else {},
        )

    def get_info(self) -> dict:
        """Return info dict for graders."""
        return {
            "total_conflicts_created": self.total_conflicts_created,
            "communications_sent": self.communications_sent,
            "total_pm_messages": len([
                m for m in self.pm_messages
                if m.event_type != "clarification_response"
            ]),
        }
