# Quality log

One row per quality miss by an agent: caught by the owner, a reviewer, a checker, or CI. The weekly tune-up uses it to set each agent type's model and effort.

| Date | Agent type | Model / effort | What was wrong | Caught by | Should its checks have caught it? | Action |
|---|---|---|---|---|---|---|
| 2026-11-11 | diagrammer | Sonnet 5.5 / medium | Kept the skill's default gateway legend in an unrelated doc and coloured nearly every box the same, so the legend was meaningless. Long return arrows routed around the outside, making two diagrams wide | Owner | Yes: the skill says "the legend must match what you use" | Stepped up to Sonnet high, with 4 written acceptance checks; rebuilt |
