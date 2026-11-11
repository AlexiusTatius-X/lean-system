# Quality log

One row per quality miss by an agent: caught by the owner, a reviewer, a checker, or CI. The weekly tune-up uses it to set each agent type's model and effort.

| Date | Agent type | Model / effort | What was wrong | Caught by | Should its checks have caught it? | Action |
|---|---|---|---|---|---|---|
| 2026-11-11 | diagrammer | Sonnet 5.5 / medium | Kept the skill's default gateway legend in an unrelated doc and coloured nearly every box the same, so the legend was meaningless. Long return arrows routed around the outside, making two diagrams wide | Owner | Yes: the skill says "the legend must match what you use" | Stepped up to Sonnet high, with 4 written acceptance checks; rebuilt |
| 2026-11-11 | diagrammer (re-run) | Sonnet 5.5 / **medium** (meant to be high) | The step-up to high didn't apply: definitions are read at session start, so the re-run still ran at medium. Its acceptance checks were met by its own report; return arrows are still long-ish | Main chat, from the ledger's effort field | n/a (a system issue) | Rule added: pass `effort` explicitly until a new session; the owner judges the result by eye |
| 2026-11-11 | track-lead (gateway-merges, st11) | Sonnet 5.5 / medium | Started run-locked.sh detached, so the agents were never woken; one didn't know where summaries land | Main chat | Partly: the skill said 'background' but not how | Skill now says: use the tool's run_in_background, never & or nohup, and gives the summary path |
| 2026-11-11 | track-lead (st12) | Sonnet 5.5 / medium | Ran a test suite itself instead of delegating to a builder; its first command ran every project (wasted run) | Self-reported | Yes: the track-lead definition says it coordinates, not runs | Reminded; watch at the tune-up whether leads keep doing work themselves |
