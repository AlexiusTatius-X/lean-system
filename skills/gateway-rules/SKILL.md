---
name: gateway-rules
description: The owner's standing rules for the EtherealLabs repos (the tokitoki-provider-gateway AI gateway, Filmcity tokitoki-production, Studio tokitoki-studio): security, tests, commits, merges and docs. Preloaded by agents working on these repos; read it before touching them.
---

# EtherealLabs rules

**The repos:**
- gateway: `~/Desktop/EtherealLabs_MasterRepo/tokitoki-provider-gateway`, branch `master`, us-east-1;
- Filmcity: `tokitoki-production`, branches `env-dev` and `master`, ap-south-1;
- Studio: `tokitoki-studio`.

Work in worktrees under `~/Desktop/EtherealLabs_MasterRepo/gateway-tracks/`, never in the owner's checkouts. Evidence goes to `~/Desktop/EtherealLabs_MasterRepo/gateway-evidence/<date>/`, never only to `/tmp`.

## Security (absolute)
- Never print a key or secret. Never read, grep, print or copy any `.env` file, `apps/gateway/config/local.env`, `apps/dashboard/config/local.env`, `*.override.env` or `terraform.tfvars`. Running the repo's own test commands, which load `local.env` themselves, is allowed; writing code that loads it is not.
- Never read `~/.aws/credentials` or `~/.aws/sso/cache`. Never run `aws configure get` or `export-credentials`. Never put an AWS account id in a committed file.
- Keep real owner emails, AWS usernames, Slack ids and Google ids out of the repos.
- **Needs the owner's explicit yes each time, and only the main chat does it:** creating anything in AWS (plan → show → yes → apply), pushing, opening or merging PRs, publishing packages, messaging anyone. Slack is read-only. Commit only when the brief says to.
- Before every commit or push, run the secret scan as its own step, read its result, and use word-boundary regexes for key, token and secret shapes, AWS account ids and emails.

## Tests
- Node 24: `export PATH=~/.local/node-v24.22.1-darwin-arm64/bin:$PATH`. Docker via Colima (`run-locked.sh` starts it). Terraform at `~/.local/bin/terraform`.
- **Full unit suite:** `npx jest --selectProjects unit`, leaving out `placeholder-register.spec.ts` explicitly. **Never put a file path after `--selectProjects`**: it is read as a project name and runs everything.
- **Targeted tests:** `npx jest <paths>` (check with `--listTests`; use `--runTestsByPath` for bracketed paths). For db specs, the path comes first and `--selectProjects db` last.
- **Heavy suites** (`test:int`, `test:process`, Playwright, db/e2e projects, mutation runs) run only through `run-locked.sh`, one at a time, in the background.
- Known flakes: `race/live.spec` R13, R14 and R20; `call-counts.spec` (the lock race); `usage-reports.spec` "reads 31 days…" (planner statistics). See `gateway-evidence/2026-11-11/merge-coordinator/known-flakes.md`. Re-run before concluding.
- Compose harnesses go in private folders, never `/opt/filmcity`.

## Git, merges, migrations
- Commit author: `AlexiusTatius-X <225477969+AlexiusTatius-X@users.noreply.github.com>`. The message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. PR bodies end with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- Squash merges. Stacked branches merge master after a squash; never rewrite history.
- **Merge proof:** after merging master into a branch, `git diff <branch's pre-merge head> HEAD` must list only files master changed. git can silently revert deliberate changes (it happened on ST5 and ST8).
  - Take the branch's side of a code conflict only if master's copy of that file equals the parent head's.
  - Otherwise stop and report.
- Migrations are never merged by git. Use `gateway-build/merge_migrations.py`, numbered by merge order: 0034 ST4, 0035 ST7, 0036 ST9.
- Avoid unnecessary CI runs.

## Docs
- Notes twins under `~/Desktop/Master_Notes/1_T Internal_AI_Usage/` ("Gateway Repo Docs/", "Gateway Low-Level Design/", "Finalized Gateway Service Design/") stay in sync with the repo docs, both ways. Apply diffs; never copy a whole file over a twin.
- Excalidraw only through the `mermaid-to-excalidraw` skill (the `diagrammer` agent), never the Excalidraw MCP server.
- Write in plain words, with short sections and tables. Name the owner's open questions one at a time, each with a recommendation.
