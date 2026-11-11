#!/bin/zsh
# Runs a heavy local command one at a time, with no model watching.
# Usage: run-locked.sh <label> <workdir> -- <command…>
# Run it in the background and end the turn; its exit wakes the agent once.
# The full log stays in a file; agents read only <label>.summary.
set -u
if [ $# -lt 4 ] || [ "$3" != "--" ]; then
  echo "usage: run-locked.sh <label> <workdir> -- <command…>" >&2; exit 64
fi
label=$1; workdir=$2; shift 3
EV=/Users/mehtabsingh/Desktop/EtherealLabs_MasterRepo/gateway-evidence
LOCK=$EV/locks/heavy-tests
RUNS=$EV/runs/$(date +%Y-%m-%d)
mkdir -p "$RUNS" "$EV/locks"
log=$RUNS/$label.log; sum=$RUNS/$label.summary
export PATH="$HOME/.local/node-v24.22.1-darwin-arm64/bin:$HOME/.local/bin:$PATH"
echo "queued $(date '+%H:%M:%S')" > "$sum"

# Queue for the lock. A lock is stale after 3 hours with no test process running.
while ! mkdir "$LOCK" 2>/dev/null; do
  if [ -f "$LOCK/owner" ] && [ -n "$(find "$LOCK/owner" -mmin +180 2>/dev/null)" ] \
     && ! pgrep -f 'jest|playwright' >/dev/null; then
    rm -rf "$LOCK"; continue
  fi
  sleep 30
done
echo "$label $workdir $(date) pid $$" > "$LOCK/owner"
trap 'rm -rf "$LOCK"' EXIT INT TERM HUP

# Start Docker (Colima) only if this run needs it.
if [[ "$*" =~ '(test:int|test:process|selectProjects.*(db|e2e)|compose|testcontainers|playwright|docker)' ]] \
   && ! colima status >/dev/null 2>&1; then
  colima start >/dev/null 2>&1 || echo "warning: colima start failed" >> "$sum"
fi

start=$(date +%s)
( cd "$workdir" && LEAN_LOCKED=1 "$@" ) > "$log" 2>&1
rc=$?
secs=$(( $(date +%s) - start ))

{
  echo "$label: exit $rc in ${secs}s; load $(uptime | sed 's/.*averages: //')"
  grep -E '(Test Suites|Tests|Snapshots):' "$log" | tail -8
  grep -E '^[[:space:]]*[0-9]+ (passed|failed|flaky|skipped)' "$log" | tail -4
  grep -E '^(FAIL |  ● |[[:space:]]+✘)' "$log" | sed 's/^[[:space:]]*//' | sort -u | head -8
  echo "full log: $log"
} > "$sum.tmp" && mv "$sum.tmp" "$sum"

# Stop Colima later if it goes idle (frees its memory).
nohup "$HOME/.claude/lean-system/tools/colima-idle.sh" >/dev/null 2>&1 &
exit $rc
