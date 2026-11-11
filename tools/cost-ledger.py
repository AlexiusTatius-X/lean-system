#!/usr/bin/env python3
"""Daily cost ledger for Claude Code work. Reads transcripts only; uses no model.

Usage: cost-ledger.py [YYYY-MM-DD ...] [--ci]   (default: yesterday and today, IST)
--ci also adds a "## GitHub Actions" section (via gh, at most ~30 s) and appends ledger/ci.csv.
Writes ~/.claude/lean-system/ledger/<date>.md and appends to ledger.csv.
Prices are API list rates per million tokens (input, output, cache read); a cache write is 1.25x input.
"""
import csv, datetime as dt, glob, json, math, os, re, subprocess, sys, time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

HOME = os.path.expanduser('~')
PROJECTS = os.path.join(HOME, '.claude', 'projects')
OUT = os.path.join(HOME, '.claude', 'lean-system', 'ledger')
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
CI_ORG, CI_REPOS, CI_BUDGET = 'ethereallabsdev', ['tokitoki-provider-gateway', 'tokitoki-production'], 28
PRICES = {'opus-5-5': (4, 20, 0.20), 'opus-5': (5, 25, 0.50), 'sonnet-5-5': (2, 10, 0.10), 'sonnet-5': (2, 10, 0.20),
          'haiku-5-5': (0.10, 0.50, 0.01), 'fable-5-2': (8, 40, 0.20), 'fable-5-1': (10, 50, 1.0)}


def price(model):
    m = (model or '').replace('claude-', '')
    for k in sorted(PRICES, key=len, reverse=True):
        if m.startswith(k):
            return PRICES[k]
    return PRICES['opus-5-5']


def step_kind(name, inp):
    if name in ('Edit', 'Write', 'NotebookEdit'):
        return 'edit'
    if name in ('Read', 'Grep', 'Glob', 'WebFetch', 'WebSearch'):
        return 'read'
    if name in ('Agent', 'SendMessage', 'TaskStop', 'Skill', 'ToolSearch'):
        return 'coordinate'
    if name == 'Monitor':
        return 'wait'
    if name != 'Bash':
        return 'other'
    c = inp.get('command', '') if isinstance(inp, dict) else ''
    if not inp.get('run_in_background') and re.search(r'\bsleep\s+\d|until |while :|--watch|pgrep|locks/heavy|\.(out|log|summary)\b', c):
        return 'wait'
    if re.search(r'jest|npm (run )?test|playwright|test:int|test:process|run-locked|mutation|tsc|lint|terraform (validate|test)', c):
        return 'test'
    if re.search(r'gh (pr|run)|git (push|commit|merge|checkout|worktree|fetch|add)', c):
        return 'git'
    return 'read'


def load(path, main):
    """Return (agent_type, effort, model, steps); each step: (day, cost, kind, ctx, out_tokens, tool_name, tool_input)."""
    msgs, meta = {}, {'type': 'main chat' if main else None, 'effort': None, 'model': None}
    results = Counter()
    for line in open(path, errors='ignore'):
        try:
            o = json.loads(line)
        except Exception:
            continue
        if not isinstance(o, dict):
            continue
        if o.get('type') == 'user':
            c = (o.get('message') or {}).get('content') if isinstance(o.get('message'), dict) else None
            if isinstance(c, list):
                for b in c:
                    if isinstance(b, dict) and b.get('type') == 'tool_result':
                        cc = b.get('content')
                        n = len(cc) if isinstance(cc, str) else sum(len(x.get('text', '') or '') for x in cc or [] if isinstance(x, dict))
                        results[b.get('tool_use_id')] = n // 4
            continue
        if o.get('type') != 'assistant' or (main and o.get('isSidechain')):
            continue
        m = o.get('message') or {}
        if not isinstance(m, dict) or not m.get('usage'):
            continue
        if not main and o.get('attributionAgent'):
            meta['type'] = o['attributionAgent']
        meta['effort'] = o.get('effort') or meta['effort']
        e = msgs.setdefault(m.get('id') or id(o), {'u': None, 'c': [], 'ts': o.get('timestamp'), 'model': m.get('model')})
        e['u'] = m['usage']
        e['c'].extend(m.get('content') or [])
    steps = []
    for e in msgs.values():
        u, ts = e['u'], e['ts']
        if not ts:
            continue
        meta['model'] = e['model'] or meta['model']
        i, o_, r = price(e['model'])
        cr, cw = u.get('cache_read_input_tokens', 0) or 0, u.get('cache_creation_input_tokens', 0) or 0
        inp, out = u.get('input_tokens', 0) or 0, u.get('output_tokens', 0) or 0
        cost = inp / 1e6 * i + out / 1e6 * o_ + cr / 1e6 * r + cw / 1e6 * i * 1.25
        tools = [b for b in e['c'] if isinstance(b, dict) and b.get('type') == 'tool_use']
        name = tools[0].get('name') if tools else None
        tinp = tools[0].get('input') or {} if tools else {}
        kind = step_kind(name, tinp) if tools else 'think'
        big = max((results.get(t.get('id'), 0) for t in tools), default=0)
        day = dt.datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(IST).strftime('%Y-%m-%d')
        steps.append((day, cost, kind, cr + cw + inp, big, name, tinp))
    return meta, steps


def gh(path, deadline):
    left = deadline - time.time()
    if left <= 1:
        raise TimeoutError('time budget used')
    r = subprocess.run(['gh', 'api', path], capture_output=True, text=True, timeout=left)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:200])
    return json.loads(r.stdout)


def parse_ts(v):
    return dt.datetime.fromisoformat(v.replace('Z', '+00:00')) if v else None


def ci_collect(day, deadline):
    start = dt.datetime.fromisoformat(day).replace(tzinfo=IST).astimezone(dt.timezone.utc)
    rng = f"{start:%Y-%m-%dT%H:%M:%SZ}..{start + dt.timedelta(days=1) - dt.timedelta(seconds=1):%Y-%m-%dT%H:%M:%SZ}"
    out = {}
    for repo in CI_REPOS:
        base = f"repos/{CI_ORG}/{repo}/actions"
        runs, page = [], 1
        while True:
            d = gh(f"{base}/runs?created={rng}&per_page=100&page={page}", deadline)
            runs += d.get('workflow_runs', [])
            if len(d.get('workflow_runs', [])) < 100:
                break
            page += 1

        def jobs_of(run):
            got, pg = [], 1
            while True:
                d = gh(f"{base}/runs/{run['id']}/jobs?filter=all&per_page=100&page={pg}", deadline)
                got += d.get('jobs', [])
                if len(d.get('jobs', [])) < 100:
                    return got
                pg += 1
        with ThreadPoolExecutor(8) as ex:
            job_lists = list(ex.map(jobs_of, runs))
        out[repo] = (runs, job_lists)
    return out


def ci_section(day, deadline):
    """Returns (markdown lines, csv rows). Never raises."""
    try:
        data = ci_collect(day, deadline)
        refused, top = [], []
        per_wf, tot = defaultdict(lambda: [0, 0, 0]), {}
        for repo, (runs, job_lists) in data.items():
            jobs_n = mins = 0
            for run, jobs in zip(runs, job_lists):
                wf = (run.get('name') or '?', run.get('event') or '?')
                per_wf[wf][0] += 1
                for j in jobs:
                    if j.get('conclusion') == 'skipped':
                        continue
                    a, b = parse_ts(j.get('started_at')), parse_ts(j.get('completed_at'))
                    m = math.ceil(max((b - a).total_seconds(), 0) / 60) if a and b else 0
                    jobs_n += 1
                    mins += m
                    per_wf[wf][1] += 1
                    per_wf[wf][2] += m
                    top.append((m, repo, run.get('name'), j.get('name')))
                    if j.get('conclusion') == 'failure' and not any(s.get('conclusion') for s in j.get('steps') or []):
                        why = 'no steps run'
                        try:
                            ann = gh(f"repos/{CI_ORG}/{repo}/check-runs/{j['id']}/annotations", deadline)
                            hit = [x.get('message', '') for x in ann if re.search(r'payment|spending limit', x.get('message', ''), re.I)]
                            if hit:
                                why = hit[0][:110]
                        except Exception:
                            pass
                        refused.append(f"{repo}: {run.get('name')} / {j.get('name')} (run {run['id']}): {why}")
            tot[repo] = (len(runs), jobs_n, mins)
        lines = ["", "## GitHub Actions (billed minutes: each job rounded up, skipped jobs excluded)",
                 "| Repo | Runs | Jobs | Minutes |", "|---|---|---|---|"]
        lines += [f"| {r} | {a} | {b} | {c} |" for r, (a, b, c) in tot.items()]
        lines += ["", "| Workflow | Event | Runs | Jobs | Minutes |", "|---|---|---|---|---|"]
        lines += [f"| {w} | {e} | {v[0]} | {v[1]} | {v[2]} |" for (w, e), v in sorted(per_wf.items(), key=lambda kv: -kv[1][2])]
        lines += ["", "Top 5 jobs by minutes:"]
        lines += [f"- {m} min: {r} / {w} / {n}" for m, r, w, n in sorted(top, key=lambda t: -t[0])[:5]] or ["- none"]
        lines += ["", "Runs GitHub refused to start:"] + ([f"- {x}" for x in refused] or ["- none"])
        return lines, [[day, r, a, b, c] for r, (a, b, c) in tot.items()]
    except Exception as e:
        why = 'gh not installed' if isinstance(e, FileNotFoundError) else 'over the time budget' if isinstance(e, (TimeoutError, subprocess.TimeoutExpired)) else 'gh failed (not logged in or offline?)'
        return ["", "## GitHub Actions", f"CI usage wasn't available for {day}: {why}."], None


def add_ci(day, deadline):
    lines, rows = ci_section(day, deadline)
    path = os.path.join(OUT, f"{day}.md")
    old = open(path).read() if os.path.exists(path) else f"# Cost ledger {day} (API list rates)\n\nNo token usage found.\n"
    old = re.split(r'\n## GitHub Actions', old)[0].rstrip('\n') + '\n'
    open(path, 'w').write(old + "\n".join(lines) + "\n")
    if rows:
        cp = os.path.join(OUT, 'ci.csv')
        keep = []
        if os.path.exists(cp):
            keep = [r for r in csv.reader(open(cp)) if r and r[0] != day and r[0] != 'day']
        with open(cp, 'w', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['day', 'repo', 'runs', 'jobs', 'minutes'])
            w.writerows(keep + rows)


def main():
    today = dt.datetime.now(IST).date()
    args = [a for a in sys.argv[1:] if a != '--ci']
    ci = '--ci' in sys.argv[1:]
    days = args or [str(today - dt.timedelta(days=1)), str(today)]
    os.makedirs(OUT, exist_ok=True)
    runs = []  # (day, project, session, agent file, meta, steps for day)
    cutoff = min(dt.date.fromisoformat(d) for d in days) - dt.timedelta(days=1)
    for proj in glob.glob(os.path.join(PROJECTS, '*')):
        for path in glob.glob(os.path.join(proj, '*.jsonl')) + glob.glob(os.path.join(proj, '*', 'subagents', '*.jsonl')):
            if dt.date.fromtimestamp(os.path.getmtime(path)) < cutoff:
                continue
            main_chat = '/subagents/' not in path
            meta, steps = load(path, main_chat)
            for d in days:
                s = [x for x in steps if x[0] == d]
                if s:
                    runs.append((d, os.path.basename(proj), path, meta, s))
    for d in days:
        rows = [r for r in runs if r[0] == d]
        if not rows:
            continue
        total = sum(x[1] for r in rows for x in r[4])
        by_type, by_kind, by_model = defaultdict(float), defaultdict(float), defaultdict(float)
        waste = []
        agent_rows = []
        for _, proj, path, meta, s in rows:
            c = sum(x[1] for x in s)
            label = f"{meta['type'] or '?'} / {(meta['model'] or '?').replace('claude-', '')} / {meta['effort'] or '?'}"
            by_type[label] += c
            by_model[(meta['model'] or '?').replace('claude-', '')] += c
            for x in s:
                by_kind[x[2]] += x[1]
            peak = max(x[3] for x in s)
            waits = sum(x[1] for x in s if x[2] == 'wait')
            reads = Counter((x[6] or {}).get('file_path') for x in s if x[5] == 'Read' and (x[6] or {}).get('file_path'))
            agent_rows.append((c, label, len(s), peak, waits, os.path.basename(path)))
            if peak > 300_000:
                waste.append((c, f"memory peaked at {peak // 1000}k: {label} ({os.path.basename(path)})"))
            if waits > 1:
                waste.append((waits, f"${waits:.2f} spent waiting: {label} ({os.path.basename(path)})"))
            for fp, n in reads.items():
                if n >= 3:
                    waste.append((n * 0.05, f"{os.path.basename(fp)} read {n} times by one {meta['type']} agent"))
            for x in s:
                if x[4] > 20_000:
                    waste.append((x[4] / 1e6 * 5, f"one {x[5]} output of ~{x[4] // 1000}k tokens: {label}"))
        lines = [f"# Cost ledger {d} (API list rates)", "",
                 f"**Total ~${total:.0f}** over {sum(len(r[4]) for r in rows)} steps; main chat ~${sum(sum(x[1] for x in r[4]) for r in rows if r[3]['type'] == 'main chat'):.0f}.", "",
                 "## By agent type / model / effort", "| Type | Cost | Share |", "|---|---|---|"]
        lines += [f"| {k} | ${v:.2f} | {100 * v / total:.0f}% |" for k, v in sorted(by_type.items(), key=lambda kv: -kv[1])]
        lines += ["", "## By step kind", "| Kind | Cost | Share |", "|---|---|---|"]
        lines += [f"| {k} | ${v:.2f} | {100 * v / total:.0f}% |" for k, v in sorted(by_kind.items(), key=lambda kv: -kv[1])]
        lines += ["", "## Top 10 runs", "| Cost | Type | Steps | Peak memory | Waiting | Transcript |", "|---|---|---|---|---|---|"]
        lines += [f"| ${c:.2f} | {lab} | {n} | {p // 1000}k | ${w:.2f} | {f} |" for c, lab, n, p, w, f in sorted(agent_rows, reverse=True)[:10]]
        lines += ["", "## Waste list (biggest first)"]
        lines += [f"- {t}" for _, t in sorted(waste, reverse=True)[:15]] or ["- none"]
        open(os.path.join(OUT, f"{d}.md"), 'w').write("\n".join(lines) + "\n")
        new = not os.path.exists(os.path.join(OUT, 'ledger.csv'))
        with open(os.path.join(OUT, 'ledger.csv'), 'a', newline='') as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(['day', 'type_model_effort', 'cost'])
            for k, v in by_type.items():
                w.writerow([d, k, f"{v:.4f}"])
        top = ", ".join(f"{k.split(' / ')[0]} ${v:.0f}" for k, v in sorted(by_type.items(), key=lambda kv: -kv[1])[:3])
        print(f"Cost {d}: ~${total:.0f} (waiting {100 * by_kind.get('wait', 0) / total:.0f}%; top: {top}). Ledger: {os.path.join(OUT, d + '.md')}")
    if ci:
        deadline = time.time() + CI_BUDGET
        for d in days:
            add_ci(d, deadline)


if __name__ == '__main__':
    main()
