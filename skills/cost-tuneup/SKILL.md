---
name: cost-tuneup
description: The weekly review that makes the lean agent system cheaper without lowering quality. Use when asked for a "cost tune-up", "weekly tune-up", "token review", or when the main chat's weekly reminder says it's due.
---

# Weekly cost tune-up

Run it as one `designer`-class job (Opus high). The input is small, so never read raw transcripts.

## Inputs (only these)
1. Refresh the ledger: `python3 ~/.claude/lean-system/tools/cost-ledger.py <each day of the week>`.
2. Read the week's `~/.claude/lean-system/ledger/<date>.md` files: the totals, the type and step-kind tables, and the waste lists.
3. `~/.claude/lean-system/experiments.md`: what was tried and its result. Also `quality-log.md`: every quality miss, by agent type.
4. The quality signals from `gateway-evidence/tracks/*/STATE.md` "Reviews:" lines: findings by severity, rounds, escalations and CI failures.

## Output: `~/.claude/lean-system/tuneups/<date>.md`
- **First, and required every time: the effort calibration table.** This is the loop's main job: the cheapest model and effort per agent type that still meets the quality bar. One row per agent type:

  | Type | Current rung (model / effort) | Jobs this week | Quality misses (from quality-log.md) | Cost per finished job (incl. rework) | Decision: hold / step up / trial a step down | Why |

  Apply the rules under "Effort calibration" below. A type with no jobs this week holds.
- **The week in numbers:** the total, the trend against last week, the top 3 cost drivers, and the waiting share.
- **Quality check:** did review findings, rounds, escalations or CI failures rise? If a change made last week worsened quality, propose reverting it, first.
- **Proposals:** at most 5, ranked by expected saving. Each states:
  - the change (to an agent type, skill, hook, script or routing rule);
  - the evidence (the ledger lines);
  - the expected saving in $ and %;
  - the risk to quality;
  - how it will be measured;
  - how to revert it.

  Look for:
  - repeated waste patterns;
  - a type's work that a cheaper type could do, or that is failing and needs a stronger one;
  - big reads that a scout or a narrower tool could replace (for example, reading a whole Slack channel instead of searching one thread);
  - idle cost;
  - memory peaks over 300k.
- **New ideas:** anything outside the current design worth trying, labelled as an experiment.

## Effort calibration (every tune-up)
For each agent type, decide its model and effort from evidence: `quality-log.md` (misses), the ledger (cost per job), and `STATE.md` review results.

**The ladder, cheapest first:** Haiku → Sonnet low → Sonnet medium → Sonnet high → Sonnet extra high → Opus high → Opus extra high.

- **Step up one rung** when a type has 2 or more quality misses in a week, or 1 owner-caught miss that its own acceptance checks should have caught. First add or sharpen the check that would have caught it. If that check already existed and was skipped, step up.
- **Step down one rung, as a trial,** when a type has had 0 misses over at least 10 jobs in 2 weeks. Trial it on part of the work, compare misses and cost per job, then keep or revert at the next tune-up.
- **Judge by cost per finished job, including rework.** A cheap rung that needs a redo isn't cheaper.
- **Never step down** the reviewer or the thinker without a thinker's check of that proposal.
- Record every change in `experiments.md` and every miss in `quality-log.md`.

## Rules
- One change at a time per area, so each effect can be measured.
- **Never propose cheaper reviews of logic, security or money without a thinker's check** of that proposal.
- The owner approves each change. The main chat applies it as one commit in `~/.claude/lean-system` and adds a row to `experiments.md` (date, change, expected effect, then the measured effect next week, and kept or reverted).
- Monthly: also review the whole design in `~/Desktop/Master_Notes/Claude Token Optimization/` with fresh eyes, and propose structural changes.
