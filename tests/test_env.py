"""Tests for the DevSim environment."""
import pytest
from env.models import Action, DevAction, DevActionType, CommunicationType, TaskStatus
from env.environment import DevSimEnv
from env.graders import grade


@pytest.fixture
def env():
    return DevSimEnv()


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
        assert "dev1_invalid_action_penalty" in reward.breakdown

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
        assert "dev1_invalid_action_penalty" in reward.breakdown

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
        assert "dev1_invalid_action_penalty" in reward.breakdown


class TestConflicts:
    def test_no_conflict_during_simultaneous_work(self, env):
        """T2 and T3 conflict but working simultaneously is fine — conflict only at completion."""
        env.reset("medium")
        idle = DevAction(action_type=DevActionType.IDLE)
        work_t1 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")

        # Complete T1 (effort 3) and review it
        for _ in range(3):
            env.step(Action(dev1_action=work_t1, dev2_action=idle))
        state = env.state()
        pr_id = next(pr.pr_id for pr in state.pr_queue if pr.task_id == "T1")
        review = DevAction(action_type=DevActionType.REVIEW_PR, pr_id=pr_id)
        env.step(Action(dev1_action=idle, dev2_action=review))

        # Work on T2 and T3 simultaneously — should NOT conflict yet
        work_t2 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T2")
        work_t3 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T3")
        obs, reward, _, _ = env.step(Action(dev1_action=work_t2, dev2_action=work_t3))
        assert "conflict_penalty" not in reward.breakdown
        assert len(obs.merge_conflicts) == 0

    def test_conflict_at_completion_time(self, env):
        """Conflict triggers when a task completes while its conflicting task is in progress."""
        env.reset("medium")
        idle = DevAction(action_type=DevActionType.IDLE)
        work_t1 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")

        # Complete T1 and review
        for _ in range(3):
            env.step(Action(dev1_action=work_t1, dev2_action=idle))
        state = env.state()
        pr_id = next(pr.pr_id for pr in state.pr_queue if pr.task_id == "T1")
        env.step(Action(dev1_action=idle, dev2_action=DevAction(action_type=DevActionType.REVIEW_PR, pr_id=pr_id)))

        # Start T3 with dev2 (effort=3, will take a few steps)
        work_t3 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T3")
        env.step(Action(dev1_action=idle, dev2_action=work_t3))  # T3: effort 2 remaining

        # Now complete T2 with dev1 (effort=3). T3 is IN_PROGRESS → conflict on T2 completion
        work_t2 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T2")
        env.step(Action(dev1_action=work_t2, dev2_action=work_t3))  # T2: 2 left, T3: 1 left
        env.step(Action(dev1_action=work_t2, dev2_action=work_t3))  # T2: 1 left, T3 completes (conflict! T2 is in progress)

        # T3 should have conflict since T2 is IN_PROGRESS
        state = env.state()
        t3 = next(t for t in state.tasks if t.task_id == "T3")
        assert t3.status == TaskStatus.HAS_CONFLICT

    def test_simultaneous_completion_both_conflict(self, env):
        """When both devs complete conflicting tasks in the same step, BOTH get HAS_CONFLICT."""
        env.reset("medium")
        idle = DevAction(action_type=DevActionType.IDLE)
        work_t1 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")

        # Complete T1 and review (T2 and T3 depend on T1)
        for _ in range(3):
            env.step(Action(dev1_action=work_t1, dev2_action=idle))
        state = env.state()
        pr_id = next(pr.pr_id for pr in state.pr_queue if pr.task_id == "T1")
        env.step(Action(dev1_action=idle, dev2_action=DevAction(action_type=DevActionType.REVIEW_PR, pr_id=pr_id)))

        # T2 effort=3, T3 effort=3. Work both simultaneously to complete at same step.
        work_t2 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T2")
        work_t3 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T3")
        env.step(Action(dev1_action=work_t2, dev2_action=work_t3))  # T2:2, T3:2
        env.step(Action(dev1_action=work_t2, dev2_action=work_t3))  # T2:1, T3:1
        env.step(Action(dev1_action=work_t2, dev2_action=work_t3))  # Both complete!

        state = env.state()
        t2 = next(t for t in state.tasks if t.task_id == "T2")
        t3 = next(t for t in state.tasks if t.task_id == "T3")
        assert t2.status == TaskStatus.HAS_CONFLICT
        assert t3.status == TaskStatus.HAS_CONFLICT
        # No PRs should exist — both are conflicted
        assert len(state.pr_queue) == 0

    def test_fix_conflict_creates_pr(self, env):
        """Full conflict resolution flow: conflict → sync → fix → review."""
        env.reset("medium")
        idle = DevAction(action_type=DevActionType.IDLE)
        work_t1 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")
        work_t2 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T2")
        work_t3 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T3")
        sync = DevAction(action_type=DevActionType.COMMUNICATE, comm_type=CommunicationType.SYNC_WITH_DEV)

        # Complete T1 and review
        for _ in range(3):
            env.step(Action(dev1_action=work_t1, dev2_action=idle))
        state = env.state()
        pr_id = next(pr.pr_id for pr in state.pr_queue if pr.task_id == "T1")
        env.step(Action(dev1_action=idle, dev2_action=DevAction(action_type=DevActionType.REVIEW_PR, pr_id=pr_id)))

        # Work T2 and T3 simultaneously to completion → both HAS_CONFLICT
        for _ in range(3):
            env.step(Action(dev1_action=work_t2, dev2_action=work_t3))

        state = env.state()
        t2 = next(t for t in state.tasks if t.task_id == "T2")
        t3 = next(t for t in state.tasks if t.task_id == "T3")
        assert t2.status == TaskStatus.HAS_CONFLICT
        assert t3.status == TaskStatus.HAS_CONFLICT

        # fix_conflict should NOT work before sync
        fix_t3 = DevAction(action_type=DevActionType.FIX_CONFLICT, task_id="T3")
        obs, reward, _, _ = env.step(Action(dev1_action=fix_t3, dev2_action=idle))
        assert "dev1_invalid_action_penalty" in reward.breakdown

        # Both devs sync → higher-pri task (T2, p1) auto-resolves to IN_REVIEW
        obs, reward, _, _ = env.step(Action(dev1_action=sync, dev2_action=sync))
        assert "conflict_auto_resolved" in reward.breakdown

        state = env.state()
        t2 = next(t for t in state.tasks if t.task_id == "T2")
        t3 = next(t for t in state.tasks if t.task_id == "T3")
        assert t2.status == TaskStatus.IN_REVIEW  # auto-resolved
        assert t3.status == TaskStatus.HAS_CONFLICT  # still needs fix

        # Now: dev2 reviews T2's PR (dev1 can't self-review) + dev1 fixes T3's conflict
        t2_pr = next(pr for pr in state.pr_queue if pr.task_id == "T2")
        fix_t3 = DevAction(action_type=DevActionType.FIX_CONFLICT, task_id="T3")
        review_t2 = DevAction(action_type=DevActionType.REVIEW_PR, pr_id=t2_pr.pr_id)
        obs, reward, _, _ = env.step(Action(dev1_action=fix_t3, dev2_action=review_t2))

        state = env.state()
        t2 = next(t for t in state.tasks if t.task_id == "T2")
        t3 = next(t for t in state.tasks if t.task_id == "T3")
        assert t2.status == TaskStatus.DONE
        assert t3.status == TaskStatus.IN_REVIEW
        assert len([pr for pr in state.pr_queue if pr.task_id == "T3"]) == 1

    def test_sync_prevents_conflict_at_completion(self, env):
        """Completing a conflicting task without sync = conflict. Sequencing avoids it."""
        env.reset("medium")
        idle = DevAction(action_type=DevActionType.IDLE)
        work_t1 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T1")
        work_t2 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T2")
        work_t3 = DevAction(action_type=DevActionType.WORK_ON_TASK, task_id="T3")

        # Complete T1 and review
        for _ in range(3):
            env.step(Action(dev1_action=work_t1, dev2_action=idle))
        state = env.state()
        pr_id = next(pr.pr_id for pr in state.pr_queue if pr.task_id == "T1")
        env.step(Action(dev1_action=idle, dev2_action=DevAction(action_type=DevActionType.REVIEW_PR, pr_id=pr_id)))

        # Sequencing: complete T3 first (T2 not started yet → no conflict)
        for _ in range(3):
            env.step(Action(dev1_action=idle, dev2_action=work_t3))
        state = env.state()
        t3 = next(t for t in state.tasks if t.task_id == "T3")
        assert t3.status == TaskStatus.IN_REVIEW  # No conflict — T2 wasn't in progress


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
        assert "dev1_invalid_action_penalty" in reward.breakdown


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
        assert score == 0.0

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
