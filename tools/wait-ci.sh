#!/bin/zsh
# Waits for a PR's checks with no model watching, then writes a short summary.
# Usage: wait-ci.sh <owner/repo> <pr> ; run it in the background and end the turn.
set -u
repo=$1; pr=$2
RUNS=/Users/mehtabsingh/Desktop/EtherealLabs_MasterRepo/gateway-evidence/runs/$(date +%Y-%m-%d)
mkdir -p "$RUNS"; sum=$RUNS/ci-${repo##*/}-$pr.summary
sleep 20
gh pr checks "$pr" --repo "$repo" --watch --interval 60 >/dev/null 2>&1
rc=$?
{
  echo "PR #$pr ($repo): checks finished, exit $rc"
  gh pr checks "$pr" --repo "$repo" 2>/dev/null | cut -f1,2 | head -15
  failed=$(gh pr checks "$pr" --repo "$repo" --json name,state,link --jq '.[] | select(.state=="FAILURE") | .link' 2>/dev/null | head -1)
  if [ -n "$failed" ]; then
    run=$(echo "$failed" | sed -E 's#.*/runs/([0-9]+)/job/.*#\1#')
    echo "first failing run: $run"
    gh run view "$run" --repo "$repo" --log-failed 2>/dev/null | grep -E '● |FAIL |Error:|✘' | cut -c1-200 | sort -u | head -8
  fi
} > "$sum"
echo "$sum"
exit $rc
