from env.models import (
    ScenarioConfig, ProjectTask, PMEvent,
    TaskType, TaskStatus, PMEventType,
)


# ──────────────────────────────────────────────────────────────────────
#  EASY scenarios – no mechanics, no dependencies, no conflicts
# ──────────────────────────────────────────────────────────────────────

EASY_1 = ScenarioConfig(
    scenario_id="easy_1",
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


EASY_2 = ScenarioConfig(
    scenario_id="easy_2",
    name="Bug Bash",
    description="4 quick tasks focused on bug fixes and test coverage. No dependencies or conflicts.",
    difficulty="easy",
    max_steps=15,
    tasks=[
        ProjectTask(
            task_id="T1", title="Fix login validation edge cases",
            task_type=TaskType.TESTING, effort_remaining=2, effort_total=2, priority=1,
        ),
        ProjectTask(
            task_id="T2", title="Patch session timeout handler",
            task_type=TaskType.BACKEND, effort_remaining=3, effort_total=3, priority=2,
        ),
        ProjectTask(
            task_id="T3", title="Add smoke tests for checkout flow",
            task_type=TaskType.TESTING, effort_remaining=1, effort_total=1, priority=3,
        ),
        ProjectTask(
            task_id="T4", title="Fix rate limiter bypass",
            task_type=TaskType.BACKEND, effort_remaining=2, effort_total=2, priority=2,
        ),
    ],
    pm_events=[],
)


EASY_3 = ScenarioConfig(
    scenario_id="easy_3",
    name="Frontend Sprint",
    description="6 tasks dominated by frontend work with a small devops chore. No dependencies or conflicts.",
    difficulty="easy",
    max_steps=18,
    tasks=[
        ProjectTask(
            task_id="T1", title="Build onboarding wizard",
            task_type=TaskType.FRONTEND, effort_remaining=2, effort_total=2, priority=1,
        ),
        ProjectTask(
            task_id="T2", title="Add dark mode toggle",
            task_type=TaskType.FRONTEND, effort_remaining=1, effort_total=1, priority=2,
        ),
        ProjectTask(
            task_id="T3", title="Implement notification drawer",
            task_type=TaskType.FRONTEND, effort_remaining=2, effort_total=2, priority=2,
        ),
        ProjectTask(
            task_id="T4", title="Build settings preferences panel",
            task_type=TaskType.FRONTEND, effort_remaining=2, effort_total=2, priority=3,
        ),
        ProjectTask(
            task_id="T5", title="Configure CDN caching rules",
            task_type=TaskType.DEVOPS, effort_remaining=1, effort_total=1, priority=4,
        ),
        ProjectTask(
            task_id="T6", title="Create responsive nav bar",
            task_type=TaskType.FRONTEND, effort_remaining=1, effort_total=1, priority=3,
        ),
    ],
    pm_events=[],
)


EASY_4 = ScenarioConfig(
    scenario_id="easy_4",
    name="Infrastructure Setup",
    description="5 tasks covering database provisioning and devops tooling. No dependencies or conflicts.",
    difficulty="easy",
    max_steps=20,
    tasks=[
        ProjectTask(
            task_id="T1", title="Provision primary Postgres cluster",
            task_type=TaskType.DATABASE, effort_remaining=3, effort_total=3, priority=1,
        ),
        ProjectTask(
            task_id="T2", title="Set up Terraform modules",
            task_type=TaskType.DEVOPS, effort_remaining=2, effort_total=2, priority=2,
        ),
        ProjectTask(
            task_id="T3", title="Configure monitoring dashboards",
            task_type=TaskType.DEVOPS, effort_remaining=2, effort_total=2, priority=2,
        ),
        ProjectTask(
            task_id="T4", title="Create read replica configuration",
            task_type=TaskType.DATABASE, effort_remaining=2, effort_total=2, priority=3,
        ),
        ProjectTask(
            task_id="T5", title="Build deployment pipeline scripts",
            task_type=TaskType.DEVOPS, effort_remaining=3, effort_total=3, priority=4,
        ),
    ],
    pm_events=[],
)


EASY_5 = ScenarioConfig(
    scenario_id="easy_5",
    name="MVP Prototype",
    description="5 tasks spanning the full stack for a quick MVP. No dependencies or conflicts.",
    difficulty="easy",
    max_steps=16,
    tasks=[
        ProjectTask(
            task_id="T1", title="Implement core REST endpoints",
            task_type=TaskType.BACKEND, effort_remaining=2, effort_total=2, priority=1,
        ),
        ProjectTask(
            task_id="T2", title="Build product listing page",
            task_type=TaskType.FRONTEND, effort_remaining=2, effort_total=2, priority=1,
        ),
        ProjectTask(
            task_id="T3", title="Set up SQLite dev database",
            task_type=TaskType.DATABASE, effort_remaining=1, effort_total=1, priority=2,
        ),
        ProjectTask(
            task_id="T4", title="Write API contract tests",
            task_type=TaskType.TESTING, effort_remaining=2, effort_total=2, priority=3,
        ),
        ProjectTask(
            task_id="T5", title="Create Docker Compose dev stack",
            task_type=TaskType.DEVOPS, effort_remaining=1, effort_total=1, priority=4,
        ),
    ],
    pm_events=[],
)


# ──────────────────────────────────────────────────────────────────────
#  MEDIUM scenarios – specialization + review rejection enabled
# ──────────────────────────────────────────────────────────────────────

MEDIUM_1 = ScenarioConfig(
    scenario_id="medium_1",
    name="Feature Pipeline",
    description="8 tasks with dependency chains and merge conflict potential. PM changes priorities mid-sprint.",
    difficulty="medium",
    max_steps=25,
    enable_specialization=True,
    enable_review_rejection=True,
    dev_specializations={
        "dev1": [TaskType.BACKEND, TaskType.DATABASE],
        "dev2": [TaskType.FRONTEND, TaskType.DEVOPS],
    },
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
            rejection_on_first_review=True,
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


MEDIUM_2 = ScenarioConfig(
    scenario_id="medium_2",
    name="API Rewrite",
    description="7 tasks rewriting the API layer with conflict risk and a late priority escalation.",
    difficulty="medium",
    max_steps=22,
    enable_specialization=True,
    enable_review_rejection=True,
    dev_specializations={
        "dev1": [TaskType.BACKEND, TaskType.DATABASE],
        "dev2": [TaskType.FRONTEND, TaskType.DEVOPS],
    },
    tasks=[
        ProjectTask(
            task_id="T1", title="Migrate database to new schema",
            task_type=TaskType.DATABASE, effort_remaining=2, effort_total=2, priority=1,
        ),
        ProjectTask(
            task_id="T2", title="Rewrite REST controllers",
            task_type=TaskType.BACKEND, effort_remaining=3, effort_total=3, priority=1,
            depends_on=["T1"], conflicts_with=["T3"],
        ),
        ProjectTask(
            task_id="T3", title="Build v2 API handlers",
            task_type=TaskType.BACKEND, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T1"], conflicts_with=["T2"],
        ),
        ProjectTask(
            task_id="T4", title="Update API consumer dashboard",
            task_type=TaskType.FRONTEND, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T2"],
        ),
        ProjectTask(
            task_id="T5", title="Write API regression tests",
            task_type=TaskType.TESTING, effort_remaining=2, effort_total=2, priority=3,
            depends_on=["T2", "T3"],
        ),
        ProjectTask(
            task_id="T6", title="Set up blue-green deploy",
            task_type=TaskType.DEVOPS, effort_remaining=2, effort_total=2, priority=3,
        ),
        ProjectTask(
            task_id="T7", title="Build API documentation portal",
            task_type=TaskType.FRONTEND, effort_remaining=3, effort_total=3, priority=2,
            depends_on=["T3"],
            rejection_on_first_review=True,
        ),
    ],
    pm_events=[
        PMEvent(
            trigger_step=8,
            event_type=PMEventType.PRIORITY_CHANGE,
            target_task_id="T7",
            details={"new_priority": 1},
            message="Client demo prep - T7 now top priority",
        ),
    ],
)


MEDIUM_3 = ScenarioConfig(
    scenario_id="medium_3",
    name="Mobile Backend",
    description="8 tasks building the mobile backend with dependency chains and a conflict pair.",
    difficulty="medium",
    max_steps=24,
    enable_specialization=True,
    enable_review_rejection=True,
    dev_specializations={
        "dev1": [TaskType.DATABASE, TaskType.DEVOPS],
        "dev2": [TaskType.BACKEND, TaskType.FRONTEND],
    },
    tasks=[
        ProjectTask(
            task_id="T1", title="Design mobile data models",
            task_type=TaskType.DATABASE, effort_remaining=2, effort_total=2, priority=1,
        ),
        ProjectTask(
            task_id="T2", title="Build push notification service",
            task_type=TaskType.BACKEND, effort_remaining=3, effort_total=3, priority=1,
            depends_on=["T1"],
        ),
        ProjectTask(
            task_id="T3", title="Implement offline sync engine",
            task_type=TaskType.BACKEND, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T1"], conflicts_with=["T4"],
        ),
        ProjectTask(
            task_id="T4", title="Build real-time feed UI",
            task_type=TaskType.FRONTEND, effort_remaining=3, effort_total=3, priority=2,
            depends_on=["T2"], conflicts_with=["T3"],
            rejection_on_first_review=True,
        ),
        ProjectTask(
            task_id="T5", title="Create user activity stream",
            task_type=TaskType.FRONTEND, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T2"],
        ),
        ProjectTask(
            task_id="T6", title="Write mobile API test suite",
            task_type=TaskType.TESTING, effort_remaining=3, effort_total=3, priority=3,
            depends_on=["T4", "T5"],
        ),
        ProjectTask(
            task_id="T7", title="Configure mobile CI/CD",
            task_type=TaskType.DEVOPS, effort_remaining=2, effort_total=2, priority=3,
        ),
        ProjectTask(
            task_id="T8", title="Run load testing for mobile APIs",
            task_type=TaskType.TESTING, effort_remaining=2, effort_total=2, priority=4,
            depends_on=["T6"],
        ),
    ],
    pm_events=[
        PMEvent(
            trigger_step=12,
            event_type=PMEventType.PRIORITY_CHANGE,
            target_task_id="T5",
            details={"new_priority": 1},
            message="Marketing wants T5 for campaign launch",
        ),
    ],
)


MEDIUM_4 = ScenarioConfig(
    scenario_id="medium_4",
    name="Data Pipeline",
    description="7 tasks building a data pipeline with database conflicts and a mid-sprint scope change.",
    difficulty="medium",
    max_steps=23,
    enable_specialization=True,
    enable_review_rejection=True,
    dev_specializations={
        "dev1": [TaskType.DATABASE, TaskType.BACKEND],
        "dev2": [TaskType.FRONTEND, TaskType.DEVOPS],
    },
    tasks=[
        ProjectTask(
            task_id="T1", title="Build ingestion pipeline tables",
            task_type=TaskType.DATABASE, effort_remaining=3, effort_total=3, priority=1,
        ),
        ProjectTask(
            task_id="T2", title="Create ETL stored procedures",
            task_type=TaskType.DATABASE, effort_remaining=2, effort_total=2, priority=1,
            depends_on=["T1"], conflicts_with=["T3"],
        ),
        ProjectTask(
            task_id="T3", title="Build streaming transform service",
            task_type=TaskType.BACKEND, effort_remaining=3, effort_total=3, priority=2,
            depends_on=["T1"], conflicts_with=["T2"],
        ),
        ProjectTask(
            task_id="T4", title="Implement batch export API",
            task_type=TaskType.BACKEND, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T2"],
        ),
        ProjectTask(
            task_id="T5", title="Build pipeline monitoring dashboard",
            task_type=TaskType.FRONTEND, effort_remaining=3, effort_total=3, priority=3,
            depends_on=["T3", "T4"],
        ),
        ProjectTask(
            task_id="T6", title="Write data integrity tests",
            task_type=TaskType.TESTING, effort_remaining=2, effort_total=2, priority=3,
            depends_on=["T3"],
            rejection_on_first_review=True,
        ),
        ProjectTask(
            task_id="T7", title="Set up Airflow orchestration",
            task_type=TaskType.DEVOPS, effort_remaining=2, effort_total=2, priority=4,
        ),
    ],
    pm_events=[
        PMEvent(
            trigger_step=7,
            event_type=PMEventType.REQUIREMENT_CHANGE,
            target_task_id="T5",
            details={"effort_increase": 2},
            message="Stakeholder wants dashboard revamp - T5 expanded",
        ),
    ],
)


MEDIUM_5 = ScenarioConfig(
    scenario_id="medium_5",
    name="Auth System",
    description="9 tasks building an auth system with conflicts between API and database layers.",
    difficulty="medium",
    max_steps=25,
    enable_specialization=True,
    enable_review_rejection=True,
    dev_specializations={
        "dev1": [TaskType.FRONTEND, TaskType.TESTING],
        "dev2": [TaskType.BACKEND, TaskType.DATABASE],
    },
    tasks=[
        ProjectTask(
            task_id="T1", title="Implement JWT token service",
            task_type=TaskType.BACKEND, effort_remaining=2, effort_total=2, priority=1,
        ),
        ProjectTask(
            task_id="T2", title="Build OAuth2 authorization flow",
            task_type=TaskType.BACKEND, effort_remaining=3, effort_total=3, priority=1,
            depends_on=["T1"], conflicts_with=["T3"],
            rejection_on_first_review=True,
        ),
        ProjectTask(
            task_id="T3", title="Create session store schema",
            task_type=TaskType.DATABASE, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T1"], conflicts_with=["T2"],
        ),
        ProjectTask(
            task_id="T4", title="Build login/signup UI",
            task_type=TaskType.FRONTEND, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T2"],
        ),
        ProjectTask(
            task_id="T5", title="Create password reset flow UI",
            task_type=TaskType.FRONTEND, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T3"],
        ),
        ProjectTask(
            task_id="T6", title="Write auth integration tests",
            task_type=TaskType.TESTING, effort_remaining=3, effort_total=3, priority=3,
            depends_on=["T2", "T3"],
        ),
        ProjectTask(
            task_id="T7", title="Configure secrets manager",
            task_type=TaskType.DEVOPS, effort_remaining=2, effort_total=2, priority=3,
        ),
        ProjectTask(
            task_id="T8", title="Write UI end-to-end tests",
            task_type=TaskType.TESTING, effort_remaining=2, effort_total=2, priority=3,
            depends_on=["T4", "T5"],
        ),
        ProjectTask(
            task_id="T9", title="Set up SSO SAML proxy",
            task_type=TaskType.DEVOPS, effort_remaining=1, effort_total=1, priority=4,
            depends_on=["T7"],
        ),
    ],
    pm_events=[
        PMEvent(
            trigger_step=9,
            event_type=PMEventType.PRIORITY_CHANGE,
            target_task_id="T6",
            details={"new_priority": 1},
            message="QA team needs T6 urgently for compliance",
        ),
    ],
)


# ──────────────────────────────────────────────────────────────────────
#  HARD scenarios – PIP + specialization + review rejection enabled
# ──────────────────────────────────────────────────────────────────────

HARD_1 = ScenarioConfig(
    scenario_id="hard_1",
    name="Crunch Time",
    description="10+ tasks, complex DAG, tight deadline, PM changes requirements and injects emergency work. Cannot complete everything — must triage.",
    difficulty="hard",
    max_steps=20,
    enable_pip=True,
    enable_specialization=True,
    enable_review_rejection=True,
    dev_specializations={
        "dev1": [TaskType.BACKEND, TaskType.DATABASE],
        "dev2": [TaskType.FRONTEND, TaskType.DEVOPS],
    },
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
            rejection_on_first_review=True,
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
            rejection_on_first_review=True,
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


HARD_2 = ScenarioConfig(
    scenario_id="hard_2",
    name="Platform Migration",
    description="11 tasks migrating an existing platform with tight deadlines, two conflict pairs, and an emergency injection.",
    difficulty="hard",
    max_steps=20,
    enable_pip=True,
    enable_specialization=True,
    enable_review_rejection=True,
    pip_conflict_threshold=2,
    pip_idle_threshold=4,
    pip_duration=2,
    dev_specializations={
        "dev1": [TaskType.BACKEND, TaskType.DATABASE],
        "dev2": [TaskType.FRONTEND, TaskType.TESTING],
    },
    tasks=[
        ProjectTask(
            task_id="T1", title="Export legacy database dump",
            task_type=TaskType.DATABASE, effort_remaining=2, effort_total=2, priority=1,
        ),
        ProjectTask(
            task_id="T2", title="Build new API gateway",
            task_type=TaskType.BACKEND, effort_remaining=3, effort_total=3, priority=1,
            depends_on=["T1"],
        ),
        ProjectTask(
            task_id="T3", title="Create compatibility shim layer",
            task_type=TaskType.BACKEND, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T1"], conflicts_with=["T2"],
            rejection_on_first_review=True,
        ),
        ProjectTask(
            task_id="T4", title="Rebuild settings UI in React",
            task_type=TaskType.FRONTEND, effort_remaining=3, effort_total=3, priority=2,
            depends_on=["T2"], conflicts_with=["T5"],
        ),
        ProjectTask(
            task_id="T5", title="Port profile page to React",
            task_type=TaskType.FRONTEND, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T3"], conflicts_with=["T4"],
        ),
        ProjectTask(
            task_id="T6", title="Migrate audit log tables",
            task_type=TaskType.DATABASE, effort_remaining=2, effort_total=2, priority=3,
            depends_on=["T2"],
        ),
        ProjectTask(
            task_id="T7", title="Write migration validation tests",
            task_type=TaskType.TESTING, effort_remaining=3, effort_total=3, priority=3,
            depends_on=["T4", "T5"],
            rejection_on_first_review=True,
        ),
        ProjectTask(
            task_id="T8", title="Set up canary deployment",
            task_type=TaskType.DEVOPS, effort_remaining=2, effort_total=2, priority=3,
        ),
        ProjectTask(
            task_id="T9", title="Backfill analytics data",
            task_type=TaskType.BACKEND, effort_remaining=2, effort_total=2, priority=4,
            depends_on=["T6"],
        ),
        ProjectTask(
            task_id="T10", title="Run regression test pass",
            task_type=TaskType.TESTING, effort_remaining=2, effort_total=2, priority=4,
            depends_on=["T7"],
        ),
        ProjectTask(
            task_id="T11", title="Configure rollback scripts",
            task_type=TaskType.DEVOPS, effort_remaining=1, effort_total=1, priority=4,
            depends_on=["T8"],
        ),
    ],
    pm_events=[
        PMEvent(
            trigger_step=5,
            event_type=PMEventType.REQUIREMENT_CHANGE,
            target_task_id="T4",
            details={"effort_increase": 2},
            message="Migration scope expanded for T4",
        ),
        PMEvent(
            trigger_step=10,
            event_type=PMEventType.PRIORITY_CHANGE,
            target_task_id="T9",
            details={"new_priority": 1},
            message="Critical data fix needed - T9 top priority",
        ),
        PMEvent(
            trigger_step=15,
            event_type=PMEventType.NEW_TASK,
            target_task_id="T12",
            details={
                "task": {
                    "task_id": "T12",
                    "title": "Emergency: rollback plan needed",
                    "task_type": "devops",
                    "effort_remaining": 2,
                    "effort_total": 2,
                    "priority": 1,
                    "depends_on": ["T1"],
                    "conflicts_with": [],
                }
            },
            message="Emergency: rollback plan needed",
        ),
    ],
)


HARD_3 = ScenarioConfig(
    scenario_id="hard_3",
    name="Security Overhaul",
    description="10 tasks overhauling security infrastructure with aggressive PIP thresholds and multiple PM escalations.",
    difficulty="hard",
    max_steps=18,
    enable_pip=True,
    enable_specialization=True,
    enable_review_rejection=True,
    pip_conflict_threshold=3,
    pip_idle_threshold=4,
    pip_duration=3,
    dev_specializations={
        "dev1": [TaskType.BACKEND, TaskType.TESTING],
        "dev2": [TaskType.DATABASE, TaskType.DEVOPS],
    },
    tasks=[
        ProjectTask(
            task_id="T1", title="Harden authentication middleware",
            task_type=TaskType.BACKEND, effort_remaining=2, effort_total=2, priority=1,
        ),
        ProjectTask(
            task_id="T2", title="Encrypt sensitive columns at rest",
            task_type=TaskType.DATABASE, effort_remaining=2, effort_total=2, priority=1,
            depends_on=["T1"],
        ),
        ProjectTask(
            task_id="T3", title="Implement RBAC authorization",
            task_type=TaskType.BACKEND, effort_remaining=3, effort_total=3, priority=2,
            depends_on=["T1"], conflicts_with=["T4"],
        ),
        ProjectTask(
            task_id="T4", title="Build API key rotation service",
            task_type=TaskType.BACKEND, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T2"], conflicts_with=["T3"],
        ),
        ProjectTask(
            task_id="T5", title="Write penetration test suite",
            task_type=TaskType.TESTING, effort_remaining=3, effort_total=3, priority=2,
            depends_on=["T3", "T4"],
            rejection_on_first_review=True,
        ),
        ProjectTask(
            task_id="T6", title="Build security audit log viewer",
            task_type=TaskType.FRONTEND, effort_remaining=2, effort_total=2, priority=3,
            depends_on=["T3"],
        ),
        ProjectTask(
            task_id="T7", title="Set up WAF and DDoS protection",
            task_type=TaskType.DEVOPS, effort_remaining=2, effort_total=2, priority=3,
        ),
        ProjectTask(
            task_id="T8", title="Automate compliance report generation",
            task_type=TaskType.TESTING, effort_remaining=2, effort_total=2, priority=3,
            depends_on=["T5"],
        ),
        ProjectTask(
            task_id="T9", title="Create admin security dashboard",
            task_type=TaskType.FRONTEND, effort_remaining=3, effort_total=3, priority=4,
            depends_on=["T6"],
        ),
        ProjectTask(
            task_id="T10", title="Deploy secret rotation cron jobs",
            task_type=TaskType.DEVOPS, effort_remaining=2, effort_total=2, priority=4,
            depends_on=["T7"],
        ),
    ],
    pm_events=[
        PMEvent(
            trigger_step=4,
            event_type=PMEventType.PRIORITY_CHANGE,
            target_task_id="T5",
            details={"new_priority": 1},
            message="Audit deadline moved up - T5 critical",
        ),
        PMEvent(
            trigger_step=8,
            event_type=PMEventType.REQUIREMENT_CHANGE,
            target_task_id="T6",
            details={"effort_increase": 1},
            message="Security review requires T6 changes",
        ),
        PMEvent(
            trigger_step=12,
            event_type=PMEventType.PRIORITY_CHANGE,
            target_task_id="T8",
            details={"new_priority": 1},
            message="Pen test results - T8 urgent",
        ),
        PMEvent(
            trigger_step=15,
            event_type=PMEventType.DEADLINE_WARNING,
            message="Sprint end approaching - focus on P1 tasks!",
        ),
    ],
)


HARD_4 = ScenarioConfig(
    scenario_id="hard_4",
    name="Microservices Split",
    description="12 tasks splitting a monolith into microservices with two conflict chains and an emergency task injection.",
    difficulty="hard",
    max_steps=20,
    enable_pip=True,
    enable_specialization=True,
    enable_review_rejection=True,
    pip_conflict_threshold=2,
    pip_idle_threshold=5,
    pip_duration=2,
    dev_specializations={
        "dev1": [TaskType.BACKEND, TaskType.DATABASE],
        "dev2": [TaskType.FRONTEND, TaskType.DEVOPS],
    },
    tasks=[
        ProjectTask(
            task_id="T1", title="Extract shared database layer",
            task_type=TaskType.DATABASE, effort_remaining=2, effort_total=2, priority=1,
        ),
        ProjectTask(
            task_id="T2", title="Build user microservice",
            task_type=TaskType.BACKEND, effort_remaining=3, effort_total=3, priority=1,
            depends_on=["T1"], conflicts_with=["T3"],
        ),
        ProjectTask(
            task_id="T3", title="Build order microservice",
            task_type=TaskType.BACKEND, effort_remaining=3, effort_total=3, priority=1,
            depends_on=["T1"], conflicts_with=["T2"],
        ),
        ProjectTask(
            task_id="T4", title="Implement user service client SDK",
            task_type=TaskType.BACKEND, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T2"],
        ),
        ProjectTask(
            task_id="T5", title="Implement order service client SDK",
            task_type=TaskType.BACKEND, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T3"],
        ),
        ProjectTask(
            task_id="T6", title="Build user management console",
            task_type=TaskType.FRONTEND, effort_remaining=3, effort_total=3, priority=2,
            depends_on=["T4"], conflicts_with=["T7"],
        ),
        ProjectTask(
            task_id="T7", title="Build order tracking dashboard",
            task_type=TaskType.FRONTEND, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T5"], conflicts_with=["T6"],
        ),
        ProjectTask(
            task_id="T8", title="Write cross-service integration tests",
            task_type=TaskType.TESTING, effort_remaining=3, effort_total=3, priority=3,
            depends_on=["T4", "T5"],
            rejection_on_first_review=True,
        ),
        ProjectTask(
            task_id="T9", title="Set up service mesh with Istio",
            task_type=TaskType.DEVOPS, effort_remaining=2, effort_total=2, priority=3,
        ),
        ProjectTask(
            task_id="T10", title="Write contract tests between services",
            task_type=TaskType.TESTING, effort_remaining=2, effort_total=2, priority=3,
            depends_on=["T8"],
        ),
        ProjectTask(
            task_id="T11", title="Configure distributed tracing",
            task_type=TaskType.DEVOPS, effort_remaining=2, effort_total=2, priority=4,
            depends_on=["T9"],
        ),
        ProjectTask(
            task_id="T12", title="Build unified admin portal",
            task_type=TaskType.FRONTEND, effort_remaining=2, effort_total=2, priority=4,
            depends_on=["T6", "T7"],
        ),
    ],
    pm_events=[
        PMEvent(
            trigger_step=6,
            event_type=PMEventType.REQUIREMENT_CHANGE,
            target_task_id="T6",
            details={"effort_increase": 1},
            message="UI team wants richer T6 interface",
        ),
        PMEvent(
            trigger_step=12,
            event_type=PMEventType.NEW_TASK,
            target_task_id="T13",
            details={
                "task": {
                    "task_id": "T13",
                    "title": "Emergency: service mesh compatibility fix",
                    "task_type": "backend",
                    "effort_remaining": 2,
                    "effort_total": 2,
                    "priority": 1,
                    "depends_on": ["T1"],
                    "conflicts_with": ["T4"],
                }
            },
            message="Emergency: service mesh compatibility fix",
        ),
    ],
)


HARD_5 = ScenarioConfig(
    scenario_id="hard_5",
    name="Product Launch",
    description="11 tasks for a product launch with frontend conflict chains, PM priority shifts, and an emergency hotfix.",
    difficulty="hard",
    max_steps=20,
    enable_pip=True,
    enable_specialization=True,
    enable_review_rejection=True,
    pip_conflict_threshold=3,
    pip_idle_threshold=5,
    pip_duration=2,
    dev_specializations={
        "dev1": [TaskType.FRONTEND, TaskType.TESTING],
        "dev2": [TaskType.BACKEND, TaskType.DATABASE],
    },
    tasks=[
        ProjectTask(
            task_id="T1", title="Set up product catalog schema",
            task_type=TaskType.DATABASE, effort_remaining=2, effort_total=2, priority=1,
        ),
        ProjectTask(
            task_id="T2", title="Build product listing API",
            task_type=TaskType.BACKEND, effort_remaining=2, effort_total=2, priority=1,
            depends_on=["T1"],
        ),
        ProjectTask(
            task_id="T3", title="Create storefront browse page",
            task_type=TaskType.FRONTEND, effort_remaining=3, effort_total=3, priority=1,
            depends_on=["T1"], conflicts_with=["T4"],
        ),
        ProjectTask(
            task_id="T4", title="Build product detail page",
            task_type=TaskType.FRONTEND, effort_remaining=3, effort_total=3, priority=2,
            depends_on=["T2"], conflicts_with=["T3"],
        ),
        ProjectTask(
            task_id="T5", title="Implement cart and wishlist API",
            task_type=TaskType.BACKEND, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T2"],
        ),
        ProjectTask(
            task_id="T6", title="Build shopping cart UI",
            task_type=TaskType.FRONTEND, effort_remaining=2, effort_total=2, priority=2,
            depends_on=["T3"],
        ),
        ProjectTask(
            task_id="T7", title="Write checkout flow tests",
            task_type=TaskType.TESTING, effort_remaining=3, effort_total=3, priority=3,
            depends_on=["T4", "T5"],
        ),
        ProjectTask(
            task_id="T8", title="Set up production Kubernetes cluster",
            task_type=TaskType.DEVOPS, effort_remaining=2, effort_total=2, priority=3,
        ),
        ProjectTask(
            task_id="T9", title="Write storefront accessibility tests",
            task_type=TaskType.TESTING, effort_remaining=2, effort_total=2, priority=3,
            depends_on=["T6"],
            rejection_on_first_review=True,
        ),
        ProjectTask(
            task_id="T10", title="Configure auto-scaling policies",
            task_type=TaskType.DEVOPS, effort_remaining=2, effort_total=2, priority=4,
            depends_on=["T8"],
        ),
        ProjectTask(
            task_id="T11", title="Build promotional banner system",
            task_type=TaskType.FRONTEND, effort_remaining=3, effort_total=3, priority=4,
            depends_on=["T6", "T7"],
        ),
    ],
    pm_events=[
        PMEvent(
            trigger_step=5,
            event_type=PMEventType.PRIORITY_CHANGE,
            target_task_id="T9",
            details={"new_priority": 1},
            message="Launch date moved - T9 critical for go-live",
        ),
        PMEvent(
            trigger_step=10,
            event_type=PMEventType.REQUIREMENT_CHANGE,
            target_task_id="T4",
            details={"effort_increase": 2},
            message="Design team added new mockups for T4",
        ),
        PMEvent(
            trigger_step=14,
            event_type=PMEventType.NEW_TASK,
            target_task_id="T12",
            details={
                "task": {
                    "task_id": "T12",
                    "title": "Emergency: payment gateway hotfix",
                    "task_type": "backend",
                    "effort_remaining": 2,
                    "effort_total": 2,
                    "priority": 1,
                    "depends_on": ["T2"],
                    "conflicts_with": ["T5"],
                }
            },
            message="Emergency: payment gateway hotfix",
        ),
    ],
)


# ──────────────────────────────────────────────────────────────────────
#  Master scenario registry
# ──────────────────────────────────────────────────────────────────────

SCENARIOS: dict[str, ScenarioConfig] = {
    "easy_1": EASY_1, "easy_2": EASY_2, "easy_3": EASY_3, "easy_4": EASY_4, "easy_5": EASY_5,
    "medium_1": MEDIUM_1, "medium_2": MEDIUM_2, "medium_3": MEDIUM_3, "medium_4": MEDIUM_4, "medium_5": MEDIUM_5,
    "hard_1": HARD_1, "hard_2": HARD_2, "hard_3": HARD_3, "hard_4": HARD_4, "hard_5": HARD_5,
    # Backward compatibility
    "easy": EASY_1, "medium": MEDIUM_1, "hard": HARD_1,
}
