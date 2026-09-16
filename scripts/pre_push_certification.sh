#!/usr/bin/env bash

set -e

# Trap for failure
trap 'echo ""; echo "======================================"; echo "   PRE-PUSH CERTIFICATION: FAILED     "; echo "======================================"' ERR

echo "======================================"
echo "    PRE-PUSH CERTIFICATION SCRIPT     "
echo "======================================"
echo ""

echo "--------------------------------------"
echo "1. Checking for trailing whitespace & conflict markers (git diff --check)..."
echo "--------------------------------------"
git diff --check

ALL_CHANGED_FILES=$( { git diff --name-only origin/main...HEAD; git diff --name-only; git diff --cached --name-only; } 2>/dev/null | sort -u || true )

echo "--------------------------------------"
echo "2. Backend Ruff format & lint (Changed files only)..."
echo "--------------------------------------"
CHANGED_PY_FILES=$(echo "$ALL_CHANGED_FILES" | grep '\.py$' | while read -r f; do [ -f "$f" ] && echo "$f"; done || true)

if [ -n "$CHANGED_PY_FILES" ]; then
  echo "Running Ruff formatter check on changed Python files..."
  echo "$CHANGED_PY_FILES" | xargs uv run ruff format --check
  
  echo "Running Ruff linter on changed Python files..."
  echo "$CHANGED_PY_FILES" | xargs uv run ruff check
else
  echo "No Python files changed. Skipping Ruff format & lint."
fi

echo "--------------------------------------"
echo "3. Backend MyPy (Changed apps/api files only)..."
echo "--------------------------------------"
CHANGED_API_FILES=$(echo "$CHANGED_PY_FILES" | grep '^apps/api/' || true)

if [ -n "$CHANGED_API_FILES" ]; then
  echo "Running MyPy on changed apps/api files..."
  echo "$CHANGED_API_FILES" | xargs uv run mypy
else
  echo "No Python files changed in apps/api. Skipping MyPy."
fi

echo "--------------------------------------"
echo "4. Backend full pytest..."
echo "--------------------------------------"
PYTHONPATH=. uv run pytest --cov=hiron --cov-fail-under=80

echo "--------------------------------------"
echo "5. Frontend unit tests..."
echo "--------------------------------------"
pnpm --filter @hiron/web test:unit

echo "--------------------------------------"
echo "6. Frontend build..."
echo "--------------------------------------"
pnpm --filter @hiron/web build

echo ""
echo "======================================"
echo "   PRE-PUSH CERTIFICATION: PASSED     "
echo "======================================"

# Clear the trap so it doesn't print FAILED on success exit
trap - ERR
