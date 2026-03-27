from env.models import (
    ScenarioConfig, ProjectTask, PMEvent,
    TaskType, TaskStatus, PMEventType,
)


EASY_SCENARIO = ScenarioConfig(
    scenario_id="easy",
    name="Quick Launch",
    description="5 independent tasks, no dependencies or conflicts. Complete the sprint efficiently.",
    difficulty="easy",
    max_steps=20,
    tasks=[
        ProjectTask(
            task_id="T1", title="Build landing page",
            task_type=TaskType.FRONTEND, effort_remaining=2, effort_total=2, priority=2,
        ),
        ProjectTask(
            task_id="T2", title="Implement auth API",
            task_type=TaskType.BACKEND, effort_remaining=3, effort_total=3, priority=1,
        ),
        ProjectTask(
            task_id="T3", title="Create user profile page",
            task_type=TaskType.FRONTEND, effort_remaining=2, effort_total=2, priority=3,
        ),
        ProjectTask(
            task_id="T4", title="Write integration tests",
            task_type=TaskType.TESTING, effort_remaining=3, effort_total=3, priority=2,
        ),
        ProjectTask(
            task_id="T5", title="Set up CI pipeline",
            task_type=TaskType.DEVOPS, effort_remaining=2, effort_total=2, priority=4,
        ),
    ],
    pm_events=[],
)


MEDIUM_SCENARIO = ScenarioConfig(
    scenario_id="medium",
    name="Feature Pipeline",
    description="8 tasks with dependency chains and merge conflict potential. PM changes priorities mid-sprint.",
    difficulty="medium",
    max_steps=25,
    tasks=[
        ProjectTask(
            task_id="T1", title="Design database schema",
            task_type=TaskType.DATABASE, effort_remaining=3, effort_total=3, priority=1,
        ),
        ProjectTask(
            task_id="T2", title="Build REST API endpoints",
            task_type=TaskType.BACKEND, effort_remaining=3, effort_total=3, priority=1,
            depends_on=["T1"], conflicts_with=["T3"],
        ),
        ProjectTask(
            task_id="T3", title="Build GraphQL layer",
            task_type=TaskType.BACKEND, effort_remaining=3, effort_total=3, priority=2,
            depends_on=["T1"], conflicts_with=["T2"],
        ),
        ProjectTask(
            task_id="T4", title="Admin dashboard frontend",
            task_type=TaskType.FRONTEND, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T2"],
        ),
        ProjectTask(
            task_id="T5", title="Public-facing frontend",
            task_type=TaskType.FRONTEND, effort_remaining=3, effort_total=3, priority=2,
            depends_on=["T3"],
        ),
        ProjectTask(
            task_id="T6", title="End-to-end test suite",
            task_type=TaskType.TESTING, effort_remaining=3, effort_total=3, priority=3,
            depends_on=["T2", "T3"],
        ),
        ProjectTask(
            task_id="T7", title="Deploy infrastructure",
            task_type=TaskType.DEVOPS, effort_remaining=2, effort_total=2, priority=3,
        ),
        ProjectTask(
            task_id="T8", title="Performance testing",
            task_type=TaskType.TESTING, effort_remaining=3, effort_total=3, priority=4,
            depends_on=["T4", "T5"],
        ),
    ],
    pm_events=[
        PMEvent(
            trigger_step=10,
            event_type=PMEventType.PRIORITY_CHANGE,
            target_task_id="T5",
            details={"new_priority": 1},
            message="Client demo moved up. T5 (Public-facing frontend) is now critical priority.",
        ),
    ],
)


HARD_SCENARIO = ScenarioConfig(
    scenario_id="hard",
    name="Crunch Time",
    description="10+ tasks, complex DAG, tight deadline, PM changes requirements and injects emergency work. Cannot complete everything — must triage.",
    difficulty="hard",
    max_steps=20,
    tasks=[
        ProjectTask(
            task_id="T1", title="Core database migrations",
            task_type=TaskType.DATABASE, effort_remaining=2, effort_total=2, priority=1,
        ),
        ProjectTask(
            task_id="T2", title="User service API",
            task_type=TaskType.BACKEND, effort_remaining=3, effort_total=3, priority=1,
            depends_on=["T1"], conflicts_with=["T3"],
        ),
        ProjectTask(
            task_id="T3", title="Payment service API",
            task_type=TaskType.BACKEND, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T1"], conflicts_with=["T2"],
        ),
        ProjectTask(
            task_id="T4", title="User management UI",
            task_type=TaskType.FRONTEND, effort_remaining=3, effort_total=3, priority=2,
            depends_on=["T2"], conflicts_with=["T5"],
        ),
        ProjectTask(
            task_id="T5", title="Payment checkout UI",
            task_type=TaskType.FRONTEND, effort_remaining=3, effort_total=3, priority=2,
            depends_on=["T3"], conflicts_with=["T4"],
        ),
        ProjectTask(
            task_id="T6", title="Notification service",
            task_type=TaskType.BACKEND, effort_remaining=2, effort_total=2, priority=3,
            depends_on=["T2", "T3"],
        ),
        ProjectTask(
            task_id="T7", title="Integration test suite",
            task_type=TaskType.TESTING, effort_remaining=3, effort_total=3, priority=3,
            depends_on=["T4", "T5"],
        ),
        ProjectTask(
            task_id="T8", title="Kubernetes deployment",
            task_type=TaskType.DEVOPS, effort_remaining=2, effort_total=2, priority=4,
        ),
        ProjectTask(
            task_id="T9", title="Security audit automation",
            task_type=TaskType.TESTING, effort_remaining=2, effort_total=2, priority=3,
            depends_on=["T6"],
        ),
        ProjectTask(
            task_id="T10", title="Analytics dashboard",
            task_type=TaskType.FRONTEND, effort_remaining=3, effort_total=3, priority=4,
            depends_on=["T4"],
        ),
    ],
    pm_events=[
        PMEvent(
            trigger_step=5,
            event_type=PMEventType.REQUIREMENT_CHANGE,
            target_task_id="T4",
            details={"effort_increase": 2},
            message="Stakeholder wants richer UI. T4 (User management UI) scope expanded — effort increased.",
        ),
        PMEvent(
            trigger_step=10,
            event_type=PMEventType.PRIORITY_CHANGE,
            target_task_id="T9",
            details={"new_priority": 1},
            message="Security audit incoming. T9 (Security audit automation) is now critical.",
        ),
        PMEvent(
            trigger_step=14,
            event_type=PMEventType.NEW_TASK,
            target_task_id="T11",
            details={
                "task": {
                    "task_id": "T11",
                    "title": "Emergency hotfix: payment bug",
                    "task_type": "backend",
                    "effort_remaining": 2,
                    "effort_total": 2,
                    "priority": 1,
                    "depends_on": ["T1"],
                    "conflicts_with": ["T6"],
                }
            },
            message="Emergency hotfix needed! Payment processing bug found. T11 is top priority.",
        ),
    ],
)


SCENARIOS: dict[str, ScenarioConfig] = {
    "easy": EASY_SCENARIO,
    "medium": MEDIUM_SCENARIO,
    "hard": HARD_SCENARIO,
}
