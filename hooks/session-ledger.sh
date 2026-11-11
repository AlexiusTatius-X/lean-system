#!/bin/zsh
# SessionStart hook: refresh the cost ledger once a day and add a short note to the session.
# Never blocks or fails the session.
setopt NULL_GLOB
L=$HOME/.claude/lean-system
y=$(TZ=Asia/Kolkata date -v-1d +%Y-%m-%d); t=$(TZ=Asia/Kolkata date +%Y-%m-%d)
if [ ! -f "$L/ledger/$y.md" ]; then
  perl -e 'alarm 25; exec @ARGV' python3 -I "$L/tools/cost-ledger.py" "$y" >/dev/null 2>&1
fi
[ -f "$L/ledger/$y.md" ] && echo "Lean system: yesterday's cost ledger is at $L/ledger/$y.md ($(sed -n 3p "$L/ledger/$y.md" | tr -d '*'))."
last=$(ls -t "$L"/tuneups/*.md 2>/dev/null | head -1)
if [ -z "$last" ] || [ -n "$(find "$last" -mtime +7 2>/dev/null)" ]; then
  echo "Lean system: a weekly cost tune-up is due (cost-tuneup skill); offer it to the owner once."
fi
exit 0
