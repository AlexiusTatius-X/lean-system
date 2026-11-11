#!/bin/zsh
# Stops Colima after 30 idle minutes: no containers, no locked run, nothing queued.
PID=/tmp/lean-colima-idle.pid
[ -f "$PID" ] && kill -0 "$(cat $PID)" 2>/dev/null && exit 0
echo $$ > "$PID"; trap 'rm -f "$PID"' EXIT
LOCK=/Users/mehtabsingh/Desktop/EtherealLabs_MasterRepo/gateway-evidence/locks/heavy-tests
idle=0
while [ $idle -lt 30 ]; do
  sleep 60
  colima status >/dev/null 2>&1 || exit 0
  if [ -d "$LOCK" ] || pgrep -f 'run-locked.sh' >/dev/null || [ -n "$(docker ps -q 2>/dev/null)" ]; then
    idle=0
  else
    idle=$((idle + 1))
  fi
done
colima stop >/dev/null 2>&1
