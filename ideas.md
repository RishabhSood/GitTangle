# DevSim — Enhancement Ideas

## 1. Developer PIP (Performance Improvement Plan)
If a dev causes 3+ conflicts or accumulates 5+ idle steps, they get "PIP'd" — locked out for 2 steps. The agent must run on a single dev and triage harder.
- Very real-world (underperforming team members get sidelined)
- Creates interesting recovery dynamics
- Natural difficulty escalation
- Could add a "redemption" mechanic: after PIP, dev comes back with a small productivity boost

## 2. Rollback / Revert
A task that was "DONE" gets reverted due to a bug found — effort partially restored, back to IN_PROGRESS. Triggered as a PM event.
- Extremely realistic (prod bugs, failed QA)
- Forces re-prioritization mid-sprint
- Example PM event: "Bug found in T2, reverting to IN_PROGRESS, effort +1"

## 3. Code Review Rejection
When a dev reviews a PR, the review may find issues (deterministic, based on task type/complexity). Instead of DONE, task goes back to IN_PROGRESS with +1 effort.
- Teaches the agent that rushing = rework
- Adds a quality vs speed tradeoff
- Could tie into tech debt mechanic

## 4. Developer Specialization
Dev1 is a backend specialist, dev2 is frontend. Working on your specialty = normal effort. Working outside specialty = effort counts as 0.5 (takes 2 steps per unit).
- Forces smarter task assignment
- Creates interesting tradeoffs when one dev is idle and the other is overloaded
- Very realistic team dynamic

## 5. Standup Meeting
Every N steps (e.g. every 5), both devs must `communicate(sync_with_dev)` or incur a penalty. Simulates mandatory standup overhead.
- Realistic process overhead
- Forces the agent to budget communication steps
- Syncing during standup could also prevent conflicts for the next N steps

## 6. Tech Debt
Completing tasks without PR review (if we add that option) or rushing creates "tech debt" counter. At a threshold, ALL remaining tasks get +1 effort.
- Teaches balancing speed vs quality
- Adds a long-term consequence to greedy short-term play
- Very real-world engineering dynamic

## 7. Reset to Checkpoint / State Rollback
Agent can choose to "revert codebase to step X state" — tasks reset to their state at step X, but a time penalty is incurred (lose N steps from max). Rewards accumulated since step X are lost.
- Interesting "undo" mechanic
- Adds a risk/reward decision: do I revert and lose progress to fix a bad path?
- Could be limited to 1 revert per episode

## 8. Sick Day / Dev Unavailable
At a random (but seeded/deterministic) step, one dev becomes unavailable for 2-3 steps. The agent must adapt on the fly.
- Realistic (people get sick, have emergencies)
- Tests adaptability
- Different from PIP because it's not the agent's fault

## 9. Cross-team Dependency
Some tasks depend on an "external team" delivery that arrives at a fixed step. Until then, those tasks are blocked by something outside the agent's control.
- Very realistic in larger orgs
- Forces the agent to plan around external constraints
- Agent can "communicate" to try to expedite (small chance of early delivery)

## 10. Sprint Demo Pressure
Final 3 steps have a multiplier on high-priority task completion (demo to stakeholders). Encourages saving impressive work for the end — or risks running out of time.
- Creates interesting pacing decisions
- Realistic sprint demo dynamics

---

## Suggested Combinations per Difficulty

**Easy**: Keep as-is (simple, independent tasks)

**Medium**: Add Developer Specialization + Code Review Rejection

**Hard**: Add PIP + Rollback/Revert + Sick Day

**Nightmare (stretch goal?)**: All mechanics active, tight deadline, PM chaos
