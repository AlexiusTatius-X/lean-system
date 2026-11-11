#!/usr/bin/env python3
"""PreToolUse hook on Bash and Read: no polling, heavy runs only through run-locked.sh, no whole logs into memory,
read-only agent types stay read-only. Fails open: on any error it allows the call."""
import json, os, re, sys

RUN = '~/.claude/lean-system/tools/run-locked.sh'
HEAVY = [r'npm run test:(int|process|playwright|e2e)\b', r'\bplaywright test\b',
         r'--selectProjects[^|;&]*\b(db|e2e|process|dashboard-gateway)\b', r'\bdocker[ -]compose (.* )?up\b']
POLL = [r'\bsleep\s+(\d+)', r'\buntil\b[^\n]*;\s*do\b', r'\bwhile\b[^\n]*\bsleep\b', r'--watch\b']
READ_ONLY = {'scout'}
NO_GIT_WRITES = {'scout', 'reviewer', 'checker', 'thinker'}


def deny(reason):
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                                             'permissionDecisionReason': reason}}))
    sys.exit(0)


def lines(path):
    try:
        with open(os.path.expanduser(path), 'rb') as fh:
            return sum(1 for _ in fh)
    except Exception:
        return 0


try:
    data = json.load(sys.stdin)
    tool, ti, who = data.get('tool_name'), data.get('tool_input') or {}, data.get('agent_type')
    if tool == 'Read':
        p = ti.get('file_path', '')
        if p.endswith('.log') and not ti.get('limit') and lines(p) > 200:
            deny(f"{os.path.basename(p)} has {lines(p)} lines. Read its .summary, or grep the failing test: grep -n -A30 '<test name>' {p}")
        sys.exit(0)
    if tool != 'Bash':
        sys.exit(0)
    cmd = ti.get('command', '')
    bg = bool(ti.get('run_in_background'))
    if not bg:
        for pat in POLL:
            m = re.search(pat, cmd)
            if m and not (pat.startswith(r'\bsleep') and int(m.group(1)) <= 5):
                deny("Don't wait in the foreground: every check re-reads your whole memory. Start the wait in the background "
                     f"(run_in_background), e.g. {RUN} or ~/.claude/lean-system/tools/wait-ci.sh <repo> <pr>, then end your turn; you'll be woken once.")
    if 'run-locked.sh' not in cmd and not os.environ.get('LEAN_LOCKED'):
        for pat in HEAVY:
            if re.search(pat, cmd):
                deny(f"Heavy runs go through the queue, one at a time, with the log kept in a file: "
                     f"{RUN} <label> <workdir> -- <command>, in the background. Then end your turn and read the .summary when woken.")
    m = re.search(r'\b(cat|less|more)\s+([^\s|;&]+\.log)\b', cmd)
    if m and lines(m.group(2)) > 200:
        deny(f"Don't print a whole log into memory ({lines(m.group(2))} lines). Read the .summary, or grep -n -A30 '<test name>' {m.group(2)}")
    if who in READ_ONLY and re.search(r'(\bsed\s+-i\b|\bperl\s+-i\b|\btee\b|\brm\s|\bmv\s|>\s*[^&/\s]|git (commit|push|merge|reset|checkout|rebase|add)\b)', cmd):
        deny("Scouts are read-only. Report the answer instead of changing anything.")
    if who in NO_GIT_WRITES and re.search(r'\bgit (commit|push|merge|reset|rebase|checkout\s+--)\b|\bsed\s+-i\b', cmd):
        deny(f"A {who} doesn't change the repo. Report the finding; a builder or mechanic makes the change.")
except SystemExit:
    raise
except Exception:
    pass
sys.exit(0)
