"""Tests for the GitTangle environment."""
import pytest
from env.models import (
    Action, DevAction, DevActionType, CommunicationType, TaskStatus,
    ScenarioConfig, ProjectTask, TaskType,
)
from env.environment import GitTangleEnv
from env.graders import grade
from env.tasks import SCENARIOS


@pytest.fixture
def env():
    return GitTangleEnv()


@pytest.fixture
def conflict_env():
    """Env with a vanilla medium scenario (no mechanics) for testing conflict logic."""
    config = ScenarioConfig(
        scenario_id="_test_conflict",
        name="Conflict Test",
        description="Test scenario for conflict mechanics",
        difficulty="medium",
        max_steps=30,
        tasks=[
            ProjectTask(task_id="T1", title="Base task", task_type=TaskType.DATABASE,
                        effort_remaining=3, effort_total=3, priority=1),
            ProjectTask(task_id="T2", title="Conflicting A", task_type=TaskType.BACKEND,
                        effort_remaining=3, effort_total=3, priority=1,
                        depends_on=["T1"], conflicts_with=["T3"]),
            ProjectTask(task_id="T3", title="Conflicting B", task_type=TaskType.BACKEND,
                        effort_remaining=3, effort_total=3, priority=2,
                        depends_on=["T1"], conflicts_with=["T2"]),
        ],
    )
    SCENARIOS["_test_conflict"] = config
    env = GitTangleEnv()
    yield env
    del SCENARIOS["_test_conflict"]


class TestReset:
    def test_reset_easy(self, env):
        obs = env.reset("easy")
        assert len(obs.task_board) == 5
        assert obs.sprint_progress.current_step == 0
        assert obs.sprint_progress.max_steps == 20
        assert all(t.status == TaskStatus.BACKLOG for t in obs.task_board)

    def test_reset_medium(self, env):
        obs = env.reset("medium")
        assert len(obs.task_board) == 8
        assert obs.sprint_progress.max_steps == 25

    def test_reset_hard(self, env):
        obs = env.reset("hard")
        assert len(obs.task_board) == 10
        assert obs.sprint_progress.max_steps == 20

    def test_reset_invalid(self, env):
        with pytest.raises(ValueError):
            env.reset("nonexistent")

    def test_reset_clears_state(self, env):
        env.reset("easy")
        idle = DevAction(action_type=DevActionType.IDLE)
        env.step(Action(dev1_action=idle, dev2_action=idle))
        obs = env.reset("easy")
        assert obs.sprint_progress.current_step == 0


class TestStep:
    def test_basic_work(self, env):
        env.reset("easy")
        action = Action(
            dev1_action=DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1"),
            dev2_action=DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T2"),
        )
        obs, reward, done, info = env.step(action)
        assert obs.sprint_progress.current_step == 1
        assert not done
        assert reward.total > 0  # should get task_progress rewards

    def test_idle_penalty(self, env):
        env.reset("easy")
        action = Action(
            dev1_action=DevAction(action_type=DevActionType.IDLE),
            dev2_action=DevAction(action_type=DevActionType.IDLE),
        )
        obs, reward, done, info = env.step(action)
        assert reward.total < 0  # both idle = negative reward

    def test_task_completion_and_review(self, env):
        env.reset("easy")
        idle = DevAction(action_type=DevActionType.IDLE)
        # T1 has effort 2 - work on it twice with dev1
        work_t1 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")
        env.step(Action(dev1_action=work_t1, dev2_action=idle))
        obs, reward, done, info = env.step(Action(dev1_action=work_t1, dev2_action=idle))

        # T1 should now be in review with a PR
        t1_obs = next(t for t in obs.task_board if t.task_id == "T1")
        assert t1_obs.status == TaskStatus.IN_REVIEW
        assert len(obs.pr_queue) == 1
        pr_id = obs.pr_queue[0].pr_id

        # Dev2 reviews the PR (dev1 can't review own PR)
        review = DevAction(action_type=DevActionType.REVIEW_PR, pr_id=pr_id)
        obs, reward, done, info = env.step(Action(dev1_action=idle, dev2_action=review))

        t1_obs = next(t for t in obs.task_board if t.task_id == "T1")
        assert t1_obs.status == TaskStatus.DONE
        assert "dev2_pr_merged" in reward.breakdown

    def test_invalid_action_becomes_idle(self, env):
        env.reset("easy")
        # Try to work on nonexistent task
        bad = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T999")
        idle = DevAction(action_type=DevActionType.IDLE)
        obs, reward, done, info = env.step(Action(dev1_action=bad, dev2_action=idle))
        # Should have invalid action penalty
        assert any(k.startswith("dev1_invalid") for k in reward.breakdown)

    def test_cannot_self_review(self, env):
        env.reset("easy")
        idle = DevAction(action_type=DevActionType.IDLE)
        work_t1 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")
        env.step(Action(dev1_action=work_t1, dev2_action=idle))
        obs, _, _, _ = env.step(Action(dev1_action=work_t1, dev2_action=idle))

        pr_id = obs.pr_queue[0].pr_id
        # Dev1 tries to review own PR - should be invalid
        review = DevAction(action_type=DevActionType.REVIEW_PR, pr_id=pr_id)
        obs, reward, _, _ = env.step(Action(dev1_action=review, dev2_action=idle))
        assert any(k.startswith("dev1_invalid") for k in reward.breakdown)

    def test_episode_ends_at_max_steps(self, env):
        env.reset("easy")
        idle = DevAction(action_type=DevActionType.IDLE)
        action = Action(dev1_action=idle, dev2_action=idle)
        for _ in range(20):
            obs, reward, done, info = env.step(action)
        assert done

    def test_step_after_done_raises(self, env):
        env.reset("easy")
        idle = DevAction(action_type=DevActionType.IDLE)
        action = Action(dev1_action=idle, dev2_action=idle)
        for _ in range(20):
            env.step(action)
        with pytest.raises(RuntimeError):
            env.step(action)


class TestDependencies:
    def test_blocked_task_medium(self, env):
        obs = env.reset("medium")
        # T2 depends on T1, so it should be blocked
        t2 = next(t for t in obs.task_board if t.task_id == "T2")
        assert t2.status == TaskStatus.BLOCKED

    def test_working_on_blocked_task_invalid(self, env):
        env.reset("medium")
        work_t2 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T2")
        idle = DevAction(action_type=DevActionType.IDLE)
        obs, reward, _, _ = env.step(Action(dev1_action=work_t2, dev2_action=idle))
        assert any(k.startswith("dev1_invalid") for k in reward.breakdown)


class TestConflicts:
    """Conflict tests use a vanilla scenario (no specialization) to test pure conflict logic."""

    def _complete_t1_and_review(self, env):
        """Helper: complete T1 and review it to unblock T2/T3."""
        idle = DevAction(action_type=DevActionType.IDLE)
        work_t1 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")
        for _ in range(3):
            env.step(Action(dev1_action=work_t1, dev2_action=idle))
        state = env.state()
        pr_id = next(pr.pr_id for pr in state.pr_queue if pr.task_id == "T1")
        env.step(Action(dev1_action=idle, dev2_action=DevAction(action_type=DevActionType.REVIEW_PR, pr_id=pr_id)))

    def test_no_conflict_during_simultaneous_work(self, conflict_env):
        """Working simultaneously on conflicting tasks is fine — conflict only at completion."""
        conflict_env.reset("_test_conflict")
        self._complete_t1_and_review(conflict_env)

        work_t2 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T2")
        work_t3 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T3")
        obs, reward, _, _ = conflict_env.step(Action(dev1_action=work_t2, dev2_action=work_t3))
        assert "conflict_penalty" not in reward.breakdown
        assert len(obs.merge_conflicts) == 0

    def test_conflict_at_completion_time(self, conflict_env):
        """Conflict triggers when a task completes while its conflicting partner is in progress."""
        conflict_env.reset("_test_conflict")
        self._complete_t1_and_review(conflict_env)
        idle = DevAction(action_type=DevActionType.IDLE)

        # Start T3 with dev2
        work_t3 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T3")
        conflict_env.step(Action(dev1_action=idle, dev2_action=work_t3))  # T3: 2 left

        # Complete T2 with dev1 while T3 is in progress
        work_t2 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T2")
        conflict_env.step(Action(dev1_action=work_t2, dev2_action=work_t3))  # T2:2, T3:1
        conflict_env.step(Action(dev1_action=work_t2, dev2_action=work_t3))  # T2:1, T3 completes

        state = conflict_env.state()
        t3 = next(t for t in state.tasks if t.task_id == "T3")
        assert t3.status == TaskStatus.HAS_CONFLICT

    def test_simultaneous_completion_both_conflict(self, conflict_env):
        """When both devs complete conflicting tasks in the same step, BOTH get HAS_CONFLICT."""
        conflict_env.reset("_test_conflict")
        self._complete_t1_and_review(conflict_env)

        work_t2 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T2")
        work_t3 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T3")
        conflict_env.step(Action(dev1_action=work_t2, dev2_action=work_t3))  # T2:2, T3:2
        conflict_env.step(Action(dev1_action=work_t2, dev2_action=work_t3))  # T2:1, T3:1
        conflict_env.step(Action(dev1_action=work_t2, dev2_action=work_t3))  # Both complete

        state = conflict_env.state()
        t2 = next(t for t in state.tasks if t.task_id == "T2")
        t3 = next(t for t in state.tasks if t.task_id == "T3")
        assert t2.status == TaskStatus.HAS_CONFLICT
        assert t3.status == TaskStatus.HAS_CONFLICT
        assert len(state.pr_queue) == 0

    def test_fix_conflict_creates_pr(self, conflict_env):
        """Full conflict resolution flow: conflict → sync → fix → review."""
        conflict_env.reset("_test_conflict")
        self._complete_t1_and_review(conflict_env)
        idle = DevAction(action_type=DevActionType.IDLE)
        sync = DevAction(action_type=DevActionType.COMMUNICATE, comm_type=CommunicationType.SYNC_WITH_DEV)

        # Complete T2 and T3 simultaneously → both HAS_CONFLICT
        work_t2 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T2")
        work_t3 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T3")
        for _ in range(3):
            conflict_env.step(Action(dev1_action=work_t2, dev2_action=work_t3))

        state = conflict_env.state()
        assert next(t for t in state.tasks if t.task_id == "T2").status == TaskStatus.HAS_CONFLICT
        assert next(t for t in state.tasks if t.task_id == "T3").status == TaskStatus.HAS_CONFLICT

        # fix_conflict should NOT work before sync
        fix_t3 = DevAction(action_type=DevActionType.FIX_CONFLICT, task_id="T3")
        obs, reward, _, _ = conflict_env.step(Action(dev1_action=fix_t3, dev2_action=idle))
        assert any(k.startswith("dev1_invalid") for k in reward.breakdown)

        # Both devs sync → T2 (higher pri, p1) auto-resolves to IN_REVIEW
        obs, reward, _, _ = conflict_env.step(Action(dev1_action=sync, dev2_action=sync))
        assert "conflict_auto_resolved" in reward.breakdown

        state = conflict_env.state()
        assert next(t for t in state.tasks if t.task_id == "T2").status == TaskStatus.IN_REVIEW
        assert next(t for t in state.tasks if t.task_id == "T3").status == TaskStatus.HAS_CONFLICT

        # Dev2 reviews T2's PR + dev1 fixes T3
        t2_pr = next(pr for pr in state.pr_queue if pr.task_id == "T2")
        fix_t3 = DevAction(action_type=DevActionType.FIX_CONFLICT, task_id="T3")
        review_t2 = DevAction(action_type=DevActionType.REVIEW_PR, pr_id=t2_pr.pr_id)
        conflict_env.step(Action(dev1_action=fix_t3, dev2_action=review_t2))

        state = conflict_env.state()
        assert next(t for t in state.tasks if t.task_id == "T2").status == TaskStatus.DONE
        assert next(t for t in state.tasks if t.task_id == "T3").status == TaskStatus.IN_REVIEW

    def test_sync_prevents_conflict_at_completion(self, conflict_env):
        """Sequencing avoids conflicts — complete one before starting the other."""
        conflict_env.reset("_test_conflict")
        self._complete_t1_and_review(conflict_env)
        idle = DevAction(action_type=DevActionType.IDLE)
        work_t3 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T3")

        # Complete T3 first (T2 not started → no conflict)
        for _ in range(3):
            conflict_env.step(Action(dev1_action=idle, dev2_action=work_t3))
        state = conflict_env.state()
        t3 = next(t for t in state.tasks if t.task_id == "T3")
        assert t3.status == TaskStatus.IN_REVIEW


class TestCommunication:
    def test_pm_clarification_reduces_effort(self, env):
        env.reset("easy")
        ask = DevAction(
            action_type=DevActionType.COMMUNICATE,
            comm_type=CommunicationType.ASK_PM_CLARIFICATION,
            comm_target_task="T2",
        )
        idle = DevAction(action_type=DevActionType.IDLE)
        obs, reward, _, _ = env.step(Action(dev1_action=ask, dev2_action=idle))
        # T2 effort was 3, should now be 2
        t2 = next(t for t in obs.task_board if t.task_id == "T2")
        assert t2.effort_remaining == 2

    def test_clarification_only_once(self, env):
        env.reset("easy")
        ask = DevAction(
            action_type=DevActionType.COMMUNICATE,
            comm_type=CommunicationType.ASK_PM_CLARIFICATION,
            comm_target_task="T2",
        )
        idle = DevAction(action_type=DevActionType.IDLE)
        env.step(Action(dev1_action=ask, dev2_action=idle))
        # Second clarification on same task should be idle
        obs, reward, _, _ = env.step(Action(dev1_action=ask, dev2_action=idle))
        assert any(k.startswith("dev1_invalid") for k in reward.breakdown)


class TestPMEvents:
    def test_medium_priority_change(self, env):
        env.reset("medium")
        idle = DevAction(action_type=DevActionType.IDLE)
        action = Action(dev1_action=idle, dev2_action=idle)
        # Step to step 10 where PM event fires
        for _ in range(10):
            env.step(action)
        obs = env._sim.get_observation()
        t5 = next(t for t in obs.task_board if t.task_id == "T5")
        assert t5.priority == 1

    def test_hard_requirement_change(self, env):
        env.reset("hard")
        idle = DevAction(action_type=DevActionType.IDLE)
        action = Action(dev1_action=idle, dev2_action=idle)
        # Step to step 5 where requirement change fires
        for _ in range(5):
            env.step(action)
        state = env.state()
        t4 = next(t for t in state.tasks if t.task_id == "T4")
        assert t4.effort_remaining == 5  # 3 + 2 increase
        assert t4.effort_total == 5

    def test_hard_new_task_injection(self, env):
        env.reset("hard")
        idle = DevAction(action_type=DevActionType.IDLE)
        action = Action(dev1_action=idle, dev2_action=idle)
        for _ in range(14):
            env.step(action)
        state = env.state()
        task_ids = [t.task_id for t in state.tasks]
        assert "T11" in task_ids


class TestGraders:
    def test_easy_grader_no_work(self, env):
        env.reset("easy")
        idle = DevAction(action_type=DevActionType.IDLE)
        for _ in range(20):
            env.step(Action(dev1_action=idle, dev2_action=idle))
        state = env.state()
        score = grade(state)
        assert score == 0.01  # clamped minimum (strictly > 0)

    def test_easy_grader_bounds(self, env):
        env.reset("easy")
        state = env.state()
        score = grade(state)
        assert 0.0 <= score <= 1.0

    def test_grader_deterministic(self, env):
        """Same actions should produce same grader score."""
        scores = []
        for _ in range(2):
            env.reset("easy")
            work_t1 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")
            work_t2 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T2")
            for _ in range(5):
                env.step(Action(dev1_action=work_t1, dev2_action=work_t2))
            state = env.state()
            scores.append(grade(state))
        assert scores[0] == scores[1]


class TestState:
    def test_state_before_reset(self, env):
        state = env.state()
        assert state.scenario_id == ""

    def test_state_after_reset(self, env):
        env.reset("easy")
        state = env.state()
        assert state.scenario_id == "easy"
        assert len(state.tasks) == 5


class TestSpecialization:
    """Tests for developer specialization mechanic."""

    @pytest.fixture
    def spec_env(self):
        config = ScenarioConfig(
            scenario_id="_test_spec",
            name="Spec Test",
            description="Test specialization",
            difficulty="medium",
            max_steps=20,
            enable_specialization=True,
            dev_specializations={"dev1": [TaskType.BACKEND], "dev2": [TaskType.FRONTEND]},
            tasks=[
                ProjectTask(task_id="T1", title="Backend work", task_type=TaskType.BACKEND,
                            effort_remaining=2, effort_total=2, priority=1),
                ProjectTask(task_id="T2", title="Frontend work", task_type=TaskType.FRONTEND,
                            effort_remaining=2, effort_total=2, priority=2),
                ProjectTask(task_id="T3", title="Test work", task_type=TaskType.TESTING,
                            effort_remaining=2, effort_total=2, priority=3),
            ],
        )
        SCENARIOS["_test_spec"] = config
        env = GitTangleEnv()
        yield env
        del SCENARIOS["_test_spec"]

    def test_specialty_normal_effort(self, spec_env):
        """Dev1 (backend specialist) works on backend task at normal speed."""
        spec_env.reset("_test_spec")
        idle = DevAction(action_type=DevActionType.IDLE)
        work = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")
        spec_env.step(Action(dev1_action=work, dev2_action=idle))
        state = spec_env.state()
        t1 = next(t for t in state.tasks if t.task_id == "T1")
        assert t1.effort_remaining == 1.0  # 2 - 1.0 = 1.0

    def test_non_specialty_half_effort(self, spec_env):
        """Dev2 (frontend specialist) works on backend task at half speed."""
        spec_env.reset("_test_spec")
        idle = DevAction(action_type=DevActionType.IDLE)
        work = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")
        spec_env.step(Action(dev1_action=idle, dev2_action=work))
        state = spec_env.state()
        t1 = next(t for t in state.tasks if t.task_id == "T1")
        assert t1.effort_remaining == 1.5  # 2 - 0.5 = 1.5

    def test_testing_always_neutral(self, spec_env):
        """Testing tasks are always 1.0 effort regardless of specialization."""
        spec_env.reset("_test_spec")
        idle = DevAction(action_type=DevActionType.IDLE)
        work = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T3")
        spec_env.step(Action(dev1_action=work, dev2_action=idle))
        state = spec_env.state()
        t3 = next(t for t in state.tasks if t.task_id == "T3")
        assert t3.effort_remaining == 1.0  # 2 - 1.0

    def test_specialization_disabled(self, env):
        """Without specialization flag, effort is always 1.0."""
        env.reset("easy")
        idle = DevAction(action_type=DevActionType.IDLE)
        work = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")
        env.step(Action(dev1_action=work, dev2_action=idle))
        state = env.state()
        t1 = next(t for t in state.tasks if t.task_id == "T1")
        assert t1.effort_remaining == 1.0  # 2 - 1.0


class TestReviewRejection:
    """Tests for code review rejection mechanic."""

    @pytest.fixture
    def rej_env(self):
        config = ScenarioConfig(
            scenario_id="_test_rej",
            name="Rejection Test",
            description="Test review rejection",
            difficulty="medium",
            max_steps=20,
            enable_review_rejection=True,
            tasks=[
                ProjectTask(task_id="T1", title="Rejectable task", task_type=TaskType.BACKEND,
                            effort_remaining=1, effort_total=1, priority=1,
                            rejection_on_first_review=True),
                ProjectTask(task_id="T2", title="Normal task", task_type=TaskType.FRONTEND,
                            effort_remaining=1, effort_total=1, priority=2),
            ],
        )
        SCENARIOS["_test_rej"] = config
        env = GitTangleEnv()
        yield env
        del SCENARIOS["_test_rej"]

    def test_first_review_rejected(self, rej_env):
        """First review of a flagged task gets rejected."""
        rej_env.reset("_test_rej")
        idle = DevAction(action_type=DevActionType.IDLE)
        work = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")
        rej_env.step(Action(dev1_action=work, dev2_action=idle))  # T1 completes → IN_REVIEW

        state = rej_env.state()
        pr_id = next(pr.pr_id for pr in state.pr_queue if pr.task_id == "T1")
        review = DevAction(action_type=DevActionType.REVIEW_PR, pr_id=pr_id)
        obs, reward, _, _ = rej_env.step(Action(dev1_action=idle, dev2_action=review))

        t1 = next(t for t in obs.task_board if t.task_id == "T1")
        assert t1.status == TaskStatus.IN_PROGRESS  # Rejected, back to work
        assert any(k.startswith("dev2_review_rejected") for k in reward.breakdown)

    def test_rejected_task_has_extra_effort(self, rej_env):
        """After rejection, task gets +1 effort."""
        rej_env.reset("_test_rej")
        idle = DevAction(action_type=DevActionType.IDLE)
        work = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")
        rej_env.step(Action(dev1_action=work, dev2_action=idle))

        state = rej_env.state()
        pr_id = next(pr.pr_id for pr in state.pr_queue if pr.task_id == "T1")
        review = DevAction(action_type=DevActionType.REVIEW_PR, pr_id=pr_id)
        rej_env.step(Action(dev1_action=idle, dev2_action=review))

        state = rej_env.state()
        t1 = next(t for t in state.tasks if t.task_id == "T1")
        assert t1.effort_remaining == 1  # 0 + 1 from rejection

    def test_second_review_succeeds(self, rej_env):
        """Second review of a flagged task succeeds normally."""
        rej_env.reset("_test_rej")
        idle = DevAction(action_type=DevActionType.IDLE)
        work = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")

        # First: work → review (rejected) → rework → review again
        rej_env.step(Action(dev1_action=work, dev2_action=idle))  # Complete
        state = rej_env.state()
        pr_id = next(pr.pr_id for pr in state.pr_queue if pr.task_id == "T1")
        rej_env.step(Action(dev1_action=idle, dev2_action=DevAction(action_type=DevActionType.REVIEW_PR, pr_id=pr_id)))  # Rejected
        rej_env.step(Action(dev1_action=work, dev2_action=idle))  # Rework completes

        state = rej_env.state()
        pr_id = next(pr.pr_id for pr in state.pr_queue if pr.task_id == "T1")
        obs, reward, _, _ = rej_env.step(Action(dev1_action=idle, dev2_action=DevAction(action_type=DevActionType.REVIEW_PR, pr_id=pr_id)))

        t1 = next(t for t in obs.task_board if t.task_id == "T1")
        assert t1.status == TaskStatus.DONE
        assert "dev2_pr_merged" in reward.breakdown


class TestPIP:
    """Tests for Developer PIP mechanic."""

    @pytest.fixture
    def pip_env(self):
        config = ScenarioConfig(
            scenario_id="_test_pip",
            name="PIP Test",
            description="Test PIP mechanic",
            difficulty="hard",
            max_steps=30,
            enable_pip=True,
            pip_conflict_threshold=2,
            pip_idle_threshold=3,
            pip_duration=2,
            tasks=[
                ProjectTask(task_id="T1", title="Task 1", task_type=TaskType.BACKEND,
                            effort_remaining=1, effort_total=1, priority=1),
                ProjectTask(task_id="T2", title="Task 2", task_type=TaskType.FRONTEND,
                            effort_remaining=1, effort_total=1, priority=2),
            ],
        )
        SCENARIOS["_test_pip"] = config
        env = GitTangleEnv()
        yield env
        del SCENARIOS["_test_pip"]

    def test_pip_triggers_on_idle_threshold(self, pip_env):
        """Dev gets PIP'd after too many idle steps."""
        pip_env.reset("_test_pip")
        idle = DevAction(action_type=DevActionType.IDLE)
        work = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")
        # Dev2 idles 3 times (threshold)
        for _ in range(3):
            pip_env.step(Action(dev1_action=work, dev2_action=idle))

        state = pip_env.state()
        assert state.dev2_status.pip_active is True
        assert state.dev2_status.pip_steps_remaining == 2

    def test_pip_forces_idle(self, pip_env):
        """PIP'd dev has all actions forced to idle with pip_penalty."""
        pip_env.reset("_test_pip")
        idle = DevAction(action_type=DevActionType.IDLE)
        work_t1 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")
        work_t2 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T2")

        # Trigger PIP on dev2 via idle
        for _ in range(3):
            pip_env.step(Action(dev1_action=work_t1, dev2_action=idle))

        # Dev2 tries to work but is PIP'd
        obs, reward, _, _ = pip_env.step(Action(dev1_action=idle, dev2_action=work_t2))
        assert "dev2_pip_penalty" in reward.breakdown
        assert obs.dev2_status.current_action == "pip_locked"

    def test_pip_duration(self, pip_env):
        """PIP lasts exactly pip_duration steps."""
        pip_env.reset("_test_pip")
        idle = DevAction(action_type=DevActionType.IDLE)
        work = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")

        # Trigger PIP (3 idles)
        for _ in range(3):
            pip_env.step(Action(dev1_action=work, dev2_action=idle))

        assert pip_env.state().dev2_status.pip_active is True

        # PIP duration = 2 steps
        pip_env.step(Action(dev1_action=idle, dev2_action=idle))  # PIP step 1
        assert pip_env.state().dev2_status.pip_active is True
        pip_env.step(Action(dev1_action=idle, dev2_action=idle))  # PIP step 2
        assert pip_env.state().dev2_status.pip_active is False  # PIP ended

    def test_pip_disabled(self, env):
        """Without PIP flag, no PIP regardless of idle count."""
        env.reset("easy")
        idle = DevAction(action_type=DevActionType.IDLE)
        work = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")
        for _ in range(10):
            env.step(Action(dev1_action=work, dev2_action=idle))
        state = env.state()
        assert state.dev2_status.pip_active is False


class TestMultipleScenarios:
    """Tests for the 15-scenario system."""

    def test_all_scenarios_reset(self, env):
        """All 15 scenarios can be reset without error."""
        for sid in ["easy_1", "easy_2", "easy_3", "easy_4", "easy_5",
                     "medium_1", "medium_2", "medium_3", "medium_4", "medium_5",
                     "hard_1", "hard_2", "hard_3", "hard_4", "hard_5"]:
            obs = env.reset(sid)
            assert len(obs.task_board) > 0
            assert obs.sprint_progress.current_step == 0

    def test_grader_works_for_all(self, env):
        """Grader returns valid score for all scenarios."""
        for sid in ["easy_1", "easy_2", "easy_3", "easy_4", "easy_5",
                     "medium_1", "medium_2", "medium_3", "medium_4", "medium_5",
                     "hard_1", "hard_2", "hard_3", "hard_4", "hard_5"]:
            env.reset(sid)
            state = env.state()
            score = grade(state)
            assert 0.0 <= score <= 1.0

    def test_backward_compat_aliases(self, env):
        """Old scenario IDs still work."""
        for sid in ["easy", "medium", "hard"]:
            obs = env.reset(sid)
            assert len(obs.task_board) > 0

    def test_episode_summary_present(self, env):
        """Reset observation includes episode summary."""
        obs = env.reset("medium_1")
        assert obs.episode_summary is not None
        assert "Feature Pipeline" in obs.episode_summary
        assert "Specialization" in obs.episode_summary
