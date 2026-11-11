---
name: lean-agents
description: How to plan, delegate and run agent work at the lowest cost with the same quality. Use whenever you are about to start agents, run tests, wait for anything, or coordinate parallel work; also preloaded by every lean agent type.
---

# Lean agents: the lowest cost at the same quality

The principle: **the lowest cost at the same quality, keeping the parallelism.** Cost is **steps × memory size**, because each step re-reads the agent's whole memory. Thinking is cheap; big memories doing many steps are expensive. The design is in `~/Desktop/Master_Notes/Claude Token Optimization/`.

## Routing: every task to the cheapest type that does it fully
| Task | Type (model, effort) |
|---|---|
| Waiting for the test lock, tests, Docker, Playwright or CI | **A script, never a model**: `run-locked.sh`, `wait-ci.sh` |
| Where something is, who calls it, what a config or doc says | `scout` (Haiku) |
| A merge by rule, a PR prepared, a test re-run, an AWS read or plan, a docs sync | `mechanic` (Sonnet medium) |
| Writing or fixing code, infrastructure or tests | `builder` (Sonnet medium) |
| Checking that listed fixes were made; a factual code answer | `checker` (Sonnet high) |
| Running one track's loop (build → test → review → fix → check) | `track-lead` (Sonnet medium) |
| A design or a fix plan with options; Mermaid diagrams inside a design | `designer` (Opus high) |
| A first review; a review after a logic change; money, security, data loss, live migrations or IAM | `reviewer` (Opus high) |
| A hard trade-off; a root cause unclear after 2 tries; a design that fails a 3rd review round | `thinker` (Opus extra high) |
| Mermaid → Excalidraw | `diagrammer` (Sonnet medium, uses the mermaid-to-excalidraw skill) |
| A lookup of 2–3 quick tool calls, or a message to another chat | Do it yourself; don't start an agent |

## Nesting
- At most: main chat → track lead → worker. Workers start only scouts; scouts start nothing.
- At most 3 leads at once, 3 workers per lead and 3 scouts per job (the owner may raise these).
- Outward steps (push, PR, merge, AWS changes, messages) belong to the main chat only.

## Memory rules (every agent)
1. Start from the track's `STATE.md` (`gateway-evidence/tracks/<track>/STATE.md`), not from history. Never resume an old agent for a new job.
2. One job, then end with a report of 10 lines or fewer. Details go in `STATE.md` or the evidence folder.
3. **How to start a heavy run so you're woken:** call the Bash tool with `run_in_background: true` and the command `~/.claude/lean-system/tools/run-locked.sh <label> <workdir> -- <command>`. **Never use `&`, `nohup` or `setsid`**: a detached run never wakes you, and the track stalls. Its summary is always at `~/Desktop/EtherealLabs_MasterRepo/gateway-evidence/runs/<YYYY-MM-DD>/<label>.summary` (the full log is beside it, `.log`). Several runs: one background call each, or one call chaining them with `&&`.
   Heavy runs (`test:int`, `test:process`, Playwright, db/e2e Jest, mutation runs, `docker compose up`) go only through
   `~/.claude/lean-system/tools/run-locked.sh <label> <workdir> -- <command>` **in the background**. Then end your turn; you are woken once. Read the `.summary`, and if something failed, `grep -n -A30 '<test name>'` the log. **Never read whole logs.**
   **Don't report before your run finishes.** If you started a background run you still need, end your turn **without** your final report. You'll be resumed when it exits. Report only once you have its result. Handing back early leaves the run orphaned.
4. Waiting for CI: `~/.claude/lean-system/tools/wait-ci.sh <owner/repo> <pr>` in the background, then end your turn.
5. **Never poll** (`sleep` loops, a foreground `--watch`, repeated status checks). A hook blocks it.
6. Read sections, not whole files: `grep -n` first, then a line range. Large docs are read by section. Broad searches go to a scout.
7. Targeted tests: run them directly, but trim the output: `… 2>&1 | tail -40`.
8. Rewrite `STATE.md` at each checkpoint: after a commit, a test result or a review.
9. **Before every commit:** the secret scan as its own step, then the commit, with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the owner's rule, whatever model you run on).

## Reviews (quality is never traded for cost)
- First review: a `reviewer` (Opus high), given the code, not the author's conclusions.
- After **every** fix, another round: a `reviewer` if the fix changed logic, a `checker` if it changed only text. Repeat until nothing Critical, High or Medium remains and the tests pass. There is no cap on rounds. If round 3 still finds new problems, a `thinker` checks the design itself.

## Changing an agent type
Claude Code reads agent definitions when a session starts. An edit to a type's model or effort applies only in **new** sessions. Until then, in the current session, pass the new `effort` explicitly when starting that agent, and check the run's recorded effort in the ledger.

## Quality log
When the owner, a reviewer, a checker or CI finds a quality miss by an agent, the main chat adds a row to `~/.claude/lean-system/quality-log.md`: the type, model and effort, what was wrong, who caught it, and whether the agent's own checks should have caught it. The weekly tune-up uses it to set each type's effort (see the `cost-tuneup` skill).

## Escalation
- A builder stuck twice on the same piece → `thinker` (root cause) or Opus high for that piece.
- A scout that comes back thin → `checker` → read it yourself.
- Report every escalation upward.

## STATE.md template
```
# <track>: state            (updated <date time> by <type>)
Goal:
Branch / worktree / head:
Done:
Tests: (last result per suite, with the summary path)
Reviews: (round n: findings by severity, status, file)
Open:
Next step: (exactly one)
Owner decisions needed:
Do not:
```
