#!/usr/bin/env bash
set -Eeuo pipefail

: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY required}"
: "${GITHUB_RUN_ID:?GITHUB_RUN_ID required}"
: "${CERTIFIED_HEAD:?CERTIFIED_HEAD required}"
BASE_BRANCH="${BASE_BRANCH:-candidate/document-factory-v1-20261005}"
DEFAULT_GITHUB_TOKEN="${GITHUB_TOKEN_FALLBACK:-}"
ASSIGN_TOKEN=""
ASSIGN_TOKEN_SOURCE=""
for pair in \
  "GH_AW_AGENT_TOKEN:${GH_AW_AGENT_TOKEN:-}" \
  "GH_AW_GITHUB_TOKEN:${GH_AW_GITHUB_TOKEN:-}" \
  "COPILOT_GITHUB_TOKEN:${COPILOT_GITHUB_TOKEN:-}"
do
  name="${pair%%:*}"
  value="${pair#*:}"
  if [ -n "$value" ]; then
    ASSIGN_TOKEN="$value"
    ASSIGN_TOKEN_SOURCE="$name"
    break
  fi
done
if [ -z "$ASSIGN_TOKEN" ]; then
  ASSIGN_TOKEN="$DEFAULT_GITHUB_TOKEN"
  ASSIGN_TOKEN_SOURCE="GITHUB_TOKEN_APP_FALLBACK"
fi
if [ -z "$ASSIGN_TOKEN" ]; then
  echo "COPILOT_ASSIGNMENT=HOLD"
  echo "AUTH_REASON=MISSING_USER_PAT"
  exit 78
fi
export GH_TOKEN="$ASSIGN_TOKEN"
MISSION_FILE="${MISSION_FILE:-document-factory/AUTONOMOUS_CONTINUATION.md}"

TITLE='[DOCUMENT-FACTORY][AUTONOMOUS-CONTINUATION] Finish governed skeleton'
QUERY="repo:$GITHUB_REPOSITORY is:issue is:open in:title AUTONOMOUS-CONTINUATION"

ISSUE_NUM="$(gh api -X GET search/issues -f q="$QUERY" --jq '.items[0].number // empty')"
if [ -z "$ISSUE_NUM" ]; then
  cp "$MISSION_FILE" /tmp/document-factory-issue-body.md
  {
    echo
    echo '## Dispatch evidence'
    echo "CERTIFIED_START_HEAD=$CERTIFIED_HEAD"
    echo "DISPATCH_RUN_ID=$GITHUB_RUN_ID"
    echo 'OPERATIONAL_AUTHORIZATION=DEVELOPMENT_CONTINUATION_ON_CANDIDATE_ONLY'
  } >> /tmp/document-factory-issue-body.md

  jq -n     --arg title "$TITLE"     --rawfile body /tmp/document-factory-issue-body.md     '{title:$title,body:$body}' > /tmp/document-factory-issue.json

  ISSUE_NUM="$(gh api --method POST     "repos/$GITHUB_REPOSITORY/issues"     --input /tmp/document-factory-issue.json     --jq '.number')"
fi

echo "CONTINUATION_ISSUE=$ISSUE_NUM"
echo "ASSIGN_TOKEN_SOURCE=$ASSIGN_TOKEN_SOURCE"

if gh api "repos/$GITHUB_REPOSITORY/issues/$ISSUE_NUM"   --jq '.assignees[].login' | grep -Fx 'copilot-swe-agent[bot]' >/dev/null 2>&1; then
  echo 'COPILOT_ASSIGNMENT=ALREADY_ACTIVE'
  exit 0
fi

INSTRUCTIONS='Read document-factory/AUTONOMOUS_CONTINUATION.md and execute it exactly. Base all work on candidate/document-factory-v1-20261005. Create your own working branch and one PR back to that candidate branch. Do not modify main, Louksna.md, PUAC2.md, recovery/**, scripts/assurance/**, or trust-root/document-factory-v1-20261005. Do not merge your PR. Preserve failures and use HOLD/UNKNOWN instead of inventing PASS. The existing PR validation must rerun producer, independent G23 and digest-bound G24.'

jq -n   --arg repo "$GITHUB_REPOSITORY"   --arg branch "$BASE_BRANCH"   --arg instructions "$INSTRUCTIONS"   '{assignees:["copilot-swe-agent[bot]"],agent_assignment:{target_repo:$repo,base_branch:$branch,custom_instructions:$instructions,custom_agent:"",model:""}}'   > /tmp/document-factory-agent-assignment.json

set +e
gh api --method POST   -H 'Accept: application/vnd.github+json'   -H 'X-GitHub-Api-Version: 2022-11-28'   "repos/$GITHUB_REPOSITORY/issues/$ISSUE_NUM/assignees"   --input /tmp/document-factory-agent-assignment.json   > /tmp/document-factory-agent-response.json   2> /tmp/document-factory-agent-error.txt
RC=$?
set -e

if [ "$RC" -ne 0 ]; then
  ERROR_TEXT="$(tr '\n' ' ' < /tmp/document-factory-agent-error.txt | head -c 1500)"
  gh issue comment "$ISSUE_NUM" --body "AUTONOMOUS_DISPATCH=HOLD

GitHub-native Copilot coding-agent assignment was not accepted by the repository/API. No substitute executor was used.

ASSIGN_TOKEN_SOURCE=$ASSIGN_TOKEN_SOURCE

CERTIFIED_HEAD=$CERTIFIED_HEAD
DISPATCH_RUN_ID=$GITHUB_RUN_ID
ERROR=$ERROR_TEXT"
  echo 'COPILOT_ASSIGNMENT=HOLD'
  exit 78
fi

gh issue comment "$ISSUE_NUM" --body "AUTONOMOUS_DISPATCH=ACTIVE

GitHub Copilot coding agent is assigned with base branch `$BASE_BRANCH`. It must work in its own branch and open a PR back to the candidate. No main/trust-root mutation and no auto-merge are authorized.

CERTIFIED_HEAD=$CERTIFIED_HEAD
DISPATCH_RUN_ID=$GITHUB_RUN_ID"

echo 'COPILOT_ASSIGNMENT=ACTIVE'
