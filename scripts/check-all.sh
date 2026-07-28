#!/usr/bin/env bash
# ==============================================================================
# HIRON PLATFORM MONOREPO QUALITY GATE SCRIPT
# ==============================================================================
# Phase 0 Quality Gate: Validates configuration files, formatting, and file syntax.

set -euo pipefail

echo "=========================================="
echo " Running Hiron Monorepo Quality Gate Checks"
echo "=========================================="

echo "[1/2] Checking Root Formatting (Prettier)..."
npx prettier --check "**/*.{json,yaml,yml,md}"

echo "[2/2] Checking Infrastructure & Docker Configurations..."
test -f pyproject.toml
test -f package.json
test -f tsconfig.base.json
test -f docker-compose.yml
echo "✓ Root infrastructure configuration files present."

echo ""
echo "------------------------------------------------------------------"
echo "ℹ️  NOTE: Application-level static checks (MyPy strict mode, Pytest,"
echo "   TypeScript compiler, ESLint) will be enabled in Phase 1+ as"
echo "   application source code and dependencies are introduced."
echo "------------------------------------------------------------------"

echo "=========================================="
echo " Phase 0 quality gate checks passed!"
echo "=========================================="
