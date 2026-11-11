#!/usr/bin/env python3
"""PreToolUse hook on the Agent tool: only lean agent types, with fixed models, under the nesting rules.
Fails open: on any error it allows the call."""
import json, sys

LEAN = {'thinker', 'designer', 'reviewer', 'checker', 'builder', 'mechanic', 'track-lead', 'scout', 'diagrammer'}
BUILTIN_OK = {'web-fetch', 'claude-code-guide', 'statusline-setup'}
WORKERS = {'thinker', 'designer', 'reviewer', 'checker', 'builder', 'mechanic', 'diagrammer'}


def deny(reason):
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                                             'permissionDecisionReason': reason}}))
    sys.exit(0)


try:
    data = json.load(sys.stdin)
    if data.get('tool_name') != 'Agent':
        sys.exit(0)
    ti = data.get('tool_input') or {}
    want = ti.get('subagent_type') or 'general-purpose'
    caller = data.get('agent_type')  # set only when the call comes from inside an agent
    guide = "See the lean-agents skill: thinker, designer, reviewer, checker, builder, mechanic, track-lead, scout or diagrammer."
    if want not in LEAN | BUILTIN_OK:
        deny(f"'{want}' agents aren't allowed (they run on an expensive model with no limits). Pick the lean type for this task. {guide}")
    if want in LEAN and ti.get('model'):
        deny(f"Don't override the model: '{want}' has its model and effort fixed in its definition. If the task needs a stronger model, pick a stronger type (e.g. thinker or reviewer).")
    if want in BUILTIN_OK and (ti.get('model') or 'haiku') not in ('haiku', 'sonnet'):
        deny(f"Run '{want}' on haiku or sonnet, not {ti.get('model')}.")
    if caller == 'scout':
        deny("Scouts don't start other agents. Return what you found.")
    if caller in WORKERS and want != 'scout':
        deny(f"A {caller} may only start scouts. Report back to your track lead or the main chat so they can start a '{want}'.")
    if caller == 'track-lead' and want == 'track-lead':
        deny("Track leads don't start other track leads. Report to the main chat.")
except SystemExit:
    raise
except Exception:
    pass
sys.exit(0)
