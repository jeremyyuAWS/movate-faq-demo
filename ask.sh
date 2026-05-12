#!/usr/bin/env bash
# ask.sh — bash equivalent of ask.py. 5 lines of orchestration.
#
# Usage:
#   ./ask.sh "How do I scaffold an agent?"
set -euo pipefail

QUESTION="$*"
if [ -z "$QUESTION" ]; then
    echo "usage: $0 <question>" >&2
    exit 1
fi

# 1. Manager classifies the question
LANE=$(movate run agents/manager "{\"question\": \"$QUESTION\"}" -o json 2>/dev/null \
       | jq -r '.data.classification')

echo "→ routed to: expert-$LANE" >&2

# 2. Right expert answers
movate run "agents/expert-$LANE" "{\"question\": \"$QUESTION\"}" -o json \
    | jq '.data'
